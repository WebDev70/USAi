# Implementation Plan

[Overview]
Implement backlog item #10: allow users to export a conversation as JSON or Markdown and re-import a previously exported JSON file.

This feature adds two pure-frontend capabilities — download and upload — that operate entirely within the browser using vanilla JS (Blob + URL.createObjectURL for download; FileReader for upload). No new server endpoints are needed: the existing in-memory `conversationHistory` and `chatDisplayHistory` arrays are the data source, and the existing `appendMessage` + `archiveCurrentSession` flow handles import replay. The feature is gated behind two buttons added to the composer toolbar area (or the sidebar settings panel), keeping the HTML/CSS change minimal. A `styles.css?v=N` bump is required per convention. All new logic goes into `app.js` as pure exported helper functions backed by `node --test` unit tests.

[Types]
No new TypeScript types; the plan uses JSDoc-style descriptions for the two format shapes.

The two export formats are:

**JSON format** (`.json`) — a structured object matching the existing session shape so a file produced by export can also be used with the session-restore path if desired:
```json
{
  "exported": "2026-06-25T18:00:00.000Z",
  "model": "gpt-4o",
  "messageCount": 4,
  "messages": [
    { "role": "user",      "content": "Hello" },
    { "role": "assistant", "content": "Hi there!" }
  ]
}
```
Fields: `exported` (ISO timestamp string), `model` (string, current selected model), `messageCount` (integer), `messages` (array of `{role, content}` objects — same shape as `conversationHistory`).

**Markdown format** (`.md`) — a human-readable transcript:
```markdown
# Conversation Export

**Exported:** 2026-06-25T18:00:00.000Z
**Model:** gpt-4o
**Messages:** 4

---

**User**

Hello

---

**Assistant**

Hi there!

---
```

**Import** accepts only the JSON format. Validation rules:
- Must be valid JSON (catch parse errors → user-visible error log)
- Must have a top-level `messages` array
- Every element must have `role` in `["user","assistant","system","tool"]` and a truthy `content` string
- Reject empty arrays
- Maximum 500 messages (safety cap)

[Files]
New and modified files for the export/import feature.

**New files:**
- `docs/specs/export-import-conversations.md` — RAIL spec document for this item

**Modified files:**
- `app.js` — add `buildExportJson`, `buildExportMarkdown`, `triggerDownload`, `parseImportJson`, `importConversation` pure helpers; add `exportConversationJSON`, `exportConversationMarkdown`, `handleImportFile` UI-wired functions; wire two export buttons + one import button in `DOMContentLoaded`; add exports to `module.exports`
- `index.html` — add Export JSON button, Export Markdown button, Import (file input + label button) in the sidebar under a new "Export / Import" collapsible section; bump `styles.css?v=N` query string
- `styles.css` — add styling for the export/import button group and file-input label button; bump version comment
- `tests/js/app.test.mjs` — add 6+ new unit tests (EX-1 through EX-6) for the pure helpers
- `CHANGELOG.md` — new entry for #10
- `backlog.md` — check off item #10
- `docs/USER_GUIDE.md` — add export/import description to §8 "Managing Chats & History"

**No server.py changes required.**

[Functions]
New and modified functions for the export/import feature.

**New pure helper functions in `app.js`** (all exported via `module.exports`):

| Name | Signature | Purpose |
|------|-----------|---------|
| `buildExportJson` | `(messages, model) → string` | Serializes `conversationHistory` + current model to the JSON export format. Returns a JSON string. |
| `buildExportMarkdown` | `(messages, model) → string` | Converts `conversationHistory` + current model to the Markdown transcript format. Returns a string. |
| `triggerDownload` | `(content, filename, mimeType) → void` | Creates a `Blob`, calls `URL.createObjectURL`, appends a temporary `<a>` to `document.body`, clicks it, then revokes the URL. Browser-only; skipped in Node tests by passing a stub. |
| `parseImportJson` | `(text) → { messages, model, error }` | Parses and validates the JSON import payload. Returns `{ messages, model }` on success or `{ error: string }` on failure. Pure — no DOM or fetch. |

**New UI-wired functions in `app.js`** (not exported):

| Name | Signature | Purpose |
|------|-----------|---------|
| `exportConversationJSON` | `() → void` | Reads `conversationHistory`, calls `buildExportJson`, then `triggerDownload` with a timestamped filename. |
| `exportConversationMarkdown` | `() → void` | Reads `conversationHistory`, calls `buildExportMarkdown`, then `triggerDownload`. |
| `handleImportFile` | `(file: File) → Promise<void>` | Reads the file via `FileReader`, calls `parseImportJson`, validates, then rebuilds `conversationHistory` + `chatDisplayHistory` by calling `appendMessage` for each turn, then archives the new session. Shows error/success via `logger`. |

**`DOMContentLoaded` wiring additions:**
- Attach `click` listener on `#exportJsonBtn` → `exportConversationJSON()`
- Attach `click` listener on `#exportMdBtn` → `exportConversationMarkdown()`
- Attach `change` listener on `#importFileInput` → `handleImportFile(event.target.files[0])`

**`module.exports` additions:**
- `buildExportJson`
- `buildExportMarkdown`
- `parseImportJson`
- `triggerDownload` (with a note that it is no-op in tests without a DOM)

[Classes]
No new or modified classes. The codebase uses module-level functions, not classes for this kind of feature.

[Dependencies]
No new runtime or dev dependencies. The feature uses only browser-native APIs already available:
- `Blob` — already available in all target browsers
- `URL.createObjectURL` / `URL.revokeObjectURL` — already available
- `FileReader` — already available
- `JSON.stringify` / `JSON.parse` — stdlib

No changes to `requirements.txt`, `requirements-dev.txt`, or `package.json`.

[Testing]
Six new JS unit tests (EX-1 through EX-6) in `tests/js/app.test.mjs` covering all new pure helpers; no Python tests needed.

| Test ID | Function under test | What it verifies |
|---------|--------------------|--------------------|
| EX-1 | `buildExportJson` | Returns valid JSON; contains `messages`, `model`, `exported`, `messageCount` fields |
| EX-2 | `buildExportJson` | Message array in output matches input `conversationHistory` exactly |
| EX-3 | `buildExportMarkdown` | Output starts with `# Conversation Export`; contains each message `content` |
| EX-4 | `parseImportJson` | Valid JSON input → returns `{ messages, model }` with correct values |
| EX-5 | `parseImportJson` | Invalid JSON string → returns `{ error: '...' }` (no throw) |
| EX-6 | `parseImportJson` | JSON missing `messages` array → returns `{ error: '...' }` |
| EX-7 | `parseImportJson` | `messages` array contains item with invalid `role` → returns `{ error: '...' }` |
| EX-8 | `parseImportJson` | Empty `messages` array → returns `{ error: '...' }` |

**Coverage targets (must not regress):**
- `server.py` line ≥ 90%, branch ≥ 80%
- JS branch ≥ 70%
- Security scan clean (bandit Medium 0, pip-audit 0 CVEs)

[Implementation Order]
Steps to implement the feature in the correct sequence to minimize conflicts.

1. **Write the spec** — create `docs/specs/export-import-conversations.md` with full RAIL spec (goal, user story, acceptance criteria, affected files, technical approach, test plan, docs to update, risks)
2. **Write failing tests first (TDD Red)** — add EX-1 through EX-8 stubs to `tests/js/app.test.mjs`; confirm they fail with `node --test`
3. **Implement pure helpers** — add `buildExportJson`, `buildExportMarkdown`, `parseImportJson`, `triggerDownload` to `app.js`; add all four to `module.exports`
4. **Run tests (TDD Green)** — run `node --test tests/js/app.test.mjs`; all 8 new tests must pass
5. **Add HTML controls** — add the Export / Import collapsible section to `index.html` with `#exportJsonBtn`, `#exportMdBtn`, `#importFileInput`; bump `styles.css?v=N` reference
6. **Add CSS** — add minimal styles for the button group and file-input label button to `styles.css`; bump version comment at top
7. **Wire UI** — add `exportConversationJSON`, `exportConversationMarkdown`, `handleImportFile` to `app.js`; attach event listeners in `DOMContentLoaded`
8. **Run full test suite** — `./run-tests.sh --coverage`; confirm all gates pass
9. **Security scan** — `./scripts/security-scan.sh`; must be clean
10. **Update docs** — `CHANGELOG.md` new entry; `docs/USER_GUIDE.md` §8; `backlog.md` item #10 checked off; spec §6 docs checklist completed
11. **Write sprint + memory artifacts** — create `Cline/scrum/sprints/sprint-05.md`; update `Cline/scrum/sprint-index.md`; write `Cline/memories/YYYY-MM-DD-HHMMSS-sprint05-export-import.md`
