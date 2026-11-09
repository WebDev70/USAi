"""Static checks for the Dockerfile — the container must reproduce the repo layout.

backend/server.py anchors everything on REPO_ROOT (two levels up from its own
file) and imports its siblings as `backend.<module>`. An image that flattens the
files into one folder therefore looks for the frontend and data dirs in the wrong
place and cannot import its own modules. Docker is not always available (CI's
Python job, locked-down laptops), so these tests read the Dockerfile and resolve
its COPY lines against the real tree instead of building an image.

Stdlib `unittest` only — no third-party deps.
"""

import fnmatch
import re
import unittest
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = PROJECT_ROOT / 'Dockerfile'
IMPORT_RE = re.compile(r'^\s*(?:from\s+backend(?:\.(\w+))?\s+import\s+([\w, ]+)|import\s+backend\.(\w+))',
                       re.MULTILINE)


def _instructions():
    """Return (KEYWORD, args) pairs with comments dropped and continuations joined."""
    out, buf = [], ''
    for raw in DOCKERFILE.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not buf and (not line or line.startswith('#')):
            continue
        if line.endswith('\\'):
            buf += line[:-1] + ' '
            continue
        buf += line
        keyword, _, args = buf.strip().partition(' ')
        out.append((keyword.upper(), args.strip()))
        buf = ''
    return out


def _image_files():
    """Resolve every COPY into the set of absolute in-image paths it creates."""
    workdir = PurePosixPath('/')
    files = set()
    for keyword, args in _instructions():
        if keyword == 'WORKDIR':
            workdir = workdir / args
        elif keyword == 'COPY':
            parts = [p for p in args.split() if not p.startswith('--')]
            *sources, dest = parts
            dest_dir = workdir / dest if not dest.startswith('/') else PurePosixPath(dest)
            for src in sources:
                matches = [p for p in PROJECT_ROOT.glob(src) if p.is_file()]
                for match in matches:
                    rel = match.relative_to(PROJECT_ROOT).as_posix()
                    if not fnmatch.fnmatch(rel, src):
                        continue
                    if dest.endswith('/') or len(matches) > 1 or len(sources) > 1:
                        files.add(dest_dir / match.name)
                    else:
                        files.add(dest_dir)
    return workdir, files


def _required_backend_modules():
    """Every backend module reachable from server.py through `backend.` imports."""
    seen, queue = set(), ['server']
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        source = (PROJECT_ROOT / 'backend' / f'{name}.py').read_text(encoding='utf-8')
        for dotted, imported, plain in IMPORT_RE.findall(source):
            if dotted or plain:
                queue.append(dotted or plain)
            else:  # `from backend import a as x, b`
                for item in imported.split(','):
                    mod = item.strip().split(' ')[0]
                    if (PROJECT_ROOT / 'backend' / f'{mod}.py').exists():
                        queue.append(mod)
    return seen


class DockerfileLayoutTests(unittest.TestCase):
    def setUp(self):
        self.workdir, self.files = _image_files()
        self.app = PurePosixPath('/app')

    def test_workdir_is_app(self):
        self.assertEqual(self.workdir, self.app)

    def test_every_imported_backend_module_is_under_app_backend(self):
        missing = sorted(m for m in _required_backend_modules()
                         if self.app / 'backend' / f'{m}.py' not in self.files)
        self.assertEqual(missing, [],
                         'modules server.py imports are not copied to /app/backend/')

    def test_frontend_assets_are_under_app_frontend(self):
        # server.py serves STATIC_DIR = REPO_ROOT / 'frontend'.
        for asset in ('index.html', 'app.js', 'styles.css'):
            self.assertIn(self.app / 'frontend' / asset, self.files,
                          f'frontend/{asset} is not copied to /app/frontend/')

    def test_tests_are_not_shipped_in_the_image(self):
        shipped = sorted(str(p) for p in self.files if '/tests/' in str(p))
        self.assertEqual(shipped, [], 'test files would be baked into the image')

    def test_cmd_runs_backend_server(self):
        cmd = [args for keyword, args in _instructions() if keyword == 'CMD']
        self.assertEqual(len(cmd), 1)
        self.assertIn('backend/server.py', cmd[0])

    def test_runtime_data_dir_is_writable_by_app_user(self):
        # server.py creates .chunk_cache/, .projects/, logs/ … under REPO_ROOT at
        # import time; a root-owned /app makes the non-root user crash on start.
        runs = ' '.join(args for keyword, args in _instructions() if keyword == 'RUN')
        self.assertRegex(runs, r'chown\s+(-R\s+)?appuser(:appuser)?\s+/app(\s|$)')

    def test_env_file_is_never_copied(self):
        copies = ' '.join(args for keyword, args in _instructions() if keyword == 'COPY')
        self.assertNotRegex(copies, r'(^|\s)\.env(\s|$)|(^|\s)\.(\s|$)',
                            '.env (or the whole context) must not be copied into the image')


if __name__ == '__main__':
    unittest.main()
