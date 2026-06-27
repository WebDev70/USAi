# Spec: Reasoning / Thinking Display (#11)

**Status:** Ready
**Type:** feature
**Created:** 2026-06-25
**Author:** Cline / user
**Prior context:** Parking-lot item since project start; unblocked by Sprint 04 (#9 — streaming + tool calling). No prior implementation context found.

---

## 1. Goal & scope

### Goal
Reasoning-capable models (OpenAI o-series, GPT-5, Claude with extended thinking, etc.)
emit a separate "thinking" / reasoning stream alongside the final answer, delivered as
`delta.reasoning` or `delta.reasoning_content` in SSE chunks, and as `message.reasoning`
/ `message.reasoning_content` in non-streaming responses. Today USAi drops this data.
This feature captures it and presents it in a collapsible **💭 Thinking** block
above the assistant answer, collapsed by default, so users can inspect the model's
chain-of-thought without it cluttering the main response.

### Out of scope (v1 — defer to backlog #11a–#11e)
- **#11a** — Persist reasoning text to session history / localStorage (survives reload/restore).
- **#11b** — Live token-by-token streaming animation of the thinking block.
- **#11c** — Settings toggle to enable/disable the thinking display.
- **#11d** — Copy / Remember buttons specific to the reasoning block.
- **#11e** — Markdown rendering inside the thinking block (plain/pre-wrapped text for v1).

---

## 2. User story & acceptance criteria

As a USAi user I want to see a reasoning model's chain-of-thought in a
collapsible block so that I can inspect its thinking without it cluttering
the main answer.

- [ ] **AC-1:** During streaming, reasoning fragments (`delta.reasoning` OR
  `delta.reasoning_content`) are accumulated separately from `delta.content`
  and do **not** appear in the main answer bubble.
- [ ] **AC-2:** When reasoning content is non-empty at the end of a stream (or
  in a non-streaming response), a **collapsible "💭 Thinking" block** renders
  within the assistant message, **collapsed by default**, expandable on click.
  The block uses semantic `<details>`/`<summary>` markup.
- [ ] **AC-3:** When a model returns **no** reasoning content the thinking block
  is not rendered — zero visual change for normal models.
- [ ] **AC-4:** The non-streaming path (`callChatApi`) also surfaces
  `message.reasoning` / `message.reasoning_content` when present.
- [ ] **AC-5:** Reasoning text is HTML-escaped before insertion (XSS-safe).

---

## 3. Affected files

| File | Change |
|------|--------|
| `app.js` | New `renderReasoningBlock(bubble, text)` helper; `streamChatApi` accumulates reasoning delta; `callChatApi` reads reasoning from message; wire both into the send flow; export `renderReasoningBlock` for tests |
| `index.html` | Bump `styles.css?v=26 → v27` |
| `styles.css` | Add `.reasoning-block` / `<details>` / `<summary>` styles |
| `tests/js/app.test.mjs` | 5 new unit tests (RD-1 … RD-5) — TDD Red-first |
| `docs/specs/reasoning-thinking-display.md` | This file |
| `docs/USER_GUIDE.md` | New "Reasoning / Thinking display" section |
| `CHANGELOG.md` | Add entry |
| `backlog.md` | Mark #11 done; add deferred items #11a–#11e |

No `server.py` change required — the proxy already relays SSE verbatim.

---

## 4. Technical approach

### Role 2 — Architect sign-off

#### `renderReasoningBlock(bubble, text)`
- Pure DOM helper: creates (or updates) a `<details class="reasoning-block">` /
  `<summary>💭 Thinking</summary>` / `<pre class="reasoning-text">` structure.
- Inserted as the **first child** of `bubble` (before the `.message-text` element)
  so the thinking block appears above the final answer.
- `text` is HTML-escaped via the existing `escapeHtml()` before insertion.
- Idempotent: if a `.reasoning-block` already exists in the bubble, updates its
  `<pre>` text rather than creating a second one (supports future streaming).
- Exported in `module.exports` so unit tests can call it without a real DOM.

#### `streamChatApi`
- Add `let reasoningText = ''` alongside `assistantText`.
- In the inner parse loop, extract `delta.reasoning || delta.reasoning_content || ''`
  and accumulate it into `reasoningText`.
- Return `{ assistantText, reasoningText, usage }` (backward-compatible; callers that
  ignore `reasoningText` are unaffected).

#### `callChatApi`
- After parsing `message`, read `message.reasoning || message.reasoning_content || null`.
- Return `{ assistantText, reasoningText, message, usage }`.

#### Callers (the two send paths in `sendMessage`)
- After the stream/non-stream call, if `reasoningText` is non-empty, call
  `renderReasoningBlock(bubble, reasoningText)`.
- No change needed to `runWithTools` — it calls `streamChatApi` internally;
  `reasoningText` flows back through `streamFn` result.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A — no new endpoint)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A)
- [x] `/config` exposes no secrets (or N/A)
- [x] Path traversal rejected on filesystem access (or N/A — frontend-only)
- [x] CSS bump applied — `?v=26 → v27`

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| RD-1 | `renderReasoningBlock` with non-empty text creates `<details class="reasoning-block">` containing a `<summary>` and `<pre>` with escaped text | `tests/js/app.test.mjs` | unit |
| RD-2 | `renderReasoningBlock` with empty string (or null) does **not** insert a `.reasoning-block` element | `tests/js/app.test.mjs` | unit |
| RD-3 | `renderReasoningBlock` is idempotent — calling it twice on the same bubble updates the existing block rather than adding a second | `tests/js/app.test.mjs` | unit |
| RD-4 | `renderReasoningBlock` HTML-escapes `<`, `>`, `&` in the reasoning text | `tests/js/app.test.mjs` | unit |
| RD-5 | `renderReasoningBlock` inserts the `.reasoning-block` as the **first child** of the bubble | `tests/js/app.test.mjs` | unit |

**TDD order:** write all 5 tests first (Red) → implement `renderReasoningBlock` (Green) → refactor.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — add entry under `[Unreleased]`
- [x] `docs/USER_GUIDE.md` — "Reasoning / Thinking display" section
- [x] `backlog.md` — mark #11 done; add #11a–#11e as deferred items
- [ ] `README.md` — no setup/config change needed
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention change

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Provider uses `reasoning_content` vs `reasoning` | Accept both field names; use `delta.reasoning \|\| delta.reasoning_content` |
| Reasoning arrives in multiple delta chunks | Accumulate into `reasoningText` across the whole stream; render once at the end |
| Model returns empty string `""` as reasoning | Treat `""` as absent — no block rendered (AC-3) |
| `<details>` CSS not styled consistently across browsers | CSS explicitly styles `summary` cursor + marker; fallback graceful |
| `renderReasoningBlock` called in Node test env without real DOM | Use the existing `module.exports` guard pattern; tests inject a minimal DOM stub |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-5 all verified
- [ ] Memory note written to `Cline/memories/`
