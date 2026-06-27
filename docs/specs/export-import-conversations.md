# Spec: Export / Import Conversations

**Status:** Ready
**Type:** feature
**Created:** 2026-06-26
**Author:** Cline / user
**Prior context:** None found in Obsidian vault for export/import; session storage uses `.chat_sessions/*.json` (server-side) and `chatDisplayHistory` (client-side).

---

## 1. Goal & scope

### Goal
Allow users to **download** the current or any past conversation as a JSON or Markdown
file, and to **re-import** a previously exported JSON file to restore the conversation
in the app. This makes conversations portable — users can archive, share, or reload
any chat without relying on the server's `.chat_sessions/` directory. The feature is
fully dependency-free (browser `Blob` / `FileReader` APIs only; no server changes
required for export; a small new `/import-session` endpoint for import).

### Out of scope
- Bulk export (all sessions at once) — only one session at a time for v1.
- Markdown import (export-only for Markdown; only JSON can be re-imported).
- Modifying an imported session after re-importing (treat it as a restored session).
- Any cloud/sync destination — local filesystem only.
- Auto-export scheduling.

---

## 2. User story & acceptance criteria

As a USAi user I want to export a conversation to a file and re-import it later so
that I can archive, share, or restore any chat independently of the server's session
storage.

- [ ] **AC-1 (JSON export):** A "⬇ Export" button in the session list context area (or on the active conversation toolbar) downloads the current session as a `.json` file. The file contains `title`, `createdAt`, `updatedAt`, `turns` (full `chatDisplayHistory` array). File is named `usai-export-<title-slug>-<date>.json`.
- [ ] **AC-2 (Markdown export):** The same export UI offers a "Markdown" variant that produces a `.md` file with each turn rendered as `**User:**` / `**Assistant:**` blocks (with the raw text, not HTML). Named `usai-export-<title-slug>-<date>.md`.
- [ ] **AC-3 (JSON import):** An "⬆ Import" button opens a file-picker restricted to `.json`. After the user selects an exported file, the app validates its structure (`turns` array with `role`/`content` fields), sends it to `POST /import-session`, which saves it as a new session and returns the new session ID. The app then loads and renders that session without a page reload.
- [ ] **AC-4 (Validation / error handling):** If the import file is not valid JSON, missing required fields, or exceeds a size limit (500 KB), the app shows a user-visible error message (not a console error) and does NOT corrupt the current session.
- [ ] **AC-5 (No regression):** All existing session-save/load/archive flows continue to work; `./run-tests.sh --coverage` passes with coverage gates unchanged or improved.

---

## 3. Affected files

| File | Change |
|------|--------|
| `app.js` | Add `exportSession(format)` (JSON/Markdown), `importSession()` (file-picker + POST), wire Export/Import buttons into UI |
| `index.html` | Add Export (JSON/Markdown) and Import buttons to sidebar header or session toolbar; bump `styles.css?v=28` |
| `styles.css` | Minor: style Export/Import buttons; bump to `?v=28` |
| `server.py` | Add `POST /import-session` handler: validate body, write new session JSON to `SESSIONS_DIR`, return `{id}` |
| `tests/python/test_server.py` | New `TestImportSession` class (unit + integration) |
| `tests/python/test_server_http.py` | New `TestImportSessionHTTP` integration tests |
| `tests/js/app.test.mjs` | New export/import helper unit tests |
| `docs/specs/export-import-conversations.md` | This spec |
| `docs/USER_GUIDE.md` | New "Export & Import Conversations" section |
| `CHANGELOG.md` | New entry under `[Unreleased]` |
| `backlog.md` | Mark #10 done |

---

## 4. Technical approach

### Role 2 — Architect sign-off

#### Client-side (app.js)

**`exportSession(format)`** — pure, testable helper:
- Reads `chatDisplayHistory` (current session) and current session metadata (`title`,
  `createdAt`, timestamps).
- `format === 'json'`: serialises the session object to a pretty-printed JSON string,
  creates a `Blob('application/json')`, triggers `URL.createObjectURL` + synthetic
  `<a>` click download. Filename: `usai-export-<slug>-<YYYY-MM-DD>.json`.
- `format === 'markdown'`: iterates turns, writes `**User:** …\n\n**Assistant:** …\n\n`
  blocks (using raw `content` text, not rendered HTML). Same download mechanism.
  Filename: `usai-export-<slug>-<YYYY-MM-DD>.md`.
- Returns early (no-op) if `chatDisplayHistory.length === 0`.
- Exported for unit tests: `exportedForTesting.exportSession`.

**`importSession()`** — UI-facing:
- Creates a hidden `<input type="file" accept=".json">`, triggers a click.
- On `change`: reads the file with `FileReader.readAsText`, parses JSON, validates
  structure (`turns` array with at least one `{role, content}` entry, total size ≤ 500 KB).
- On failure: calls `showImportError(message)` — renders an inline error below the
  Import button (not `alert()`), does NOT touch current session state.
- On success: POSTs `{title, turns, createdAt}` to `/import-session`, on 200 response
  loads the returned `id` via `loadSession(id)`.

**`slugify(str)`** — new pure helper (already partially covered by `_slugify` in Python; JS side needed for filename generation). Exported for tests.

**UI wiring:**
- Export: two buttons `"⬇ JSON"` / `"⬇ MD"` added to the active session's header action row (next to the existing New Chat button, or as a small icon-row in the sidebar header). Both are `aria-label`-ed and visible only when `chatDisplayHistory.length > 0`.
- Import: one `"⬆ Import"` button in the sidebar header area. Always enabled.

#### Server-side (server.py)

**`POST /import-session`** — new endpoint:
- Reads JSON body; validates: must have `turns` (list, ≥ 1 items each with `role` +
  `content`), and total body size ≤ 512 000 bytes (enforced via `Content-Length` check
  or `rfile.read` limit).
- Generates a new unique session ID (same pattern as `_post_new_chat_session`:
  `session_<timestamp>`).
- Sanitizes `title` (strip, truncate to 200 chars, fallback "Imported chat").
- Writes `{id, title, turns, createdAt, updatedAt, source: "import"}` to
  `SESSIONS_DIR / (new_id + '.json')`.
- Returns `{"id": new_id}` with status 200.
- On validation failure: returns 400 + `{"error": "..."}`.
- Path traversal: uses `Path(new_id).name` guard (same as existing session handlers).
- No SSRF — pure filesystem; no upstream calls.

**Conventions applied:**
- [x] No new runtime dependency added (Blob/FileReader/URL are browser-built-in; server-side is pure stdlib)
- [x] New endpoint follows `_handler` + `routes` pattern
- [x] New tool — N/A (not a tool-calling tool, just a UI feature)
- [x] `/config` exposes no secrets — N/A
- [x] Path traversal rejected — `Path(id).name` used for session file path
- [x] CSS bump applied — `styles.css?v=28`

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | `exportSession('json')` returns a JSON blob with correct `turns` from `chatDisplayHistory` | `tests/js/app.test.mjs` | unit |
| T-2 | `exportSession('markdown')` returns a Markdown string with `**User:**` / `**Assistant:**` blocks | `tests/js/app.test.mjs` | unit |
| T-3 | `exportSession()` is a no-op when `chatDisplayHistory` is empty | `tests/js/app.test.mjs` | unit |
| T-4 | `slugify('Hello World! 2026')` → `'hello-world-2026'` (strips special chars, lowercases) | `tests/js/app.test.mjs` | unit |
| T-5 | `POST /import-session` with valid body → 200 + `{"id": "session_..."}` + file exists in `SESSIONS_DIR` | `tests/python/test_server.py` | unit |
| T-6 | `POST /import-session` with missing `turns` field → 400 | `tests/python/test_server.py` | unit |
| T-7 | `POST /import-session` with empty `turns` list → 400 | `tests/python/test_server.py` | unit |
| T-8 | `POST /import-session` with body > 512 KB → 400 | `tests/python/test_server.py` | unit |
| T-9 | `POST /import-session` with invalid JSON body → 400 | `tests/python/test_server.py` | unit |
| T-10 | `POST /import-session` integration: session file is created and readable by `GET /sessions` | `tests/python/test_server_http.py` | integration |

**TDD order:** write all T-1…T-10 tests first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — new "Export & Import Conversations" section
- [ ] `README.md` — N/A (no setup/config/env changes)
- [ ] `backlog.md` — mark #10 done
- [ ] `AGENTS.md` / `CONTINUE.md` — N/A (no convention changes)

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Large conversations (1000+ turns) produce very large JSON files | `turns` are already capped at 200 in `archiveCurrentSession`; export uses `chatDisplayHistory` which is the display slice — document the 200-turn cap |
| Markdown export of assistant messages with embedded HTML (from `renderMarkdown`) | Export uses raw `content` text field, never the rendered DOM — no HTML in output |
| Import file from a different/future version with extra fields | Server ignores unknown fields; only `turns` (role+content) and `title` are required |
| Malformed `content` value (null, object) in imported turns | Validate each turn: `role` in `['user','assistant','system']`, `content` is a non-empty string or array; reject with 400 otherwise |
| Race condition: user clicks Import while a request is in flight | Import button checks `activeAbortController` and shows "Please wait for the current request to finish" |
| Path traversal via crafted session id in import | Server generates its own ID — never uses any ID from the import payload |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-5 all verified
- [ ] Memory note written to `Cline/memories/`
