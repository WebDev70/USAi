# Spec: Prompt Templates / Saved System Prompts

**Status:** Ready
**Type:** feature
**Created:** 2026-06-26
**Author:** Cline / Ron
**Prior context:** None found in Obsidian vault. Item #12 has been in the backlog parking lot since project start, listed as "A small library of reusable system prompts." No earlier design notes.

---

## 1. Goal & scope

### Goal
Users frequently retype the same system prompt for recurring workflows (e.g. "You are a code reviewer", "You are a Python expert", "Answer concisely in bullet points"). This feature adds a small built-in library of named system-prompt templates plus the ability for users to save their own, so any template can be applied to the `#systemPrompt` field with a single click. Templates are stored in `localStorage` alongside existing settings — no backend change required.

### Out of scope
- Per-conversation template assignment (templates apply only to the `systemPrompt` field; they don't automatically wire into new chats — the user still clicks "New Chat" after selecting one).
- Server-side / shared template storage.
- Template categories, tags, or search.
- Importing/exporting templates (separate concern).

---

## 2. User story & acceptance criteria

As a USAi user, I want to pick a pre-defined or custom system prompt from a dropdown/list so that I don't have to retype common prompts every time I start a new task.

- [ ] **AC-1:** A "Templates" button or dropdown appears adjacent to the `#systemPrompt` input. Clicking it opens a list showing 5+ built-in templates plus any user-saved templates.
- [ ] **AC-2:** Selecting a template from the list copies its content into `#systemPrompt` and calls `saveSettings()` (persists to localStorage).
- [ ] **AC-3:** A "Save current" action saves the current `#systemPrompt` value as a named user template. The user is prompted for a name (via `prompt()` or an inline input). The saved template appears in the list immediately.
- [ ] **AC-4:** User-saved templates can be deleted from the list (each user template has a ✕ delete control). Built-in templates cannot be deleted.
- [ ] **AC-5:** User templates survive page reload (persisted to `localStorage` under a new key `usai.prompt-templates.v1`).
- [ ] **AC-6:** `./run-tests.sh` passes; `./run-tests.sh --coverage` meets gates (server.py ≥ 90%, JS branch ≥ 70%).
- [ ] **AC-7:** `./scripts/security-scan.sh` clean.

---

## 3. Affected files

| File | Change |
|------|--------|
| `app.js` | Add `PROMPT_TEMPLATES_KEY`, built-in template list, `loadPromptTemplates()`, `savePromptTemplates()`, `renderTemplateDropdown()`, `applyTemplate()`, `saveCurrentAsTemplate()`, `deleteUserTemplate()` helpers; wire button/dropdown in `_testInit()` / DOM-ready block |
| `index.html` | Add a templates trigger button next to `#systemPrompt`; add dropdown/list panel (`#promptTemplatePanel`); bump `styles.css?v=24` → `v=25` |
| `styles.css` | Add styles for the template panel (dropdown-style overlay), template list items, delete buttons; uses existing CSS variable tokens |
| `tests/js/app.test.mjs` | New PT-* tests (≥6) covering: built-in list load, applyTemplate sets input value, saveCurrentAsTemplate round-trips, deleteUserTemplate removes entry, persistence across simulated reload, empty/whitespace guard |
| `tests/python/` | None — no backend change |
| `docs/specs/prompt-templates.md` | This file |
| `docs/USER_GUIDE.md` | Add §9 Prompt Templates |
| `CHANGELOG.md` | Add entry under [Unreleased] |
| `backlog.md` | Mark #12 done |

---

## 4. Technical approach

### Role 2 — Architect sign-off

**Built-in templates** — hardcoded array in `app.js`:
```js
const BUILTIN_TEMPLATES = [
  { id: 'code-reviewer',    name: 'Code reviewer',         text: 'You are an expert code reviewer. Review for correctness, clarity, and security.' },
  { id: 'python-expert',    name: 'Python expert',         text: 'You are a Python expert. Provide idiomatic, well-documented Python.' },
  { id: 'concise-bullets',  name: 'Concise bullet points', text: 'Answer concisely using bullet points. Skip preamble.' },
  { id: 'socratic-tutor',   name: 'Socratic tutor',        text: 'Guide me with questions rather than giving direct answers.' },
  { id: 'editor',           name: 'Editor / proofreader',  text: 'Edit my text for grammar, clarity, and conciseness. Preserve my voice.' },
  { id: 'no-system',        name: '(Clear system prompt)', text: '' },
];
```

**User templates** — persisted to `localStorage` under `usai.prompt-templates.v1` as `Array<{id, name, text}>`. IDs are `user-<timestamp>`.

**UI pattern** — a small `▾ Templates` button immediately below (or beside) the `#systemPrompt` label. Clicking it toggles a positioned dropdown panel `#promptTemplatePanel` (CSS `position: absolute` anchored to the button). The panel lists built-ins (non-deletable) then user templates (each has a ✕). A "Save current as template…" button at the bottom opens an inline name-input (no `prompt()` — use a hidden `<input>` that appears inline in the panel for accessibility). Clicking outside the panel closes it (`blur`/`focusout` or a document click listener).

**Integration with existing settings** — `applyTemplate(text)` sets `#systemPrompt.value = text` then calls `saveSettings()` (same as the existing `'input'` event listener does, but imperatively).

**No new runtime dependency.** Pure `app.js` + `localStorage`. No backend call.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern — N/A (no server change)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern — N/A
- [x] `/config` exposes no secrets — N/A
- [x] Path traversal rejected on filesystem access — N/A
- [x] CSS bump applied — `styles.css?v=24` → `v=25` in `index.html`

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| PT-1 | `loadPromptTemplates()` returns BUILTIN_TEMPLATES when localStorage is empty | `tests/js/app.test.mjs` | unit |
| PT-2 | `applyTemplate(text)` sets `#systemPrompt.value` to the given text | `tests/js/app.test.mjs` | unit |
| PT-3 | `saveCurrentAsTemplate(name, text)` appends to user templates and persists to localStorage | `tests/js/app.test.mjs` | unit |
| PT-4 | `loadPromptTemplates()` after save returns built-ins + saved user template | `tests/js/app.test.mjs` | unit |
| PT-5 | `deleteUserTemplate(id)` removes correct entry; built-ins unchanged | `tests/js/app.test.mjs` | unit |
| PT-6 | `saveCurrentAsTemplate` with empty/whitespace name is rejected (returns false / no save) | `tests/js/app.test.mjs` | unit |
| PT-7 | `saveCurrentAsTemplate` with empty/whitespace text is rejected | `tests/js/app.test.mjs` | unit |

**TDD order:** write PT-1…PT-7 first (Red) → implement helpers (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — add §9 Prompt Templates (how to select, save, delete)
- [ ] `README.md` — no setup/config/env change; no update needed
- [ ] `backlog.md` — mark #12 done
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention change; no update needed

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| User saves a prompt containing `<script>` or malicious HTML | `applyTemplate()` sets `.value` (plain text), never `.innerHTML` — safe by construction; `systemPrompt` is sent as a JSON string to the server, never rendered as HTML |
| localStorage quota exceeded (many large templates) | Catch `QuotaExceededError` in `savePromptTemplates()`; log a warning via `logger.warn`, leave existing data intact |
| Template panel stays open and obscures other UI | Document-level `pointerdown` listener closes the panel when clicking outside it |
| `(Clear system prompt)` built-in applies empty string | `applyTemplate('')` sets value to `''` and calls `saveSettings()` — tested in PT-2 |
| Built-in template IDs clash with user IDs | Built-in IDs are plain slugs; user IDs are `user-<timestamp>` — no overlap possible |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-7 all verified
- [ ] Memory note written to `Cline/memories/`
