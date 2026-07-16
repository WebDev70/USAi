"""session_handlers.py — Session, chat-history, chunk-cache, and log handler mixin.

Contains SessionHandlersMixin with all session/chunk-cache/log endpoint methods
extracted from EnvConfigHTTPRequestHandler (server.py backlog #45 module split).
"""

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import sys


class _ServerProxy:
    """Lazy proxy to the 'server' module — breaks the circular import at script startup.

    See proxy_handlers.py for the full explanation.
    """
    def __getattr__(self, name):
        return getattr(sys.modules['server'], name)


_server = _ServerProxy()


class SessionHandlersMixin:
    """Mixin providing session, chat-history, chunk-cache, and log handler methods.

    Methods rely on self being an HTTPRequestHandler instance with:
      - self.path, self.headers, self.rfile, self.wfile
      - self._json_response(), self._safe_project_id()
    """

    def _resolve_chunk_cache_dir(self, params):
        """Return (cache_dir: Path | None, error_code: int | None).

        When ?projectId=<id> is present the per-project sub-directory is returned
        after validating the id with _safe_project_id.  Returns (None, 400) when
        the id is a traversal attempt.  Falls back to the global CACHE_DIR when
        no projectId param is supplied.
        """
        project_id = params.get('projectId', [None])[0]
        if project_id:
            safe_id = self._safe_project_id(project_id)
            if safe_id is None:
                return None, 400
            proj_dir: Path = _server.PROJECT_CACHE_DIR / safe_id
            proj_dir.mkdir(parents=True, exist_ok=True)
            return proj_dir, None
        return _server.CACHE_DIR, None

    def _get_chunk_cache(self):
        params = parse_qs(urlparse(self.path).query)
        cache_dir, err = self._resolve_chunk_cache_dir(params)
        if err:
            self._json_response(400, {'error': 'Invalid project id'})
            return
        filename = params.get('file', [None])[0]
        if filename:
            safe_name = Path(filename).name
            cache_file = cache_dir / (safe_name + '.json')
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
            for p in sorted(cache_dir.glob('*.json')):
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
            session_file = _server.SESSIONS_DIR / (safe_id + '.json')
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
            for p in sorted(_server.SESSIONS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
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
        if _server.HISTORY_FILE.exists():
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(_server.HISTORY_FILE.read_bytes())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'turns': []}).encode('utf-8'))

    def _get_logs(self):
        """GET /logs — return the in-memory server_logs buffer as JSON array."""
        self._json_response(200, _server.server_logs)

    def _get_log_files(self):
        """GET /logs/files          → list session log files (newest first).
        GET /logs/files?name=<f>  → read one file as array of log entries.

        Path-traversal guard: name must be a plain filename with no path
        separators, no leading dot, and must resolve to inside LOGS_DIR.
        Returns {enabled, files} on list (200 even when PERSIST_LOGS=false).
        Returns 404 when named file not found; 400 on traversal attempt.
        Large files are capped at 500 entries (newest lines read first).
        Malformed JSONL lines are skipped silently.
        """
        params = parse_qs(urlparse(self.path).query)
        name = params.get('name', [None])[0]

        if name:
            # ── Read a specific log file ─────────────────────────────────────
            # Path-traversal guard (same pattern as /raw-responses).
            if '/' in name or '\\' in name or name.startswith('.'):
                self._json_response(400, {'error': 'Invalid name'})
                return
            safe_name = Path(name).name
            log_file = _server.LOGS_DIR / safe_name
            try:
                log_file.resolve().relative_to(_server.LOGS_DIR.resolve())
            except ValueError:
                self._json_response(400, {'error': 'Invalid name'})
                return
            if not log_file.exists():
                self._json_response(404, {'error': 'Not found'})
                return
            entries = []
            try:
                lines = log_file.read_text(encoding='utf-8').splitlines()
                # Cap at last 500 entries (newest = bottom of file)
                for line in lines[-500:]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass  # skip malformed lines
            except Exception:
                pass
            self._json_response(200, {'name': safe_name, 'entries': entries})
        else:
            # ── List all session log files ───────────────────────────────────
            enabled = bool(_server.CONFIG.get('persist_logs'))
            files = []
            try:
                for p in sorted(
                    _server.LOGS_DIR.glob('*.jsonl'),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True,
                ):
                    stat = p.stat()
                    files.append({
                        'name': p.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
            except Exception:
                pass
            self._json_response(200, {'enabled': enabled, 'files': files})

    def _post_logs(self):
        """POST /logs — receive a structured log entry from the frontend and
        store it in server_logs (and persist to JSONL when enabled).

        Body: {level, component, message, details?}
        Returns 200 {ok: true} on success, 400 on bad JSON, 413 when too large.
        """
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

            _server.add_log(level, component, message, details)

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
        _server.server_logs.clear()
        _server.add_log('info', 'server', 'Logs cleared')
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
            session_file = _server.SESSIONS_DIR / (safe_id + '.json')
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
            _server.HISTORY_FILE.write_text(json.dumps(data), encoding='utf-8')
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
        # Resolve target dir (project-scoped or global) before reading body so
        # we can return 400 on a bad projectId without consuming the body.
        params = parse_qs(urlparse(self.path).query)
        cache_dir, err = self._resolve_chunk_cache_dir(params)
        if err:
            self._json_response(400, {'error': 'Invalid project id'})
            return
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
            cache_file = cache_dir / (filename + '.json')
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

    def _post_new_chat_session(self):
        """POST /new-chat-session — archive the current chat_history.json into a session file.

        Accepts an optional JSON body with { projectId } to stamp the archived session.
        """
        # Read optional body (projectId).
        project_id = None
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body_raw = self.rfile.read(content_length).decode('utf-8')
                body_data = json.loads(body_raw)
                pid = (body_data.get('projectId') or '').strip()
                if pid:
                    project_id = pid
        except Exception:
            pass

        archived_id = None
        if _server.HISTORY_FILE.exists():
            try:
                data = json.loads(_server.HISTORY_FILE.read_text(encoding='utf-8'))
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
                    if project_id:
                        session_data['projectId'] = project_id
                    (_server.SESSIONS_DIR / (session_id + '.json')).write_text(
                        json.dumps(session_data), encoding='utf-8'
                    )
                    archived_id = session_id
            except Exception:
                pass
            _server.HISTORY_FILE.unlink()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True, 'archivedId': archived_id}).encode('utf-8'))

    def _delete_chunk_cache(self):
        params = parse_qs(urlparse(self.path).query)
        cache_dir, err = self._resolve_chunk_cache_dir(params)
        if err or cache_dir is None:
            self._json_response(400, {'error': 'Invalid project id'})
            return
        filename = params.get('file', [None])[0]
        if filename:
            safe_name = Path(filename).name
            cache_file = cache_dir / (safe_name + '.json')
            if cache_file.exists():
                cache_file.unlink()
        else:
            for p in cache_dir.glob('*.json'):
                p.unlink()
        self._json_response(200, {'ok': True})

    def _delete_sessions(self):
        params = parse_qs(urlparse(self.path).query)
        session_id = params.get('id', [None])[0]
        if session_id:
            safe_id = Path(session_id).name
            session_file = _server.SESSIONS_DIR / (safe_id + '.json')
            if session_file.exists():
                session_file.unlink()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True}).encode('utf-8'))
