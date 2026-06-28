"""HTTP integration tests for server.py (zero third-party deps).

These boot the REAL ThreadingHTTPServer on an ephemeral port (in a daemon thread)
and exercise the request handlers end-to-end with stdlib urllib — covering routing,
/config redaction, the /memory/* lifecycle (save/list/read/search), /sessions and
/chunk-cache round-trips, input-size limits, and path-traversal guards.

Run from the project root with:
    .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'

No external test framework or HTTP client — stdlib `unittest` + `urllib` only, per
the project's zero-new-dependency philosophy. We import server.py and start its
server ourselves (importing must not start it — run() is guarded by __main__).
"""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402


def _request(method, url, body=None, headers=None):
    """Make an HTTP request and return (status, parsed_json_or_text)."""
    data = None
    hdrs = headers or {}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        hdrs.setdefault('Content-Type', 'application/json')
    req = Request(url, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req) as resp:
            raw = resp.read().decode('utf-8')
            status = resp.status
    except HTTPError as err:
        raw = err.read().decode('utf-8')
        status = err.code
    except (ConnectionResetError, BrokenPipeError):
        # The server rejected an oversized/invalid request before reading the
        # full body and closed the connection. Re-raise so size-limit tests can
        # treat it as the "refused" outcome they expect.
        raise
    except URLError as err:
        # urllib wraps a broken pipe (server closed the socket after a 413) in a
        # URLError; surface the underlying connection error for size-limit tests.
        if isinstance(err.reason, (ConnectionResetError, BrokenPipeError)):
            raise err.reason
        raise
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


class ServerHTTPTestBase(unittest.TestCase):
    """Boots the real server on an ephemeral port for the duration of the class.

    Each test class points CONFIG/SESSIONS_DIR/CACHE_DIR/HISTORY_FILE at temp dirs
    so tests never touch the developer's real vault or runtime files.
    """

    @classmethod
    def setUpClass(cls):
        cls._saved_config = dict(server.CONFIG)
        cls._saved_sessions = server.SESSIONS_DIR
        cls._saved_cache = server.CACHE_DIR
        cls._saved_history = server.HISTORY_FILE
        cls._saved_raw_responses = server.RAW_RESPONSES_DIR

        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        # Redirect all filesystem state into the temp dir.
        server.SESSIONS_DIR = tmp / 'sessions'
        server.SESSIONS_DIR.mkdir()
        server.CACHE_DIR = tmp / 'cache'
        server.CACHE_DIR.mkdir()
        server.RAW_RESPONSES_DIR = tmp / 'raw_responses'
        server.RAW_RESPONSES_DIR.mkdir()
        server.HISTORY_FILE = tmp / 'chat_history.json'
        # A real, empty vault so has_obsidian works for memory tests.
        cls._vault = tmp / 'vault'
        cls._vault.mkdir()
        server.CONFIG = {
            'api_key': 'SECRET-should-never-leak',
            'base_url': 'https://example.invalid',
            'default_model': 'test-model',
            'default_system_prompt': 'sys',
            'context7_api_key': 'CTX-SECRET',
            'context7_base_url': 'https://ctx.invalid',
            'context7_path': '/v1/context',
            'context7_method': 'GET',
            'obsidian_vault_path': str(cls._vault),
            'obsidian_memory_subdir': 'USAi',
        }

        cls._httpd = ThreadingHTTPServer(('127.0.0.1', 0),
                                         server.EnvConfigHTTPRequestHandler)
        cls.port = cls._httpd.server_address[1]
        cls._thread = threading.Thread(target=cls._httpd.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._httpd.shutdown()
        cls._httpd.server_close()
        cls._tmp.cleanup()
        server.CONFIG = cls._saved_config
        server.SESSIONS_DIR = cls._saved_sessions
        server.CACHE_DIR = cls._saved_cache
        server.HISTORY_FILE = cls._saved_history
        server.RAW_RESPONSES_DIR = cls._saved_raw_responses

    def url(self, path):
        return f'http://127.0.0.1:{self.port}{path}'


class ConfigEndpointTests(ServerHTTPTestBase):
    def test_config_returns_non_secret_fields_and_flags(self):
        status, body = _request('GET', self.url('/config'))
        self.assertEqual(status, 200)
        self.assertEqual(body['base_url'], 'https://example.invalid')
        self.assertEqual(body['default_model'], 'test-model')
        self.assertTrue(body['has_api_key'])
        self.assertTrue(body['has_context7'])
        self.assertTrue(body['has_obsidian'])

    def test_config_never_leaks_secrets(self):
        status, body = _request('GET', self.url('/config'))
        self.assertEqual(status, 200)
        # The raw response must not contain either secret anywhere.
        raw = json.dumps(body)
        self.assertNotIn('SECRET-should-never-leak', raw)
        self.assertNotIn('CTX-SECRET', raw)
        self.assertNotIn('api_key', body)
        self.assertNotIn('context7_api_key', body)

    def test_config_includes_tier_model_fields(self):
        """GET /config exposes tier_*_model fields so the client TIER_MAP can
        pick up operator overrides set via TIER_HIGH/MEDIUM/LOW_MODEL env vars.
        When unset (empty), the fields are still present so the client knows
        no override is in force and falls back to its hardcoded verified defaults.
        (#19 fix — these keys were missing from _get_config before this patch.)
        """
        status, body = _request('GET', self.url('/config'))
        self.assertEqual(status, 200)
        self.assertIn('tier_high_model',   body)
        self.assertIn('tier_medium_model', body)
        self.assertIn('tier_low_model',    body)
        # Default test server has no TIER_*_MODEL set — keys must be empty strings.
        self.assertEqual(body['tier_high_model'],   '')
        self.assertEqual(body['tier_medium_model'], '')


class MemoryLifecycleTests(ServerHTTPTestBase):
    def test_save_then_list_read_and_search(self):
        # Save
        status, saved = _request('POST', self.url('/memory/save'), {
            'title': 'Pizza preference',
            'content': 'The user loves pineapple on pizza.',
            'tags': ['food', 'preference'],
        })
        self.assertEqual(status, 200)
        self.assertTrue(saved['ok'])
        path = saved['path']
        self.assertTrue(path.endswith('.md'))

        # List shows it
        status, listing = _request('GET', self.url('/memory/list'))
        self.assertEqual(status, 200)
        self.assertIn(path, [i['path'] for i in listing['items']])

        # Read returns the content with frontmatter
        status, read = _request('GET', self.url(f'/memory/read?path={path}'))
        self.assertEqual(status, 200)
        self.assertIn('pineapple', read['content'])
        self.assertIn('usai-memory', read['content'])  # auto-tagged

        # Search finds it by keyword
        status, results = _request('GET', self.url('/memory/search?q=pineapple&k=5'))
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(results['results']), 1)
        self.assertIn(path, [r['path'] for r in results['results']])

    def test_save_requires_content(self):
        status, body = _request('POST', self.url('/memory/save'),
                                {'title': 'empty', 'content': '   '})
        self.assertEqual(status, 400)

    def test_save_accepts_tags_as_string_and_auto_tags(self):
        status, saved = _request('POST', self.url('/memory/save'), {
            'title': 'Single tag note',
            'content': 'body text here',
            'tags': 'mood',  # a bare string, not a list
        })
        self.assertEqual(status, 200)
        status, read = _request('GET', self.url(f"/memory/read?path={saved['path']}"))
        self.assertIn('mood', read['content'])
        self.assertIn('usai-memory', read['content'])  # auto-added

    def test_save_untitled_when_title_missing(self):
        status, saved = _request('POST', self.url('/memory/save'),
                                 {'content': 'no title given'})
        self.assertEqual(status, 200)
        self.assertEqual(saved['title'], 'Untitled memory')

    def test_read_rejects_path_traversal(self):
        # Attempt to escape the memory folder.
        status, body = _request('GET', self.url('/memory/read?path=../../../../etc/passwd'))
        self.assertEqual(status, 404)

    def test_save_rejects_oversized_payload(self):
        # /memory/save caps the body at 5 MB. The server rejects before reading
        # the whole body, so a connection reset / broken pipe is also acceptable
        # evidence that the oversized payload was refused.
        try:
            status, _ = _request('POST', self.url('/memory/save'),
                                 {'title': 'big', 'content': 'x' * (5 * 1024 * 1024 + 10)})
            self.assertEqual(status, 413)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def test_search_missing_query_is_400(self):
        status, _ = _request('GET', self.url('/memory/search?q=&k=5'))
        self.assertEqual(status, 400)

    def test_search_clamps_k_to_valid_range(self):
        # Non-numeric k falls back to default without error.
        status, body = _request('GET', self.url('/memory/search?q=pizza&k=notanumber'))
        self.assertEqual(status, 200)
        self.assertIn('results', body)


class SessionsAndCacheTests(ServerHTTPTestBase):
    def test_session_save_list_delete_roundtrip(self):
        status, saved = _request('POST', self.url('/sessions'), {
            'id': 'session_test_1',
            'title': 'Test chat',
            'turns': [{'role': 'user', 'content': 'hi'}],
        })
        self.assertEqual(status, 200)
        self.assertEqual(saved['id'], 'session_test_1')

        status, listing = _request('GET', self.url('/sessions'))
        self.assertEqual(status, 200)
        self.assertIn('session_test_1', [s['id'] for s in listing])

        status, _ = _request('DELETE', self.url('/sessions?id=session_test_1'))
        self.assertEqual(status, 200)
        status, listing = _request('GET', self.url('/sessions'))
        self.assertNotIn('session_test_1', [s['id'] for s in listing])

    def test_session_save_generates_id_when_omitted(self):
        status, saved = _request('POST', self.url('/sessions'),
                                 {'title': 'No id', 'turns': []})
        self.assertEqual(status, 200)
        self.assertTrue(saved['id'].startswith('session_'))

    def test_delete_session_without_id_is_ok_noop(self):
        # DELETE /sessions with no id is a no-op that still returns 200.
        status, _ = _request('DELETE', self.url('/sessions'))
        self.assertEqual(status, 200)

    def test_get_unknown_session_is_404(self):
        status, _ = _request('GET', self.url('/sessions?id=nope_12345'))
        self.assertEqual(status, 404)

    def test_chunk_cache_roundtrip_and_traversal_safe(self):
        status, saved = _request('POST', self.url('/chunk-cache'), {
            'filename': '../../evil',  # must be sanitized to a basename
            'chunks': [{'text': 'hello'}],
        })
        self.assertEqual(status, 200)
        # Saved under a basename only — no traversal.
        self.assertNotIn('/', saved['savedAs'])
        self.assertNotIn('..', saved['savedAs'])


class InputLimitTests(ServerHTTPTestBase):
    def test_log_entry_too_large_is_rejected(self):
        # /logs caps body at 64 KB. The server replies 413 BEFORE reading the
        # oversized body, so the connection may reset as urllib reads the error
        # body — either way, a 413 (or the reset that follows it) proves the limit
        # is enforced and the big payload was refused.
        big = {'level': 'info', 'component': 'x', 'message': 'm',
               'details': {'d': 'a' * 70000}}
        try:
            status, _ = _request('POST', self.url('/logs'), big)
            self.assertEqual(status, 413)
        except ConnectionResetError:
            # Server rejected (413) and reset before we could read the body —
            # this still confirms the oversized payload was not accepted.
            pass


class RoutingTests(ServerHTTPTestBase):
    def test_unknown_post_route_is_404(self):
        status, _ = _request('POST', self.url('/no-such-endpoint'), {})
        self.assertEqual(status, 404)

    def test_unknown_delete_route_is_404(self):
        status, _ = _request('DELETE', self.url('/no-such-endpoint'))
        self.assertEqual(status, 404)


class RawResponsesIntegrationTests(ServerHTTPTestBase):
    """RC-1…RC-4: integration tests for the raw-response capture feature."""

    def _enable_capture(self):
        """Helper — enable capture and return original value for teardown."""
        orig = server.CONFIG.get('capture_raw_responses')
        server.CONFIG['capture_raw_responses'] = True
        server.CONFIG['raw_responses_max'] = 200
        return orig

    def _disable_capture(self, orig):
        if orig is None:
            server.CONFIG.pop('capture_raw_responses', None)
        else:
            server.CONFIG['capture_raw_responses'] = orig

    def test_rc1_capture_on_creates_file(self):
        """RC-1: calling _capture_raw_response writes exactly one file with correct metadata."""
        raw_dir = server.RAW_RESPONSES_DIR
        # Clear any pre-existing files in the temp raw dir.
        for p in raw_dir.glob('*.json'):
            p.unlink()
        orig = self._enable_capture()
        try:
            server._capture_raw_response(
                {'timestamp': '2026-06-27T10:00:00', 'method': 'POST',
                 'path': '/api/v1/chat/completions', 'status': 200, 'model': 'gpt-4'},
                b'{"id":"chat-abc","choices":[{"message":{"content":"hello"}}],"usage":{"total_tokens":5}}'
            )
            files = list(raw_dir.glob('*.json'))
            self.assertEqual(len(files), 1, 'Exactly one capture file should be written')
            record = json.loads(files[0].read_text(encoding='utf-8'))
            self.assertEqual(record['status'], 200)
            self.assertEqual(record['path'], '/api/v1/chat/completions')
            self.assertEqual(record['model'], 'gpt-4')
            self.assertFalse(record['streamed'])
            self.assertIn('id', record['raw'])
            # Auth key must NOT appear anywhere.
            content = json.dumps(record)
            self.assertNotIn('SECRET-should-never-leak', content)
        finally:
            self._disable_capture(orig)

    def test_rc2_list_and_read_and_delete_single(self):
        """RC-2: GET /raw-responses lists; GET ?id= reads; DELETE ?id= removes."""
        raw_dir = server.RAW_RESPONSES_DIR
        for p in raw_dir.glob('*.json'):
            p.unlink()
        orig = self._enable_capture()
        try:
            server._capture_raw_response(
                {'timestamp': '2026-06-27T10:01:00', 'method': 'POST',
                 'path': '/api/v1/chat/completions', 'status': 201, 'model': 'gpt-3.5'},
                b'{"choices":[{"message":{"content":"test"}}]}'
            )
            # List — no 'raw' field in listing.
            status, listing = _request('GET', self.url('/raw-responses'))
            self.assertEqual(status, 200)
            self.assertEqual(len(listing), 1)
            self.assertNotIn('raw', listing[0])
            rec_id = listing[0]['id']
            # Read full record.
            status, full = _request('GET', self.url(f'/raw-responses?id={rec_id}'))
            self.assertEqual(status, 200)
            self.assertIn('raw', full)
            self.assertEqual(full['status'], 201)
            # Delete single record.
            status, _ = _request('DELETE', self.url(f'/raw-responses?id={rec_id}'))
            self.assertEqual(status, 200)
            status, _ = _request('GET', self.url(f'/raw-responses?id={rec_id}'))
            self.assertEqual(status, 404)
        finally:
            self._disable_capture(orig)

    def test_rc3_delete_all_clears_store(self):
        """RC-3: DELETE /raw-responses (no id) clears all files."""
        raw_dir = server.RAW_RESPONSES_DIR
        for p in raw_dir.glob('*.json'):
            p.unlink()
        orig = self._enable_capture()
        try:
            for i in range(3):
                server._capture_raw_response(
                    {'timestamp': f'2026-06-27T10:0{i}:00', 'method': 'POST',
                     'path': '/api/test', 'status': 200, 'model': None},
                    b'{}'
                )
            status, listing = _request('GET', self.url('/raw-responses'))
            self.assertEqual(len(listing), 3)
            status, _ = _request('DELETE', self.url('/raw-responses'))
            self.assertEqual(status, 200)
            status, listing = _request('GET', self.url('/raw-responses'))
            self.assertEqual(listing, [])
        finally:
            self._disable_capture(orig)

    def test_rc4_config_has_raw_capture_boolean(self):
        """RC-4: /config returns has_raw_capture boolean."""
        # Default: off in test setup (capture_raw_responses not set).
        status, body = _request('GET', self.url('/config'))
        self.assertEqual(status, 200)
        self.assertIn('has_raw_capture', body)
        self.assertFalse(body['has_raw_capture'])
        # Enable and re-check.
        orig = self._enable_capture()
        try:
            status, body = _request('GET', self.url('/config'))
            self.assertTrue(body['has_raw_capture'])
        finally:
            self._disable_capture(orig)


if __name__ == '__main__':
    unittest.main()
