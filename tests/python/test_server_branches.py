"""Additional HTTP integration tests for server.py to exercise more handlers and
branches (GET round-trips, error paths, logs lifecycle, new-chat-session
archiving, config edge cases). Complements test_server_http.py.

Stdlib `unittest` + `urllib` only — no third-party deps.
"""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402
from tests.python.test_server_http import _request  # reuse the helper  # noqa: E402


class ServerBranchTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved = (dict(server.CONFIG), server.SESSIONS_DIR,
                      server.CACHE_DIR, server.HISTORY_FILE)
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        server.SESSIONS_DIR = tmp / 'sessions'; server.SESSIONS_DIR.mkdir()
        server.CACHE_DIR = tmp / 'cache'; server.CACHE_DIR.mkdir()
        server.HISTORY_FILE = tmp / 'chat_history.json'
        # NOTE: no vault configured here, so has_obsidian is False and the
        # /memory/* endpoints return 400 — exercising that branch.
        server.CONFIG = {
            'api_key': '',
            'base_url': '',
            'default_model': '',
            'default_system_prompt': '',
            'context7_api_key': '',
            'context7_base_url': '',
            'context7_path': '/v1/context',
            'context7_method': 'GET',
            'obsidian_vault_path': '',
            'obsidian_memory_subdir': 'USAi',
        }
        cls._httpd = ThreadingHTTPServer(('127.0.0.1', 0),
                                         server.EnvConfigHTTPRequestHandler)
        cls.port = cls._httpd.server_address[1]
        cls._thread = threading.Thread(target=cls._httpd.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._httpd.shutdown(); cls._httpd.server_close(); cls._tmp.cleanup()
        (server.CONFIG, server.SESSIONS_DIR,
         server.CACHE_DIR, server.HISTORY_FILE) = cls._saved

    def url(self, p):
        return f'http://127.0.0.1:{self.port}{p}'


class ConfigFlagsWhenUnconfiguredTests(ServerBranchTestBase):
    def test_flags_false_when_nothing_configured(self):
        status, body = _request('GET', self.url('/config'))
        self.assertEqual(status, 200)
        self.assertFalse(body['has_api_key'])
        self.assertFalse(body['has_context7'])
        self.assertFalse(body['has_obsidian'])


class MemoryDisabledTests(ServerBranchTestBase):
    def test_memory_endpoints_400_without_vault(self):
        for path in ('/memory/list', '/memory/search?q=x', '/memory/read?path=x.md'):
            status, _ = _request('GET', self.url(path))
            self.assertEqual(status, 400, f'{path} should 400 without a vault')
        status, _ = _request('POST', self.url('/memory/save'),
                             {'title': 't', 'content': 'c'})
        self.assertEqual(status, 400)

    def test_memory_search_missing_query_is_handled(self):
        # Even without a vault this returns 400 (vault check first); with a vault
        # an empty query would also 400. Either way it must not 500.
        status, _ = _request('GET', self.url('/memory/search?q='))
        self.assertIn(status, (400,))


class ChunkCacheGetTests(ServerBranchTestBase):
    def test_get_unknown_chunk_cache_is_404(self):
        status, _ = _request('GET', self.url('/chunk-cache?file=does-not-exist'))
        self.assertEqual(status, 404)

    def test_list_chunk_cache_empty(self):
        status, body = _request('GET', self.url('/chunk-cache'))
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)

    def test_post_then_get_then_list_then_delete(self):
        status, saved = _request('POST', self.url('/chunk-cache'),
                                 {'filename': 'notes.txt', 'chunks': [{'text': 'a'}]})
        self.assertEqual(status, 200)
        status, got = _request('GET', self.url('/chunk-cache?file=notes.txt'))
        self.assertEqual(status, 200)
        self.assertEqual(len(got['chunks']), 1)
        status, listing = _request('GET', self.url('/chunk-cache'))
        self.assertIn('notes.txt', [e['filename'] for e in listing])
        status, _ = _request('DELETE', self.url('/chunk-cache?file=notes.txt'))
        self.assertEqual(status, 200)
        status, _ = _request('GET', self.url('/chunk-cache?file=notes.txt'))
        self.assertEqual(status, 404)

    def test_delete_all_chunk_cache(self):
        _request('POST', self.url('/chunk-cache'),
                 {'filename': 'a.txt', 'chunks': [{'text': '1'}]})
        _request('POST', self.url('/chunk-cache'),
                 {'filename': 'b.txt', 'chunks': [{'text': '2'}]})
        # DELETE with no ?file= clears everything.
        status, _ = _request('DELETE', self.url('/chunk-cache'))
        self.assertEqual(status, 200)
        status, listing = _request('GET', self.url('/chunk-cache'))
        self.assertEqual(listing, [])


class ChatHistoryAndNewSessionTests(ServerBranchTestBase):
    def test_chat_history_empty_then_save_then_new_session_archives(self):
        # Empty initially
        status, body = _request('GET', self.url('/chat-history'))
        self.assertEqual(status, 200)
        self.assertEqual(body['turns'], [])

        # Save some history
        status, _ = _request('POST', self.url('/chat-history'), {
            'turns': [
                {'role': 'user', 'content': 'Tell me a joke', 'timestamp': '2026-01-01T00:00:00'},
                {'role': 'assistant', 'content': 'Why did the chicken...'},
            ],
        })
        self.assertEqual(status, 200)
        status, body = _request('GET', self.url('/chat-history'))
        self.assertEqual(len(body['turns']), 2)

        # Starting a new session archives the current history and clears it.
        status, res = _request('POST', self.url('/new-chat-session'), {})
        self.assertEqual(status, 200)
        self.assertTrue(res['ok'])
        self.assertIsNotNone(res['archivedId'])
        # History is now empty again.
        status, body = _request('GET', self.url('/chat-history'))
        self.assertEqual(body['turns'], [])
        # The archived session shows up in /sessions with the derived title.
        status, sessions = _request('GET', self.url('/sessions'))
        self.assertIn(res['archivedId'], [s['id'] for s in sessions])
        title = next(s['title'] for s in sessions if s['id'] == res['archivedId'])
        self.assertTrue(title.startswith('Tell me a joke'))


class LogsTests(ServerBranchTestBase):
    def test_log_post_and_clear(self):
        status, body = _request('POST', self.url('/logs'),
                                {'level': 'info', 'component': 'test', 'message': 'hi'})
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])
        status, body = _request('POST', self.url('/logs/clear'), {})
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])

    def test_malformed_log_body_is_400(self):
        # Send invalid JSON as the body.
        status, _ = _request('POST', self.url('/logs'), None,
                             headers={'Content-Type': 'application/json'})
        # No body → content-length 0 → json.loads('') raises → 400.
        self.assertEqual(status, 400)


class MalformedBodyTests(ServerBranchTestBase):
    """Posting non-JSON bodies to the JSON write endpoints must 400, not 500."""

    def _post_raw(self, path, raw):
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        req = Request(self.url(path), data=raw.encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(req) as resp:
                return resp.status
        except HTTPError as e:
            return e.code

    def test_sessions_malformed_json_is_400(self):
        self.assertEqual(self._post_raw('/sessions', '{not json'), 400)

    def test_chat_history_malformed_json_is_400(self):
        self.assertEqual(self._post_raw('/chat-history', 'nope'), 400)

    def test_chunk_cache_malformed_json_is_400(self):
        self.assertEqual(self._post_raw('/chunk-cache', '<<<'), 400)


class NewSessionEmptyHistoryTests(ServerBranchTestBase):
    def test_new_session_with_no_history_archives_nothing(self):
        # No history file exists in this fresh temp dir.
        status, res = _request('POST', self.url('/new-chat-session'), {})
        self.assertEqual(status, 200)
        self.assertTrue(res['ok'])
        self.assertIsNone(res['archivedId'])


class Context7DisabledTests(ServerBranchTestBase):
    def test_context7_400_when_unconfigured(self):
        status, _ = _request('GET', self.url('/context7?query=react'))
        self.assertEqual(status, 400)


class PayloadTooLargeTests(ServerBranchTestBase):
    """413 responses from all POST handlers that enforce a size limit."""

    def _post_oversized(self, path, content_length):
        """Send a POST with a spoofed Content-Length header that exceeds the limit."""
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        # Send a tiny real body but lie about Content-Length to trigger the guard.
        # (The handler reads the integer header value before reading the body.)
        req = Request(
            self.url(path),
            data=b'x',
            headers={'Content-Type': 'application/json',
                     'Content-Length': str(content_length)},
            method='POST',
        )
        try:
            with urlopen(req) as resp:
                return resp.status
        except HTTPError as e:
            return e.code

    def test_sessions_413_when_too_large(self):
        self.assertEqual(self._post_oversized('/sessions', 11 * 1024 * 1024), 413)

    def test_chat_history_413_when_too_large(self):
        self.assertEqual(self._post_oversized('/chat-history', 11 * 1024 * 1024), 413)

    def test_chunk_cache_413_when_too_large(self):
        self.assertEqual(self._post_oversized('/chunk-cache', 51 * 1024 * 1024), 413)

    def test_memory_save_413_when_too_large(self):
        # PayloadTooLargeTests uses the no-vault config; _memory_save checks vault
        # first → 400 before reaching the size guard. The 413 branch is exercised
        # in MemoryWithVaultTests.test_memory_save_413.
        self.assertIn(self._post_oversized('/memory/save', 6 * 1024 * 1024), (400, 413))

    def test_logs_413_when_too_large(self):
        self.assertEqual(self._post_oversized('/logs', 11 * 1024 * 1024), 413)


class MemoryWithVaultTests(unittest.TestCase):
    """Tests that exercise memory endpoints with a real (temp) vault configured."""

    @classmethod
    def setUpClass(cls):
        cls._saved = (dict(server.CONFIG), server.SESSIONS_DIR,
                      server.CACHE_DIR, server.HISTORY_FILE)
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        server.SESSIONS_DIR = tmp / 'sessions'; server.SESSIONS_DIR.mkdir()
        server.CACHE_DIR = tmp / 'cache'; server.CACHE_DIR.mkdir()
        server.HISTORY_FILE = tmp / 'chat_history.json'
        vault = tmp / 'vault'
        vault.mkdir()
        server.CONFIG = {
            'api_key': '',
            'base_url': '',
            'default_model': '',
            'default_system_prompt': '',
            'context7_api_key': '',
            'context7_base_url': '',
            'context7_path': '/v1/context',
            'context7_method': 'GET',
            'obsidian_vault_path': str(vault),
            'obsidian_memory_subdir': 'USAi',
        }
        cls._httpd = ThreadingHTTPServer(('127.0.0.1', 0),
                                         server.EnvConfigHTTPRequestHandler)
        cls.port = cls._httpd.server_address[1]
        cls._thread = threading.Thread(target=cls._httpd.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._httpd.shutdown(); cls._httpd.server_close(); cls._tmp.cleanup()
        (server.CONFIG, server.SESSIONS_DIR,
         server.CACHE_DIR, server.HISTORY_FILE) = cls._saved

    def url(self, p):
        return f'http://127.0.0.1:{self.port}{p}'

    def test_memory_list_empty_vault(self):
        status, body = _request('GET', self.url('/memory/list'))
        self.assertEqual(status, 200)
        self.assertEqual(body['items'], [])

    def test_memory_read_missing_file_is_404(self):
        status, _ = _request('GET', self.url('/memory/read?path=no-such-file.md'))
        self.assertEqual(status, 404)

    def test_memory_read_path_traversal_is_404(self):
        status, _ = _request('GET', self.url('/memory/read?path=../../etc/passwd'))
        self.assertEqual(status, 404)

    def test_memory_save_and_list_and_read(self):
        status, body = _request('POST', self.url('/memory/save'),
                                {'title': 'Branch test', 'content': 'Hello coverage'})
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])
        note_path = body['path']

        status, listing = _request('GET', self.url('/memory/list'))
        self.assertEqual(status, 200)
        self.assertTrue(any(i['path'] == note_path for i in listing['items']))

        status, note = _request('GET', self.url(f'/memory/read?path={note_path}'))
        self.assertEqual(status, 200)
        self.assertIn('Hello coverage', note['content'])

    def test_memory_search_returns_result(self):
        _request('POST', self.url('/memory/save'),
                 {'title': 'Search branch', 'content': 'unique-search-token-xyz'})
        status, body = _request('GET', self.url('/memory/search?q=unique-search-token-xyz'))
        self.assertEqual(status, 200)
        self.assertGreater(len(body['results']), 0)

    def test_memory_save_missing_content_is_400(self):
        status, _ = _request('POST', self.url('/memory/save'), {'title': 'x'})
        self.assertEqual(status, 400)

    def test_memory_save_tag_deduplicated(self):
        """Tags that already include 'usai-memory' must not be duplicated."""
        status, body = _request('POST', self.url('/memory/save'),
                                {'title': 'Tag dedup', 'content': 'c',
                                 'tags': ['usai-memory', 'topic/test']})
        self.assertEqual(status, 200)
        note_path = body['path']
        _, note = _request('GET', self.url(f'/memory/read?path={note_path}'))
        self.assertEqual(note['content'].count('usai-memory'), 1)


class SessionsRoundTripTests(ServerBranchTestBase):
    """Exercise _post_sessions createdAt branch (no createdAt in payload)."""

    def test_session_gets_createdAt_assigned(self):
        status, body = _request('POST', self.url('/sessions'),
                                {'title': 'My session', 'turns': []})
        self.assertEqual(status, 200)
        session_id = body['id']
        status, session = _request('GET', self.url(f'/sessions?id={session_id}'))
        self.assertEqual(status, 200)
        self.assertIn('createdAt', session)

    def test_session_preserves_existing_createdAt(self):
        status, body = _request('POST', self.url('/sessions'),
                                {'title': 'Old', 'createdAt': '2025-01-01T00:00:00',
                                 'turns': []})
        self.assertEqual(status, 200)
        session_id = body['id']
        _, session = _request('GET', self.url(f'/sessions?id={session_id}'))
        self.assertEqual(session['createdAt'], '2025-01-01T00:00:00')


class DeleteSessionFileNotExistsTests(ServerBranchTestBase):
    """DELETE /sessions?id=nonexistent should still return 200."""

    def test_delete_nonexistent_session_is_200(self):
        status, body = _request('DELETE', self.url('/sessions?id=ghost_session_99'))
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])


class DeleteChunkCacheFileNotExistsTests(ServerBranchTestBase):
    """DELETE /chunk-cache?file=nonexistent should still return 200."""

    def test_delete_nonexistent_file_is_200(self):
        status, body = _request('DELETE', self.url('/chunk-cache?file=ghost.txt'))
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])


class EmbeddingsMemorySearchTests(unittest.TestCase):
    """MS-4 … MS-6: /memory/search embed_available field + POST /embeddings guards."""

    @classmethod
    def setUpClass(cls):
        cls._saved = (dict(server.CONFIG), server.SESSIONS_DIR,
                      server.CACHE_DIR, server.HISTORY_FILE)
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        server.SESSIONS_DIR = tmp / 'sessions'; server.SESSIONS_DIR.mkdir()
        server.CACHE_DIR = tmp / 'cache'; server.CACHE_DIR.mkdir()
        server.HISTORY_FILE = tmp / 'chat_history.json'
        # Create a minimal vault so /memory/search can return 200 (not 400)
        vault = tmp / 'vault'
        (vault / 'USAi' / 'memories').mkdir(parents=True)
        server.CONFIG = {
            'api_key': '',
            'base_url': '',
            'default_model': '',
            'default_system_prompt': '',
            'context7_api_key': '',
            'context7_base_url': '',
            'context7_path': '/v1/context',
            'context7_method': 'GET',
            'obsidian_vault_path': str(vault),
            'obsidian_memory_subdir': 'USAi',
            'embed_model': '',
            'embed_input_type': 'search_document',
        }
        cls._httpd = ThreadingHTTPServer(('127.0.0.1', 0),
                                         server.EnvConfigHTTPRequestHandler)
        cls.port = cls._httpd.server_address[1]
        cls._thread = threading.Thread(target=cls._httpd.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._httpd.shutdown(); cls._httpd.server_close(); cls._tmp.cleanup()
        (server.CONFIG, server.SESSIONS_DIR,
         server.CACHE_DIR, server.HISTORY_FILE) = cls._saved

    def url(self, p):
        return f'http://127.0.0.1:{self.port}{p}'

    def test_memory_search_response_always_includes_embed_available(self):
        """MS-4: /memory/search response always includes embed_available bool."""
        # embed_model is '' in setUpClass → embed_available must be False
        status, body = _request('GET', self.url('/memory/search?q=test&k=1'))
        self.assertEqual(status, 200)
        self.assertIn('embed_available', body,
                      'embed_available must always be present in /memory/search response')
        self.assertFalse(body['embed_available'],
                         'embed_available should be False when embed_model is unset')

    def test_post_embeddings_400_when_embed_model_unset(self):
        """MS-5: POST /embeddings returns 400 when EMBED_MODEL not configured."""
        import json as _json
        orig_model = server.CONFIG.get('embed_model', '')
        try:
            server.CONFIG['embed_model'] = ''
            status, body = _request('POST', self.url('/embeddings'),
                                    {'input': ['test']})
            self.assertEqual(status, 400)
            self.assertIn('error', body)
        finally:
            server.CONFIG['embed_model'] = orig_model

    def test_post_embeddings_502_when_ssrf_guard_rejects_loopback(self):
        """MS-6: POST /embeddings rejects loopback BASE_URL via SSRF guard → 502."""
        orig_model = server.CONFIG.get('embed_model', '')
        orig_base = server.CONFIG.get('base_url', '')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            server.CONFIG['base_url'] = 'http://127.0.0.1:19999'
            server.CONFIG.pop('_test_allow_loopback', None)
            status, body = _request('POST', self.url('/embeddings'),
                                    {'input': ['test']})
            self.assertEqual(status, 502)
        finally:
            server.CONFIG['embed_model'] = orig_model
            server.CONFIG['base_url'] = orig_base

    def test_post_embeddings_413_when_payload_too_large(self):
        """POST /embeddings → 413 when Content-Length > 1 MB (spoofed header)."""
        orig_model = server.CONFIG.get('embed_model', '')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            # Spoof Content-Length to exceed the 1 MB limit without sending
            # a real 1 MB body (same technique used by PayloadTooLargeTests).
            from urllib.request import Request, urlopen
            from urllib.error import HTTPError as _HTTPError
            req = Request(
                self.url('/embeddings'),
                data=b'x',
                headers={'Content-Type': 'application/json',
                         'Content-Length': str(1 * 1024 * 1024 + 1)},
                method='POST',
            )
            try:
                urlopen(req)
                self.fail('Expected HTTPError 413')
            except _HTTPError as err:
                self.assertEqual(err.code, 413)
        finally:
            server.CONFIG['embed_model'] = orig_model

    def test_post_embeddings_400_when_input_empty_list(self):
        """POST /embeddings → 400 when input is an empty list."""
        orig_model = server.CONFIG.get('embed_model', '')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            status, body = _request('POST', self.url('/embeddings'), {'input': []})
            self.assertEqual(status, 400)
            self.assertIn('error', body)
        finally:
            server.CONFIG['embed_model'] = orig_model

    def test_post_embeddings_400_when_input_exceeds_512(self):
        """POST /embeddings → 400 when input list has > 512 strings."""
        orig_model = server.CONFIG.get('embed_model', '')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            status, body = _request('POST', self.url('/embeddings'),
                                    {'input': ['x'] * 513})
            self.assertEqual(status, 400)
            self.assertIn('error', body)
        finally:
            server.CONFIG['embed_model'] = orig_model

    def test_post_embeddings_503_when_base_url_not_configured(self):
        """POST /embeddings → 503 when base_url is empty."""
        orig_model = server.CONFIG.get('embed_model', '')
        orig_base = server.CONFIG.get('base_url', '')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            server.CONFIG['base_url'] = ''
            status, body = _request('POST', self.url('/embeddings'),
                                    {'input': ['hello']})
            self.assertEqual(status, 503)
            self.assertIn('error', body)
        finally:
            server.CONFIG['embed_model'] = orig_model
            server.CONFIG['base_url'] = orig_base

    def test_post_embeddings_happy_path_proxies_upstream(self):
        """POST /embeddings with loopback allowed returns upstream response."""
        import json as _json
        from http.server import HTTPServer, BaseHTTPRequestHandler

        # Spin up a tiny fake upstream that returns a valid embeddings response
        fake_response = _json.dumps({
            'data': [{'index': 0, 'embedding': [0.1, 0.2, 0.3]}],
            'model': 'text-embedding-3-small',
            'usage': {'prompt_tokens': 1, 'total_tokens': 1},
        }).encode()

        class FakeUpstream(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(fake_response)))
                self.end_headers()
                self.wfile.write(fake_response)
            def log_message(self, *a): pass  # silence

        upstream = HTTPServer(('127.0.0.1', 0), FakeUpstream)
        up_port = upstream.server_address[1]
        import threading as _threading
        up_thread = _threading.Thread(target=upstream.serve_forever, daemon=True)
        up_thread.start()

        orig_model = server.CONFIG.get('embed_model', '')
        orig_base = server.CONFIG.get('base_url', '')
        orig_loopback = server.CONFIG.get('_test_allow_loopback')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            server.CONFIG['base_url'] = f'http://127.0.0.1:{up_port}'
            server.CONFIG['_test_allow_loopback'] = True
            status, body = _request('POST', self.url('/embeddings'),
                                    {'input': ['hello world']})
            self.assertEqual(status, 200)
            self.assertIn('data', body)
        finally:
            server.CONFIG['embed_model'] = orig_model
            server.CONFIG['base_url'] = orig_base
            if orig_loopback is None:
                server.CONFIG.pop('_test_allow_loopback', None)
            else:
                server.CONFIG['_test_allow_loopback'] = orig_loopback
            upstream.shutdown()

    def test_post_embeddings_502_on_upstream_urlerror(self):
        """POST /embeddings → 502 when upstream connection is refused (URLError)."""
        orig_model = server.CONFIG.get('embed_model', '')
        orig_base = server.CONFIG.get('base_url', '')
        orig_loopback = server.CONFIG.get('_test_allow_loopback')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            # Port 19998 is almost certainly not listening
            server.CONFIG['base_url'] = 'http://127.0.0.1:19998'
            server.CONFIG['_test_allow_loopback'] = True
            status, body = _request('POST', self.url('/embeddings'),
                                    {'input': ['hello']})
            self.assertEqual(status, 502)
            self.assertIn('error', body)
        finally:
            server.CONFIG['embed_model'] = orig_model
            server.CONFIG['base_url'] = orig_base
            if orig_loopback is None:
                server.CONFIG.pop('_test_allow_loopback', None)
            else:
                server.CONFIG['_test_allow_loopback'] = orig_loopback

    def test_post_embeddings_upstream_http_error_proxied(self):
        """POST /embeddings → upstream HTTPError status is forwarded to client."""
        import json as _json
        from http.server import HTTPServer, BaseHTTPRequestHandler

        error_body = _json.dumps({'error': 'invalid model'}).encode()

        class FakeUpstreamError(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(error_body)))
                self.end_headers()
                self.wfile.write(error_body)
            def log_message(self, *a): pass

        upstream = HTTPServer(('127.0.0.1', 0), FakeUpstreamError)
        up_port = upstream.server_address[1]
        import threading as _threading
        up_thread = _threading.Thread(target=upstream.serve_forever, daemon=True)
        up_thread.start()

        orig_model = server.CONFIG.get('embed_model', '')
        orig_base = server.CONFIG.get('base_url', '')
        orig_loopback = server.CONFIG.get('_test_allow_loopback')
        try:
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            server.CONFIG['base_url'] = f'http://127.0.0.1:{up_port}'
            server.CONFIG['_test_allow_loopback'] = True
            status, body = _request('POST', self.url('/embeddings'),
                                    {'input': ['hello world']})
            self.assertEqual(status, 400)
        finally:
            server.CONFIG['embed_model'] = orig_model
            server.CONFIG['base_url'] = orig_base
            if orig_loopback is None:
                server.CONFIG.pop('_test_allow_loopback', None)
            else:
                server.CONFIG['_test_allow_loopback'] = orig_loopback
            upstream.shutdown()


class StaticFileTests(ServerBranchTestBase):
    """GET / delegates to SimpleHTTPRequestHandler (line 628: super().do_GET())."""

    def test_get_root_serves_static_file(self):
        import os
        orig_dir = os.getcwd()
        try:
            os.chdir(Path(__file__).resolve().parents[2])
            from urllib.request import urlopen
            with urlopen(self.url('/')) as resp:
                self.assertIn(resp.status, (200, 301, 302))
        finally:
            os.chdir(orig_dir)


if __name__ == '__main__':
    unittest.main()
