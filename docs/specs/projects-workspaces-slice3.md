# Spec: Projects (ChatGPT-style Workspaces) — Slice 3: Memory Modes (Default dual-read vs. Project-only isolation)

**Status:** Done
**Type:** feature
**Created:** 2026-06-30
**Author:** Cline / user
**Prior context:** Slice 1 (CRUD + sidebar) and Slice 2 (3-layer instructions) both Done. Memory-mode concept designed in `Continue Extension/memories/2026-06-20-223334-projects-feature-plan-and-review.md`. `memoryMode` field already stored (immutable) on every project since Slice 1.

---

## 1. Goal & scope

### Goal
Wire the already-stored, immutable `memoryMode` field on each Project so it
actually governs memory reads and writes:

- **Default** — a project's memory lives in a **project-scoped folder** but the
  `/memory/*` endpoints (and client auto-recall) read **both** that folder and
  the global vault folder, merged by relevance score. Saves land in the project
  folder.
- **Project-only** — reads and writes use **only** the project-scoped folder;
  the folder is **excluded** from global searches (no `projectId` active → only
  global folder is searched).

This completes Projects v1 (Slices 1–3).  No new UI is needed — `memoryMode`
is already displayed (read-only) in the project Settings modal from Slice 1.

### Out of scope
- Project files / shared knowledge (`projectChunks`) — Slice 4, deferred
- Any new UI controls (mode read-only in settings from Slice 1)
- Changes to `memoryMode` mutability (server already rejects updates — stays that way)
- MCP bridge endpoints (`/mcp/*`) — no change needed

---

## 2. User story & acceptance criteria

As a USAi user I want my memory auto-recall and 💾 Remember saves to respect
the memory mode I chose when I created a project so that Default projects share
context with my global memory and Project-only projects stay isolated.

- [ ] **AC-1** — `get_project_memory_dir(project_id)` resolves
  `<vault>/<subdir>/projects/<id>/memories`, traversal-guarded via
  `_safe_project_id`; returns `None` if vault is unconfigured or `project_id`
  fails the guard.
- [ ] **AC-2** — `/memory/search`, `/memory/list`, `/memory/read`, and
  `/memory/save` accept an optional `?projectId=` query parameter (GET) /
  `projectId` body key (POST save). When present and the project exists, the
  mode is resolved; when absent the behaviour is unchanged (global only).
- [ ] **AC-3 — Default mode, search/list:** results are drawn from **both** the
  global folder and the project folder, merged and sorted descending by relevance
  score, deduped by absolute file path.
- [ ] **AC-4 — Default mode, save:** note is written to the **project** folder
  (not the global folder).
- [ ] **AC-5 — Project-only mode, search/list/read/save:** all operations use
  **only** the project folder; the global folder is not read or written.
- [ ] **AC-6 — Global isolation:** a global search (no `projectId`) **never**
  returns notes from any `project-only` folder. (`default`-mode project folders
  are only searched when that project is active via `?projectId=`.)
- [ ] **AC-7 — Client wiring:** `embedMemorySearch`, the auto-recall path in
  `prepareContextMessages`, and `saveMemory` (including the 💾 Remember button)
  all pass `currentProjectId` to their respective endpoints when non-null.
- [ ] **AC-8 — Backward compat:** projects with no `memoryMode` field (legacy)
  default to `'default'`; sessions with no `projectId` behave exactly as today
  (global folder only).

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | New helper `get_project_memory_dir(project_id)`; new helper `_project_memory_dirs(project_id)` returning list of dirs to search; update `_memory_search`, `_memory_list`, `_memory_read`, `_memory_save` to accept `projectId` param and route by mode |
| `app.js` | Thread `currentProjectId` into `embedMemorySearch`, auto-recall path in `prepareContextMessages`, and `saveMemory` / 💾 Remember button calls |
| `index.html` | No change |
| `styles.css` | No change |
| `tests/python/test_server_http.py` | New tests MM-1…MM-6 (dir resolution, dual-read merge, project-only isolation, global exclusion, save target, legacy compat) |
| `tests/python/test_server.py` | MM-7: `get_project_memory_dir` traversal guard unit tests |
| `tests/js/app.test.mjs` | New tests MJ-1…MJ-3 (`projectId` threaded through search and save) |
| `docs/specs/projects-workspaces-slice3.md` | This spec |
| `CHANGELOG.md` | Entry under `[Unreleased]` |
| `docs/USER_GUIDE.md` | §8 Projects — add Memory Modes subsection |
| `backlog.md` | Mark Slice 3 `[~]` In Progress → `[x]` Done at loop end |

---

## 4. Technical approach

### Role 2 — Architect sign-off

#### Backend: `server.py`

**New module-level helper** (alongside existing `get_memory_dir()`):

```python
def get_project_memory_dir(project_id):
    """Resolve the absolute path to a project-scoped memory folder.

    Path: <vault>/<subdir>/projects/<safe_id>/memories
    Returns None if vault is unconfigured, project_id fails the slug guard,
    or the vault root does not exist.
    """
    base = get_memory_dir()        # reuse existing vault-root resolution
    if base is None:
        return None
    # Reuse the existing slug pattern (alphanumeric + _ + -)
    import re as _re
    if not project_id or not _re.match(r'^[A-Za-z0-9_-]+$', str(project_id)):
        return None
    proj_dir = (base.parent.parent / 'projects' / project_id / 'memories').resolve()
    # Traversal guard: must remain inside the vault
    vault = (Path(os.path.expanduser(
        (CONFIG.get('obsidian_vault_path') or '').strip())).resolve())
    try:
        proj_dir.relative_to(vault)
    except ValueError:
        return None
    return proj_dir
```

**New instance helper** on `USAiHandler`:

```python
def _project_memory_dirs(self, project_id):
    """Return the list of memory directories to search/read for a given
    project.  Reads the project's memoryMode from disk to determine scope.

    Returns:
        (dirs, mode) where dirs is a list[Path] and mode is 'default' |
        'project-only'.  Falls back to ([global_dir], 'default') if project
        not found or vault unconfigured.
    """
    global_dir = get_memory_dir()
    proj_dir = get_project_memory_dir(project_id) if project_id else None

    if not project_id or proj_dir is None:
        return ([global_dir] if global_dir else [], 'default')

    # Load the project to read its memoryMode
    safe_id = self._safe_project_id(project_id)
    if safe_id is None:
        return ([global_dir] if global_dir else [], 'default')
    proj_file = Path('.projects') / f'{safe_id}.json'
    try:
        with open(proj_file, encoding='utf-8') as f:
            project = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return ([global_dir] if global_dir else [], 'default')

    mode = (project.get('memoryMode') or 'default').strip()
    if mode == 'project-only':
        return ([proj_dir], 'project-only')
    else:
        # Default: both dirs, global first (will be merged by score)
        dirs = []
        if global_dir:
            dirs.append(global_dir)
        dirs.append(proj_dir)
        return (dirs, 'default')
```

**Update `_memory_search`** — extract `projectId` from query string, call
`_project_memory_dirs`, gather results from each dir, merge & sort by score,
dedup by path.

**Update `_memory_list`** — same `projectId` extraction; list from all dirs,
merge newest-first, dedup by filename.

**Update `_memory_read`** — accept `projectId`; resolve the note path against
the resolved dirs (check each dir in order).

**Update `_memory_save`** — accept `projectId` in POST body; resolve save
target: Default → project dir (if projectId provided), Project-only → project
dir, no projectId → global dir.

**Global isolation (AC-6):** A search/list with *no* `projectId` uses only the
global dir (current behaviour). The `project-only` folders live under
`<vault>/<subdir>/projects/<id>/memories` — they are *never* in `global_dir`
so they are naturally excluded.

#### Frontend: `app.js`

**`embedMemorySearch`** — add `projectId` param, append `&projectId=...` to
the fetch URL when non-null/non-empty.

**Auto-recall in `prepareContextMessages`** — pass `currentProjectId` to
`embedMemorySearch(query, 5, undefined, currentProjectId)`.

**`saveMemory`** — add `projectId` param, include in POST body when set.

**💾 Remember button (`addRememberButton`)** — pass `currentProjectId` to
`saveMemory`.

No new exported helpers needed; the existing `_embedMemorySearchTest` export
signature gains an optional 4th param.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] No new endpoint (existing `/memory/*` endpoints extended in-place)
- [x] No new tool (`search_memory` / `save_memory` tools already call these endpoints — they will pass `projectId` through the existing call path once the server accepts it)
- [x] `/config` unchanged (no secret exposure)
- [x] Path traversal rejected via `_safe_project_id` + vault-relative check in `get_project_memory_dir`
- [x] CSS bump: N/A (no CSS change)

---

## 4b. Shift-left governance findings

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All 8 ACs are binary and observable (HTTP status, JSON body shape, file written to correct path, notes from wrong folder absent from result set) |
| G-2 Scope / value | ✅ Pass | Exactly the feature described in backlog #27 Slice 3. No gold-plating. `get_project_memory_dir` is the minimal new helper. |
| G-3 Dependency coherence | ✅ Pass | Slice 1 (`_safe_project_id`, `/projects` CRUD, `currentProjectId`, `.projects/<id>.json` store) and Slice 2 (no dependency on instructions for this slice) are both `[x]` Done. |

---

## 5. Test plan (TDD-first)

| # | Test description | File | Type |
|---|-----------------|------|------|
| MM-1 | `get_project_memory_dir('proj_123')` returns correct path inside vault | `tests/python/test_server.py` | unit |
| MM-2 | `get_project_memory_dir('../traversal')` returns `None` (traversal rejected) | `tests/python/test_server.py` | unit |
| MM-3 | `GET /memory/search?q=foo&projectId=<default-proj>` returns results merged from both global and project dirs | `tests/python/test_server_http.py` | integration |
| MM-4 | `GET /memory/search?q=foo&projectId=<project-only-proj>` returns results only from project dir (no global notes) | `tests/python/test_server_http.py` | integration |
| MM-5 | `GET /memory/search?q=foo` (no projectId) never returns notes from a project-only folder | `tests/python/test_server_http.py` | integration |
| MM-6 | `POST /memory/save` with `projectId=<default-proj>` writes note to project dir, not global dir | `tests/python/test_server_http.py` | integration |
| MM-7 | `GET /memory/list?projectId=<project-only-proj>` returns only project-dir notes | `tests/python/test_server_http.py` | integration |
| MM-8 | Project with no `memoryMode` field (legacy JSON) treated as `'default'` | `tests/python/test_server_http.py` | integration |
| MJ-1 | `embedMemorySearch` appends `&projectId=proj_abc` to fetch URL when `projectId` is non-null | `tests/js/app.test.mjs` | unit |
| MJ-2 | `embedMemorySearch` does NOT append `projectId` when null/undefined | `tests/js/app.test.mjs` | unit |
| MJ-3 | `saveMemory` includes `projectId` key in POST body when non-null | `tests/js/app.test.mjs` | unit |

**TDD order:** write MM-1…MM-8 and MJ-1…MJ-3 first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — §8 Projects: add Memory Modes subsection (what Default vs. Project-only mean, how saves/searches are scoped)
- [ ] `README.md` — no setup/config/env var changes needed for Slice 3
- [ ] `backlog.md` — mark Slice 3 `[~]` In Progress then `[x]` Done with spec link
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention changes needed

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Dedup across folders — same filename exists in both global + project dir | Dedup by **absolute path** (not filename) in search/list results; each dir is walked independently so same-name files in different paths are treated as distinct notes |
| `get_project_memory_dir` called before vault is configured | Returns `None`; `_project_memory_dirs` falls back gracefully to global dir list |
| Project JSON corrupt or missing when resolving mode | `_project_memory_dirs` catches `FileNotFoundError` / `json.JSONDecodeError`, falls back to `('default', [global_dir])` |
| `project-only` dir does not exist yet (no notes saved) | `list/search` returns empty list for that dir; `save` creates the dir with `mkdir(parents=True, exist_ok=True)` before writing |
| `save_memory` tool in `TOOL_REGISTRY` — client-side tool call needs `projectId` | The tool call JSON from `app.js` already passes `projectId` via the `saveMemory` function's updated body; server reads it from `data.get('projectId')` |
| `server.py` line count | After Slice 3 adds ~60 lines, still under the ~1,500 split threshold (currently ~1,721 — already above; refactor is backlog item #45, deferred) |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-8 all verified
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

> *Optional — populated only when a spec amendment is made during `/build`
> (see build.md §3d). Leave empty if no amendments were needed.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
