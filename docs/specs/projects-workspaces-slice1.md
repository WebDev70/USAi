# Spec: Projects (ChatGPT-style Workspaces) — Slice 1: CRUD + Sidebar + `currentProjectId` Plumbing

**Status:** Done
**Type:** feature
**Created:** 2026-06-29
**Author:** Cline / user
**Prior context:** Full planning note + 2nd-round critical quality review found in `Continue Extension/memories/2026-06-20-223334-projects-feature-plan-and-review.md`. Three §8 decisions confirmed by user: (1) delete orphans chats to "Chats" + preserves memory notes, (2) project instructions prepended first `\n\n`-joined, (3) v1 = Slices 1–3 only.

---

## 1. Goal & scope

### Goal
Add a ChatGPT-style **Projects** feature to USAi Chat. A Project is a named workspace
that groups related chats and gives them shared context (instructions, optional files,
and a scoped memory mode). Slice 1 delivers the foundational plumbing: project CRUD,
`currentProjectId` state wired through **both** archive paths, and a sectioned/collapsible
sidebar (Pinned / Projects / Chats). Without this slice the later instruction and memory
slices have nothing to hang on.

### Out of scope (this slice)
- Project instructions (3-layer system prompt) — Slice 2
- Memory modes (Default / Project-only) — Slice 3
- Project files / shared knowledge (`projectChunks`) — Slice 4 (deferred)
- Share project, emoji/icon picker, "Project home" landing view — deferred polish
- v1 scope confirmed: only Slices 1–3 will be built

---

## 2. User story & acceptance criteria

As a USAi user I want to create named Projects and start chats inside them so that related work stays organized and I can find it easily.

- [ ] **AC-1 — Create project:** `POST /projects` accepts `{name, memoryMode}`, generates a server-side `project_<epoch-ms>` id, writes `.projects/<id>.json`, and returns `{id, name, memoryMode, pinned, createdAt}`. `memoryMode` defaults to `"default"` and is **immutable** after creation — the `PUT /projects/:id` endpoint silently ignores any `memoryMode` field in the request body and returns the stored value unchanged.
- [ ] **AC-2 — List / read / delete:** `GET /projects` returns the array of all project metadata sorted by `createdAt` desc. `DELETE /projects/:id` removes `.projects/<id>.json` and **clears** the `projectId` field from every session in `.chat_sessions/` that references it (orphans chats to "Chats") — it does NOT delete sessions or Obsidian memory notes.
- [ ] **AC-3 — Pin / rename:** `PUT /projects/:id` updates `name` and/or `pinned` flag; `memoryMode` changes are silently ignored. Returns updated metadata.
- [ ] **AC-4 — `currentProjectId` plumbing:** The frontend maintains a `currentProjectId` variable. When a user opens or creates a project, `currentProjectId` is set. Both archive paths — JS `archiveCurrentSession()` (POST `/sessions`) **and** Python `_post_new_chat_session` (POST `/new-chat-session`) — stamp `projectId` onto the archived session JSON. Sessions restored from `.chat_sessions/` re-populate `currentProjectId` from their stored `projectId` field.
- [ ] **AC-5 — Sectioned sidebar:** `showSessionsList()` is rewritten to render three sections: **Pinned** (pinned projects + any pinned chats), **Projects** (collapsible `<details>` with "Show more" truncation at 5), and **Chats** (ungrouped sessions, sessions with no `projectId`, or sessions whose project was deleted). Uses semantic `<details>`/`aria-expanded`; `styles.css?v=N` bumped.
- [ ] **AC-6 — Legacy migration:** Existing session JSON files that have no `projectId` field load without error and appear under the **Chats** section. No migration script is needed — `undefined`/`null` `projectId` is treated as "no project."
- [ ] **AC-7 — Traversal guard:** `projectId` values used in filesystem paths (`.projects/<id>.json`, future `.chunk_cache/projects/<id>/`) are validated server-side against the generated `project_<epoch-ms>` slug pattern; path traversal attempts return 400.

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | Add `/projects` GET/POST/PUT/DELETE handlers; `get_project()` helper; `_post_new_chat_session` stamps `projectId`; traversal guard for project ids |
| `app.js` | Add `currentProjectId` state; update `archiveCurrentSession()` to include `projectId`; rewrite `showSessionsList()` into sectioned sidebar; project create/rename/delete/pin wiring |
| `index.html` | Add "New Project" button + create-project modal (name + memory mode selector); sidebar section markup if not fully JS-rendered; bump `styles.css?v=N` |
| `styles.css` | Sidebar section styles (Pinned/Projects/Chats headings, `<details>` disclosure, "Show more"); project-item icons; bump `?v=N` |
| `tests/python/test_server_http.py` | New integration tests PR-1…PR-8 for `/projects` CRUD + orphan-on-delete + traversal guard |
| `tests/python/test_server.py` | Unit tests for `_slugify`-like project id validation, `_post_new_chat_session` projectId stamping |
| `tests/js/app.test.mjs` | New JS unit tests PJ-1…PJ-6 for `currentProjectId` stamping in archive path, sidebar section rendering |
| `docs/specs/projects-workspaces-slice1.md` | This spec |
| `CHANGELOG.md` | Entry under `[Unreleased]` |
| `docs/USER_GUIDE.md` | New §9 Projects section |
| `backlog.md` | Mark #27 `[~]` In Progress with spec link |

---

## 4. Technical approach

### Role 2 — Architect sign-off

#### Backend: `/projects` endpoints

New handler class additions to `EnvConfigHTTPRequestHandler`:

```python
# Routes to add:
do_GET:  '/projects'      → _get_projects()       # list all
do_POST: '/projects'      → _post_project()        # create
do_PUT:  '/projects'      → _put_project(id)        # update name/pin; ignore memoryMode
do_DELETE:'/projects'     → _delete_project(id)     # orphan sessions, preserve memory

# Helper:
_resolve_project_file(project_id) → Path   # traversal guard (rejects '../', checks pattern)
_load_projects()                   → list  # reads .projects/*.json sorted by createdAt
```

Project storage: `.projects/<project_id>.json` (mirroring `.chat_sessions/` pattern).

`_delete_project(id)`:
1. Remove `.projects/<id>.json`.
2. List all `.chat_sessions/*.json`; for each: if `session["projectId"] == id`, write back with `projectId` set to `None` (or omitted).
3. Do NOT touch `.chunk_cache/` (Slice 4) or Obsidian vault (Slice 3).

`_post_new_chat_session` update: extract `projectId` from the JSON body and stamp it onto the session before writing.

#### Frontend: `currentProjectId` state

```js
// New module-level variable:
let currentProjectId = null;

// Updated archiveCurrentSession():
body.projectId = currentProjectId;   // add to POST /sessions payload

// Session restore: set currentProjectId from session.projectId (or null)
```

#### Frontend: `showSessionsList()` rewrite

Replace the flat `innerHTML` rebuild with three `<section>` blocks:

```
<section class="sidebar-section" id="sidebar-pinned">
  <h3>Pinned</h3>  <!-- shown only when items exist -->
  ...pinned projects + pinned chats...
</section>

<section class="sidebar-section" id="sidebar-projects">
  <details open>
    <summary>Projects <button class="new-project-btn">+</button></summary>
    ...project items (max 5 visible; "Show more" expands)...
  </details>
</section>

<section class="sidebar-section" id="sidebar-chats">
  <h3>Chats</h3>
  ...ungrouped sessions...
</section>
```

Project items show folder icon + name + context menu (Rename / Pin / Settings / Delete).

#### `/config` addition

Add `has_projects: true` boolean to `/config` response (always true when the server is running — no env-var gate needed).

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (N/A — no new tools in Slice 1)
- [x] `/config` exposes no secrets (only `has_projects` boolean)
- [x] Path traversal rejected on filesystem access (project id validated)
- [x] CSS bump applied (`styles.css?v=N`)

---

## 4b. Shift-left governance findings (Step 2b output)

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All 7 ACs are binary and observable (HTTP status codes, JSON field presence, filesystem state, DOM sections) |
| G-2 Scope / value | ✅ Pass | Every item maps to "organize chats into projects." Memory modes, project files, and polish deferred to later slices — no gold-plating. |
| G-3 Dependency coherence | ✅ Pass | All prerequisite systems (#16 Obsidian memory, #7 RAG, #9 streaming, #10 sessions) are `[x]` Done. No open prerequisites. |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| PR-1 | `POST /projects` → 201 + `{id, name, memoryMode, pinned, createdAt}` | `test_server_http.py` | integration |
| PR-2 | `GET /projects` returns array sorted by `createdAt` desc | `test_server_http.py` | integration |
| PR-3 | `PUT /projects/:id` updates `name` and `pinned`; `memoryMode` change is silently ignored | `test_server_http.py` | integration |
| PR-4 | `DELETE /projects/:id` removes project file + clears `projectId` from sessions that referenced it | `test_server_http.py` | integration |
| PR-5 | `DELETE /projects/:id` does NOT delete orphaned sessions (they persist with `projectId=null`) | `test_server_http.py` | integration |
| PR-6 | Path traversal in project id (e.g. `../../etc/passwd`) → 400 | `test_server_http.py` | integration |
| PR-7 | `POST /new-chat-session` with `projectId` in body stamps it onto the archived session JSON | `test_server.py` | unit |
| PR-8 | `POST /new-chat-session` without `projectId` → archived session has no `projectId` field (legacy compat) | `test_server.py` | unit |
| PJ-1 | `currentProjectId` is included in `archiveCurrentSession()` POST body when set | `app.test.mjs` | unit |
| PJ-2 | `currentProjectId` is `null` in `archiveCurrentSession()` POST body when not set | `app.test.mjs` | unit |
| PJ-3 | Session restore sets `currentProjectId` from `session.projectId` | `app.test.mjs` | unit |
| PJ-4 | Session with no `projectId` field → `currentProjectId` set to `null` (legacy migration) | `app.test.mjs` | unit |
| PJ-5 | Sidebar renders "Pinned", "Projects", and "Chats" sections when projects exist | `app.test.mjs` | unit |
| PJ-6 | Sidebar renders only "Chats" section when no projects exist | `app.test.mjs` | unit |

**TDD order:** write all PR-* and PJ-* tests first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — new §9 Projects (create, open, rename, pin, delete)
- [ ] `README.md` — no setup/config changes needed for Slice 1
- [ ] `backlog.md` — mark #27 `[~]` In Progress, add spec link
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention changes needed

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| `projectId` silently dropped on archive path | Both paths covered by PR-7/PR-8 and PJ-1/PJ-2 TDD tests |
| Concurrent session writes during delete-orphan sweep | `.chat_sessions/` writes are already single-threaded via Python GIL + ThreadingHTTPServer; sweep reads then rewrites each file atomically |
| Sidebar rebuild breaks existing session click listeners | `showSessionsList` already does full `innerHTML` + re-binds listeners on every call; maintain that pattern |
| `<details>` / `aria-expanded` accessibility | UI/UX rule requires semantic disclosure + `aria-expanded`; already in AC-5 |
| CSS version collision | Must audit current `?v=` value in `index.html` before bumping |
| `server.py` line count approaching ~1,200 (Slice 1 will add ~100 lines) | Module split at ~1,500 is already on backlog as #45 (deferred) |
| Memory-mode immutability (enforced here in Slice 1, used in Slice 3) | `PUT /projects` ignores `memoryMode` field in update; PR-3 verifies this |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-7 all verified
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

> *Optional — populated only when a spec amendment is made during `/build`
> (see build.md §3d). Leave empty if no amendments were needed.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
