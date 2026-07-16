# Spec: `server.py` Module Split (#45)

**Status:** Done
**Completed:** 2026-07-04  
**Type:** Chore (pure refactor — zero behaviour change)  
**Size:** M  
**Sprint:** 16  
**Author:** Cline  
**Created:** 2026-07-03  

---

## §1 User story

*As a developer maintaining USAi Chat, I want the 1,871-line `server.py` to be split into focused modules so that each file is under the 1,500-line governance threshold, related code lives together, and the codebase is easier to navigate, review, and extend — with zero behaviour change and all 193 tests passing unchanged.*

---

## §2 Context / motivation

`server.py` grew to 1,871 lines (24% over the 1,500-line threshold) as features were incrementally added across Projects v1, Obsidian memory integration, MCP bridge, raw-response capture, log file viewer, and the proxy layer.

The Governance Board escalated this to **BLOCKING-02** at the 2026-07-01 audit (originally INNOV-01 at the 2026-06-26 audit).

**Chosen approach:** Python mixin classes.

- Five new mixin modules define handler subsets as plain Python classes.
- `EnvConfigHTTPRequestHandler` inherits all five mixins + `SimpleHTTPRequestHandler`.
- All module-level constants, helpers, routing tables, and the entrypoint stay in `server.py`.
- No test files change — the test suite imports `server` and accesses only `server.*` names.

---

## §3 Acceptance criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | `./run-tests.sh` exits 0 — no test file edits | Run `./run-tests.sh` |
| AC-2 | `./run-tests.sh --coverage` → server.py ≥ 90% line, ≥ 80% branch, JS ≥ 70% | Run with `--coverage` |
| AC-3 | `./scripts/security-scan.sh` exits 0 | Run scan |
| AC-4 | All 6 Python files under 1,500 lines | `wc -l *.py` |
| AC-5 | `docs/specs/server-module-split.md` Status: Done | This file |
| AC-6 | `backlog.md` #45 marked `[x]` with date/outcome/spec link | Check backlog.md |
| AC-7 | New `[ ]` items #56 and #57 added to `backlog.md` | Check backlog.md |
| AC-8 | `CHANGELOG.md` updated with #45 entry | Check CHANGELOG.md |
| AC-9 | `docs/ARCHITECTURE.md` module structure section added | Check ARCHITECTURE.md |
| AC-10 | Memory note written to vault | Check vault |

---

## §4 Technical approach

### 4a Module layout

| File | Class | Lines (target) | Responsibility |
|------|-------|----------------|----------------|
| `server.py` | `EnvConfigHTTPRequestHandler` | ~450 | Scaffold, config, routing, shared helpers, entrypoint |
| `proxy_handlers.py` | `ProxyHandlersMixin` | ~310 | Proxy API, context7, embeddings, raw responses |
| `session_handlers.py` | `SessionHandlersMixin` | ~230 | Sessions, chat history, chunk cache, logs |
| `memory_handlers.py` | `MemoryHandlersMixin` | ~340 | `/memory/*` endpoints |
| `mcp_handlers.py` | `McpHandlersMixin` | ~130 | `/mcp/*` endpoints |
| `projects_handlers.py` | `ProjectsHandlersMixin` | ~260 | `/projects` CRUD |

### 4b New class declaration

```python
class EnvConfigHTTPRequestHandler(
    ProxyHandlersMixin,
    SessionHandlersMixin,
    MemoryHandlersMixin,
    McpHandlersMixin,
    ProjectsHandlersMixin,
    SimpleHTTPRequestHandler,
):
```

`SimpleHTTPRequestHandler` is last to preserve correct MRO.

### 4c Import strategy

Each mixin file imports what it needs from `server` (the module):

```python
from server import CONFIG, add_log, SESSIONS_DIR, ...
```

No cross-mixin imports. No new runtime dependencies.

### 4d Circular import management

All state (constants, mutable globals, helper functions) lives in `server.py`. Mixin files import **from** `server` — this is safe because Python resolves the import at call time during class definition, not at module load time. The mixin classes are imported into `server.py` after all module-level names are defined.

### 4e Methods that stay in server.py

- `disable_nagle_algorithm = True` (class attribute)
- `_json_response(self, status, payload)` — called via `self` from all mixins
- `_get_config(self)` — reads CONFIG heavily
- `do_GET`, `do_POST`, `do_PUT`, `do_DELETE` — routing tables
- All module-level functions: `load_config`, `get_memory_dir`, `get_project_memory_dir`, `_slugify`, `_resolve_memory_file`, `_mcp_enabled`, `call_obsidian_mcp`, `is_safe_upstream_url`, `add_log`, `_persist_log`, `_capture_raw_response`, `run`, `install_dependencies`
- All module-level constants: `CONFIG`, `SESSIONS_DIR`, `HISTORY_FILE`, `CACHE_DIR`, `PROJECT_CACHE_DIR`, `PROJECTS_DIR`, `LOGS_DIR`, `RAW_RESPONSES_DIR`, `MCP_TOOL_ALLOWLIST`, `server_logs`, `MAX_LOGS`, `_LOG_SESSION_STAMP`

---

## §5 Risk table

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Circular import at module load | Low | High | All state in `server.py`; mixins imported last |
| Missing import in a mixin | Medium | Medium | `py_compile` gate after each file; full test run |
| Coverage drops below gate | Low | Medium | Mixin methods inherit coverage through `EnvConfigHTTPRequestHandler` |
| `_INSTRUCTIONS_MAX` class attribute not found by mixin | Low | Medium | Stays in `server.py` class body; accessed via `self._INSTRUCTIONS_MAX` |

---

## §6 Implementation order

1. Write this spec → mark #45 `[~]`
2. Create `mcp_handlers.py` → `py_compile`
3. Create `memory_handlers.py` → `py_compile`
4. Create `projects_handlers.py` → `py_compile`
5. Create `proxy_handlers.py` → `py_compile`
6. Create `session_handlers.py` → `py_compile`
7. Edit `server.py` → `py_compile`
8. `./run-tests.sh` — all 193 must pass
9. `./run-tests.sh --coverage` — gates
10. `./scripts/security-scan.sh` — exits 0
11. Verify line counts
12. Update `run-tests.sh` syntax gate
13. Update `docs/ARCHITECTURE.md`
14. Update `CHANGELOG.md`
15. Mark #45 `[x]`
16. Write memory note

---

## §7 Spec changelog

| Date | Change |
|------|--------|
| 2026-07-03 | Created — Status: In Progress |
