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


if __name__ == '__main__':
    unittest.main()
