"""projects_handlers.py — Projects CRUD handler mixin.

Contains ProjectsHandlersMixin with all /projects endpoint methods extracted
from EnvConfigHTTPRequestHandler (server.py backlog #45 module split).
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

import sys


class _ServerProxy:
    """Lazy proxy to the 'server' module — breaks the circular import at script startup.

    See proxy_handlers.py for the full explanation.
    """
    def __getattr__(self, name):
        mod = sys.modules.get('server') or sys.modules.get('__main__')
        return getattr(mod, name)


_server = _ServerProxy()


class ProjectsHandlersMixin:
    """Mixin providing /projects CRUD handler methods for EnvConfigHTTPRequestHandler.

    Methods rely on self being an HTTPRequestHandler instance with:
      - self.path, self.headers, self.rfile, self.wfile
      - self._json_response()
      - self._INSTRUCTIONS_MAX (class attribute defined in EnvConfigHTTPRequestHandler)
    """

    # ── Projects CRUD (#projects-slice1) ──────────────────────────────────────

    # Maximum byte length for project instructions (8 KiB).
    _INSTRUCTIONS_MAX = 8192

    def _safe_project_id(self, raw_id):
        """Validate a project id from the URL path.

        Returns the sanitised id string, or None if it looks like a traversal
        attempt (contains '/', '\\', or starts with '.').
        """
        if not raw_id:
            return None
        if '/' in raw_id or '\\' in raw_id or raw_id.startswith('.'):
            return None
        return Path(raw_id).name

    def _get_projects(self):
        """GET /projects — list all projects sorted by createdAt descending."""
        projects = []
        for p in _server.PROJECTS_DIR.glob('*.json'):
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                projects.append(data)
            except Exception:
                pass
        # Sort newest-first by createdAt; fall back to file mtime.
        projects.sort(
            key=lambda x: x.get('createdAt', ''),
            reverse=True,
        )
        self._json_response(200, projects)

    def _get_project(self, project_id):
        """GET /projects/<id> — fetch a single project by id.

        Returns 400 on traversal attempt, 404 if the project file doesn't exist,
        otherwise 200 + the project JSON. Used by the frontend when opening a
        project (openProject) and when restoring a session that belongs to a
        project (restoreSession) so both flows see the same, single source of
        project metadata instead of relying on a list-scan the client has to
        do itself.
        """
        safe_id = self._safe_project_id(project_id)
        if safe_id is None:
            self._json_response(400, {'error': 'Invalid project id'})
            return
        proj_file = _server.PROJECTS_DIR / f'{safe_id}.json'
        if not proj_file.exists():
            self._json_response(404, {'error': 'Project not found'})
            return
        try:
            data = json.loads(proj_file.read_text(encoding='utf-8'))
        except Exception as err:
            self._json_response(500, {'error': str(err)})
            return
        self._json_response(200, data)

    def _post_projects(self):
        """POST /projects — create a new project.

        Body: { name, memoryMode?, instructions? }
        Returns 201 + {id, name, memoryMode, pinned, instructions, createdAt}.
        Returns 400 if name is missing/blank or instructions exceed 8 KiB.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 64 * 1024:  # 64 KB max
                self._json_response(413, {'error': 'Payload too large'})
                return
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
        except Exception as err:
            self._json_response(400, {'error': str(err)})
            return

        name = (data.get('name') or '').strip()
        if not name:
            self._json_response(400, {'error': 'name is required'})
            return

        instructions = (data.get('instructions') or '').strip()
        if len(instructions.encode('utf-8')) > self._INSTRUCTIONS_MAX:
            self._json_response(400, {'error': 'instructions too long'})
            return

        memory_mode = (data.get('memoryMode') or 'default').strip()
        now = datetime.now().isoformat()
        # Use microsecond-precision timestamp + 6-char uuid hex suffix so that two
        # projects created in the same millisecond (e.g. rapid test POSTs) still get
        # distinct IDs and distinct filenames — preventing the second project from
        # silently overwriting the first.
        project_id = f"project_{int(datetime.now().timestamp() * 1_000_000)}_{uuid.uuid4().hex[:6]}"
        project = {
            'id': project_id,
            'name': name,
            'memoryMode': memory_mode,
            'pinned': False,
            'instructions': instructions,
            'createdAt': now,
            'updatedAt': now,
        }
        (_server.PROJECTS_DIR / f'{project_id}.json').write_text(
            json.dumps(project), encoding='utf-8'
        )
        _server.add_log('info', 'projects', f'Created project "{name}" ({project_id})')
        self._json_response(201, project)

    # Valid values for a project's memoryMode field. Any other value in a PUT
    # body is rejected with 400 rather than silently ignored, so the frontend
    # gets clear feedback instead of a mismatch that only surfaces later when
    # memory search/save behaves unexpectedly.
    _VALID_MEMORY_MODES = ('default', 'project-only')

    def _put_project(self, project_id):
        """PUT /projects/<id> — update name, pinned, instructions, and/or memoryMode.

        memoryMode was previously immutable after creation; it is now editable
        so users can switch a project between shared ("default") and private
        ("project-only") memory scoping without recreating the project. Only
        the values in _VALID_MEMORY_MODES are accepted.
        Returns 400 on traversal attempt or invalid memoryMode, 404 if not found.
        """
        safe_id = self._safe_project_id(project_id)
        if safe_id is None:
            self._json_response(400, {'error': 'Invalid project id'})
            return
        proj_file = _server.PROJECTS_DIR / f'{safe_id}.json'
        if not proj_file.exists():
            self._json_response(404, {'error': 'Project not found'})
            return
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 64 * 1024:
                self._json_response(413, {'error': 'Payload too large'})
                return
            body = self.rfile.read(content_length).decode('utf-8')
            updates = json.loads(body)
        except Exception as err:
            self._json_response(400, {'error': str(err)})
            return

        project = json.loads(proj_file.read_text(encoding='utf-8'))
        if 'name' in updates:
            name = (updates['name'] or '').strip()
            if name:
                project['name'] = name
        if 'pinned' in updates:
            project['pinned'] = bool(updates['pinned'])
        if 'instructions' in updates:
            inst = (updates['instructions'] or '').strip()
            if len(inst.encode('utf-8')) > self._INSTRUCTIONS_MAX:
                self._json_response(400, {'error': 'instructions too long'})
                return
            project['instructions'] = inst
        if 'memoryMode' in updates:
            mode = (updates['memoryMode'] or '').strip()
            if mode not in self._VALID_MEMORY_MODES:
                self._json_response(400, {'error': "memoryMode must be 'default' or 'project-only'"})
                return
            project['memoryMode'] = mode
        project['updatedAt'] = datetime.now().isoformat()
        proj_file.write_text(json.dumps(project), encoding='utf-8')
        _server.add_log('info', 'projects', f'Updated project {safe_id}')
        self._json_response(200, project)

    def _delete_project(self, project_id):
        """DELETE /projects/<id> — delete project file; clear projectId from sessions.

        Sessions that referenced the deleted project are retained but have their
        projectId field set to None so they become "uncategorised".
        Returns 400 on traversal, 200 even when not found (idempotent).
        """
        safe_id = self._safe_project_id(project_id)
        if safe_id is None:
            self._json_response(400, {'error': 'Invalid project id'})
            return
        proj_file = _server.PROJECTS_DIR / f'{safe_id}.json'
        if proj_file.exists():
            proj_file.unlink()
            _server.add_log('info', 'projects', f'Deleted project {safe_id}')

        # Scan all sessions and clear projectId where it matches.
        for sess_path in _server.SESSIONS_DIR.glob('*.json'):
            try:
                sess_data = json.loads(sess_path.read_text(encoding='utf-8'))
                if sess_data.get('projectId') == safe_id:
                    sess_data['projectId'] = None
                    sess_path.write_text(json.dumps(sess_data), encoding='utf-8')
            except Exception:
                pass

        # Remove per-project chunk-cache directory (PF-6).
        import shutil as _shutil
        proj_cache_dir = _server.PROJECT_CACHE_DIR / safe_id
        if proj_cache_dir.exists():
            _shutil.rmtree(proj_cache_dir, ignore_errors=True)

        self._json_response(200, {'ok': True})
