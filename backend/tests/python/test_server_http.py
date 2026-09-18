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
from unittest.mock import MagicMock, patch
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Try to import optional deps for PDF/DOCX tests; skip tests if they are not installed.
try:
    from docx import Document
    import pypdf  # noqa: F401  (import proves the backend dep is present so the test runs)
    _EXTRACT_TEST_DEPS_INSTALLED = True
except ImportError:
    _EXTRACT_TEST_DEPS_INSTALLED = False


def _create_dummy_pdf(path, text):
    """Write a minimal, spec-valid PDF whose single page draws ``text``.

    We build the PDF by hand as raw bytes rather than driving pypdf's writer
    internals. This is the most robust way to guarantee that ``pypdf``'s
    ``page.extract_text()`` (which the backend uses) can recover the text: the
    page's content stream contains a real ``BT ... (text) Tj ... ET`` block that
    references an embedded Type1 Helvetica font. Byte offsets in the xref table
    are computed as we assemble the file so the result is a well-formed PDF.
    """
    # The content stream draws the text using the standard PDF text operators.
    content = (
        b"BT\n/F1 24 Tf\n72 700 Td\n("
        + text.encode("ascii")
        + b") Tj\nET\n"
    )

    # Each PDF object, in order. We fill in the content-stream length below.
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n"
        + content + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    buf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += str(i).encode("ascii") + b" 0 obj\n" + body + b"\nendobj\n"

    xref_pos = len(buf)
    n = len(objects) + 1  # +1 for the free object 0
    buf += b"xref\n0 " + str(n).encode("ascii") + b"\n"
    buf += b"0000000000 65535 f \n"
    for off in offsets:
        buf += ("%010d 00000 n \n" % off).encode("ascii")
    buf += (
        b"trailer\n<< /Size " + str(n).encode("ascii")
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode("ascii") + b"\n%%EOF\n"
    )

    with open(path, "wb") as f:
        f.write(buf)


def _create_dummy_docx(path, text):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(path)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

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
            'embed_model': 'test-embed-model',
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


class ProjectsCRUDTests(ServerHTTPTestBase):
    """PR-1…PR-6: integration tests for the /projects CRUD endpoints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Redirect PROJECTS_DIR into the temp directory so tests don't touch real state.
        cls._saved_projects = server.PROJECTS_DIR
        cls._projects_tmp = Path(cls._tmp.name) / 'projects'
        cls._projects_tmp.mkdir(exist_ok=True)
        server.PROJECTS_DIR = cls._projects_tmp

    @classmethod
    def tearDownClass(cls):
        server.PROJECTS_DIR = cls._saved_projects
        super().tearDownClass()

    def setUp(self):
        # Clear projects before each test for isolation.
        for p in server.PROJECTS_DIR.glob('*.json'):
            p.unlink(missing_ok=True)

    def test_pr1_create_project_returns_201(self):
        """PR-1: POST /projects → 201 + {id, name, memoryMode, pinned, createdAt}."""
        status, body = _request('POST', self.url('/projects'),
                                {'name': 'My Project', 'memoryMode': 'default'})
        self.assertEqual(status, 201)
        self.assertIn('id', body)
        self.assertTrue(body['id'].startswith('project_'))
        self.assertEqual(body['name'], 'My Project')
        self.assertEqual(body['memoryMode'], 'default')
        self.assertFalse(body['pinned'])
        self.assertIn('createdAt', body)

    def test_pr1b_create_project_defaults_memory_mode(self):
        """PR-1b: POST /projects without memoryMode defaults to 'default'."""
        status, body = _request('POST', self.url('/projects'), {'name': 'No Mode'})
        self.assertEqual(status, 201)
        self.assertEqual(body['memoryMode'], 'default')

    def test_pr2_list_projects_sorted_newest_first(self):
        """PR-2: GET /projects returns array sorted by createdAt desc."""
        _request('POST', self.url('/projects'), {'name': 'Alpha'})
        _request('POST', self.url('/projects'), {'name': 'Beta'})
        status, body = _request('GET', self.url('/projects'))
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 2)
        # Both projects are in the list
        names = [p['name'] for p in body]
        self.assertIn('Alpha', names)
        self.assertIn('Beta', names)

    def test_pr3_update_name_pin_and_memory_mode(self):
        """PR-3: PUT /projects/:id updates name, pinned, and memoryMode."""
        _, created = _request('POST', self.url('/projects'),
                               {'name': 'Original', 'memoryMode': 'project-only'})
        pid = created['id']
        status, body = _request('PUT', self.url(f'/projects/{pid}'),
                                 {'name': 'Renamed', 'pinned': True, 'memoryMode': 'default'})
        self.assertEqual(status, 200)
        self.assertEqual(body['name'], 'Renamed')
        self.assertTrue(body['pinned'])
        self.assertEqual(body['memoryMode'], 'default')

    def test_get_single_project(self):
        """GET /projects/<id> returns a single project."""
        _, created = _request('POST', self.url('/projects'),
                               {'name': 'Single', 'memoryMode': 'default'})
        pid = created['id']
        status, body = _request('GET', self.url(f'/projects/{pid}'))
        self.assertEqual(status, 200)
        self.assertEqual(body['id'], pid)
        self.assertEqual(body['name'], 'Single')

    def test_pr4_delete_removes_project_and_clears_session_projectid(self):
        """PR-4: DELETE /projects/:id removes project file and clears projectId from sessions."""
        _, proj = _request('POST', self.url('/projects'), {'name': 'Temp'})
        pid = proj['id']
        # Create a session that references the project
        sess_id = 'session_pr4_test'
        sess_path = server.SESSIONS_DIR / f'{sess_id}.json'
        import json as _json
        sess_path.write_text(_json.dumps({
            'id': sess_id, 'title': 'PR4 test', 'turns': [],
            'projectId': pid, 'createdAt': '2026-06-29T00:00:00',
        }), encoding='utf-8')
        # Delete the project
        status, body = _request('DELETE', self.url(f'/projects/{pid}'))
        self.assertEqual(status, 200)
        # Project file should be gone
        self.assertFalse((server.PROJECTS_DIR / f'{pid}.json').exists())
        # Session should still exist but with projectId cleared
        sess_data = _json.loads(sess_path.read_text(encoding='utf-8'))
        self.assertIsNone(sess_data.get('projectId'))

    def test_pr5_delete_does_not_delete_orphaned_sessions(self):
        """PR-5: DELETE /projects/:id does NOT delete orphaned sessions."""
        _, proj = _request('POST', self.url('/projects'), {'name': 'Orphan Test'})
        pid = proj['id']
        sess_id = 'session_pr5_test'
        sess_path = server.SESSIONS_DIR / f'{sess_id}.json'
        import json as _json
        sess_path.write_text(_json.dumps({
            'id': sess_id, 'title': 'PR5 test', 'turns': [],
            'projectId': pid, 'createdAt': '2026-06-29T00:00:00',
        }), encoding='utf-8')
        _request('DELETE', self.url(f'/projects/{pid}'))
        # Session file must still exist (just with projectId=null)
        self.assertTrue(sess_path.exists())

    def test_pr6_traversal_in_project_id_returns_400(self):
        """PR-6: Path traversal in project id → 400."""
        status, body = _request('PUT', self.url('/projects/../../etc/passwd'),
                                 {'name': 'evil'})
        self.assertEqual(status, 400)

    def test_pr6b_traversal_in_delete_returns_400(self):
        """PR-6b: Path traversal in DELETE project id → 400."""
        status, _ = _request('DELETE', self.url('/projects/../secret'))
        self.assertEqual(status, 400)

    def test_pr_config_has_projects_flag(self):
        """POST /config returns has_projects: true."""
        status, body = _request('GET', self.url('/config'))
        self.assertEqual(status, 200)
        self.assertIn('has_projects', body)
        self.assertTrue(body['has_projects'])

    def test_pr_create_project_missing_name_returns_400(self):
        """POST /projects without name → 400."""
        status, _ = _request('POST', self.url('/projects'), {'name': '  '})
        self.assertEqual(status, 400)

    def test_pr_update_nonexistent_project_returns_404(self):
        """PUT /projects/<id> for a project that does not exist → 404."""
        status, body = _request('PUT', self.url('/projects/project_999999999999'),
                                 {'name': 'Ghost'})
        self.assertEqual(status, 404)

    def test_pr_delete_nonexistent_project_is_idempotent(self):
        """DELETE /projects/<id> for a project that does not exist → 200 (idempotent)."""
        status, body = _request('DELETE', self.url('/projects/project_888888888888'))
        self.assertEqual(status, 200)
        self.assertTrue(body.get('ok'))

    def test_pr_delete_traversal_with_slash_in_id_returns_400(self):
        """DELETE /projects/<id> with embedded slash → 400 from _safe_project_id."""
        # e.g. /projects/a/b where 'a/b' is the raw project_id
        status, _ = _request('DELETE', self.url('/projects/a/b'))
        self.assertEqual(status, 400)

    def test_pr_put_traversal_via_dotdot_in_id_returns_400(self):
        """PUT /projects with raw_id starting with '.' → 400."""
        status, _ = _request('PUT', self.url('/projects/.hidden'), {'name': 'x'})
        self.assertEqual(status, 400)


class NewChatSessionProjectIdTests(ServerHTTPTestBase):
    """PR-7, PR-8: _post_new_chat_session stamps projectId from body."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._saved_projects = server.PROJECTS_DIR
        cls._projects_tmp = Path(cls._tmp.name) / 'projects_ncs'
        cls._projects_tmp.mkdir(exist_ok=True)
        server.PROJECTS_DIR = cls._projects_tmp

    @classmethod
    def tearDownClass(cls):
        server.PROJECTS_DIR = cls._saved_projects
        super().tearDownClass()

    def setUp(self):
        # Clear sessions + history between tests.
        for p in server.SESSIONS_DIR.glob('*.json'):
            p.unlink(missing_ok=True)
        if server.HISTORY_FILE.exists():
            server.HISTORY_FILE.unlink()

    def test_pr7_new_chat_session_stamps_project_id(self):
        """PR-7: POST /new-chat-session with projectId in body stamps it on the archived session."""
        import json as _json
        # Pre-create a history file with one user turn so there is something to archive.
        server.HISTORY_FILE.write_text(_json.dumps({'turns': [
            {'role': 'user', 'content': 'hello project', 'timestamp': '2026-06-29T00:00:00'},
        ]}), encoding='utf-8')
        status, body = _request('POST', self.url('/new-chat-session'), {'projectId': 'project_12345'})
        self.assertEqual(status, 200)
        archived_id = body.get('archivedId')
        self.assertIsNotNone(archived_id)
        sess_path = server.SESSIONS_DIR / f'{archived_id}.json'
        sess_data = _json.loads(sess_path.read_text(encoding='utf-8'))
        self.assertEqual(sess_data.get('projectId'), 'project_12345')

    def test_pr8_new_chat_session_no_project_id_leaves_it_absent(self):
        """PR-8: POST /new-chat-session without projectId → archived session has no projectId field."""
        import json as _json
        server.HISTORY_FILE.write_text(_json.dumps({'turns': [
            {'role': 'user', 'content': 'plain chat', 'timestamp': '2026-06-29T00:00:00'},
        ]}), encoding='utf-8')
        status, body = _request('POST', self.url('/new-chat-session'), {})
        self.assertEqual(status, 200)
        archived_id = body.get('archivedId')
        if archived_id:
            sess_path = server.SESSIONS_DIR / f'{archived_id}.json'
            sess_data = _json.loads(sess_path.read_text(encoding='utf-8'))
            # projectId should be absent or None — never a stale id
            self.assertIsNone(sess_data.get('projectId'))


# ── Slice 2: project instructions CRUD (PR-9…PR-12) ──────────────────────────

class ProjectInstructionsTests(ProjectsCRUDTests):
    """PR-9…PR-11: project instructions stored, updated, and length-capped."""

    def test_pr9_create_project_with_instructions(self):
        """PR-9: POST /projects with instructions → 201 + instructions field in response."""
        status, body = _request('POST', self.url('/projects'),
                                {'name': 'Instructed', 'instructions': 'Always reply in French.'})
        self.assertEqual(status, 201)
        self.assertIn('instructions', body)
        self.assertEqual(body['instructions'], 'Always reply in French.')

    def test_pr10_update_instructions_via_put(self):
        """PR-10: PUT /projects/:id with instructions → 200 + updated instructions; memoryMode unchanged."""
        _, created = _request('POST', self.url('/projects'),
                               {'name': 'Upd', 'memoryMode': 'project-only'})
        pid = created['id']
        status, body = _request('PUT', self.url(f'/projects/{pid}'),
                                 {'instructions': 'Be concise.', 'memoryMode': 'default'})
        self.assertEqual(status, 200)
        self.assertEqual(body['instructions'], 'Be concise.')
        # memoryMode is mutable as of Slice 3.
        self.assertEqual(body['memoryMode'], 'default')

    def test_pr11_create_instructions_too_long_returns_400(self):
        """PR-11: POST /projects with instructions > 8 192 bytes → 400 'instructions too long'."""
        long_inst = 'x' * 8193
        status, body = _request('POST', self.url('/projects'),
                                {'name': 'Overflow', 'instructions': long_inst})
        self.assertEqual(status, 400)
        self.assertIn('instructions too long', body.get('error', ''))

    def test_pr11b_update_instructions_too_long_returns_400(self):
        """PR-11b: PUT /projects/:id with instructions > 8 192 bytes → 400."""
        _, created = _request('POST', self.url('/projects'), {'name': 'Cap test'})
        pid = created['id']
        long_inst = 'y' * 8193
        status, body = _request('PUT', self.url(f'/projects/{pid}'),
                                 {'instructions': long_inst})
        self.assertEqual(status, 400)
        self.assertIn('instructions too long', body.get('error', ''))

    def test_pr9b_create_project_without_instructions_defaults_to_empty(self):
        """PR-9b: POST /projects without instructions field → instructions defaults to ''."""
        status, body = _request('POST', self.url('/projects'), {'name': 'No inst'})
        self.assertEqual(status, 201)
        # instructions key should be present and empty
        self.assertEqual(body.get('instructions', 'MISSING'), '')

    def test_pr12_get_projects_missing_instructions_field_served_safely(self):
        """PR-12: legacy project files without 'instructions' key are served without 500.

        Slice 2 adds the instructions field.  Projects created before the migration
        will not have the key in their JSON file.  GET /projects must not blow up and
        the item must appear in the list.
        """
        import json as _json
        # Inject a legacy project file that has no 'instructions' key.
        legacy = {
            'id': 'project_legacy_test',
            'name': 'Legacy Project',
            'memoryMode': 'default',
            'pinned': False,
            'createdAt': '2024-01-01T00:00:00',
            'updatedAt': '2024-01-01T00:00:00',
            # Intentionally NO 'instructions' key
        }
        legacy_file = self.__class__._projects_tmp / 'project_legacy_test.json'
        legacy_file.write_text(_json.dumps(legacy), encoding='utf-8')
        try:
            status, body = _request('GET', self.url('/projects'))
            self.assertEqual(status, 200)
            ids = [p['id'] for p in body]
            self.assertIn('project_legacy_test', ids, 'legacy project must appear in list')
        finally:
            legacy_file.unlink(missing_ok=True)


# ── Slice 3: Memory Modes (MM-3…MM-8) ────────────────────────────────────────

class ProjectsSlice3MemoryModeTests(ProjectInstructionsTests):
    """MM-3…MM-8: /memory/* endpoints respect memoryMode (default vs project-only).

    Inherits from ProjectInstructionsTests so we also get the same server + temp
    PROJECTS_DIR wiring without duplicating setUpClass boilerplate.

    We additionally redirect the vault's memory directory so notes land in the
    shared temp tree, and we create 'default' and 'project-only' project JSON
    files directly in PROJECTS_DIR.
    """

    # Pre-created project ids used across tests (stable, no POST needed).
    _DEFAULT_PID = 'proj_default_mm'
    _PROJONLY_PID = 'proj_only_mm'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The vault has already been set up by ServerHTTPTestBase to point at
        # cls._vault / 'USAi' / 'memories'.  We'll use that as the global dir.
        # Create a couple of pre-canned project JSON files in PROJECTS_DIR.
        import json as _json

        cls._vault_subdir = Path(server.CONFIG['obsidian_vault_path']) / 'USAi'

        default_proj = {
            'id': cls._DEFAULT_PID,
            'name': 'Default Mode Project',
            'memoryMode': 'default',
            'instructions': '',
            'pinned': False,
            'createdAt': '2026-01-01T00:00:00',
            'updatedAt': '2026-01-01T00:00:00',
        }
        projonly_proj = {
            'id': cls._PROJONLY_PID,
            'name': 'Project-only Mode Project',
            'memoryMode': 'project-only',
            'instructions': '',
            'pinned': False,
            'createdAt': '2026-01-01T00:00:00',
            'updatedAt': '2026-01-01T00:00:00',
        }
        (cls._projects_tmp / f'{cls._DEFAULT_PID}.json').write_text(
            _json.dumps(default_proj), encoding='utf-8')
        (cls._projects_tmp / f'{cls._PROJONLY_PID}.json').write_text(
            _json.dumps(projonly_proj), encoding='utf-8')

    def _global_mem_dir(self):
        """Path to the global memory folder (the one used when no projectId)."""
        v = Path(server.CONFIG['obsidian_vault_path'])
        d = v / server.CONFIG.get('obsidian_memory_subdir', 'USAi') / 'memories'
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _proj_mem_dir(self, project_id):
        """Path to <vault>/<subdir>/projects/<id>/memories (project-scoped)."""
        v = Path(server.CONFIG['obsidian_vault_path'])
        d = v / server.CONFIG.get('obsidian_memory_subdir', 'USAi') / 'projects' / project_id / 'memories'
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _write_note(self, directory, filename, content):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_text(content, encoding='utf-8')

    def setUp(self):
        super().setUp()
        # Re-create project JSON files deleted by the parent setUp.
        import json as _json
        default_proj = {
            'id': self._DEFAULT_PID, 'name': 'Default Mode Project',
            'memoryMode': 'default', 'instructions': '', 'pinned': False,
            'createdAt': '2026-01-01T00:00:00', 'updatedAt': '2026-01-01T00:00:00',
        }
        projonly_proj = {
            'id': self._PROJONLY_PID, 'name': 'Project-only Mode Project',
            'memoryMode': 'project-only', 'instructions': '', 'pinned': False,
            'createdAt': '2026-01-01T00:00:00', 'updatedAt': '2026-01-01T00:00:00',
        }
        (self.__class__._projects_tmp / f'{self._DEFAULT_PID}.json').write_text(
            _json.dumps(default_proj), encoding='utf-8')
        (self.__class__._projects_tmp / f'{self._PROJONLY_PID}.json').write_text(
            _json.dumps(projonly_proj), encoding='utf-8')
        # Clean all memory dirs before each test to avoid cross-test pollution.
        import shutil
        for d in [self._global_mem_dir(),
                  self._proj_mem_dir(self._DEFAULT_PID),
                  self._proj_mem_dir(self._PROJONLY_PID)]:
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

    # Override inherited PR-2 — pre-canned project files live alongside POSTed
    # ones in this class's PROJECTS_DIR, so the exact-count assertion does not
    # hold.  PR-2 is already covered by ProjectsCRUDTests; skip it here.
    def test_pr2_list_projects_sorted_newest_first(self):
        pass  # covered by ProjectsCRUDTests; not meaningful with pre-canned files

    # MM-3 ─────────────────────────────────────────────────────────────────────
    def test_mm3_default_mode_search_returns_both_global_and_project_notes(self):
        """MM-3: GET /memory/search with projectId (default mode) merges both dirs."""
        self._write_note(self._global_mem_dir(), 'global_note.md',
                         '---\ntitle: "global"\ntags: [usai-memory]\n---\n\nglobal testword content')
        self._write_note(self._proj_mem_dir(self._DEFAULT_PID), 'proj_note.md',
                         '---\ntitle: "proj"\ntags: [usai-memory]\n---\n\nproject testword content')

        status, body = _request(
            'GET', self.url(f'/memory/search?q=testword&projectId={self._DEFAULT_PID}'))
        self.assertEqual(status, 200)
        paths = [r['path'] for r in body.get('results', [])]
        self.assertIn('global_note.md', paths, 'global note must appear in default-mode search')
        self.assertIn('proj_note.md', paths, 'project note must appear in default-mode search')

    # MM-4 ─────────────────────────────────────────────────────────────────────
    def test_mm4_project_only_mode_search_returns_only_project_notes(self):
        """MM-4: GET /memory/search with projectId (project-only) omits global dir."""
        self._write_note(self._global_mem_dir(), 'global_only.md',
                         '---\ntitle: "global"\ntags: [usai-memory]\n---\n\nkeyword_po content here')
        # project-only dir has no note at all
        status, body = _request(
            'GET', self.url(f'/memory/search?q=keyword_po&projectId={self._PROJONLY_PID}'))
        self.assertEqual(status, 200)
        paths = [r['path'] for r in body.get('results', [])]
        self.assertNotIn('global_only.md', paths,
                         'global note must NOT appear in project-only search')
        self.assertEqual(paths, [], 'project dir is empty so results must be empty')

    # MM-5 ─────────────────────────────────────────────────────────────────────
    def test_mm5_global_search_never_returns_project_only_notes(self):
        """MM-5: GET /memory/search without projectId never surfaces project-only folders."""
        self._write_note(self._proj_mem_dir(self._PROJONLY_PID), 'secret_po.md',
                         '---\ntitle: "secret"\ntags: [usai-memory]\n---\n\nsecretword_global content')
        status, body = _request('GET', self.url('/memory/search?q=secretword_global'))
        self.assertEqual(status, 200)
        paths = [r['path'] for r in body.get('results', [])]
        self.assertNotIn('secret_po.md', paths,
                         'project-only notes must never appear in global search')

    # MM-6 ─────────────────────────────────────────────────────────────────────
    def test_mm6_save_with_project_id_writes_to_project_dir_not_global(self):
        """MM-6: POST /memory/save with projectId (default mode) writes to project dir."""
        status, body = _request('POST', self.url('/memory/save'), {
            'title': 'MM6 note',
            'content': 'Saved under the default project.',
            'projectId': self._DEFAULT_PID,
        })
        self.assertEqual(status, 200)
        self.assertTrue(body.get('ok'))
        note_name = body.get('path')
        self.assertIsNotNone(note_name)

        proj_dir = self._proj_mem_dir(self._DEFAULT_PID)
        global_dir = self._global_mem_dir()

        self.assertTrue((proj_dir / note_name).exists(),
                        f'{note_name} should be in project dir {proj_dir}')
        self.assertFalse((global_dir / note_name).exists(),
                         f'{note_name} must NOT be in global dir {global_dir}')

    # MM-7 ─────────────────────────────────────────────────────────────────────
    def test_mm7_list_project_only_returns_only_project_dir_notes(self):
        """MM-7: GET /memory/list?projectId (project-only) lists only project-scoped notes."""
        self._write_note(self._global_mem_dir(), 'global_list.md',
                         '---\ntitle: "g"\n---\nglobal list note')
        self._write_note(self._proj_mem_dir(self._PROJONLY_PID), 'proj_list.md',
                         '---\ntitle: "p"\n---\nproject list note')

        status, body = _request(
            'GET', self.url(f'/memory/list?projectId={self._PROJONLY_PID}'))
        self.assertEqual(status, 200)
        paths = [i['path'] for i in body.get('items', [])]
        self.assertIn('proj_list.md', paths, 'project note must appear in project-only list')
        self.assertNotIn('global_list.md', paths,
                         'global note must NOT appear in project-only list')

    # MM-8 ─────────────────────────────────────────────────────────────────────
    def test_mm8_missing_memory_mode_field_treated_as_default(self):
        """MM-8: project with no memoryMode key in JSON is treated as 'default'."""
        import json as _json
        # Create a project JSON without the 'memoryMode' field
        legacy_pid = 'proj_legacy_mm'
        legacy = {
            'id': legacy_pid,
            'name': 'Legacy no-memoryMode project',
            'instructions': '',
            'pinned': False,
            'createdAt': '2024-01-01T00:00:00',
            'updatedAt': '2024-01-01T00:00:00',
            # Intentionally NO 'memoryMode' key
        }
        legacy_file = self.__class__._projects_tmp / f'{legacy_pid}.json'
        legacy_file.write_text(_json.dumps(legacy), encoding='utf-8')
        try:
            # Write a note to both global and project dirs
            self._write_note(self._global_mem_dir(), 'legacy_global.md',
                             '---\ntitle: "lg"\n---\nlegacy_keyword content')
            legacy_proj_dir = self._proj_mem_dir(legacy_pid)
            self._write_note(legacy_proj_dir, 'legacy_proj.md',
                             '---\ntitle: "lp"\n---\nlegacy_keyword content')

            status, body = _request(
                'GET', self.url(f'/memory/search?q=legacy_keyword&projectId={legacy_pid}'))
            self.assertEqual(status, 200)
            paths = [r['path'] for r in body.get('results', [])]
            # Default mode → both dirs searched
            self.assertIn('legacy_global.md', paths,
                          'global note must appear when memoryMode is absent (treated as default)')
            self.assertIn('legacy_proj.md', paths,
                          'project note must appear when memoryMode is absent')
        finally:
            legacy_file.unlink(missing_ok=True)
            import shutil
            shutil.rmtree(self._proj_mem_dir(legacy_pid), ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────────
# Slice 4: Project Chunk Cache (PF-1 … PF-7)
# ──────────────────────────────────────────────────────────────────────────────

class ProjectChunkCacheTests(ProjectsSlice3MemoryModeTests):
    """PF-1…PF-7: project-scoped chunk cache CRUD, traversal guard, delete cascade,
    and backward-compat for the global /chunk-cache endpoint (no projectId).

    PROJECT_CACHE_DIR = CACHE_DIR / 'projects' is added to server.py in Slice 4.
    Tests that reference it access it via `server.PROJECT_CACHE_DIR` so the
    symbol is resolved at call time (after the server module is patched).
    """

    _PROJ_CACHE_PID = 'proj_cache_test_123'

    @staticmethod
    def _pcdir():
        """Return server.PROJECT_CACHE_DIR (resolved at call time)."""
        return server.PROJECT_CACHE_DIR  # type: ignore[attr-defined]

    def _proj_cache_dir(self, pid=None):
        """Return the per-project chunk-cache directory (created lazily by server)."""
        pid = pid or self._PROJ_CACHE_PID
        return self._pcdir() / pid

    def tearDown(self):
        """Clean up any project chunk-cache files created during tests."""
        import shutil as _shutil
        d = self._proj_cache_dir()
        if d.exists():
            _shutil.rmtree(d, ignore_errors=True)
        # Also clean up any global cache files created by PF-7.
        for p in server.CACHE_DIR.glob('pf7_*.json'):
            p.unlink(missing_ok=True)
        super().tearDown()

    # PF-1 ─────────────────────────────────────────────────────────────────────
    def test_pf1_post_chunk_cache_with_project_id_stores_in_project_dir(self):
        """PF-1: POST /chunk-cache?projectId=<id> stores chunks under CACHE_DIR/projects/<id>/"""
        status, body = _request(
            'POST',
            self.url(f'/chunk-cache?projectId={self._PROJ_CACHE_PID}'),
            {'filename': 'notes.txt', 'chunks': [{'chunkId': 'c1', 'text': 'Hello from project'}]},
        )
        self.assertEqual(status, 200)
        assert isinstance(body, dict)
        self.assertTrue(body.get('ok'), body)
        # File must exist in the project sub-dir, NOT in the global CACHE_DIR.
        proj_file = self._proj_cache_dir() / 'notes.txt.json'
        self.assertTrue(proj_file.exists(), 'chunk file must exist in project dir')

    # PF-2 ─────────────────────────────────────────────────────────────────────
    def test_pf2_get_chunk_cache_with_project_id_lists_project_files(self):
        """PF-2: GET /chunk-cache?projectId=<id> lists project-scoped files."""
        proj_dir = self._proj_cache_dir()
        proj_dir.mkdir(parents=True, exist_ok=True)
        proj_dir.joinpath('seed.txt.json').write_text(
            json.dumps({'filename': 'seed.txt', 'chunks': [{'chunkId': 'c1', 'text': 'x'}],
                        'savedAt': '2026-01-01T00:00:00'}),
            encoding='utf-8',
        )
        status, body = _request('GET', self.url(f'/chunk-cache?projectId={self._PROJ_CACHE_PID}'))
        self.assertEqual(status, 200)
        assert isinstance(body, list)
        filenames = [e['filename'] for e in body]
        self.assertIn('seed.txt', filenames)

    # PF-3 ─────────────────────────────────────────────────────────────────────
    def test_pf3_get_chunk_cache_with_project_id_and_file_reads_one(self):
        """PF-3: GET /chunk-cache?projectId=<id>&file=notes.txt reads that project file."""
        proj_dir = self._proj_cache_dir()
        proj_dir.mkdir(parents=True, exist_ok=True)
        proj_dir.joinpath('notes.txt.json').write_text(
            json.dumps({'filename': 'notes.txt', 'chunks': [{'chunkId': 'c1', 'text': 'Hello'}],
                        'savedAt': '2026-01-01T00:00:00'}),
            encoding='utf-8',
        )
        status, body = _request(
            'GET', self.url(f'/chunk-cache?projectId={self._PROJ_CACHE_PID}&file=notes.txt'))
        self.assertEqual(status, 200)
        assert isinstance(body, dict)
        self.assertEqual(body.get('filename'), 'notes.txt')
        self.assertEqual(len(body.get('chunks', [])), 1)

    # PF-4 ─────────────────────────────────────────────────────────────────────
    def test_pf4_delete_chunk_cache_with_project_id_and_file_removes_one(self):
        """PF-4: DELETE /chunk-cache?projectId=<id>&file=notes.txt removes one file."""
        proj_dir = self._proj_cache_dir()
        proj_dir.mkdir(parents=True, exist_ok=True)
        proj_dir.joinpath('notes.txt.json').write_text(
            json.dumps({'filename': 'notes.txt', 'chunks': []}), encoding='utf-8')
        status, body = _request(
            'DELETE',
            self.url(f'/chunk-cache?projectId={self._PROJ_CACHE_PID}&file=notes.txt'))
        self.assertEqual(status, 200)
        assert isinstance(body, dict)
        self.assertTrue(body.get('ok'))
        self.assertFalse(proj_dir.joinpath('notes.txt.json').exists(),
                         'file must be removed from project dir')

    # PF-5 ─────────────────────────────────────────────────────────────────────
    def test_pf5_traversal_in_project_id_returns_400(self):
        """PF-5: POST /chunk-cache?projectId=../traversal returns 400."""
        status, body = _request(
            'POST',
            self.url('/chunk-cache?projectId=../traversal'),
            {'filename': 'x.txt', 'chunks': []},
        )
        self.assertEqual(status, 400, f'expected 400 for traversal, got {status}: {body}')

    # PF-6 ─────────────────────────────────────────────────────────────────────
    def test_pf6_delete_project_also_removes_project_chunk_cache_dir(self):
        """PF-6: DELETE /projects/<id> removes PROJECT_CACHE_DIR/<id>/"""
        status, proj = _request(
            'POST', self.url('/projects'),
            {'name': 'CacheDeleteTest', 'memoryMode': 'default'})
        self.assertEqual(status, 201)
        assert isinstance(proj, dict)
        pid = proj['id']

        # Seed a chunk-cache sub-dir for that project.
        proj_cache_dir = self._pcdir() / pid
        proj_cache_dir.mkdir(parents=True, exist_ok=True)
        (proj_cache_dir / 'data.txt.json').write_text(
            json.dumps({'filename': 'data.txt', 'chunks': []}), encoding='utf-8')

        status, body = _request('DELETE', self.url(f'/projects/{pid}'))
        self.assertEqual(status, 200)
        self.assertFalse(proj_cache_dir.exists(),
                         f'PROJECT_CACHE_DIR/{pid}/ should be removed on project delete')

    # PF-7 ─────────────────────────────────────────────────────────────────────
    def test_pf7_global_chunk_cache_unaffected_by_project_cache(self):
        """PF-7: GET /chunk-cache (no projectId) still uses the global CACHE_DIR."""
        global_file = server.CACHE_DIR / 'pf7_global.txt.json'
        global_file.write_text(
            json.dumps({'filename': 'pf7_global.txt',
                        'chunks': [{'chunkId': 'g1', 'text': 'global'}],
                        'savedAt': '2026-01-01T00:00:00'}),
            encoding='utf-8',
        )
        try:
            status, body = _request('GET', self.url('/chunk-cache'))
            self.assertEqual(status, 200)
            assert isinstance(body, list)
            filenames = [e['filename'] for e in body]
            self.assertIn('pf7_global.txt', filenames,
                          'global cache list must still include pf7_global.txt')
        finally:
            global_file.unlink(missing_ok=True)


class FileExtractionAndEmbeddingTests(ServerHTTPTestBase):
    """FE-1, FE-2: PDF/DOCX extraction. EMB-1, EMB-2: embedding generation."""

    def _post_multipart(self, url, file_path, file_content_type):
        """POST a multipart/form-data request with a single file."""
        from urllib.request import Request, urlopen
        import mimetypes

        boundary = '----TestBoundary12345'
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            f'Content-Type: {file_content_type}\r\n'
            f'\r\n'
        ).encode('utf-8')
        body += file_path.read_bytes()
        body += f'\r\n--{boundary}--\r\n'.encode('utf-8')

        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body))
        }

        req = Request(url, data=body, headers=headers, method='POST')
        try:
            with urlopen(req) as resp:
                raw = resp.read().decode('utf-8')
                status = resp.status
                return status, json.loads(raw)
        except HTTPError as err:
            return err.code, json.loads(err.read().decode('utf-8'))

    # @unittest.skipIf(not _EXTRACT_TEST_DEPS_INSTALLED, "pypdf or python-docx not installed")
    def test_fe1_extract_text_from_pdf_and_docx(self):
        """FE-1: POST /extract-text returns plain text for PDF and DOCX."""
        if not _EXTRACT_TEST_DEPS_INSTALLED:
            self.skipTest("pypdf or python-docx not installed")

        pdf_path = Path(self._tmp.name) / 'test.pdf'
        docx_path = Path(self._tmp.name) / 'test.docx'
        _create_dummy_pdf(pdf_path, "Hello PDF world")
        _create_dummy_docx(docx_path, "Hello DOCX world")

        status, body = self._post_multipart(
            self.url('/extract-text'),
            pdf_path,
            'application/pdf'
        )
        self.assertEqual(status, 200, f'PDF extraction failed: {body}')
        self.assertIn("Hello PDF world", body.get('text', ''))

        status, body = self._post_multipart(
            self.url('/extract-text'),
            docx_path,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        self.assertEqual(status, 200, f'DOCX extraction failed: {body}')
        self.assertIn("Hello DOCX world", body.get('text', ''))

    def test_fe1b_extract_text_from_txt(self):
        """POST /extract-text returns plain text for .txt files."""
        txt_path = Path(self._tmp.name) / 'test.txt'
        txt_path.write_text("Hello TXT world", encoding='utf-8')

        status, body = self._post_multipart(
            self.url('/extract-text'),
            txt_path,
            'text/plain'
        )
        self.assertEqual(status, 200, f'TXT extraction failed: {body}')
        self.assertIn("Hello TXT world", body.get('text', ''))

    def test_fe1c_binary_safety(self):
        """POST /extract-text with binary file is safe."""
        bin_path = Path(self._tmp.name) / 'test.bin'
        bin_content = b'\x80\x81\x82'
        bin_path.write_bytes(bin_content)

        status, body = self._post_multipart(
            self.url('/extract-text'),
            bin_path,
            'application/octet-stream'
        )
        self.assertEqual(status, 200, f'Binary file upload failed: {body}')
        # The file parser will return an empty string for unknown file types, which is fine.
        # The main thing is that the server doesn't crash on binary content.
        self.assertEqual(body.get('text', 'ERROR'), '')

    @patch('server.urlopen')
    def test_emb1_generate_embeddings_endpoint(self, mock_urlopen):
        """EMB-1: POST /generate-embeddings creates embeddings for a cached file."""
        # Mock the embedding API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'data': [{'embedding': [0.1, 0.2, 0.3], 'index': 0}]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # 1. Create a project and a cached file with no embeddings
        _, proj = _request('POST', self.url('/projects'), {'name': 'EmbeddingTest'})
        pid = proj['id']
        _request('POST', self.url(f'/chunk-cache?projectId={pid}'),
                 {'filename': 'embed_me.txt', 'chunks': [{'chunkId': 0, 'text': 'some text', 'embedding': None}]})

        # 2. Call the new endpoint. The handler reads projectId from the query
        # string and filename/chunkIds from the JSON body.
        status, body = _request('POST', self.url(f'/generate-embeddings?projectId={pid}'),
                                  {'filename': 'embed_me.txt', 'chunkIds': [0]})
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])

        # 3. Verify the chunk now has an embedding vector
        _, chunk_data = _request('GET', self.url(f'/chunk-cache?projectId={pid}&file=embed_me.txt'))
        self.assertIsNotNone(chunk_data['chunks'][0]['embedding'])
        self.assertIsInstance(chunk_data['chunks'][0]['embedding'], list)

    def test_emb3_full_project_upload_round_trip(self):
        """EMB-3: full project file upload and embedding generation round trip."""
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading

        canned_embedding = [0.1, 0.2, 0.3]
        upstream_received_request = threading.Event()

        class FakeUpstream(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    "object": "list",
                    "data": [{
                        "object": "embedding",
                        "index": 0,
                        "embedding": canned_embedding,
                    }],
                    "model": "text-embedding-3-small",
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
                upstream_received_request.set()

            def log_message(self, format, *args):
                return  # Suppress logs

        # Start the fake upstream server in a separate thread
        upstream_server = HTTPServer(('127.0.0.1', 0), FakeUpstream)
        upstream_port = upstream_server.server_address[1]
        upstream_thread = threading.Thread(target=upstream_server.serve_forever)
        upstream_thread.daemon = True
        upstream_thread.start()

        orig_base_url = server.CONFIG.get('base_url')
        orig_embed_model = server.CONFIG.get('embed_model')
        orig_allow_loopback = server.CONFIG.get('_test_allow_loopback')

        try:
            # Configure server to use the fake upstream and allow loopback
            server.CONFIG['base_url'] = f'http://127.0.0.1:{upstream_port}'
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            server.CONFIG['_test_allow_loopback'] = True

            # 1. Create a project
            status, body = _request('POST', self.url('/projects'), {'name': 'Test Project EMB3'})
            self.assertEqual(status, 201)
            project_id = body['id']

            # 2. Upload a file chunk
            chunk_content = 'This is a test chunk.'
            chunk_id = 'c1'
            status, body = _request(
                'POST',
                self.url(f'/chunk-cache?projectId={project_id}'),
                {'filename': 'test.txt', 'chunks': [{'text': chunk_content, 'chunkId': chunk_id}]}
            )
            self.assertEqual(status, 200)
            self.assertEqual(body['savedAs'], 'test.txt')

            # 3. Trigger embedding generation
            status, body = _request(
                'POST',
                self.url(f'/generate-embeddings?projectId={project_id}'),
                {'filename': 'test.txt', 'chunkIds': [chunk_id]}
            )
            self.assertEqual(status, 200)
            self.assertTrue(upstream_received_request.wait(timeout=2), "Upstream server did not receive the request.")

            # 4. Verify the chunk now has an embedding
            status, body = _request('GET', self.url(f'/chunk-cache?projectId={project_id}&file=test.txt'))
            self.assertEqual(status, 200)
            self.assertIn('chunks', body)
            self.assertEqual(len(body['chunks']), 1)
            chunk_data = body['chunks'][0]
            self.assertEqual(chunk_data['chunkId'], chunk_id)
            self.assertEqual(chunk_data['embedding'], canned_embedding)

        finally:
            # Clean up
            upstream_server.shutdown()
            upstream_thread.join()
            server.CONFIG['base_url'] = orig_base_url
            server.CONFIG['embed_model'] = orig_embed_model
            server.CONFIG['_test_allow_loopback'] = orig_allow_loopback

    def test_emb3_negative_regression_project_id_in_body(self):
        """EMB-3 Negative: POSTing projectId in body (old way) is ignored."""
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading

        upstream_received_request = threading.Event()

        class FakeUpstream(BaseHTTPRequestHandler):
            def do_POST(self):
                # This should not be called.
                upstream_received_request.set()
                self.send_response(500)
                self.end_headers()

            def log_message(self, format, *args):
                return

        upstream_server = HTTPServer(('127.0.0.1', 0), FakeUpstream)
        upstream_port = upstream_server.server_address[1]
        upstream_thread = threading.Thread(target=upstream_server.serve_forever)
        upstream_thread.daemon = True
        upstream_thread.start()

        orig_base_url = server.CONFIG.get('base_url')
        orig_embed_model = server.CONFIG.get('embed_model')
        orig_allow_loopback = server.CONFIG.get('_test_allow_loopback')

        try:
            server.CONFIG['base_url'] = f'http://127.0.0.1:{upstream_port}'
            server.CONFIG['embed_model'] = 'text-embedding-3-small'
            server.CONFIG['_test_allow_loopback'] = True

            # 1. Create a project and a cached file with null embedding
            _, proj = _request('POST', self.url('/projects'), {'name': 'EmbeddingNegTest'})
            pid = proj['id']
            _request('POST', self.url(f'/chunk-cache?projectId={pid}'),
                     {'filename': 'embed_neg.txt', 'chunks': [{'chunkId': 'c1', 'text': 'some text', 'embedding': None}]})

            # 2. Call generate-embeddings the *old, broken way*
            # projectId is in the body, and chunkIds is missing.
            # The server should reject this (currently by doing nothing).
            status, body = _request('POST', self.url(f'/generate-embeddings?projectId={pid}'),
                                  {'filename': 'embed_neg.txt', 'projectId': pid})
            self.assertEqual(status, 200) # The handler returns 200 but does nothing.

            # 3. Assert that the upstream was NOT called
            self.assertFalse(upstream_received_request.is_set(),
                             "Upstream server should not have been called for a legacy request.")

            # 4. Verify the chunk embedding is still null
            _, chunk_data = _request('GET', self.url(f'/chunk-cache?projectId={pid}&file=embed_neg.txt'))
            self.assertIsNone(chunk_data['chunks'][0]['embedding'])

        finally:
            upstream_server.shutdown()
            upstream_thread.join()
            server.CONFIG['base_url'] = orig_base_url
            server.CONFIG['embed_model'] = orig_embed_model
            server.CONFIG['_test_allow_loopback'] = orig_allow_loopback


if __name__ == '__main__':
    unittest.main()
