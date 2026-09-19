import sys
from pathlib import Path

# REPO_ROOT: repo root (two levels up from backend/server.py).
# All runtime data dirs, .env, and requirements.txt are anchored here so
# existing user data is never orphaned when the backend lives in backend/.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Add project root to sys.path for consistent `from backend...` imports
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
import ipaddress
import json
import os
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from dotenv import load_dotenv
from datetime import datetime
import subprocess

# Handler mixin imports — placed AFTER all module-level constants and functions
# are defined in this file, so the mixins can safely import names from server.
# The actual import statements are deferred to just before the class declaration.
# STATIC_DIR: the directory served by SimpleHTTPRequestHandler (frontend assets).
STATIC_DIR = REPO_ROOT / 'frontend'
ENV_FILE = REPO_ROOT / '.env'
CACHE_DIR = REPO_ROOT / '.chunk_cache'
CACHE_DIR.mkdir(exist_ok=True)
# Per-project chunk cache: .chunk_cache/projects/<project_id>/
PROJECT_CACHE_DIR = CACHE_DIR / 'projects'
PROJECT_CACHE_DIR.mkdir(exist_ok=True)
HISTORY_FILE = REPO_ROOT / 'chat_history.json'
SESSIONS_DIR = REPO_ROOT / '.chat_sessions'
SESSIONS_DIR.mkdir(exist_ok=True)
RAW_RESPONSES_DIR = REPO_ROOT / '.raw_responses'
RAW_RESPONSES_DIR.mkdir(exist_ok=True)
PROJECTS_DIR = REPO_ROOT / '.projects'
PROJECTS_DIR.mkdir(exist_ok=True)
LOGS_DIR = REPO_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
# Per-session log file stamp: set once at import so every add_log() call within
# a single server run writes to the same JSONL file (e.g. 2026-06-27-143000-server.jsonl).
_LOG_SESSION_STAMP = datetime.now().strftime('%Y-%m-%d-%H%M%S')

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
        # Raw API response capture (#48-v1) — opt-in, off by default.
        # CAPTURE_RAW_RESPONSES=true|1|yes to enable.
        'capture_raw_responses': os.getenv('CAPTURE_RAW_RESPONSES', '').lower() in ('1', 'true', 'yes'),
        'raw_responses_max': max(1, int(os.getenv('RAW_RESPONSES_MAX', '200') or '200')),
        # Log file persistence (#49) — opt-in, off by default.
        # PERSIST_LOGS=true|1|yes to write JSONL log files to logs/.
        'persist_logs': os.getenv('PERSIST_LOGS', '').lower() in ('1', 'true', 'yes'),
        'log_file_max': max(1, int(os.getenv('LOG_FILE_MAX', '20') or '20')),
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


def get_project_memory_dir(project_id):
    """Resolve the absolute path to a project-scoped memory folder.

    Path: <vault>/<subdir>/projects/<safe_id>/memories
    Returns None if vault is unconfigured, project_id fails the slug guard,
    or the vault root does not exist.
    """
    import re as _re
    if not project_id or not _re.match(r'^[A-Za-z0-9_-]+$', str(project_id)):
        return None
    base = get_memory_dir()  # resolves <vault>/<subdir>/memories
    if base is None:
        return None
    vault = Path(os.path.expanduser(
        (CONFIG.get('obsidian_vault_path') or '').strip())).resolve()
    # Project memories live at <vault>/<subdir>/projects/<id>/memories
    subdir = (CONFIG.get('obsidian_memory_subdir') or 'USAi').strip()
    proj_dir = (vault / subdir / 'projects' / str(project_id) / 'memories').resolve()
    # Traversal guard: must remain inside the vault
    try:
        proj_dir.relative_to(vault)
    except ValueError:
        return None
    return proj_dir


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
    if CONFIG.get('_test_allow_loopback'):
        return True

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
    _persist_log(log_entry)


def _persist_log(entry):
    """Append one log entry as a JSON line to the session JSONL file in logs/.

    Opt-in: does nothing when PERSIST_LOGS is not enabled.
    Write failures are always swallowed — a logging failure must never break
    request handling. Secrets are never logged (same guarantee as add_log).
    Rotation: prune the oldest *.jsonl files (excluding the current session file)
    beyond log_file_max before each write so logs/ never grows unbounded.
    The log filename is server-generated (never from user input), so there is
    no path-traversal risk here.
    """
    if not CONFIG.get('persist_logs'):
        return
    try:
        cap = max(1, int(CONFIG.get('log_file_max') or 20))
        log_file = LOGS_DIR / f'{_LOG_SESSION_STAMP}-server.jsonl'
        # Rotation: enforce cap on number of session JSONL files, keeping the
        # current session file alive regardless of count.
        existing = sorted(
            LOGS_DIR.glob('*.jsonl'),
            key=lambda p: p.stat().st_mtime,
        )
        others = [p for p in existing if p != log_file]
        while len(others) >= cap:
            others.pop(0).unlink(missing_ok=True)
        with log_file.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(entry) + '\n')
    except Exception:  # nosec — persist failure must never break the caller
        pass


def _capture_raw_response(meta, raw_bytes, *, streamed=False):
    """Write one raw-response record to RAW_RESPONSES_DIR (opt-in).

    meta: dict containing timestamp, method, path, status, model (str or None).
    raw_bytes: the upstream response body bytes — stored verbatim (parsed as JSON
    when possible; falls back to a UTF-8 string on decode error).
    streamed: True when capturing a completed SSE stream; False (default) for
    non-streaming responses.

    Callers must wrap this in try/except — a capture failure must never break the
    proxy response that is already being sent to the client.

    Security: the Authorization header / API key is NEVER passed here and is never
    stored. Only response-body content and neutral request metadata are persisted.
    """
    import secrets as _secrets
    # Generate a collision-safe filename from the timestamp + 4 random hex bytes.
    ts_safe = meta['timestamp'].replace(':', '-').replace('.', '-')
    uid = _secrets.token_hex(4)
    filename = f"{ts_safe}_{uid}.json"
    dest = RAW_RESPONSES_DIR / filename  # server-generated name — no user input

    try:
        raw_parsed = json.loads(raw_bytes.decode('utf-8'))
    except Exception:
        raw_parsed = raw_bytes.decode('utf-8', errors='replace')

    record = {
        'id': filename,
        'timestamp': meta['timestamp'],
        'method': meta['method'],
        'path': meta['path'],
        'status': meta['status'],
        'streamed': streamed,
        'model': meta.get('model'),
        'raw': raw_parsed,
    }

    # Rotation: enforce the cap by deleting the oldest file(s) first.
    cap = max(1, int(CONFIG.get('raw_responses_max') or 200))
    existing = sorted(
        RAW_RESPONSES_DIR.glob('*.json'),
        key=lambda p: p.stat().st_mtime,
    )
    while len(existing) >= cap:
        existing.pop(0).unlink(missing_ok=True)

    dest.write_text(json.dumps(record), encoding='utf-8')
    add_log('info', 'capture', f'Raw response captured: {filename} status={meta["status"]}')


def generate_embeddings(texts):
    """Generate embeddings for a list of texts using the configured EMBED_MODEL."""
    embed_model = CONFIG.get('embed_model')
    base_url = CONFIG.get('base_url')
    api_key = CONFIG.get('api_key')

    if not embed_model:
        raise ValueError("Embedding model is not configured in .env (EMBED_MODEL)")
    if not base_url:
        raise ValueError("BASE_URL is not configured in .env")
    if not api_key:
        raise ValueError("API_KEY is not configured in .env")

    # Ensure base_url has a trailing slash for urljoin to work correctly.
    if not base_url.endswith('/'):
        base_url += '/'
    endpoint = urljoin(base_url, 'embeddings')
    if not is_safe_upstream_url(endpoint):
        add_log('error', 'embeddings', f'Unsafe upstream URL for embeddings: {endpoint}')
        raise ValueError(f"Embeddings endpoint URL is not safe: {endpoint}")

    payload = {
        "input": texts,
        "model": embed_model,
    }
    input_type = CONFIG.get('embed_input_type')
    if input_type:
        payload['input_type'] = input_type

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        req = Request(endpoint, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urlopen(req, timeout=60) as response:  # nosec B310 — url validated by is_safe_upstream_url
            resp_body = response.read()
            data = json.loads(resp_body)
            items = data.get("data", [])
            if not isinstance(items, list):
                raise ValueError("Embeddings response is missing 'data' array")

            # Sort by index to guarantee order matches the input `texts` array
            sorted_items = sorted(items, key=lambda x: x.get("index", 0))
            return [item.get("embedding") for item in sorted_items]
    except HTTPError as e:
        error_body = e.read().decode(errors='replace')
        add_log('error', 'embeddings', f'Upstream API error: {e.code}', {'body': error_body})
        raise ValueError(f"Embeddings API error: {e.code} - {error_body}") from e
    except Exception as e:
        add_log('error', 'embeddings', f'Embedding generation failed: {e}')
        raise ValueError(f"Embedding generation failed: {e}") from e


from backend.proxy_handlers import ProxyHandlersMixin
from backend.session_handlers import SessionHandlersMixin
from backend.memory_handlers import MemoryHandlersMixin
from backend.mcp_handlers import McpHandlersMixin
from backend.projects_handlers import ProjectsHandlersMixin
from backend.file_parser_handlers import FileParserHandlerMixin

class EnvConfigHTTPRequestHandler(
    ProxyHandlersMixin,
    SessionHandlersMixin,
    MemoryHandlersMixin,
    McpHandlersMixin,
    ProjectsHandlersMixin,
    FileParserHandlerMixin,
    SimpleHTTPRequestHandler
):
    # Stream tokens to the browser the moment they arrive instead of letting the
    # OS coalesce tiny SSE packets. Nagle's algorithm (on by default) buffers
    # small writes for up to ~40ms waiting for an ACK, which — combined with
    # many tiny token frames — adds noticeable latency to streamed responses.
    disable_nagle_algorithm = True







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
            # Boolean: whether raw API response capture is enabled (#48-v1).
            # Never expose the flag value itself — only the derived boolean.
            'has_raw_capture': bool(CONFIG.get('capture_raw_responses')),
            # Boolean: whether JSONL log file persistence is enabled (#49).
            # Never expose the flag value itself — only the derived boolean.
            'persist_logs': bool(CONFIG.get('persist_logs')),
            # Projects feature is always available (files stored in .projects/).
            'has_projects': True,
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(safe_config).encode('utf-8'))


    def _json_response(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)











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
            '/raw-responses': self._get_raw_responses,
            '/logs': self._get_logs,
            '/logs/files': self._get_log_files,
            '/projects': self._get_projects,
        }

        handler = routes.get(request_path)
        if handler:
            handler()
            return

        # /projects/<id> — single-project fetch (list-all is handled above).
        if request_path.startswith('/projects/'):
            project_id = request_path[len('/projects/'):]
            self._get_project(project_id)
            return

        if request_path.startswith('/api/'):
            self._proxy_api('GET')
            return

        super().do_GET()









    def do_POST(self):
        request_path = self.path.split('?', 1)[0]
        routes = {
            '/logs': self._post_logs,
            '/logs/clear': self._post_logs_clear,
            '/sessions': self._post_sessions,
            '/chat-history': self._post_chat_history,
            '/new-chat-session': self._post_new_chat_session,
            '/extract-text': self._post_extract_text,
            '/chunk-cache': self._post_chunk_cache,
            '/memory/save': self._memory_save,
            '/embeddings': self._post_embeddings,
            '/generate-embeddings': self._post_generate_embeddings,
            '/mcp/tool': self._post_mcp_tool,
            '/mcp/rename-tag': self._post_mcp_rename_tag,
            '/mcp/move-note': self._post_mcp_move_note,
            '/projects': self._post_projects,
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

    def do_PATCH(self):
        request_path = self.path.split('?', 1)[0]
        # PATCH /sessions/<id> — move a session into (or out of) a project.
        if request_path.startswith('/sessions/'):
            session_id = request_path[len('/sessions/'):]
            self._patch_session(session_id)
            return
        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        request_path = self.path.split('?', 1)[0]
        # /projects/<id>
        if request_path.startswith('/projects/'):
            project_id = request_path[len('/projects/'):]
            self._put_project(project_id)
            return
        self.send_response(404)
        self.end_headers()











    def do_DELETE(self):
        request_path = self.path.split('?', 1)[0]
        routes = {
            '/chunk-cache': self._delete_chunk_cache,
            '/sessions': self._delete_sessions,
            '/raw-responses': self._delete_raw_responses,
        }

        handler = routes.get(request_path)
        if handler:
            handler()
            return

        # /projects/<id>
        if request_path.startswith('/projects/'):
            project_id = request_path[len('/projects/'):]
            self._delete_project(project_id)
            return

        self.send_response(404)
        self.end_headers()


def run(host='127.0.0.1', port=8000):
    os.chdir(STATIC_DIR)
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
    requirements_file = REPO_ROOT / 'requirements.txt'
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
    _host = os.getenv('HOST', '127.0.0.1')
    _port = int(os.getenv('PORT', '8000'))
    run(host=_host, port=_port)

