"""proxy_handlers.py — API proxy, context7, embeddings, and raw-response handler mixin.

Contains ProxyHandlersMixin with all proxy-related methods extracted
from EnvConfigHTTPRequestHandler (server.py backlog #45 module split).
"""

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import sys


class _ServerProxy:
    """Lazy proxy to the 'server' module.

    Defers attribute access to sys.modules['server'] at call time rather than
    at import time. This breaks the circular-import that occurs when server.py
    is run as __main__: Python starts executing server.py, hits the deferred
    handler-mixin imports near the bottom of the file, and at that point
    the 'server' module object in sys.modules is only partially initialized.
    A top-level `import server` in a handler module would therefore capture an
    incomplete snapshot. The proxy avoids this by resolving names only when a
    mixin method is actually *called* — at which point server.py has finished
    executing and all module-level names are fully bound.
    """
    def __getattr__(self, name):
        return getattr(sys.modules['server'], name)


_server = _ServerProxy()


class ProxyHandlersMixin:
    """Mixin providing proxy/embeddings/context7/raw-responses handler methods.

    Methods rely on self being an HTTPRequestHandler instance with:
      - self.path, self.headers, self.rfile, self.wfile, self.protocol_version
      - self._json_response()
    """

    def _proxy_api(self, method, request_body=None):
        """Proxy /api/* requests to the base_url configured in .env.

        Every call — success, HTTP error, and network failure — is recorded via
        add_log so the full upstream conversation is visible in the debug panel
        and persisted to logs/*.jsonl (when PERSIST_LOGS=true).  The API key /
        Authorization header is NEVER logged.
        """
        config = _server.CONFIG
        base_url = config.get('base_url', '').rstrip('/')
        if not base_url:
            _server.add_log('error', 'proxy', 'base_url not configured — cannot proxy request',
                    {'method': method, 'path': self.path})
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'base_url not configured'}).encode('utf-8'))
            return

        upstream_url = base_url + self.path

        # SSRF guard — reject any URL that doesn't point at a public http/https host.
        # This makes the nosec B310 suppression below honest.
        # _test_allow_loopback is set only by the test suite; never set in production.
        if not _server.CONFIG.get('_test_allow_loopback') and not _server.is_safe_upstream_url(upstream_url):
            _server.add_log('error', 'proxy', 'SSRF guard rejected upstream URL',
                    {'method': method, 'path': self.path})
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'upstream URL rejected by SSRF guard'}).encode('utf-8'))
            return

        # Forward Authorization from client; fall back to server-configured key
        auth = self.headers.get('Authorization', '')
        if not auth and config.get('api_key'):
            auth = 'Bearer ' + config['api_key']

        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if auth:
            headers['Authorization'] = auth

        # Detect a streaming request so we can relay bytes as they arrive.
        # Also extract model name for log context (never the key).
        wants_stream = False
        req_model = None
        if request_body:
            try:
                parsed_body = json.loads(request_body)
                wants_stream = bool(parsed_body.get('stream'))
                req_model = parsed_body.get('model')
            except Exception:
                wants_stream = False

        _t0 = datetime.now()
        _server.add_log('info', 'proxy', f'→ {method} {self.path}',
                {'model': req_model, 'stream': wants_stream,
                 'body_bytes': len(request_body) if request_body else 0})
        try:
            req = Request(upstream_url, data=request_body, headers=headers, method=method)
            with urlopen(req) as resp:  # nosec B310 — URL validated by is_safe_upstream_url() above (http/https only)
                if wants_stream:
                    # Relay the Server-Sent Events stream chunk-by-chunk without buffering.
                    #
                    # CRITICAL: speak HTTP/1.1 with *chunked* transfer-encoding for
                    # the duration of this response. The handler's default protocol
                    # is HTTP/1.0, which has no streaming framing — the browser's
                    # fetch() ReadableStream then can't surface any bytes until the
                    # whole connection closes, so the entire reply appears at once
                    # after a long wait (the reported "1–2 min, all at once" bug).
                    # We emit each upstream block as its own HTTP chunk so tokens
                    # reach the browser the instant they arrive.
                    self.protocol_version = 'HTTP/1.1'
                    self.send_response(resp.status)
                    self.send_header('Content-Type', resp.headers.get('Content-Type', 'text/event-stream'))
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('X-Accel-Buffering', 'no')
                    self.send_header('Transfer-Encoding', 'chunked')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    # IMPORTANT: read from the RAW, unbuffered upstream stream.
                    # `urlopen()` returns an http.client.HTTPResponse whose
                    # `.read(n)` is line/block-buffered — it blocks until it can
                    # fill its internal buffer, so SSE tokens that trickle in one
                    # at a time would be withheld for seconds. `resp.fp.raw` (the
                    # underlying SocketIO) returns whatever bytes are currently
                    # available, so we forward each token immediately. Fall back
                    # to `resp.read` if `.raw` is unavailable.
                    raw = getattr(getattr(resp, 'fp', None), 'raw', None)
                    read_chunk = raw.read if raw is not None else resp.read
                    # v2: accumulate bytes for streaming capture (zero cost when off).
                    # Only allocate the buffer if capture is enabled — the relay loop
                    # is otherwise byte-for-byte identical to before.
                    capture_buf = bytearray() if _server.CONFIG.get('capture_raw_responses') else None
                    try:
                        while True:
                            chunk = read_chunk(8192)
                            if not chunk:
                                break
                            # HTTP/1.1 chunked framing: <hex-length>\r\n<data>\r\n
                            # Relay first — client never waits for capture I/O.
                            self.wfile.write(f'{len(chunk):X}\r\n'.encode('ascii'))
                            self.wfile.write(chunk)
                            self.wfile.write(b'\r\n')
                            self.wfile.flush()
                            if capture_buf is not None:
                                capture_buf += chunk
                        # Final zero-length chunk terminates the response body.
                        self.wfile.write(b'0\r\n\r\n')
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        # Client disconnected mid-stream; fall through to capture
                        # whatever bytes were buffered (best-effort partial capture).
                        pass
                    # Write streaming capture (best-effort, non-fatal).
                    if capture_buf is not None:
                        try:
                            _server._capture_raw_response(
                                {'timestamp': datetime.now().isoformat(),
                                 'method': method, 'path': self.path,
                                 'status': resp.status, 'model': req_model},
                                bytes(capture_buf),
                                streamed=True,
                            )
                        except Exception as cap_err:  # nosec — never break the proxy
                            _server.add_log('warn', 'capture',
                                    f'Streaming capture failed (non-fatal): {cap_err}')
                    return

                response_body = resp.read()
                response_status = resp.status
                content_type = resp.headers.get('Content-Type', 'application/json')
            # Raw-response capture (opt-in, non-streaming only).
            # Never captures the Authorization header — only response body + neutral metadata.
            if _server.CONFIG.get('capture_raw_responses'):
                try:
                    req_model = None
                    if request_body:
                        try:
                            req_model = json.loads(request_body).get('model')
                        except Exception:
                            pass
                    _server._capture_raw_response({
                        'timestamp': datetime.now().isoformat(),
                        'method': method,
                        'path': self.path,
                        'status': response_status,
                        'model': req_model,
                    }, response_body)
                except Exception as cap_err:  # nosec — capture failure must never break the proxy
                    _server.add_log('warn', 'capture', f'Capture failed (non-fatal): {cap_err}')
            self.send_response(response_status)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(response_body)
        except HTTPError as err:
            error_body = err.read()
            _elapsed = round((datetime.now() - _t0).total_seconds() * 1000)
            # Log first 500 bytes of upstream error for diagnosis (never the key).
            _server.add_log('error', 'proxy', f'upstream HTTP {err.code} {self.path}',
                    {'status': err.code, 'latency_ms': _elapsed, 'model': req_model,
                     'upstream_error': error_body[:500].decode('utf-8', errors='replace')})
            # Also capture error responses when capture is enabled.
            if _server.CONFIG.get('capture_raw_responses'):
                try:
                    _server._capture_raw_response({
                        'timestamp': datetime.now().isoformat(),
                        'method': method,
                        'path': self.path,
                        'status': err.code,
                        'model': None,
                    }, error_body)
                except Exception as cap_err:
                    _server.add_log('warn', 'capture', f'Capture failed on error response (non-fatal): {cap_err}')
            self.send_response(err.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_body)
        except URLError as err:
            _elapsed = round((datetime.now() - _t0).total_seconds() * 1000)
            _server.add_log('error', 'proxy', f'upstream unreachable {self.path}',
                    {'error': str(err), 'latency_ms': _elapsed, 'model': req_model,
                     'upstream': base_url})
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(err)}).encode('utf-8'))

    def _get_context7(self):
        query = parse_qs(urlparse(self.path).query).get('query', [''])[0]
        config = _server.CONFIG
        context7_key = config.get('context7_api_key', '')
        context7_base = config.get('context7_base_url', '')
        context7_path = config.get('context7_path', '/v1/context')
        context7_method = config.get('context7_method', 'GET').upper()

        if not context7_key or not context7_base:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'context7 configuration missing'}).encode('utf-8'))
            return

        target_url = urljoin(context7_base.rstrip('/') + '/', context7_path.lstrip('/'))

        # SSRF guard — context7_base_url is admin-configured, but we still validate
        # it makes the nosec B310 suppression on urlopen() below honest.
        # _test_allow_loopback is set only by the test suite; never set in production.
        if not _server.CONFIG.get('_test_allow_loopback') and not _server.is_safe_upstream_url(target_url):
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'context7 URL rejected by SSRF guard'}).encode('utf-8'))
            return

        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + context7_key,
        }
        req = None
        try:
            if context7_method == 'GET':
                target_url = target_url + '?' + urlencode({'query': query})
                req = Request(target_url, headers=headers, method='GET')
            else:
                body = json.dumps({'query': query}).encode('utf-8')
                headers['Content-Type'] = 'application/json'
                req = Request(target_url, data=body, headers=headers, method='POST')

            with urlopen(req) as resp:  # nosec B310 — URL built from context7_base_url (admin-configured, http/https only)
                response_data = resp.read()
                try:
                    parsed = json.loads(response_data)
                except Exception:
                    parsed = response_data.decode('utf-8', errors='ignore')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'data': parsed}).encode('utf-8'))
        except HTTPError as err:
            body = err.read().decode('utf-8', errors='ignore')
            self.send_response(err.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': body}).encode('utf-8'))
        except URLError as err:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(err)}).encode('utf-8'))

    def _post_embeddings(self):
        """POST /embeddings — proxy an embeddings request to the upstream API.

        Body: { input: string[] }  (OpenAI-compatible).
        Returns the upstream /v1/embeddings response verbatim.

        Guards:
        - 400 if EMBED_MODEL is not configured.
        - 400 if 'input' is missing or not a list.
        - 400 if input list is empty or too long (> 512 strings).
        - 502 if base_url passes SSRF check fails.
        - 413 if the payload exceeds 1 MB.
        """
        embed_model = _server.CONFIG.get('embed_model', '')
        if not embed_model:
            self._json_response(400, {'error': 'EMBED_MODEL not configured'})
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 1 * 1024 * 1024:  # 1 MB max
                self._json_response(413, {'error': 'Payload too large'})
                return
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
        except Exception as err:
            self._json_response(400, {'error': str(err)})
            return

        input_texts = data.get('input')
        if not isinstance(input_texts, list) or len(input_texts) == 0:
            self._json_response(400, {'error': '"input" must be a non-empty array'})
            return
        if len(input_texts) > 512:
            self._json_response(400, {'error': '"input" exceeds maximum of 512 strings'})
            return

        base_url = _server.CONFIG.get('base_url', '').rstrip('/')
        if not base_url:
            self._json_response(503, {'error': 'base_url not configured'})
            return

        embed_url = base_url + '/v1/embeddings'

        # SSRF guard — base_url is admin-configured; still must be a public URL.
        if not _server.CONFIG.get('_test_allow_loopback') and not _server.is_safe_upstream_url(embed_url):
            self._json_response(502, {'error': 'embed URL rejected by SSRF guard'})
            return

        api_key = _server.CONFIG.get('api_key', '')
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if api_key:
            headers['Authorization'] = 'Bearer ' + api_key

        # Resolve optional input_type (Cohere-style, ignored by OpenAI)
        input_type = _server.CONFIG.get('embed_input_type', 'search_document')
        payload = {'model': embed_model, 'input': input_texts}
        if input_type:
            payload['input_type'] = input_type

        try:
            req = Request(embed_url,
                          data=json.dumps(payload).encode('utf-8'),
                          headers=headers,
                          method='POST')
            with urlopen(req) as resp:  # nosec B310 — embed_url validated by is_safe_upstream_url()
                resp_body = resp.read()
                resp_status = resp.status
            self.send_response(resp_status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(resp_body)
        except HTTPError as err:
            err_body = err.read()
            self.send_response(err.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(err_body)
        except URLError as err:
            self._json_response(502, {'error': str(err)})

    def _get_raw_responses(self):
        """GET /raw-responses         → list metadata (newest first, no 'raw' field).
        GET /raw-responses?id=<name>  → full record including 'raw' payload, or 404.
        """
        params = parse_qs(urlparse(self.path).query)
        rec_id = params.get('id', [None])[0]
        if rec_id:
            # Path-traversal guard: reject any id that contains a path separator
            # (e.g. "../../etc/passwd") before even reducing to a basename.
            # Then additionally verify the resolved file stays inside RAW_RESPONSES_DIR.
            if '/' in rec_id or '\\' in rec_id or rec_id.startswith('.'):
                self._json_response(400, {'error': 'Invalid id'})
                return
            safe_name = Path(rec_id).name
            rec_file = _server.RAW_RESPONSES_DIR / safe_name
            try:
                rec_file.resolve().relative_to(_server.RAW_RESPONSES_DIR.resolve())
            except ValueError:
                self._json_response(400, {'error': 'Invalid id'})
                return
            if rec_file.exists():
                self._json_response(200, json.loads(rec_file.read_text(encoding='utf-8')))
            else:
                self._json_response(404, {'error': 'Not found'})
        else:
            entries = []
            for p in sorted(
                _server.RAW_RESPONSES_DIR.glob('*.json'),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            ):
                try:
                    data = json.loads(p.read_text(encoding='utf-8'))
                    entries.append({
                        'id': data.get('id', p.name),
                        'timestamp': data.get('timestamp', ''),
                        'method': data.get('method', ''),
                        'path': data.get('path', ''),
                        'status': data.get('status'),
                        'model': data.get('model'),
                    })
                except Exception:
                    pass
            self._json_response(200, entries)

    def _delete_raw_responses(self):
        """DELETE /raw-responses?id=<name>  → delete one record.
        DELETE /raw-responses               → clear all records.
        """
        params = parse_qs(urlparse(self.path).query)
        rec_id = params.get('id', [None])[0]
        if rec_id:
            # Path-traversal guard: reject any id that contains a path separator
            # (e.g. "../../etc/passwd") before even reducing to a basename.
            # Then additionally verify the resolved file stays inside RAW_RESPONSES_DIR.
            if '/' in rec_id or '\\' in rec_id or rec_id.startswith('.'):
                self._json_response(400, {'error': 'Invalid id'})
                return
            safe_name = Path(rec_id).name
            rec_file = _server.RAW_RESPONSES_DIR / safe_name
            try:
                rec_file.resolve().relative_to(_server.RAW_RESPONSES_DIR.resolve())
            except ValueError:
                self._json_response(400, {'error': 'Invalid id'})
                return
            if rec_file.exists():
                rec_file.unlink()
        else:
            for p in _server.RAW_RESPONSES_DIR.glob('*.json'):
                p.unlink(missing_ok=True)
        self._json_response(200, {'ok': True})
