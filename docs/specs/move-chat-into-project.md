# Spec: Move an existing chat into a project (#66)

**Status:** Done
**Type:** feature
**Created:** 2026-09-18
**Author:** Cline / user
**Backlog item:** #66

---

## 1. Goal & scope

Add a `PATCH /sessions/<id>` endpoint and a "Move to project…" context-menu
action so a user can reassign an existing chat to a different project (or clear
it to no-project) without deleting and recreating the chat.

### In scope
- `PATCH /sessions/<id>` endpoint — accepts `{ projectId }` (string or null),
  validates with `_safe_project_id`, writes updated session JSON.
- `do_PATCH` routing in `server.py`.
- Session context-menu "Move to project…" item with a project-picker overlay.
- On move of the **currently active** chat: update `currentProjectId` + reload
  `projectChunks` for the new project.
- Sidebar re-render after any move.

### Out of scope
- Memory notes written before the move are **not** relocated. Only future
  `saveMemory` calls use the new `projectId`. Explicit documented limitation.
- Drag-and-drop from sidebar (follow-up).
- Moving multiple chats at once.

---

## 2. User story & acceptance criteria

As a USAi user I want to move an existing chat into a project (or out to no
project) so I can reorganise my work without losing conversation history.

- [ ] **AC-1:** `PATCH /sessions/<id>` with `{ "projectId": "<valid_id>" }`
      updates the session file and returns `200 { ok: true }`.
- [ ] **AC-2:** `PATCH /sessions/<id>` with `{ "projectId": null }` or `""`
      clears `projectId` to `null` and returns `200 { ok: true }`.
- [ ] **AC-3:** `projectId` containing `/`, `\`, or starting with `.`
      returns `400`.
- [ ] **AC-4:** Session id not found returns `404`.
- [ ] **AC-5:** Path-traversal in session id (e.g. `../evil`) returns `400`.
- [ ] **AC-6:** UI "Move to project…" item appears on each session row's
      ⋯ context menu and opens a project picker.
- [ ] **AC-7:** Selecting a project (or "No project") from the picker calls
      `PATCH /sessions/<id>` then re-renders the sidebar.
- [ ] **AC-8:** When the active chat is moved, `currentProjectId` is updated
      and `loadProjectChunks` is called with the new project id (or `null`).
- [ ] **AC-9:** No regressions — sessions without `projectId` and all other
      endpoints behave exactly as before.

---

## 3. Affected files

| File | Change |
|------|--------|
| `backend/session_handlers.py` | Add `_patch_session(session_id)` |
| `backend/server.py` | Add `do_PATCH` routing for `/sessions/<id>` |
| `frontend/app.js` | Add `moveSessionToProject`, `_showSessionContextMenu`, update `_renderSessionItem` |
| `frontend/index.html` | Add `#sessionMoveModal` picker overlay |
| `frontend/styles.css` | Session ⋯ button + picker styles; bump `?v=N` |
| `frontend/tests/js/app.test.mjs` | MV-JS-1 … MV-JS-3 |
| `backend/tests/python/test_server_http.py` | MV-1 … MV-5 |
| `CHANGELOG.md` | New entry |
| `docs/USER_GUIDE.md` | §8 Projects — "Moving a chat into a project" |
| `docs/ARCHITECTURE.md` | Add `PATCH /sessions/<id>` to endpoint catalog |

---

## 4. Technical approach

### 4.1 Backend — `_patch_session`

```python
def _patch_session(self, session_id):
    """PATCH /sessions/<id> — update a session's projectId field.

    Body: { "projectId": "<id>" | null | "" }
    Returns 400 on traversal (session id or project id), 404 if not found,
    200 { ok: true } on success.
    """
```

- Sanitise `session_id` via `Path(session_id).name`; if it differs from raw
  input return 400 (traversal guard) — no file I/O.
- Read and parse body JSON; body size limited to 64 KiB.
- `projectId` from body: blank string / missing key / null → clear (`None`);
  non-blank → validate via `_safe_project_id` → 400 on traversal.
- Load session JSON; set / clear `projectId`; stamp `updatedAt`; write back.
- Return `200 { ok: true, id: safe_id }`.

### 4.2 Server routing — `do_PATCH`

```python
def do_PATCH(self):
    request_path = self.path.split('?', 1)[0]
    if request_path.startswith('/sessions/'):
        session_id = request_path[len('/sessions/'):]
        self._patch_session(session_id)
        return
    self.send_response(404)
    self.end_headers()
```

### 4.3 Frontend — `moveSessionToProject`

```js
async function moveSessionToProject(sessionId, projectId) {
  const res = await loggedFetch(`/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectId: projectId || null }),
  });
  return res.ok ? res.json() : null;
}
```

### 4.4 UI — session ⋯ menu + `_showSessionMoveModal`

- `_renderSessionItem(s)` gains a ⋯ button (`session-menu-btn`).
- `_showSessionContextMenu` shows "Move to project…" (and keeps the existing
  ✕ button for delete — ⋯ adds Move only).
- `_showSessionMoveModal(sessionId, projects)`:
  - Builds a small picker: "No project" + one item per project.
  - On select: calls `moveSessionToProject`; if `sessionId === currentSessionId`
    updates `currentProjectId` and calls `loadProjectChunks(pickedId)`.
  - Calls `showSessionsList()` to re-render sidebar.

### 4.5 Conventions
- Traversal rejection on session id (URL) + projectId (body).
- No new runtime dependencies.
- CSS `?v=N` bump in `index.html`.
- Body read limit 64 KiB.
- TDD: tests written first (Red → Green → Refactor).

---

## 5. Test plan

| Test | File | Description |
|------|------|-------------|
| MV-1 | test_server_http.py | PATCH with valid projectId → 200, session updated |
| MV-2 | test_server_http.py | PATCH with `projectId: null` → 200, field cleared |
| MV-3 | test_server_http.py | PATCH with traversal projectId → 400 |
| MV-4 | test_server_http.py | PATCH session not found → 404 |
| MV-5 | test_server_http.py | Traversal in session id → 400 |
| MV-JS-1 | app.test.mjs | `moveSessionToProject` issues PATCH with correct body |
| MV-JS-2 | app.test.mjs | null projectId sends `{ projectId: null }` |
| MV-JS-3 | app.test.mjs | Active-chat move updates exported `currentProjectId` |

---

## 6. Docs to update

- [ ] `CHANGELOG.md`
- [ ] `docs/USER_GUIDE.md` — §8 Projects: add "Moving a chat" subsection
- [ ] `docs/ARCHITECTURE.md` — `PATCH /sessions/<id>` in endpoint catalog
- [ ] `backlog.md` — mark #66 Done

---

## 7. Risks / edge cases

| Risk | Mitigation |
|------|-----------|
| Session id with path separators → traversal | `Path(session_id).name` check; 400 if differs |
| Moving active chat → stale `currentProjectId` | AC-8: check `sessionId === currentSessionId` |
| Picker opened while projects list is stale | Pass already-loaded `projects` array in |
| Pre-move memory notes stay in original folder | Documented out-of-scope limitation |
| `do_PATCH` absent → 501 from base class | Explicit `do_PATCH` added |

---

## 8. Review checklist

- [ ] Implementation matches spec §3–5
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (§6)
- [ ] Memory note written

