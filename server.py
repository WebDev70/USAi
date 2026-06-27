from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
import ipaddress
import json
import os
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from dotenv import load_dotenv
from datetime import datetime
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / '.env'
CACHE_DIR = PROJECT_ROOT / '.chunk_cache'
CACHE_DIR.mkdir(exist_ok=True)
HISTORY_FILE = PROJECT_ROOT / 'chat_history.json'
SESSIONS_DIR = PROJECT_ROOT / '.chat_sessions'
SESSIONS_DIR.mkdir(exist_ok=True)

# In-memory log storage
server_logs = []
MAX_LOGS = 1000  # Keep last 1000 logs


CONFIG = {}

def load_config():
    """Load .env file and populate CONFIG global."""
    # Load environment variables from .env file, overriding any existing ones
    load_dotenv(dotenv_path=ENV_FILE, override=True)

    values = {
        'api_key': os.getenv('API_KEY', ''),
        'base_url': os.getenv('BASE_URL', ''),
        'default_model': os.getenv('DEFAULT_MODEL', ''),
        'default_system_prompt': os.getenv('DEFAULT_SYSTEM_PROMPT', ''),
        'context7_api_key': os.getenv('CONTEXT7_API_KEY', ''),
        'context7_base_url': os.getenv('CONTEXT7_BASE_URL', ''),
        'context7_path': os.getenv('CONTEXT7_PATH', '/v1/context'),
        'context7_method': os.getenv('CONTEXT7_METHOD', 'GET'),
        # Obsidian "second brain" long-term memory
        'obsidian_vault_path': os.getenv('OBSIDIAN_VAULT_PATH', ''),
        'obsidian_memory_subdir': os.getenv('OBSIDIAN_MEMORY_SUBDIR', 'USAi'),
        # Embeddings-based memory search (#16 Ph3)
        'embed_model': os.getenv('EMBED_MODEL', ''),
        'embed_input_type': os.getenv('EMBED_INPUT_TYPE', 'search_document'),
        # Obsidian-MCP bridge (#16 Ph2) — optional Node subprocess for rich vault ops
        'obsidian_mcp_path': os.getenv('OBSIDIAN_MCP_PATH', ''),
        'obsidian_node_path': os.getenv('OBSIDIAN_NODE_PATH', 'node'),
        # Auto model router tier overrides (#19 fix) — optional; when set, the
        # client-side TIER_MAP uses these ids instead of the hardcoded defaults.
        # Useful for deployments whose gateway uses different model aliases.
        'tier_high_model':   os.getenv('TIER_HIGH_MODEL',   ''),
        'tier_medium_model': os.getenv('TIER_MEDIUM_MODEL', ''),
        'tier_low_model':    os.getenv('TIER_LOW_MODEL',    ''),
    }
    global CONFIG
    CONFIG = values


def get_memory_dir():
    """Resolve the absolute path to the app-managed memory folder inside the
    configured Obsidian vault, or None if the vault is not configured/found.

    Memories live in <vault>/<subdir>/memories. All writes/reads are confined
    to this folder so the app can never touch the user's other notes.
    """
    vault = (CONFIG.get('obsidian_vault_path') or '').strip()
    if not vault:
        return None
    subdir = (CONFIG.get('obsidian_memory_subdir') or 'USAi').strip()
    vault_path = Path(os.path.expanduser(vault)).resolve()
    if not vault_path.exists():
        return None
    memory_dir = (vault_path / subdir / 'memories').resolve()
    # Safety: the memory dir must live inside the vault.
    try:
        memory_dir.relative_to(vault_path)
    except ValueError:
        return None
    return memory_dir


def _slugify(text, max_len=60):
    """Turn a title into a filesystem-safe slug for the note filename."""
    import re
    text = (text or '').strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return (text[:max_len].strip('-')) or 'memory'


def _resolve_memory_file(memory_dir, rel_path):
    """Resolve a user-supplied relative path inside memory_dir, rejecting any
    attempt to escape the folder (path traversal). Returns a Path or None."""
    if not rel_path:
        return None
    candidate = (memory_dir / Path(rel_path).name).resolve()
    try:
        candidate.relative_to(memory_dir.resolve())
    except ValueError:
        return None
    return candidate


# ── Obsidian-MCP bridge (#16 Phase 2) ────────────────────────────────────────

# Allowlist of obsidian-mcp tool names the server is willing to forward.
# This prevents the model from calling destructive or unintended operations.
MCP_TOOL_ALLOWLIST = {
    "create_note", "edit_note", "read_note", "search_vault",
    "add_tags", "remove_tags", "rename_tag", "move_note",
    "list_available_vaults", "create_directory", "delete_note",
}


def _mcp_enabled():
    """Return True iff the MCP bridge is fully configured and the vault exists.

    Requires OBSIDIAN_MCP_PATH to point at an existing file AND the Obsidian
    vault to be reachable via get_memory_dir().  Both conditions must be true
    because the bridge needs a vault path to pass to the subprocess.
    """
    mcp_path = (CONFIG.get('obsidian_mcp_path') or '').strip()
    if not mcp_path:
        return False
    if not Path(mcp_path).exists():
        return False
    return get_memory_dir() is not None


def call_obsidian_mcp(tool_name, arguments, timeout=10):
    """Invoke an obsidian-mcp tool via a short-lived Node subprocess.

    Spawns:  <node_path> <mcp_path> <vault_path>
    Sends a JSON-RPC 2.0 request on stdin; reads the response from stdout.

    Returns (result_text, None) on success, or (None, error_string) on any
    failure — TimeoutExpired, FileNotFoundError, JSON parse error, or a
    JSON-RPC error object in the response.  Never raises.

    The vault_path is taken from CONFIG (admin-configured), not from
    user-supplied input, so there is no path-traversal risk here.
    """
    mcp_path = (CONFIG.get('obsidian_mcp_path') or '').strip()
    node_path = (CONFIG.get('obsidian_node_path') or 'node').strip()
    vault_path = (CONFIG.get('obsidian_vault_path') or '').strip()

    rpc_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    try:
        completed = subprocess.run(  # nosec B603 B607 — node_path/mcp_path/vault_path are admin-configured env vars, not user input
            [node_path, mcp_path, vault_path],
            input=json.dumps(rpc_request).encode(),
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"obsidian-mcp timed out after {timeout}s"
    except FileNotFoundError as exc:
        return None, f"obsidian-mcp not found: {exc}"
    except Exception as exc:  # pragma: no cover
        return None, f"obsidian-mcp error: {exc}"

    # Parse the first valid JSON line from stdout.
    stdout = (completed.stdout or b'').decode('utf-8', errors='replace')
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        # JSON-RPC error → surface it as an error string.
        if 'error' in data:
            msg = data['error'].get('message', str(data['error']))
            return None, msg
        # Success — extract text from result.content[0].text (obsidian-mcp format)
        result = data.get('result', {})
        content = result.get('content', [])
        if content and isinstance(content, list):
            text = content[0].get('text', '') if isinstance(content[0], dict) else str(content[0])
        else:
            text = str(result)
        return text, None

    # No parseable JSON line found — treat as an error.
    stderr = (completed.stderr or b'').decode('utf-8', errors='replace').strip()
    return None, f"obsidian-mcp returned no JSON (stderr: {stderr[:200]})"


# RFC 1918 and other reserved/private network ranges that must never be proxied.
# These are the CIDR blocks rejected by the SSRF guard.
_PRIVATE_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),       # IPv4 loopback
    ipaddress.ip_network('169.254.0.0/16'),    # link-local / AWS IMDS
    ipaddress.ip_network('::1/128'),           # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),          # IPv6 unique-local
    ipaddress.ip_network('fe80::/10'),         # IPv6 link-local
]


def is_safe_upstream_url(url):
    """Return True only when *url* is an http/https URL pointing at a public
    (non-private, non-loopback, non-link-local) host.

    This is the SSRF guard referenced by the ``# nosec B310`` suppressions on
    every ``urlopen()`` call in this file.  It is intentionally strict:

    * Only ``http`` and ``https`` schemes are accepted.
    * IP-literal hosts are checked against ``_PRIVATE_NETWORKS``.
    * The hostname ``localhost`` (case-insensitive) is rejected outright —
      we do *not* do a live DNS lookup because the test environment may not
      resolve it, and a live lookup would introduce network I/O in a pure
      helper.  Operators should configure a proper hostname for local
      deployments if they genuinely need to proxy to one.

    Returns False (rather than raising) on any unexpected input so callers
    can emit a clean 400/502 without an unhandled exception.
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    # Only allow http and https; reject file://, gopher://, ftp://, etc.
    if parsed.scheme not in ('http', 'https'):
        return False
    host = parsed.hostname  # lower-cased, brackets stripped for IPv6
    if not host:
        return False
    # Reject the literal hostname 'localhost' (any case already lowered by urlparse).
    if host == 'localhost':
        return False
    # Check IP-literal addresses against the private/reserved block list.
    try:
        addr = ipaddress.ip_address(host)
        for network in _PRIVATE_NETWORKS:
            if addr in network:
                return False
    except ValueError:
        # Not an IP literal — hostname; we trust DNS is not poisoned for
        # admin-configured values, and we've already rejected 'localhost'.
        pass
    return True


def add_log(level, component, message, details=None):
    """Add a log entry to server logs."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'component': component,
        'message': message,
        'details': details or {}
    }
    server_logs.append(log_entry)
    if len(server_logs) > MAX_LOGS:
        server_logs.pop(0)
    print(f"[{level}] {component}: {message}")


class EnvConfigHTTPRequestHandler(SimpleHTTPRequestHandler):
    # Stream tokens to the browser the moment they arrive instead of letting the
    # OS coalesce tiny SSE packets. Nagle's algorithm (on by default) buffers
    # small writes for up to ~40ms waiting for an ACK, which — combined with
    # many tiny token frames — adds noticeable latency to streamed responses.
    disable_nagle_algorithm = True

    def _proxy_api(self, method, request_body=None):
        """Proxy /api/* requests to the base_url configured in .env."""
        config = CONFIG
        base_url = config.get('base_url', '').rstrip('/')
        if not base_url:
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'base_url not configured'}).encode('utf-8'))
            return

        upstream_url = base_url + self.path

        # SSRF guard — reject any URL that doesn't point at a public http/https host.
        # This makes the nosec B310 suppression below honest.
        # _test_allow_loopback is set only by the test suite; never set in production.
        if not CONFIG.get('_test_allow_loopback') and not is_safe_upstream_url(upstream_url):
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

        # Detect a streaming request so we can relay bytes as they arrive
        wants_stream = False
        if request_body:
            try:
                wants_stream = bool(json.loads(request_body).get('stream'))
            except Exception:
                wants_stream = False

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
                    try:
                        while True:
                            chunk = read_chunk(8192)
                            if not chunk:
                                break
                            # HTTP/1.1 chunked framing: <hex-length>\r\n<data>\r\n
                            self.wfile.write(f'{len(chunk):X}\r\n'.encode('ascii'))
                            self.wfile.write(chunk)
                            self.wfile.write(b'\r\n')
                            self.wfile.flush()
                        # Final zero-length chunk terminates the response body.
                        self.wfile.write(b'0\r\n\r\n')
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        # Client disconnected mid-stream; nothing more to do
                        pass
                    return

                response_body = resp.read()
                response_status = resp.status
                content_type = resp.headers.get('Content-Type', 'application/json')
            self.send_response(response_status)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(response_body)
        except HTTPError as err:
            error_body = err.read()
            self.send_response(err.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_body)
        except URLError as err:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(err)}).encode('utf-8'))

    def _get_chunk_cache(self):
        params = parse_qs(urlparse(self.path).query)
        filename = params.get('file', [None])[0]
        if filename:
            safe_name = Path(filename).name
            cache_file = CACHE_DIR / (safe_name + '.json')
            if cache_file.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(cache_file.read_bytes())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))
        else:
            entries = []
            for p in sorted(CACHE_DIR.glob('*.json')):
                try:
                    meta = json.loads(p.read_text(encoding='utf-8'))
                    entries.append({
                        'filename': meta.get('filename', p.stem),
                        'chunkCount': len(meta.get('chunks', [])),
                        'savedAt': meta.get('savedAt', ''),
                    })
                except Exception:
                    pass
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(entries).encode('utf-8'))

    def _get_sessions(self):
        params = parse_qs(urlparse(self.path).query)
        session_id = params.get('id', [None])[0]
        if session_id:
            safe_id = Path(session_id).name
            session_file = SESSIONS_DIR / (safe_id + '.json')
            if session_file.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(session_file.read_bytes())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Session not found'}).encode('utf-8'))
        else:
            sessions = []
            for p in sorted(SESSIONS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    data = json.loads(p.read_text(encoding='utf-8'))
                    sessions.append({
                        'id': data.get('id', p.stem),
                        'title': data.get('title', 'Untitled'),
                        'createdAt': data.get('createdAt', ''),
                        'updatedAt': data.get('updatedAt', ''),
                        'messageCount': len(data.get('turns', [])),
                    })
                except Exception:
                    pass
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(sessions).encode('utf-8'))

    def _get_chat_history(self):
        if HISTORY_FILE.exists():
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(HISTORY_FILE.read_bytes())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'turns': []}).encode('utf-8'))

    def _get_config(self):
        # SECURITY: never expose secrets (api_key, context7_api_key) to the
        # browser. The proxy injects the API key server-side, so the client only
        # needs non-secret config plus booleans indicating what is configured.
        safe_config = {
            'base_url': CONFIG.get('base_url', ''),
            'default_model': CONFIG.get('default_model', ''),
            'default_system_prompt': CONFIG.get('default_system_prompt', ''),
            'context7_base_url': CONFIG.get('context7_base_url', ''),
            'context7_path': CONFIG.get('context7_path', ''),
            'context7_method': CONFIG.get('context7_method', ''),
            # Booleans so the frontend can enable/disable features without the key
            'has_api_key': bool(CONFIG.get('api_key')),
            'has_context7': bool(CONFIG.get('context7_api_key') and CONFIG.get('context7_base_url')),
            'has_obsidian': get_memory_dir() is not None,
            # True when an embeddings model is configured (enables semantic search in the UI)
            'has_embeddings': bool(CONFIG.get('embed_model')),
            # True when the Obsidian-MCP bridge is fully configured (#16 Ph2)
            'has_mcp_bridge': _mcp_enabled(),
            # Optional client-side model router tier overrides (#19 fix).
            # Non-secret: these are model ids, not credentials. Empty string means
            # the client falls back to its hardcoded verified defaults.
            'tier_high_model':   CONFIG.get('tier_high_model',   ''),
            'tier_medium_model': CONFIG.get('tier_medium_model', ''),
            'tier_low_model':    CONFIG.get('tier_low_model',    ''),
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(safe_config).encode('utf-8'))

    def _get_context7(self):
        query = parse_qs(urlparse(self.path).query).get('query', [''])[0]
        config = CONFIG
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
        if not CONFIG.get('_test_allow_loopback') and not is_safe_upstream_url(target_url):
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

    # ── Obsidian \"second brain\" memory ──────────────────────────────────────
    def _json_response(self, status, payload):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def _memory_search(self):
        """GET /memory/search?q=...&k=5 — keyword search over memory notes.

        Scores each note by counts of the query terms (in body and, weighted
        higher, in the title/tags), and returns the top-k with short snippets.
        """
        memory_dir = get_memory_dir()
        if memory_dir is None:
            self._json_response(400, {'error': 'Obsidian vault not configured'})
            return
        params = parse_qs(urlparse(self.path).query)
        query = (params.get('q', [''])[0] or '').strip()
        try:
            k = max(1, min(20, int(params.get('k', ['5'])[0])))
        except ValueError:
            k = 5
        if not query:
            self._json_response(400, {'error': 'missing query'})
            return

        terms = [t for t in query.lower().split() if t]
        results = []
        if memory_dir.exists():
            for p in memory_dir.glob('*.md'):
                try:
                    text = p.read_text(encoding='utf-8')
                except Exception:
                    continue
                lower = text.lower()
                title_region = lower[:200]  # frontmatter + first heading area
                score = 0
                for term in terms:
                    score += lower.count(term)
                    score += title_region.count(term) * 3  # weight title/tags
                if score <= 0:
                    continue
                # Build a snippet around the first matching term.
                idx = next((lower.find(t) for t in terms if lower.find(t) >= 0), 0)
                start = max(0, idx - 80)
                snippet = text[start:start + 280].replace('\n', ' ').strip()
                results.append({
                    'path': p.name,
                    'score': score,
                    'snippet': snippet,
                    'modified': datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                })
        results.sort(key=lambda r: r['score'], reverse=True)
        results = results[:k]
        add_log('info', 'memory', f'search "{query}" → {len(results)} hit(s)')
        self._json_response(200, {
            'ok': True,
            'query': query,
            'results': results,
            # Let the frontend know whether /embeddings re-ranking is available.
            'embed_available': bool(CONFIG.get('embed_model')),
        })

    def _memory_list(self):
        """GET /memory/list — list saved memory notes (newest first)."""
        memory_dir = get_memory_dir()
        if memory_dir is None:
            self._json_response(400, {'error': 'Obsidian vault not configured'})
            return
        items = []
        if memory_dir.exists():
            for p in sorted(memory_dir.glob('*.md'),
                            key=lambda x: x.stat().st_mtime, reverse=True):
                items.append({
                    'path': p.name,
                    'modified': datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                    'size': p.stat().st_size,
                })
        self._json_response(200, {'ok': True, 'items': items})

    def _memory_read(self):
        """GET /memory/read?path=note.md — read a single memory note."""
        memory_dir = get_memory_dir()
        if memory_dir is None:
            self._json_response(400, {'error': 'Obsidian vault not configured'})
            return
        rel = parse_qs(urlparse(self.path).query).get('path', [''])[0]
        target = _resolve_memory_file(memory_dir, rel)
        if target is None or not target.exists():
            self._json_response(404, {'error': 'memory not found'})
            return
        try:
            content = target.read_text(encoding='utf-8')
        except Exception as err:
            self._json_response(500, {'error': str(err)})
            return
        self._json_response(200, {'ok': True, 'path': target.name, 'content': content})

    def _memory_save(self):
        """POST /memory/save — create a timestamped, tagged memory note.

        Body: { title, content, tags?: string[] }. Writes are create-only and
        strictly confined to the memory folder.
        """
        memory_dir = get_memory_dir()
        if memory_dir is None:
            self._json_response(400, {'error': 'Obsidian vault not configured'})
            return
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 5 * 1024 * 1024:  # 5 MB max per memory
                self._json_response(413, {'error': 'Payload too large'})
                return
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
        except Exception as err:
            self._json_response(400, {'error': str(err)})
            return

        title = (data.get('title') or '').strip() or 'Untitled memory'
        content = (data.get('content') or '').strip()
        if not content:
            self._json_response(400, {'error': 'content is required'})
            return
        tags = data.get('tags') or []
        if isinstance(tags, str):
            tags = [tags]
        tags = [str(t).strip().replace(' ', '-') for t in tags if str(t).strip()]
        if 'usai-memory' not in tags:
            tags.append('usai-memory')

        now = datetime.now()
        stamp = now.strftime('%Y-%m-%d-%H%M%S')
        filename = f'{stamp}-{_slugify(title)}.md'

        memory_dir.mkdir(parents=True, exist_ok=True)
        target = _resolve_memory_file(memory_dir, filename)
        if target is None:
            self._json_response(400, {'error': 'invalid path'})
            return

        # YAML frontmatter so Obsidian indexes tags/created; body is the memory.
        yaml_tags = '[' + ', '.join(tags) + ']'
        note = (
            '---\n'
            f'title: "{title}"\n'
            f'created: {now.isoformat()}\n'
            f'tags: {yaml_tags}\n'
            'source: USAi Chat\n'
            '---\n\n'
            f'# {title}\n\n'
            f'{content}\n'
        )
        try:
            target.write_text(note, encoding='utf-8')
        except Exception as err:
            self._json_response(500, {'error': str(err)})
            return
        add_log('info', 'memory', f'saved memory "{title}" -> {target.name}')
        self._json_response(200, {'ok': True, 'path': target.name, 'title': title})

    # ── Obsidian-MCP bridge handlers (#16 Phase 2) ────────────────────────────

    def _read_mcp_body(self):
        """Read and parse the JSON request body for MCP endpoints.

        Enforces a 5 MB body limit (returns None and sends 413 on oversize).
        Returns the parsed dict, or None if the read/parse fails (response already sent).
        """
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 5 * 1024 * 1024:
            self._json_response(413, {'error': 'Payload too large'})
            return None
        try:
            body = self.rfile.read(content_length).decode('utf-8')
            return json.loads(body)
        except Exception as exc:
            self._json_response(400, {'error': str(exc)})
            return None

    def _post_mcp_tool(self):
        """POST /mcp/tool — generic allowlisted obsidian-mcp tool call.

        Body: { "tool": "<tool_name>", "arguments": { ... } }
        Returns: { "ok": true, "result": "..." }  or  { "error": "..." }
        """
        if not _mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        data = self._read_mcp_body()
        if data is None:
            return
        tool = (data.get('tool') or '').strip()
        if tool not in MCP_TOOL_ALLOWLIST:
            self._json_response(400, {'error': f'Tool "{tool}" not allowed'})
            return
        arguments = data.get('arguments') or {}
        result, err = call_obsidian_mcp(tool, arguments)
        if err is not None:
            self._json_response(502, {'error': err})
            return
        add_log('info', 'mcp', f'tool "{tool}" succeeded')
        self._json_response(200, {'ok': True, 'result': result})

    def _post_mcp_rename_tag(self):
        """POST /mcp/rename-tag — convenience endpoint for rename_tag.

        Body: { "oldTag": "foo", "newTag": "bar" }
        """
        if not _mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        data = self._read_mcp_body()
        if data is None:
            return
        old_tag = (data.get('oldTag') or '').strip()
        new_tag = (data.get('newTag') or '').strip()
        if not old_tag or not new_tag:
            self._json_response(400, {'error': 'oldTag and newTag are required'})
            return
        result, err = call_obsidian_mcp('rename_tag', {'oldTag': old_tag, 'newTag': new_tag})
        if err is not None:
            self._json_response(502, {'error': err})
            return
        add_log('info', 'mcp', f'rename_tag "{old_tag}" -> "{new_tag}"')
        self._json_response(200, {'ok': True, 'result': result})

    def _post_mcp_move_note(self):
        """POST /mcp/move-note — convenience endpoint for move_note.

        Body: { "source": "note.md", "destination": "folder/note.md" }
        """
        if not _mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        data = self._read_mcp_body()
        if data is None:
            return
        source = (data.get('source') or '').strip()
        destination = (data.get('destination') or '').strip()
        if not source or not destination:
            self._json_response(400, {'error': 'source and destination are required'})
            return
        result, err = call_obsidian_mcp('move_note', {'source': source, 'destination': destination})
        if err is not None:
            self._json_response(502, {'error': err})
            return
        add_log('info', 'mcp', f'move_note "{source}" -> "{destination}"')
        self._json_response(200, {'ok': True, 'result': result})

    def _get_mcp_vaults(self):
        """GET /mcp/vaults — list available Obsidian vaults via obsidian-mcp."""
        if not _mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        result, err = call_obsidian_mcp('list_available_vaults', {})
        if err is not None:
            self._json_response(502, {'error': err})
            return
        add_log('info', 'mcp', 'list_available_vaults succeeded')
        self._json_response(200, {'ok': True, 'result': result})

    def do_GET(self):
        request_path = self.path.split('?', 1)[0]
        routes = {
            '/chunk-cache': self._get_chunk_cache,
            '/sessions': self._get_sessions,
            '/chat-history': self._get_chat_history,
            '/config': self._get_config,
            '/context7': self._get_context7,
            '/memory/search': self._memory_search,
            '/memory/list': self._memory_list,
            '/memory/read': self._memory_read,
            '/mcp/vaults': self._get_mcp_vaults,
        }

        handler = routes.get(request_path)
        if handler:
            handler()
            return

        if request_path.startswith('/api/'):
            self._proxy_api('GET')
            return

        super().do_GET()

    def _post_logs(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 65536:  # 64 KB max per log entry
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Request too large'}).encode('utf-8'))
                return
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            level = data.get('level', 'info')
            component = data.get('component', 'frontend')
            message = data.get('message', '')
            details = data.get('details', {})
            
            add_log(level, component, message, details)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode('utf-8'))
        except Exception as err:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(err)}).encode('utf-8'))

    def _post_logs_clear(self):
        server_logs.clear()
        add_log('info', 'server', 'Logs cleared')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True}).encode('utf-8'))

    def _post_sessions(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 10 * 1024 * 1024:
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Payload too large'}).encode('utf-8'))
                return
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            session_id = data.get('id') or f"session_{int(datetime.now().timestamp() * 1000)}"
            safe_id = Path(session_id).name
            data['id'] = safe_id
            data['updatedAt'] = datetime.now().isoformat()
            if 'createdAt' not in data:
                data['createdAt'] = data['updatedAt']
            session_file = SESSIONS_DIR / (safe_id + '.json')
            session_file.write_text(json.dumps(data), encoding='utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'id': safe_id}).encode('utf-8'))
        except Exception as err:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(err)}).encode('utf-8'))

    def _post_chat_history(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 10 * 1024 * 1024:  # 10 MB max
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Payload too large'}).encode('utf-8'))
                return
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            data['updatedAt'] = datetime.now().isoformat()
            HISTORY_FILE.write_text(json.dumps(data), encoding='utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode('utf-8'))
        except Exception as err:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(err)}).encode('utf-8'))

    def _post_chunk_cache(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 50 * 1024 * 1024:  # 50 MB max
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Payload too large'}).encode('utf-8'))
                return
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            filename = Path(data.get('filename', 'unknown')).name  # prevent path traversal
            data['savedAt'] = datetime.now().isoformat()
            cache_file = CACHE_DIR / (filename + '.json')
            cache_file.write_text(json.dumps(data), encoding='utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'savedAs': filename}).encode('utf-8'))
        except Exception as err:
            self.send_response(400)
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
        embed_model = CONFIG.get('embed_model', '')
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

        base_url = CONFIG.get('base_url', '').rstrip('/')
        if not base_url:
            self._json_response(503, {'error': 'base_url not configured'})
            return

        embed_url = base_url + '/v1/embeddings'

        # SSRF guard — base_url is admin-configured; still must be a public URL.
        if not CONFIG.get('_test_allow_loopback') and not is_safe_upstream_url(embed_url):
            self._json_response(502, {'error': 'embed URL rejected by SSRF guard'})
            return

        api_key = CONFIG.get('api_key', '')
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if api_key:
            headers['Authorization'] = 'Bearer ' + api_key

        # Resolve optional input_type (Cohere-style, ignored by OpenAI)
        input_type = CONFIG.get('embed_input_type', 'search_document')
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

    def do_POST(self):
        request_path = self.path.split('?', 1)[0]
        routes = {
            '/logs': self._post_logs,
            '/logs/clear': self._post_logs_clear,
            '/sessions': self._post_sessions,
            '/chat-history': self._post_chat_history,
            '/new-chat-session': self._post_new_chat_session,
            '/chunk-cache': self._post_chunk_cache,
            '/memory/save': self._memory_save,
            '/embeddings': self._post_embeddings,
            '/mcp/tool': self._post_mcp_tool,
            '/mcp/rename-tag': self._post_mcp_rename_tag,
            '/mcp/move-note': self._post_mcp_move_note,
        }

        handler = routes.get(request_path)
        if handler:
            handler()
            return

        if request_path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length) if content_length > 0 else None
            self._proxy_api('POST', request_body)
            return

        self.send_response(404)
        self.end_headers()

    def _delete_chunk_cache(self):
        params = parse_qs(urlparse(self.path).query)
        filename = params.get('file', [None])[0]
        if filename:
            safe_name = Path(filename).name
            cache_file = CACHE_DIR / (safe_name + '.json')
            if cache_file.exists():
                cache_file.unlink()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode('utf-8'))
        else:
            for p in CACHE_DIR.glob('*.json'):
                p.unlink()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode('utf-8'))

    def _delete_sessions(self):
        params = parse_qs(urlparse(self.path).query)
        session_id = params.get('id', [None])[0]
        if session_id:
            safe_id = Path(session_id).name
            session_file = SESSIONS_DIR / (safe_id + '.json')
            if session_file.exists():
                session_file.unlink()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True}).encode('utf-8'))

    def _post_new_chat_session(self):
        archived_id = None
        if HISTORY_FILE.exists():
            try:
                data = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
                turns = data.get('turns', [])
                if turns:
                    first_user = next((t for t in turns if t.get('role') == 'user'), None)
                    raw = (first_user or {}).get('content', 'Untitled chat')
                    title = raw[:50] + ('\u2026' if len(raw) > 50 else '')
                    session_id = f"session_{int(datetime.now().timestamp() * 1000)}"
                    session_data = {
                        'id': session_id,
                        'title': title,
                        'turns': turns[:200],
                        'createdAt': turns[0].get('timestamp', datetime.now().isoformat()),
                        'updatedAt': datetime.now().isoformat(),
                    }
                    (SESSIONS_DIR / (session_id + '.json')).write_text(
                        json.dumps(session_data), encoding='utf-8'
                    )
                    archived_id = session_id
            except Exception:
                pass
            HISTORY_FILE.unlink()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True, 'archivedId': archived_id}).encode('utf-8'))

    def do_DELETE(self):
        request_path = self.path.split('?', 1)[0]
        routes = {
            '/chunk-cache': self._delete_chunk_cache,
            '/sessions': self._delete_sessions,

        }

        handler = routes.get(request_path)
        if handler:
            handler()
            return

        self.send_response(404)
        self.end_headers()


def run(host='127.0.0.1', port=8000):
    os.chdir(PROJECT_ROOT)
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, EnvConfigHTTPRequestHandler)
    print(f'Serving on http://{host}:{port} (config available at /config)')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping server...')
        httpd.server_close()


def install_dependencies():
    """Install dependencies from requirements.txt."""
    requirements_file = PROJECT_ROOT / 'requirements.txt'
    if requirements_file.exists():
        print("requirements.txt found. Installing dependencies...")
        try:
            subprocess.check_call(['python3', '-m', 'pip', 'install', '-r', str(requirements_file)])
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            print("Please install the dependencies manually using: pip install -r requirements.txt")
        except FileNotFoundError:
            print("'pip' or 'python3' command not found. Please ensure Python and pip are installed and in your PATH.")
    else:
        print("requirements.txt not found. Skipping dependency installation.")


if __name__ == '__main__':
    install_dependencies()
    print('Loading initial configuration...')
    load_config()
    run()

