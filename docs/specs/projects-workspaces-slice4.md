# Spec: Projects (ChatGPT-style Workspaces) — Slice 4: Project Files (Shared Knowledge)

**Status:** Done
**Type:** feature
**Created:** 2026-07-01
**Author:** Cline / user
**Prior context:** Slices 1–3 Done. Storage model (`.chunk_cache/projects/<id>/`) and `projectChunks` design established in `Continue Extension/memories/2026-06-20-223334-projects-feature-plan-and-review.md` §4.4 + §5. `/chunk-cache` endpoints and `fileChunks`/`getRelevantChunks`/`prepareContextMessages` plumbing confirmed in existing code.

---

## 1. Goal & scope

### Goal
Allow a user to attach **shared files** to a Project so that every chat inside
that project can retrieve context from them — without re-uploading per chat.
Project files live in a project-scoped chunk-cache folder (`.chunk_cache/projects/<id>/`),
are loaded into a separate `projectChunks` array when a project opens, and are
merged with per-chat `fileChunks` at RAG query time. A simple upload/list/delete
UI is added inside the existing project Settings modal.

### Out of scope
- Semantic/embedding re-ranking changes beyond reusing the existing path
- "Project home" landing view
- Project sharing, emoji/icon picker
- Migrating existing per-chat uploads into a project's shared store
- Any changes to per-chat upload behaviour (upload-per-chat still works exactly as today)

---

## 2. User story & acceptance criteria

As a USAi user I want to upload files to a Project so that all chats in that project
can search them for context, without having to re-upload the same file in every chat.

- [x] **AC-1 — Server-side project chunk cache:** `POST /chunk-cache?projectId=<id>`
  stores chunks under `.chunk_cache/projects/<safe_id>/`; the `projectId` is
  validated through `_safe_project_id` and any traversal attempt returns 400.
- [x] **AC-2 — Server-side CRUD:** `GET /chunk-cache?projectId=<id>` lists that
  project's cached files; `GET /chunk-cache?projectId=<id>&file=<name>` reads one;
  `DELETE /chunk-cache?projectId=<id>` clears all; `DELETE /chunk-cache?projectId=<id>&file=<name>`
  removes one. No `projectId` param → unchanged global behaviour (backward compat).
- [x] **AC-3 — `projectChunks` array isolation:** when a project is opened
  (`openProject`) or a session is restored to a project, `app.js` fetches the
  project's cached files from `/chunk-cache?projectId=<id>` and stores them in a
  **separate `projectChunks` array** (never in `fileChunks`), so per-chat uploads
  remain isolated.
- [x] **AC-4 — RAG merge:** `getRelevantChunks` / `prepareContextMessages` merge
  `projectChunks` + `fileChunks` at query time; the context note shows `Files: N chunk(s)`
  reflecting the combined count.
- [x] **AC-5 — Project Settings UI:** the project Settings modal contains a
  "Project files" section with: a file-upload input, a list of uploaded filenames
  with a per-file ✕ delete button, and a status/spinner while uploading.
  `styles.css?v=29` bumped.
- [x] **AC-6 — Project delete cascade:** `DELETE /projects/<id>` (the existing
  project delete handler) also removes `.chunk_cache/projects/<id>/` and its
  contents; `projectChunks` is cleared in `app.js` when a project is deleted.
- [x] **AC-7 — Backward compat:** projects/sessions with no project files behave
  exactly as today; `projectChunks` is empty when no project is open; global
  `/chunk-cache` (no `projectId`) is unaffected.

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | `_get_chunk_cache`, `_post_chunk_cache`, `_delete_chunk_cache` gain `projectId` routing; `_delete_project` cleans up `.chunk_cache/projects/<id>/`; `PROJECT_CACHE_DIR` helper |
| `app.js` | `projectChunks` array; `loadProjectChunks()` called on `openProject` + session restore; `getRelevantChunks` / `prepareContextMessages` merge both arrays; project-file upload/delete JS wiring |
| `index.html` | "Project files" section added inside project Settings modal (inline script wired to `app.js` helpers); `styles.css?v=28` → `?v=29` |
| `styles.css` | Project-files section styles (file list, spinner, upload row) — `?v=29` |
| `tests/python/test_server_http.py` | New tests PF-1…PF-7 (project chunk-cache CRUD, traversal guard, delete cascade, global backward compat) |
| `tests/js/app.test.mjs` | New tests PCJ-1…PCJ-4 (`projectChunks` populated by `loadProjectChunks`, merge in `getRelevantChunks`, cleared on project delete, empty when no project) |
| `docs/specs/projects-workspaces-slice4.md` | This spec |
| `CHANGELOG.md` | Entry under `[Unreleased]` |
| `docs/USER_GUIDE.md` | §8 Projects — add "Project files" subsection |
| `backlog.md` | Mark Slice 4 `[~]` In Progress → `[x]` Done at loop end |

---

## 4. Technical approach

### Role 2 — Architect sign-off

#### Backend: `server.py`

**New module-level constant** (alongside `CACHE_DIR`):

```python
PROJECT_CACHE_DIR = PROJECT_ROOT / '.chunk_cache' / 'projects'
PROJECT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
```

**`_get_chunk_cache` update:**
```python
# New branch at the top of the existing method:
project_id = params.get('projectId', [None])[0]
if project_id:
    safe_id = self._safe_project_id(project_id)
    if safe_id is None:
        return self._json_response(400, {'error': 'invalid projectId'})
    proj_cache = PROJECT_CACHE_DIR / safe_id
    # file=<name> → read one; no file → list all
    ...  # mirror existing CACHE_DIR logic using proj_cache
else:
    # existing CACHE_DIR path unchanged
```

**`_post_chunk_cache` update:** same `projectId` branch — write to `PROJECT_CACHE_DIR / safe_id / (filename + '.json')` when `projectId` present; create the dir with `mkdir(parents=True, exist_ok=True)`.

**`_delete_chunk_cache` update:** same `projectId` branch — delete one file or rmtree the project subdir.

**`_delete_project` update (AC-6):** after removing `.projects/<id>.json` and orphaning sessions, also run:
```python
import shutil
proj_cache_dir = PROJECT_CACHE_DIR / safe_id
if proj_cache_dir.exists():
    shutil.rmtree(proj_cache_dir)
```

All `projectId` values pass through `_safe_project_id` (already validates `^[A-Za-z0-9_-]+$` + traversal guard from Slice 1).

#### Frontend: `app.js`

**New globals:**
```js
const projectChunks = []; // { fileName, chunkId, text, embedding? }
```

**`loadProjectChunks(projectId)`** — new async function:
```js
async function loadProjectChunks(projectId) {
  projectChunks.length = 0;
  if (!projectId) return;
  try {
    const r = await loggedFetch(`/chunk-cache?projectId=${encodeURIComponent(projectId)}`);
    if (!r.ok) return;
    const files = await r.json(); // [{filename, chunks:[...]}]
    for (const f of files) {
      const detail = await loggedFetch(`/chunk-cache?projectId=${encodeURIComponent(projectId)}&file=${encodeURIComponent(f.filename)}`);
      if (!detail.ok) continue;
      const d = await detail.json();
      for (const c of (d.chunks || [])) {
        projectChunks.push({ fileName: f.filename, ...c });
      }
    }
  } catch (e) { /* non-fatal — project files silently unavailable */ }
}
```

**`openProject` update:** call `await loadProjectChunks(projectId)` after setting `currentProjectId`.

**Session restore update:** call `await loadProjectChunks(currentProjectId)` after loading `currentProjectId` from the restored session.

**`getRelevantChunks` update:** change `const chunks = chunksArr ?? fileChunks` to:
```js
const chunks = chunksArr ?? [...fileChunks, ...projectChunks];
```
The rest (keyword + semantic scoring, topK) is unchanged.

**`prepareContextMessages` update:** the existing `fileChunks.length > 0` guard should become `(fileChunks.length + projectChunks.length) > 0`; the rest flows through `getRelevantChunks` as before.

**Project delete cleanup:** in the existing JS delete-project path, add `projectChunks.length = 0` after `currentProjectId = null`.

**Project files UI wiring** (called from the Settings modal inline script):
- `uploadProjectFile(projectId, file)` — reads file content, chunks it via the existing `chunkText` helper, posts to `/chunk-cache?projectId=<id>`
- `deleteProjectFile(projectId, filename)` — calls `DELETE /chunk-cache?projectId=<id>&file=<name>`
- `listProjectFiles(projectId)` → returns the JSON list from `GET /chunk-cache?projectId=<id>`

These will be exported on `window._test` for unit testing.

#### HTML: `index.html` (project Settings modal)

Add a "Project files" section **after** the instructions row, inside the existing `createProjectModal`. The section is shown only when editing an existing project (hidden on "New project" mode — there is no project ID yet until after creation). A data attribute `data-mode="edit"` will control visibility.

```html
<div class="project-files-section" id="projectFilesSection">
  <label class="modal-label">Project files
    <span class="modal-label-hint">(shared across all chats in this project)</span>
  </label>
  <ul id="projectFilesList" class="project-files-list" aria-label="Uploaded project files"></ul>
  <label class="modal-btn modal-btn--sm" for="projectFileUploadInput" id="projectFileUploadBtn">
    + Upload file
    <input id="projectFileUploadInput" type="file" hidden multiple accept=".txt,.md,.pdf,.docx,.json,.csv" />
  </label>
  <span id="projectFileUploadStatus" class="project-files-status" aria-live="polite"></span>
</div>
```

The modal's inline script will call `listProjectFiles` / `uploadProjectFile` / `deleteProjectFile`.

#### CSS: `styles.css`

Minimal additions: `.project-files-section`, `.project-files-list`, `.project-files-list li`, `.project-files-status`. Bump `?v=29`.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint logic follows existing `_handler` + `routes` pattern (extending existing handlers, not adding new routes)
- [x] No new tool (project chunks are passed to the existing `search_files` tool through `fileChunks` merge)
- [x] `/config` unchanged (no secret exposure)
- [x] Path traversal rejected via `_safe_project_id` + directory confinement to `PROJECT_CACHE_DIR / safe_id`
- [x] CSS bump: `?v=28` → `?v=29`

---

## 4b. Shift-left governance findings

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All 7 ACs are binary and observable: HTTP status codes, JSON body shape, files written to correct paths, `projectChunks` array contents, cascade deletion confirmed by follow-up GET 404 |
| G-2 Scope / value | ✅ Pass | Exactly the feature described in backlog #27 Slice 4; completes Projects v1. No gold-plating. "Project home" view, sharing, icon picker all explicitly deferred. |
| G-3 Dependency coherence | ✅ Pass | Slices 1–3 (`_safe_project_id`, `/projects` CRUD, `currentProjectId`, `openProject`, session restore) all `[x]` Done. `/chunk-cache` endpoints exist. All prerequisites satisfied. |

---

## 5. Test plan (TDD-first)

| # | Test description | File | Type |
|---|-----------------|------|------|
| PF-1 | `POST /chunk-cache?projectId=proj_123` stores chunks in `.chunk_cache/projects/proj_123/` | `tests/python/test_server_http.py` | integration |
| PF-2 | `GET /chunk-cache?projectId=proj_123` lists the project's files | `tests/python/test_server_http.py` | integration |
| PF-3 | `GET /chunk-cache?projectId=proj_123&file=notes.txt` reads the project file | `tests/python/test_server_http.py` | integration |
| PF-4 | `DELETE /chunk-cache?projectId=proj_123&file=notes.txt` removes one project file | `tests/python/test_server_http.py` | integration |
| PF-5 | `POST /chunk-cache?projectId=../traversal` returns 400 (traversal rejected) | `tests/python/test_server_http.py` | integration |
| PF-6 | `DELETE /projects/<id>` (project delete) also removes `.chunk_cache/projects/<id>/` | `tests/python/test_server_http.py` | integration |
| PF-7 | `GET /chunk-cache` (no projectId) still returns global cache (backward compat) | `tests/python/test_server_http.py` | integration |
| PCJ-1 | `loadProjectChunks('proj_abc')` populates `projectChunks` from a mocked `/chunk-cache` response | `tests/js/app.test.mjs` | unit |
| PCJ-2 | `getRelevantChunks` merges `fileChunks` + `projectChunks` when both are populated | `tests/js/app.test.mjs` | unit |
| PCJ-3 | `getRelevantChunks` returns only `fileChunks` when `projectChunks` is empty | `tests/js/app.test.mjs` | unit |
| PCJ-4 | `loadProjectChunks(null)` clears `projectChunks` without error | `tests/js/app.test.mjs` | unit |

**TDD order:** write PF-1…PF-7 and PCJ-1…PCJ-4 first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — add entry under `[Unreleased]`
- [x] `docs/USER_GUIDE.md` — §8 Projects: add "Project files" subsection (upload, use, delete)
- [x] `README.md` — no setup/config/env var changes needed for Slice 4
- [x] `backlog.md` — mark Slice 4 `[~]` In Progress then `[x]` Done with spec link
- [x] `AGENTS.md` / `CONTINUE.md` — no convention changes needed

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| `projectId` not yet available when "New project" modal opens | "Project files" section is hidden (`data-mode="edit"` guard) when `createProjectModal` is in "create" mode; user can add files after project is created by re-opening settings |
| Large project files bloat the chunk cache | Reuse existing 50 MB POST size limit (`_MAX_BODY = 50 * 1024 * 1024`) in `_post_chunk_cache`; existing guard applies to the new project branch too |
| `PROJECT_CACHE_DIR` does not exist on fresh install | `PROJECT_CACHE_DIR.mkdir(parents=True, exist_ok=True)` at module load; per-project subdir created lazily on first POST |
| `_delete_project` fails midway (e.g. chunk_cache rmtree error) | `shutil.rmtree` wrapped in `try/except`; log the error but still return 200 (orphaned project cache is non-critical; matching existing delete semantics for memory notes) |
| `getRelevantChunks` injectable `chunksArr` param — tests pass explicit array | Change is additive: `chunksArr ?? [...fileChunks, ...projectChunks]`; when `chunksArr` is supplied (tests), the merge is bypassed as before |
| `server.py` line count | Slice 4 adds ~50 lines; current count is already above the ~1,500 INNOV-01 threshold — the #45 refactor is a separate future item; no action in this slice |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §6
- [x] Acceptance criteria AC-1…AC-7 all verified
- [x] Memory note written to `Cline/memories/`

## Spec changelog

> *Optional — populated only when a spec amendment is made during `/build`
> (see build.md §3d). Leave empty if no amendments were needed.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
