"""Integration tests for the proxy and Context7 handlers, which talk to an
UPSTREAM HTTP server. We stand up a tiny stdlib HTTP server as the fake upstream
and point server.CONFIG at it — so these exercise _proxy_api and _get_context7
end-to-end with no network access and no third-party deps.
"""

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402
from tests.python.test_server_http import _request  # noqa: E402


class _FakeUpstreamHandler(BaseHTTPRequestHandler):
    """Echoes a canned JSON body and records the Authorization header it saw."""
    last_auth = None

    def log_message(self, *args):  # silence
        pass

    def _respond(self):
        _FakeUpstreamHandler.last_auth = self.headers.get('Authorization')
        payload = json.dumps({'ok': True, 'echoPath': self.path}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        # Drain any body just in case.
        self._respond()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        if length:
            self.rfile.read(length)
        self._respond()


class _StreamUpstreamHandler(BaseHTTPRequestHandler):
    """Emulates an SSE streaming upstream (used to exercise the relay branch).

    Uses HTTP/1.0 framing (end-of-body = connection close), which is how the
    proxy's urlopen detects the end of an un-Content-Lengthed stream.
    """

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        if length:
            self.rfile.read(length)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        for i in range(3):
            self.wfile.write(f'data: chunk{i}\n\n'.encode('utf-8'))
            self.wfile.flush()
            # A tiny pause between writes keeps the upstream socket "live" so the
            # proxy's raw, non-blocking reads always observe bytes rather than
            # racing the connection close (which made this test intermittently
            # see an empty body).
            time.sleep(0.02)
        self.wfile.write(b'data: [DONE]\n\n')
        self.wfile.flush()
        time.sleep(0.02)


class ProxyAndContext7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_config = dict(server.CONFIG)

        # Fake upstream API.
        cls._up = ThreadingHTTPServer(('127.0.0.1', 0), _FakeUpstreamHandler)
        cls._up_port = cls._up.server_address[1]
        cls._up_thread = threading.Thread(target=cls._up.serve_forever, daemon=True)
        cls._up_thread.start()
        upstream = f'http://127.0.0.1:{cls._up_port}'

        server.CONFIG = {
            'api_key': 'INJECTED-KEY',
            'base_url': upstream,
            'default_model': 'm',
            'default_system_prompt': '',
            'context7_api_key': 'CTX-KEY',
            'context7_base_url': upstream,
            'context7_path': '/ctx',
            'context7_method': 'GET',
            'obsidian_vault_path': '',
            'obsidian_memory_subdir': 'USAi',
        }

        # The app server under test.
        cls._app = ThreadingHTTPServer(('127.0.0.1', 0),
                                       server.EnvConfigHTTPRequestHandler)
        cls._app_port = cls._app.server_address[1]
        cls._app_thread = threading.Thread(target=cls._app.serve_forever, daemon=True)
        cls._app_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._app.shutdown(); cls._app.server_close()
        cls._up.shutdown(); cls._up.server_close()
        server.CONFIG = cls._saved_config

    def url(self, p):
        return f'http://127.0.0.1:{self._app_port}{p}'

    def test_proxy_injects_server_api_key_when_client_sends_none(self):
        status, body = _request('GET', self.url('/api/v1/models'))
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])
        # The proxy should have injected the server-side key as a Bearer token.
        self.assertEqual(_FakeUpstreamHandler.last_auth, 'Bearer INJECTED-KEY')

    def test_proxy_forwards_client_auth_when_provided(self):
        status, body = _request('POST', self.url('/api/v1/chat/completions'),
                                {'messages': []},
                                headers={'Authorization': 'Bearer CLIENT-KEY'})
        self.assertEqual(status, 200)
        self.assertEqual(_FakeUpstreamHandler.last_auth, 'Bearer CLIENT-KEY')

    def test_context7_success_wraps_upstream_data(self):
        status, body = _request('GET', self.url('/context7?query=react'))
        self.assertEqual(status, 200)
        self.assertTrue(body['ok'])
        # data is the upstream JSON we echoed back.
        self.assertEqual(body['data']['ok'], True)


class ProxyMisconfiguredTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_config = dict(server.CONFIG)
        server.CONFIG = dict(cls._saved_config)
        server.CONFIG['base_url'] = ''  # no upstream configured
        cls._app = ThreadingHTTPServer(('127.0.0.1', 0),
                                       server.EnvConfigHTTPRequestHandler)
        cls._port = cls._app.server_address[1]
        cls._thread = threading.Thread(target=cls._app.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._app.shutdown(); cls._app.server_close()
        server.CONFIG = cls._saved_config

    def test_proxy_503_when_base_url_missing(self):
        status, body = _request(
            'GET', f'http://127.0.0.1:{self._port}/api/v1/models')
        self.assertEqual(status, 503)
        self.assertIn('base_url', body['error'])


class _ErrorUpstreamHandler(BaseHTTPRequestHandler):
    """Always replies 500 so we can exercise the proxy/context7 error paths."""

    def log_message(self, *args):
        pass

    def _fail(self):
        body = json.dumps({'error': 'upstream boom'}).encode('utf-8')
        self.send_response(500)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._fail()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        if length:
            self.rfile.read(length)
        self._fail()


class ProxyUpstreamErrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_config = dict(server.CONFIG)
        cls._up = ThreadingHTTPServer(('127.0.0.1', 0), _ErrorUpstreamHandler)
        cls._up_port = cls._up.server_address[1]
        cls._up_thread = threading.Thread(target=cls._up.serve_forever, daemon=True)
        cls._up_thread.start()
        upstream = f'http://127.0.0.1:{cls._up_port}'
        server.CONFIG = dict(cls._saved_config)
        server.CONFIG.update({
            'api_key': 'k', 'base_url': upstream,
            'context7_api_key': 'ck', 'context7_base_url': upstream,
            'context7_path': '/ctx', 'context7_method': 'GET',
        })
        cls._app = ThreadingHTTPServer(('127.0.0.1', 0),
                                       server.EnvConfigHTTPRequestHandler)
        cls._port = cls._app.server_address[1]
        cls._thread = threading.Thread(target=cls._app.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._app.shutdown(); cls._app.server_close()
        cls._up.shutdown(); cls._up.server_close()
        server.CONFIG = cls._saved_config

    def url(self, p):
        return f'http://127.0.0.1:{self._port}{p}'

    def test_proxy_relays_upstream_error_status(self):
        # Upstream returns 500 → proxy relays the 500 (HTTPError branch).
        status, _ = _request('GET', self.url('/api/v1/models'))
        self.assertEqual(status, 500)

    def test_context7_relays_upstream_error(self):
        status, _ = _request('GET', self.url('/context7?query=x'))
        self.assertEqual(status, 500)


class ProxyUnreachableUpstreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_config = dict(server.CONFIG)
        # Point at a port nothing is listening on → URLError → 502.
        server.CONFIG = dict(cls._saved_config)
        server.CONFIG.update({
            'api_key': 'k', 'base_url': 'http://127.0.0.1:1',
            'context7_api_key': 'ck', 'context7_base_url': 'http://127.0.0.1:1',
            'context7_path': '/ctx', 'context7_method': 'GET',
        })
        cls._app = ThreadingHTTPServer(('127.0.0.1', 0),
                                       server.EnvConfigHTTPRequestHandler)
        cls._port = cls._app.server_address[1]
        cls._thread = threading.Thread(target=cls._app.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._app.shutdown(); cls._app.server_close()
        server.CONFIG = cls._saved_config

    def url(self, p):
        return f'http://127.0.0.1:{self._port}{p}'

    def test_proxy_502_on_unreachable_upstream(self):
        status, _ = _request('GET', self.url('/api/v1/models'))
        self.assertEqual(status, 502)

    def test_context7_502_on_unreachable_upstream(self):
        status, _ = _request('GET', self.url('/context7?query=x'))
        self.assertEqual(status, 502)


class _SlowStreamUpstreamHandler(BaseHTTPRequestHandler):
    """Emits SSE chunks with a real delay between them, so a test can prove the
    proxy relays each chunk AS IT ARRIVES (incrementally) rather than buffering
    the whole response and releasing it at the end."""

    inter_chunk_delay = 0.3  # seconds between chunks

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        if length:
            self.rfile.read(length)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        for i in range(4):
            self.wfile.write(f'data: chunk{i}\n\n'.encode('utf-8'))
            self.wfile.flush()
            if i < 3:
                time.sleep(self.inter_chunk_delay)
        self.wfile.write(b'data: [DONE]\n\n')
        self.wfile.flush()


class ProxyStreamingTests(unittest.TestCase):
    """Exercises the SSE relay branch of _proxy_api (stream:true)."""

    @classmethod
    def setUpClass(cls):
        cls._saved_config = dict(server.CONFIG)
        cls._up = ThreadingHTTPServer(('127.0.0.1', 0), _StreamUpstreamHandler)
        cls._up_port = cls._up.server_address[1]
        cls._up_thread = threading.Thread(target=cls._up.serve_forever, daemon=True)
        cls._up_thread.start()
        server.CONFIG = dict(cls._saved_config)
        server.CONFIG.update({
            'api_key': 'k', 'base_url': f'http://127.0.0.1:{cls._up_port}',
        })
        cls._app = ThreadingHTTPServer(('127.0.0.1', 0),
                                       server.EnvConfigHTTPRequestHandler)
        cls._port = cls._app.server_address[1]
        cls._thread = threading.Thread(target=cls._app.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._app.shutdown(); cls._app.server_close()
        cls._up.shutdown(); cls._up.server_close()
        server.CONFIG = cls._saved_config

    def test_streaming_response_is_relayed(self):
        # Use a raw socket and read until the connection closes. urlopen can race
        # on a chunked + Connection: close streaming response (intermittently
        # returning before the body is fully read), so we read the raw bytes
        # ourselves and just assert the SSE payload made it through.
        import socket
        body = json.dumps({'stream': True, 'messages': []}).encode('utf-8')
        request = (
            f'POST /api/v1/chat/completions HTTP/1.1\r\n'
            f'Host: 127.0.0.1:{self._port}\r\n'
            f'Content-Type: application/json\r\n'
            f'Content-Length: {len(body)}\r\n'
            f'Connection: close\r\n\r\n'
        ).encode('utf-8') + body

        s = socket.create_connection(('127.0.0.1', self._port), timeout=10)
        s.sendall(request)
        s.settimeout(10)
        received = b''
        while True:
            try:
                data = s.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            received += data
            if b'[DONE]' in received:
                break
        s.close()

        head = received.split(b'\r\n\r\n', 1)[0].lower()
        self.assertIn(b'http/1.1 200', head)
        self.assertIn(b'text/event-stream', head)
        self.assertIn(b'chunk0', received)
        self.assertIn(b'chunk2', received)
        self.assertIn(b'[DONE]', received)


class ProxyIncrementalStreamingTests(unittest.TestCase):
    """Regression test for the "responses take 2–5s to show up" bug.

    The proxy must relay each SSE chunk to the client AS IT ARRIVES, not buffer
    the whole upstream response and flush it at the end. We use a slow upstream
    (0.3s between 4 chunks) and assert the FIRST chunk reaches the client well
    before the LAST one — i.e. the time gap between first and last bytes is
    comparable to the upstream's own pacing, not ~0 (which would indicate the
    proxy released everything at once after buffering).
    """

    @classmethod
    def setUpClass(cls):
        cls._saved_config = dict(server.CONFIG)
        cls._up = ThreadingHTTPServer(('127.0.0.1', 0), _SlowStreamUpstreamHandler)
        cls._up_port = cls._up.server_address[1]
        cls._up_thread = threading.Thread(target=cls._up.serve_forever, daemon=True)
        cls._up_thread.start()
        server.CONFIG = dict(cls._saved_config)
        server.CONFIG.update({
            'api_key': 'k', 'base_url': f'http://127.0.0.1:{cls._up_port}',
        })
        cls._app = ThreadingHTTPServer(('127.0.0.1', 0),
                                       server.EnvConfigHTTPRequestHandler)
        cls._port = cls._app.server_address[1]
        cls._thread = threading.Thread(target=cls._app.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._app.shutdown(); cls._app.server_close()
        cls._up.shutdown(); cls._up.server_close()
        server.CONFIG = cls._saved_config

    def test_first_chunk_arrives_before_last(self):
        # Use a raw socket so we can time when individual chunks arrive, rather
        # than urlopen which may buffer until the response is complete.
        import socket
        body = json.dumps({'stream': True, 'messages': []}).encode('utf-8')
        request = (
            f'POST /api/v1/chat/completions HTTP/1.1\r\n'
            f'Host: 127.0.0.1:{self._port}\r\n'
            f'Content-Type: application/json\r\n'
            f'Content-Length: {len(body)}\r\n'
            f'Connection: close\r\n\r\n'
        ).encode('utf-8') + body

        s = socket.create_connection(('127.0.0.1', self._port), timeout=10)
        s.sendall(request)
        s.settimeout(10)

        first_chunk_at = None
        last_chunk_at = None
        seen = b''
        while True:
            try:
                data = s.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            now = time.monotonic()
            seen += data  # accumulate so markers split across recv() boundaries still match
            if first_chunk_at is None and b'data: chunk0' in seen:
                first_chunk_at = now
            if b'[DONE]' in seen:
                last_chunk_at = now
                break
        s.close()

        # The proxy must speak HTTP/1.1 with chunked transfer-encoding for the
        # stream. Under HTTP/1.0 (no Content-Length, no chunked) browsers'
        # fetch() ReadableStream withholds bytes until the connection closes —
        # which is exactly the "whole response appears at once" bug. Assert the
        # wire protocol so a regression to HTTP/1.0 fails loudly here.
        head = seen.split(b'\r\n\r\n', 1)[0].lower()
        self.assertIn(b'http/1.1 200', head)
        self.assertIn(b'transfer-encoding: chunked', head)

        self.assertIsNotNone(first_chunk_at, 'never received the first SSE chunk')
        self.assertIsNotNone(last_chunk_at, 'never received the [DONE] sentinel')
        gap = last_chunk_at - first_chunk_at
        # Upstream spaces 4 chunks by 0.3s ⇒ ~0.9s of spread. If the proxy relays
        # incrementally, the client sees a similar spread (allow generous slack).
        # If the proxy BUFFERS, first and last arrive together ⇒ gap ≈ 0.
        self.assertGreater(
            gap, 0.4,
            f'first→last chunk gap was only {gap:.3f}s — the proxy appears to be '
            f'buffering the stream instead of relaying chunks as they arrive.')


if __name__ == '__main__':
    unittest.main()
