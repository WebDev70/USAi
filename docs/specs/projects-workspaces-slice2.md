# Spec: Projects (ChatGPT-style Workspaces) — Slice 2: Project Instructions (3-layer system-prompt concat)

**Status:** Done
**Type:** feature
**Created:** 2026-06-30
**Author:** Cline / user
**Prior context:** Slice 1 spec `docs/specs/projects-workspaces-slice1.md`. Backlog note at line 440 confirms: project instructions first, `\n\n`-joined with per-chat prompt. See also `Continue Extension/memories/2026-06-20-223334-projects-feature-plan-and-review.md`.

---

## 1. Goal & scope

### Goal
Add a free-text **Instructions** field to each Project. When a user is inside a
project, every message sent to the API prepends the project's instructions to the
per-chat system prompt, forming a **3-layer system prompt**:

```
Layer 1: project.instructions          (may be empty → omitted)
Layer 2: per-chat systemPrompt input   (may fall back to default_system_prompt)
──────────────────────────────────────
Effective system prompt = [layer1, layer2].filter(non-empty).join('\n\n')
```

This must survive all build paths: first send, regenerate, edit-resend, and session restore.

### Out of scope (this slice)
- Memory modes (Default / Project-only) — Slice 3
- Project files / shared knowledge (`projectChunks`) — Slice 4 (deferred)
- Per-session overriding of project instructions — not in v1

---

## 2. User story & acceptance criteria

As a USAi user I want to set custom instructions on a project so that every chat
in that project automatically uses those instructions without me re-typing them.

- [x] **AC-1 — Store instructions:** `POST /projects` body may include optional `instructions` (string, max 8 KB, defaults `''`). The field is stored in `.projects/<id>.json` and returned in the response.
- [x] **AC-2 — Edit instructions:** `PUT /projects/:id` may update `instructions`; the updated value is persisted and returned. `memoryMode` remains immutable.
- [x] **AC-3 — Legacy compat:** Project JSON files without an `instructions` field load without error; the missing field is treated as `''`.
- [x] **AC-4 — Frontend cache:** A module-level `currentProjectInstructions` variable mirrors the open project's instructions string. It is set in `openProject()`, in `restoreSession()` (from the session's project), and cleared to `''` on new-chat / no project.
- [x] **AC-5 — 3-layer compose:** `composeSystemPrompt(projectInstructions, perChatPrompt)` (a pure exported helper) concatenates non-empty layers with `'\n\n'`. If both are empty the return value is `''`. If only one layer is non-empty the return value is that layer (no leading/trailing `\n\n`).
- [x] **AC-6 — Message-build path:** `sendMessage()` uses `composeSystemPrompt(currentProjectInstructions, inputs.systemPrompt)` to build the effective system prompt. Since regenerate and edit-resend both call `sendMessage()`, they inherit the composed prompt automatically.
- [x] **AC-7 — Session restore path:** When `restoreSession(id)` reconstructs the chat, it also fetches the project record (via `loadProjects()` already in scope) to populate `currentProjectInstructions`. If the session has no `projectId`, `currentProjectInstructions` is set to `''`.
- [x] **AC-8 — Settings UI:** The project Settings modal contains an **Instructions** textarea. Saving it calls `PUT /projects/:id` with the updated `instructions`. The create-project modal also offers an Instructions field (optional; submits empty string if blank).
- [x] **AC-9 — Instructions length cap:** Server rejects `instructions` longer than 8 192 bytes (8 KB) with HTTP 400 `{'error': 'instructions too long'}`.

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | `_post_projects` — accept + validate `instructions`; `_put_project` — allow updating `instructions`; 8 KB cap on both |
| `app.js` | Add `currentProjectInstructions` module var; `composeSystemPrompt()` helper; update `sendMessage()`, `openProject()`, `restoreSession()`, new-chat reset |
| `index.html` | Instructions `<textarea>` in create-project modal + project settings modal; bump `styles.css?v=28` |
| `styles.css` | Textarea styling for instructions field inside modals |
| `tests/python/test_server_http.py` | New tests PR-9, PR-10, PR-11 (instructions CRUD + length cap) |
| `tests/python/test_server.py` | PR-12: legacy project without `instructions` field loads as `''` |
| `tests/js/app.test.mjs` | New tests PJ-7…PJ-11 (`composeSystemPrompt`, cache, build-path) |
| `docs/specs/projects-workspaces-slice2.md` | This spec |
| `CHANGELOG.md` | Entry under `[Unreleased]` |
| `docs/USER_GUIDE.md` | §8 Projects — add Instructions subsection |
| `backlog.md` | Mark Slice 2 `[~]` In Progress → `[x]` Done at loop end |

---

## 4. Technical approach

### Role 2 — Architect sign-off

#### Backend: `server.py`

```python
# _post_projects: add instructions handling
INSTRUCTIONS_MAX = 8192  # bytes
instructions = (data.get('instructions') or '').strip()
if len(instructions.encode('utf-8')) > INSTRUCTIONS_MAX:
    self._json_response(400, {'error': 'instructions too long'})
    return
project = {
    ...,
    'instructions': instructions,
}

# _put_project: allow updating instructions
if 'instructions' in updates:
    inst = (updates['instructions'] or '').strip()
    if len(inst.encode('utf-8')) > INSTRUCTIONS_MAX:
        self._json_response(400, {'error': 'instructions too long'})
        return
    project['instructions'] = inst
```

No new server-side helper needed — `instructions` is a plain field on the project JSON, exactly like `name` and `pinned`.

#### Frontend: `app.js`

**New module-level variable** (alongside `currentProjectId`):
```js
let currentProjectInstructions = ''; // instructions string for the open project
```

**New pure helper** (exported for tests):
```js
export function composeSystemPrompt(projectInstructions, perChatPrompt) {
  const layers = [projectInstructions, perChatPrompt].filter(s => s && s.trim());
  return layers.join('\n\n');
}
```

**`sendMessage()` change (line ~2846):**
```js
// Before:
if (inputs.systemPrompt) messages.push({ role: 'system', content: inputs.systemPrompt });

// After:
const effectiveSystemPrompt = composeSystemPrompt(currentProjectInstructions, inputs.systemPrompt);
if (effectiveSystemPrompt) messages.push({ role: 'system', content: effectiveSystemPrompt });
```

**`openProject()` change:**
```js
async function openProject(projectId) {
  currentProjectId = projectId;
  // Fetch the project to populate its instructions.
  const projects = await loadProjects();
  const proj = projects.find(p => p.id === projectId);
  currentProjectInstructions = (proj && proj.instructions) || '';
  // ... rest unchanged
}
```

**`restoreSession()` change:**
```js
// After restoring currentProjectId:
currentProjectId = data.projectId || null;
if (currentProjectId) {
  const projects = await loadProjects();
  const proj = projects.find(p => p.id === currentProjectId);
  currentProjectInstructions = (proj && proj.instructions) || '';
} else {
  currentProjectInstructions = '';
}
```

**New-chat / no-project reset:** any place `currentProjectId = null` is also set, clear `currentProjectInstructions = ''`.

**Conventions applied:**
- [x] No new runtime dependency
- [x] `composeSystemPrompt` is a pure function — trivially testable
- [x] No new endpoint (instructions rides on existing `/projects` PUT/POST)
- [x] `/config` unchanged (no secret exposure)
- [x] `styles.css?v=28` bump applied
- [x] 8 KB cap enforced server-side (both create and update paths)

---

## 4b. Shift-left governance findings

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All ACs are binary and observable (HTTP status, JSON field, DOM state, composed string) |
| G-2 Scope / value | ✅ Pass | Exactly the feature described in backlog. No gold-plating. `composeSystemPrompt` helper is the minimal unit. |
| G-3 Dependency coherence | ✅ Pass | Slice 1 (`currentProjectId`, `/projects` endpoints, session restore) is `[x]` Done. |

---

## 5. Test plan (TDD-first)

| # | Test description | File | Type |
|---|-----------------|------|------|
| PR-9 | `POST /projects` with `instructions` → 201 + instructions field in response | `test_server_http.py` | integration |
| PR-10 | `PUT /projects/:id` with `instructions` → 200 + updated instructions in response; `memoryMode` still ignored | `test_server_http.py` | integration |
| PR-11 | `POST /projects` with instructions > 8 192 bytes → 400 `instructions too long` | `test_server_http.py` | integration |
| PR-12 | `GET /projects` on legacy project JSON (no `instructions` field) → does not error, `instructions` absent or `''` | `test_server.py` | unit |
| PJ-7 | `composeSystemPrompt('proj inst', 'per-chat')` → `'proj inst\n\nper-chat'` | `app.test.mjs` | unit |
| PJ-8 | `composeSystemPrompt('', 'per-chat')` → `'per-chat'` (no leading `\n\n`) | `app.test.mjs` | unit |
| PJ-9 | `composeSystemPrompt('proj inst', '')` → `'proj inst'` (no trailing `\n\n`) | `app.test.mjs` | unit |
| PJ-10 | `composeSystemPrompt('', '')` → `''` | `app.test.mjs` | unit |
| PJ-11 | `sendMessage` builds system message from composed prompt when `currentProjectInstructions` is set | `app.test.mjs` | unit |

**TDD order:** write PR-9…PR-12 and PJ-7…PJ-11 first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — §8 Projects: add Instructions subsection (how to set, how it works in chat)
- [ ] `README.md` — no setup/config changes needed for Slice 2
- [ ] `backlog.md` — mark Slice 2 `[~]` In Progress then `[x]` Done with spec link
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention changes needed

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| `currentProjectInstructions` stale after `PUT /projects/:id` updates instructions mid-chat | Session-level cache; user must re-open project or start new chat to pick up changes. Acceptable in v1 — document in USER_GUIDE. |
| `loadProjects()` called in `restoreSession()` adds latency | `loadProjects` is an existing fetch already called in `showSessionsList`; it hits the local server — negligible. |
| Instructions with only whitespace treated as non-empty | `.trim()` applied in `composeSystemPrompt` filter; server also `.strip()`s before storing. |
| 8 KB cap may be too low for power users | 8 KB ≈ 2,000 words, sufficient for most instruction sets. Can be raised in a later slice if user requests it. |
| `server.py` line count | After Slice 2 adds ~20 lines, still well under the 1,500 split threshold. |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §6
- [x] Acceptance criteria AC-1…AC-9 all verified
- [x] Memory note written to `Cline/memories/`

## Spec changelog

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
