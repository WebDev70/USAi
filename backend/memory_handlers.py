"""memory_handlers.py — Obsidian memory handler mixin.

Contains MemoryHandlersMixin with all /memory/* endpoint methods extracted
from EnvConfigHTTPRequestHandler (server.py backlog #45 module split).
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
        mod = sys.modules.get('server') or sys.modules.get('__main__')
        return getattr(mod, name)


_server = _ServerProxy()


class MemoryHandlersMixin:
    """Mixin providing /memory/* handler methods for EnvConfigHTTPRequestHandler.

    Methods rely on self being an HTTPRequestHandler instance with:
      - self.path, self.headers, self.rfile, self.wfile
      - self._json_response(), self._safe_project_id()
    """

    def _project_memory_dirs(self, project_id):
        """Return (dirs, mode) for a project_id.

        dirs  — list[Path] of memory directories to search/write (may be empty).
        mode  — 'default' | 'project-only'.

        Falls back to ([global_dir], 'default') if project not found or vault
        not configured.  Always graceful — never raises.
        """
        global_dir = _server.get_memory_dir()
        proj_dir = _server.get_project_memory_dir(project_id) if project_id else None

        if not project_id or proj_dir is None:
            return ([global_dir] if global_dir else [], 'default')

        safe_id = self._safe_project_id(project_id)
        if safe_id is None:
            return ([global_dir] if global_dir else [], 'default')
        proj_file = _server.PROJECTS_DIR / f'{safe_id}.json'
        try:
            with open(proj_file, encoding='utf-8') as fh:
                project = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return ([global_dir] if global_dir else [], 'default')

        mode = (project.get('memoryMode') or 'default').strip()
        if mode == 'project-only':
            return ([proj_dir], 'project-only')
        # default: global first, project second (merged by score)
        dirs = []
        if global_dir:
            dirs.append(global_dir)
        dirs.append(proj_dir)
        return (dirs, 'default')

    def _memory_search(self):
        """GET /memory/search?q=...&k=5[&projectId=...] — keyword search.

        Scores each note by query-term frequency (title-weighted), returns top-k.
        When projectId is supplied, the scope is determined by memoryMode:
        - default       → both global dir + project dir (merged by score, deduped)
        - project-only  → project dir only
        No projectId → global dir only (legacy behaviour, AC-6 global isolation).
        """
        global_dir = _server.get_memory_dir()
        if global_dir is None:
            self._json_response(400, {'error': 'Obsidian vault not configured'})
            return
        params = parse_qs(urlparse(self.path).query)
        query = (params.get('q', [''])[0] or '').strip()
        project_id = (params.get('projectId', [''])[0] or '').strip() or None
        try:
            k = max(1, min(20, int(params.get('k', ['5'])[0])))
        except ValueError:
            k = 5
        if not query:
            self._json_response(400, {'error': 'missing query'})
            return

        dirs, _mode = self._project_memory_dirs(project_id)

        terms = [t for t in query.lower().split() if t]
        seen_paths = set()  # dedup by absolute path
        results = []
        for mem_dir in dirs:
            if not mem_dir or not mem_dir.exists():
                continue
            for p in mem_dir.glob('*.md'):
                abs_path = str(p.resolve())
                if abs_path in seen_paths:
                    continue
                seen_paths.add(abs_path)
                try:
                    text = p.read_text(encoding='utf-8')
                except Exception:
                    continue
                lower = text.lower()
                title_region = lower[:200]
                score = 0
                for term in terms:
                    score += lower.count(term)
                    score += title_region.count(term) * 3
                if score <= 0:
                    continue
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
        _server.add_log('info', 'memory', f'search "{query}" → {len(results)} hit(s)')
        self._json_response(200, {
            'ok': True,
            'query': query,
            'results': results,
            # Always report whether semantic (embedding) search is available so
            # the client can decide between keyword-only and embedding-ranked
            # results. False when EMBED_MODEL is unset.
            'embed_available': bool(_server.CONFIG.get('embed_model')),
        })

    def _memory_list(self):
        """GET /memory/list[?projectId=...] — list memory notes newest-first.

        Scope follows memoryMode for the given project (same rules as search).
        No projectId → global dir only.
        """
        global_dir = _server.get_memory_dir()
        if global_dir is None:
            self._json_response(400, {'error': 'Obsidian vault not configured'})
            return
        params = parse_qs(urlparse(self.path).query)
        project_id = (params.get('projectId', [''])[0] or '').strip() or None
        dirs, _mode = self._project_memory_dirs(project_id)

        seen_paths = set()
        items = []
        for mem_dir in dirs:
            if not mem_dir or not mem_dir.exists():
                continue
            for p in sorted(mem_dir.glob('*.md'),
                            key=lambda x: x.stat().st_mtime, reverse=True):
                abs_path = str(p.resolve())
                if abs_path in seen_paths:
                    continue
                seen_paths.add(abs_path)
                items.append({
                    'path': p.name,
                    'modified': datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                    'size': p.stat().st_size,
                })
        # Re-sort merged list newest-first
        items.sort(key=lambda x: x['modified'], reverse=True)
        self._json_response(200, {'ok': True, 'items': items})

    def _memory_read(self):
        """GET /memory/read?path=note.md[&projectId=...] — read a memory note.

        Searches each directory in scope (per project mode) in order; returns
        the first match.  Falls back to 404 if not found in any dir.
        """
        global_dir = _server.get_memory_dir()
        if global_dir is None:
            self._json_response(400, {'error': 'Obsidian vault not configured'})
            return
        params = parse_qs(urlparse(self.path).query)
        rel = params.get('path', [''])[0]
        project_id = (params.get('projectId', [''])[0] or '').strip() or None
        dirs, _mode = self._project_memory_dirs(project_id)

        for mem_dir in dirs:
            if not mem_dir:
                continue
            target = _server._resolve_memory_file(mem_dir, rel)
            if target is not None and target.exists():
                try:
                    content = target.read_text(encoding='utf-8')
                except Exception as err:
                    self._json_response(500, {'error': str(err)})
                    return
                self._json_response(200, {'ok': True, 'path': target.name, 'content': content})
                return
        self._json_response(404, {'error': 'memory not found'})

    def _memory_save(self):
        """POST /memory/save — create a timestamped, tagged memory note.

        Body: { title, content, tags?: string[], projectId?: string }.
        Save target:
        - No projectId  → global dir (legacy behaviour).
        - projectId + default mode → project dir (AC-4).
        - projectId + project-only → project dir (AC-5).
        Writes are create-only and strictly confined to the chosen memory dir.
        """
        global_dir = _server.get_memory_dir()
        if global_dir is None:
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

        # Resolve save target directory.
        project_id = (data.get('projectId') or '').strip() or None
        if project_id:
            dirs, _mode = self._project_memory_dirs(project_id)
            # For save: always write to the project dir (first non-global dir),
            # regardless of mode.  For default mode, dirs = [global, proj_dir];
            # for project-only, dirs = [proj_dir].  We want the project dir.
            proj_dir = _server.get_project_memory_dir(project_id)
            save_dir = proj_dir if proj_dir else global_dir
        else:
            save_dir = global_dir

        now = datetime.now()
        stamp = now.strftime('%Y-%m-%d-%H%M%S')
        filename = f'{stamp}-{_server._slugify(title)}.md'

        save_dir.mkdir(parents=True, exist_ok=True)
        target = _server._resolve_memory_file(save_dir, filename)
        if target is None:
            self._json_response(400, {'error': 'invalid path'})
            return

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
        _server.add_log('info', 'memory', f'saved memory "{title}" -> {target.name}')
        self._json_response(200, {'ok': True, 'path': target.name, 'title': title})
