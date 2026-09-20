# Spec: Project Detail View (#81)

**Status:** Done
**Created:** 2026-09-18
**Author:** Cline

## 1. Goal & scope

Make projects a real container you can open and browse. Clicking a project
currently wipes the canvas — there is no way to see the chats saved under it.

### Root-cause audit

1. `openProject()` clears the canvas immediately with no detail view.
2. `showSessionsList()` (`app.js:1425`) filters project chats OUT of the
   sidebar; 11 sessions on disk are currently invisible.
3. Backend `GET /sessions` has no `?projectId=` filter.
4. `_showProjectSettingsModal` re-uses the create-modal with fragile
   handler-swapping.

**Out of scope:** per-project memory browser, bulk export.

## 2. User story & acceptance criteria

As a user I want to click a project and see its saved chats, start a new chat
inside it, and manage settings — without losing access to those chats.

- [x] **PD-1** Clicking a project opens a **project detail view** showing:
  project name, instructions snippet, and its list of chats.
- [x] **PD-2** A **"＋ New chat"** button in the detail view starts a fresh
  project-scoped chat (user explicitly initiates it).
- [x] **PD-3** Each chat in the list is clickable → calls `restoreSession`.
- [x] **PD-4** Project chats appear **grouped under their project** in the
  sidebar sub-list — no longer hidden.
- [x] **PD-5** Backend: `GET /sessions?projectId=<id>` returns only that
  project's sessions; traversal → 400.
- [x] **PD-6** Project **Settings** (name, instructions, memory mode, files)
  available from ⚙ button in detail view and from ⋯ menu. **COMPLETE (#82,
  2026-09-20):** the ⚙ button now opens a dedicated `#projectSettingsModal`; the
  fragile `_showProjectSettingsModal` handler-swap path was removed.
- [x] **PD-7** Delete from detail view confirms and returns to empty chat state.
  **COMPLETE (#82, 2026-09-20):** the detail view has a 🗑️ Delete Project button
  that confirms, `DELETE`s, and lands on the empty chat state (PD-JS-8/9).
- [x] **PD-8** All existing tests pass; new PD-* tests green.

## 3. Affected files

- `backend/session_handlers.py` — `_get_sessions`: add `?projectId=` filter
  with `_safe_project_id` guard
- `backend/tests/python/test_server_http.py` — PD-PY-1…PD-PY-3
- `frontend/app.js` — `openProject()` → `showProjectDetail()`; new helpers
  (`startNewProjectChat`, `_showProjectDetailView`, `_showChatView`); sidebar sub-lists
- `frontend/index.html` — `#projectDetailView` panel; bump `?v=31` (shared with #80).
  *(`#projectSettingsModal` deferred to #82 — the ⚙ button reuses the existing
  `_showProjectSettingsModal` path.)*
- `frontend/styles.css` — `.project-detail-view`, `.project-sub-list` etc; v31
- `frontend/tests/js/app.test.mjs` — PD-JS-1…PD-JS-5
- `docs/ARCHITECTURE.md` — §3b `/sessions` row + §4f sidebar/detail-view description

## 4. Technical approach

### 4a. Backend filter

In `_get_sessions` after building the `sessions` list:
```python
project_id_filter = params.get('projectId', [None])[0]
if project_id_filter:
    safe_pid, err = _safe_project_id(project_id_filter)
    if err:
        return  # 400 already sent
    sessions = [s for s in sessions if s.get('projectId') == safe_pid]
```

### 4b. Project detail view

`openProject(projectId)` calls `showProjectDetail(projectId)` instead of
clearing canvas directly. `showProjectDetail`:
1. Sets `currentProjectId`, loads metadata + instructions + chunks.
2. Fetches `GET /sessions?projectId=` for the session list.
3. Unhides `#projectDetailView`, hides `.chat-area` and `.empty-chat-area`.

New HTML panel (inside `.main-content`):
```html
<div id="projectDetailView" class="project-detail-view" hidden>
  <div class="project-detail-header">
    <h2 id="projectDetailName" class="project-detail-name"></h2>
    <div class="project-detail-actions">
      <button id="projectNewChatBtn">＋ New chat</button>
      <button id="projectSettingsBtn">⚙ Settings</button>
    </div>
  </div>
  <p id="projectDetailInstructions" class="project-detail-hint"></p>
  <div id="projectDetailSessions" class="project-detail-sessions"></div>
</div>
```

Clicking **＋ New chat** triggers the existing blank-canvas clear + project
scope (old `openProject` body, now refactored into `startNewProjectChat`).

### 4c. Sidebar sub-lists

`showSessionsList` groups sessions by `projectId` (object keyed by id).
`_renderProjectItem` wraps sessions in a `.project-sub-list`:
```html
<div class="project-sub-list">
  <session-item>…</session-item>
</div>
```

> **As-built deviation (accepted):** this was specced as a collapsible
> `<details><summary>2 chats</summary>` block. It shipped as a always-expanded
> plain `<div>` with no count summary, because each project's chats are already
> few and a second nested disclosure inside the `Projects` `<details>` made the
> sidebar hard to scan. The CSS class name is unchanged, so converting it back to
> `<details>` later is purely additive. No acceptance criterion referenced the
> collapse behaviour (PD-4 only requires grouping).

The "Chats" section only shows sessions where `!s.projectId` or orphaned.

### 4d. Dedicated project settings modal

Add `#projectSettingsModal` to `index.html` — a standalone modal with name,
instructions, memory mode, and files sections. `_showProjectSettingsModal`
populates and shows this modal. The `#createProjectModal` remains for creation
only — handler-swap pattern removed.

## 5. Test plan

| ID | File | Description |
|----|------|-------------|
| PD-PY-1 | test_server_http.py | GET /sessions?projectId=X → only that project's sessions |
| PD-PY-2 | test_server_http.py | GET /sessions?projectId=../x → 400 |
| PD-PY-3 | test_server_http.py | GET /sessions?projectId=nonexistent → 200 [] |
| PD-JS-1 | app.test.mjs | `showProjectDetail` renders project name in detail view |
| PD-JS-2 | app.test.mjs | "＋ New chat" calls blank-canvas path |
| PD-JS-3 | app.test.mjs | Sidebar renders sub-list sessions under correct project |
| PD-JS-4 | app.test.mjs | Sessions with `projectId` absent from root "Chats" section |
| PD-JS-5 | app.test.mjs | `openProject` calls `showProjectDetail`, not blank-canvas |
| PD-JS-6 | app.test.mjs | `_showChatView` clears **every** inline `display` override set by `_showProjectDetailView` (blank-canvas regression) |

> **As-built note on PD-JS-1/PD-JS-2:** the shipped tests do not assert on the
> DOM the way this table describes. `PD-JS-1` asserts the `sessionsByProject`
> grouping arithmetic and `PD-JS-2` asserts the `chatSessions` exclusion filter —
> both replicate the logic rather than invoke `showProjectDetail` /
> `startNewProjectChat`, because those functions need a real DOM. The behaviour
> they were meant to cover is genuinely untested at the DOM level; the
> jsdom-based `frontend/tests/js/app.behavior.test.mjs` harness is the correct
> home for it and its HTML skeleton has no `#projectDetailView` yet. Tracked as
> a follow-up cleanup item rather than silently claimed as covered.

## 6. Docs to update

- [x] CHANGELOG.md
- [x] docs/USER_GUIDE.md — Projects section rewrite
- [x] docs/ARCHITECTURE.md — `GET /sessions?projectId=` endpoint row
- [x] backlog.md — #81 lifecycle
- [x] Cline/scrum/product-backlog.md

## 7. Risks / edge cases

- Orphaned sessions (project deleted) already fall through to "Chats" — keep.
- Large project session lists: apply MAX_VISIBLE + "Show more" pattern.
- No `openCreateProjectModal` behaviour changes — creation flow untouched.

## 8. Review checklist

- [x] Implementation matches spec sections 3–5
- [x] `./run-tests.sh --coverage` passes
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated (section 6)
- [x] Memory note written
