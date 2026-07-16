# Implementation Plan

[Overview]
Reorganize the monolithic flat repo root into `backend/` (Python) and `frontend/` (HTML/JS/CSS) subdirectories while preserving 100% of runtime behaviour and keeping all tests green.

Backlog item **#56 — Frontend/backend directory reorg** calls for a clean concern separation: Python backend files into `backend/`, frontend assets into `frontend/`. The prereq (#45 module split) is done. This is a **move-only** refactor — zero new features, zero behaviour changes, zero new runtime dependencies. The hard engineering constraint is that `server.py` currently conflates three distinct anchors into one (`PROJECT_ROOT = Path(__file__).parent`): (a) where `.env` and data dirs live, (b) which directory `SimpleHTTPRequestHandler` serves files from, and (c) where `requirements.txt` lives. After the move we split those into two explicit constants: `REPO_ROOT = Path(__file__).resolve().parent.parent` for data/config (stays at repo root so no existing user data is orphaned), and `STATIC_DIR = REPO_ROOT / 'frontend'` for static-file serving. All other handler modules, tests, and tooling files get path-corrected to match the new layout.

Target tree:
```
usai/
├── backend/
│   ├── server.py
│   ├── proxy_handlers.py
│   ├── session_handlers.py
│   ├── memory_handlers.py
│   ├── mcp_handlers.py
│   ├── projects_handlers.py
│   └── tests/
│       └── python/          ← was tests/python/
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── tests/
│       └── js/              ← was tests/js/
├── .env  .env.example
├── .chunk_cache/  .chat_sessions/  .projects/  .raw_responses/  logs/
├── scripts/  docs/  tests/  (tests/js-coverage.mjs stays at root for run-tests.sh)
├── run-tests.sh  Makefile  Dockerfile  docker-compose.yml
├── package.json  requirements*.txt  .coveragerc  .coverage-thresholds
└── backlog.md  CHANGELOG.md  AGENTS.md  README.md
```

[Types]
No new types, interfaces, or data structures — this is a pure file-move + path-correction refactor.

All existing Python module-level globals (`REPO_ROOT`, `STATIC_DIR`, `CACHE_DIR`, `SESSIONS_DIR`, etc.) keep the same names and types; only the values of `PROJECT_ROOT` (renamed to `REPO_ROOT`) and the newly added `STATIC_DIR` change. No JS type changes.

[Files]
Six Python backend files move from repo root → `backend/`; three frontend files move from repo root → `frontend/`; two test directories move; several tooling/config files get path strings updated in-place.

**Files MOVED (git mv — preserves history):**
- `server.py` → `backend/server.py`
- `proxy_handlers.py` → `backend/proxy_handlers.py`
- `session_handlers.py` → `backend/session_handlers.py`
- `memory_handlers.py` → `backend/memory_handlers.py`
- `mcp_handlers.py` → `backend/mcp_handlers.py`
- `projects_handlers.py` → `backend/projects_handlers.py`
- `tests/python/` (all files) → `backend/tests/python/`
- `index.html` → `frontend/index.html`
- `app.js` → `frontend/app.js`
- `styles.css` → `frontend/styles.css`
- `tests/js/app.test.mjs` → `frontend/tests/js/app.test.mjs`
- `tests/js/app.behavior.test.mjs` → `frontend/tests/js/app.behavior.test.mjs`

**Files STAYING at repo root (no move):**
- `.env`, `.env.example`, `requirements.txt`, `requirements-dev.txt`
- `.chunk_cache/`, `.chat_sessions/`, `.projects/`, `.raw_responses/`, `logs/`
- `run-tests.sh`, `Makefile`, `Dockerfile`, `docker-compose.yml`
- `package.json`, `.coveragerc`, `.coverage-thresholds`, `.coveragerc`
- `tests/js-coverage.mjs` — STAYS at repo root (invoked by run-tests.sh from root)
- `scripts/`, `docs/`, `backlog.md`, `CHANGELOG.md`, `AGENTS.md`, `README.md`

**Files MODIFIED (path corrections only):**
- `backend/server.py` — rename `PROJECT_ROOT` → `REPO_ROOT`, add `STATIC_DIR`, fix `run()` + `install_dependencies()`
- `backend/tests/python/test_server_branches.py` — fix `StaticFileTests` `os.chdir` target
- `backend/tests/python/test_server_proxy.py` — fix `PROJECT_ROOT = parents[2]` → `parents[2]` still correct (verify)
- `backend/tests/python/test_server.py` — same `parents[2]` verification
- `backend/tests/python/test_server_http.py` — same + any StaticFileTests chdir
- `backend/tests/python/test_server_startup.py` — same
- `backend/tests/python/test_server_mcp.py` — same
- `backend/tests/python/test_server_branches.py` — `parents[2]` is now `backend/` root; `parents[3]` is repo root
- `backend/tests/python/test_scripts.py` — `REPO_ROOT = parents[2]` stays correct
- `run-tests.sh` — update all 6 path references
- `Makefile` — `run:` target + inline paths
- `Dockerfile` — COPY + CMD
- `docker-compose.yml` — command/volume refs if any
- `.coveragerc` — `source = server` → `source = backend.server` OR use `--source=backend/server` in run-tests.sh
- `scripts/security-scan.sh` — bandit target list
- `scripts/pre-commit.sh` — syntax gates
- `scripts/mutation-audit.sh` — PATHS_TO_MUTATE
- `scripts/cli-check.sh` — any path refs
- `.github/workflows/tests.yml` — `py_compile`, `bandit`, `unittest discover` paths
- `package.json` — test file globs if present
- `docs/ORGANIZATION.md` — file table (three-concern map)
- `docs/ARCHITECTURE.md` — layout + module-split section
- `README.md` — run commands
- `AGENTS.md` — layout description line
- `backlog.md` — mark #56 `[x]`
- `CHANGELOG.md` — add entry

[Functions]
Two functions in `server.py` require path logic changes; all other functions across all six Python files are unchanged.

**Modified functions:**
- `server.py → backend/server.py` module-level constants block (lines 17–31):
  - Rename `PROJECT_ROOT` → `REPO_ROOT`, update to `Path(__file__).resolve().parent.parent`
  - Add `STATIC_DIR = REPO_ROOT / 'frontend'`
  - All other dirs (`CACHE_DIR`, `SESSIONS_DIR`, etc.) switch from `PROJECT_ROOT /` to `REPO_ROOT /`
  - `ENV_FILE = REPO_ROOT / '.env'`

- `run(host, port)` in `backend/server.py` (line 594):
  - Change `os.chdir(PROJECT_ROOT)` → `os.chdir(STATIC_DIR)`
  - This makes `SimpleHTTPRequestHandler` serve from `frontend/` instead of the repo root

- `install_dependencies()` in `backend/server.py` (line 606):
  - Change `PROJECT_ROOT / 'requirements.txt'` → `REPO_ROOT / 'requirements.txt'`

**Handler file constructor (if any override `__init__`):**
- `SimpleHTTPRequestHandler` supports a `directory=` kwarg (Python 3.7+). As an alternative to `os.chdir`, set `directory=str(STATIC_DIR)` in `EnvConfigHTTPRequestHandler.__init__`. Either approach is acceptable; `os.chdir(STATIC_DIR)` in `run()` is simpler given existing test infrastructure.

**Test path constants (all test files in `backend/tests/python/`):**
- `PROJECT_ROOT = Path(__file__).resolve().parents[2]` — BEFORE the move this pointed at `usai/`. AFTER the move `__file__` is `usai/backend/tests/python/test_*.py`, so `parents[2]` → `usai/backend/`. Tests import `server` via `sys.path.insert(0, str(PROJECT_ROOT))` which would now insert `usai/backend/` — this is correct because all six Python modules live there.
- `REPO_ROOT = Path(__file__).resolve().parents[3]` — add this alias in test files that need to reference top-level scripts (e.g. `test_scripts.py` which currently uses `parents[2]` to find `scripts/`). `parents[3]` → `usai/` (repo root).
  - `test_scripts.py`: update `REPO_ROOT = parents[2]` → `REPO_ROOT = parents[3]`
  - `test_pre_commit.py`: same pattern
  - `test_dev_deps.py`: same pattern
  - `test_analyze_logs.py`: same pattern

**`StaticFileTests` in `test_server_branches.py`:**
- Current: `os.chdir(Path(__file__).resolve().parents[2])` — after move this changes from `usai/` to `usai/backend/`, breaking the test that expects `index.html` to be accessible.
- Fix: `os.chdir(server.STATIC_DIR)` — uses the newly introduced constant so it's always correct.

[Classes]
No new classes, no removed classes. The mixin classes (`ProxyHandlersMixin`, `SessionHandlersMixin`, `MemoryHandlersMixin`, `McpHandlersMixin`, `ProjectsHandlersMixin`) and the main `EnvConfigHTTPRequestHandler` class remain identical — they move to `backend/` without any signature or inheritance changes.

**No changes needed inside any handler class** — the `_ServerProxy` lazy-import pattern means all six handler files already import the server module by name at call time, not at module load time, so moving to `backend/` doesn't break inter-module imports (they'll all be in the same directory on `sys.path`).

[Dependencies]
No new runtime dependencies. No new dev dependencies. No version changes.

The only "dependency" change is tooling path references — coverage source path in `.coveragerc` changes from `source = server` to `source = backend/server` (or equivalently keep `source = server` and adjust `--source` flag in `run-tests.sh` to pass `backend.server`). The cleaner approach: keep `source = server` in `.coveragerc` but update `run-tests.sh` to run `coverage run ... --source=server` from inside `backend/` (via a subshell `cd backend && ...`), OR update the `--source` to `backend.server` in `run-tests.sh` inline. Recommended: change `.coveragerc` `source = server` to stay as-is but change `run-tests.sh` to add `sys.path` or use the module reference `backend.server`; see Implementation Order step 7 for the exact command change.

[Testing]
All existing tests must pass at all existing coverage gates after the move; no new test logic is written (this is a refactor, not a feature). The only test changes are path constant corrections.

**Test files requiring path-constant changes:**
| File | Change |
|------|--------|
| `backend/tests/python/test_scripts.py` | `REPO_ROOT = parents[3]`, `SPEC_CHECK = REPO_ROOT / 'scripts/...'` |
| `backend/tests/python/test_pre_commit.py` | `REPO_ROOT = parents[3]`, `PRE_COMMIT_SH = REPO_ROOT / 'scripts/...'` |
| `backend/tests/python/test_dev_deps.py` | `REPO_ROOT = parents[3]`, `DEV_DEPS_CHECK = REPO_ROOT / 'scripts/...'` |
| `backend/tests/python/test_analyze_logs.py` | `REPO_ROOT = parents[3]`, `SCRIPT_PATH = REPO_ROOT / 'scripts/...'` |
| `backend/tests/python/test_server_proxy.py` | `PROJECT_ROOT = parents[2]` stays → now points at `backend/` ✓ |
| `backend/tests/python/test_server.py` | `PROJECT_ROOT = parents[2]` → `backend/` ✓ |
| `backend/tests/python/test_server_http.py` | `PROJECT_ROOT = parents[2]` → `backend/` ✓ |
| `backend/tests/python/test_server_startup.py` | `PROJECT_ROOT = parents[2]` → `backend/` ✓ |
| `backend/tests/python/test_server_mcp.py` | `PROJECT_ROOT = parents[2]` → `backend/` ✓ |
| `backend/tests/python/test_server_branches.py` | `StaticFileTests` fix `os.chdir` → `server.STATIC_DIR` |

**Coverage source change:**
- `.coveragerc`: `source = server` → `source = server` (keep same — but `run-tests.sh` will change discover path so coverage can resolve it; alternatively change to `omit` strategy. See Implementation Order step 7.)
- Recommended: Change `.coveragerc` `source = server` to use omit-only approach OR change `run-tests.sh` discover command to `cd backend && $PY -m coverage run --branch --source=server -m unittest discover -s tests/python ...`.

**Run gate after completion:**
```bash
./run-tests.sh --coverage   # server.py line ≥90%, branch ≥80%; JS branch ≥70%
./scripts/security-scan.sh  # gitleaks + bandit + pip-audit
.venv/bin/python backend/server.py  # boots and serves frontend/
```

[Implementation Order]
The changes must be applied in this specific order to avoid breaking intermediate states.

1. **Create directories** — `mkdir -p backend/tests/python frontend/tests/js`

2. **git mv Python backend files** — move all 6 Python files to `backend/` using `git mv` to preserve history:
   ```
   git mv server.py backend/server.py
   git mv proxy_handlers.py backend/proxy_handlers.py
   git mv session_handlers.py backend/session_handlers.py
   git mv memory_handlers.py backend/memory_handlers.py
   git mv mcp_handlers.py backend/mcp_handlers.py
   git mv projects_handlers.py backend/projects_handlers.py
   ```

3. **git mv Python test files** — move `tests/python/` content to `backend/tests/python/`:
   ```
   git mv tests/python backend/tests/python
   ```

4. **git mv frontend files** — move `index.html`, `app.js`, `styles.css` to `frontend/`:
   ```
   git mv index.html frontend/index.html
   git mv app.js frontend/app.js
   git mv styles.css frontend/styles.css
   ```

5. **git mv JS test files** — move `tests/js/` to `frontend/tests/js/`:
   ```
   git mv tests/js frontend/tests/js
   ```

6. **Patch `backend/server.py`** — update path constants and `run()`:
   - `PROJECT_ROOT` → `REPO_ROOT = Path(__file__).resolve().parent.parent`
   - Add `STATIC_DIR = REPO_ROOT / 'frontend'`
   - All `PROJECT_ROOT /` references → `REPO_ROOT /`
   - `run()`: `os.chdir(STATIC_DIR)` 
   - `install_dependencies()`: `REPO_ROOT / 'requirements.txt'`

7. **Patch Python test files** — update `parents[N]` constants:
   - Files using `parents[2]` to find `scripts/`: update to `parents[3]`
   - `StaticFileTests.os.chdir` → `server.STATIC_DIR`

8. **Patch `run-tests.sh`** — update all path references:
   - Syntax gate: `node --check frontend/app.js`
   - `py_compile`: `backend/server.py backend/proxy_handlers.py ...` (all 6)
   - JS tests: `node --test $(find frontend/tests/js -name ...)`
   - jsdom behavior test: `node --test frontend/tests/js/app.behavior.test.mjs`
   - Python discover: `-s backend/tests/python`
   - Coverage discover: `--source=server -s backend/tests/python`
   - Coverage JSON branch extraction: `d['files']['backend/server.py']` OR `d['files']['server.py']` (depends on source path)

9. **Patch `.coveragerc`** — consider if `source = server` still resolves (it will if `backend/` is on sys.path during the coverage run, which it will be when discovering from `backend/tests/python`). Verify and update if needed.

10. **Patch `Makefile`** — `run:` → `$(PY) backend/server.py`

11. **Patch `Dockerfile`** — `COPY` + `CMD`:
    - `COPY requirements.txt ./`
    - `COPY backend/server.py backend/proxy_handlers.py backend/session_handlers.py backend/memory_handlers.py backend/mcp_handlers.py backend/projects_handlers.py ./backend/`
    - `COPY frontend/index.html frontend/app.js frontend/styles.css ./frontend/`
    - `CMD ["python", "backend/server.py"]`

12. **Patch `scripts/security-scan.sh`** — bandit list → `backend/server.py backend/proxy_handlers.py ...`

13. **Patch `scripts/pre-commit.sh`** — syntax gates → `frontend/app.js`, `backend/server.py` etc.

14. **Patch `scripts/mutation-audit.sh`** — `PATHS_TO_MUTATE` → `backend/server.py`

15. **Patch `.github/workflows/tests.yml`** — `py_compile`, `bandit`, discover paths

16. **Patch `docs/ORGANIZATION.md`** — update file table (three-concern map) with new paths

17. **Patch `docs/ARCHITECTURE.md`** — update directory layout section and module-split reference

18. **Patch `README.md`** — run command to `backend/server.py`

19. **Patch `AGENTS.md`** — layout description

20. **Verify** — run `./run-tests.sh --coverage`, `./scripts/security-scan.sh`, and boot `backend/server.py`

21. **Update backlog + docs** — mark #56 `[x]`, add `CHANGELOG.md` entry

22. **Write Obsidian memory note**
