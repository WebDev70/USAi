# Backlog

Planned improvements, ordered roughly by priority. We work through these one at
a time; each item is checked off when implemented and recorded in `CHANGELOG.md`.

## Status legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Done

---

## Security (do first)

- [x] **1. Fix `/config` secret exposure**
  - The `/config` endpoint returns the full `CONFIG` dict, including `api_key`
    and `context7_api_key`, to the browser. Return only non-secret fields and
    rely on the server-side proxy to inject the key.
  - Files: `server.py` (`_get_config`), `app.js` (`appConfig`, key usage).
  - Done: `/config` now returns only non-secret fields plus `has_api_key` /
    `has_context7` booleans; client sends Authorization only when the user types
    a key, otherwise the proxy injects it.

## High value, low effort

- [x] **2. Markdown rendering**
  - Render assistant messages as Markdown (bold, headings, lists, links) with
    code-block syntax highlighting, instead of raw text. Keep HTML escaping safe.
  - Files: `app.js` (`renderBubbleText`/`appendMessage`), `styles.css`,
    possibly `index.html` (library include).
  - Done: added dependency-free, XSS-safe `renderMarkdown` (escapes first, then
    whitelists constructs); assistant messages render as Markdown, user messages
    stay plain; streaming renders plain mid-stream then Markdown on completion.

- [x] **3. Stop / cancel button**
  - Abort an in-flight request with `AbortController`. Toggle the send button to
    a stop button while streaming/awaiting.
  - Files: `app.js` (`sendMessage`, `callChatApi`, `streamChatApi`),
    `index.html`, `styles.css`.
  - Done: shared `activeAbortController` wired into `fetch` signals; send button
    becomes a red ■ Stop button during generation; partial streamed text is kept
    on cancel; tool loop and non-stream paths handle the aborted result.

- [x] **4. Persist UI settings**
  - Save toggle/select states (stream, tools, JSON mode, reasoning effort,
    temperature, max tokens, model) to `localStorage` and restore on load.
  - Files: `app.js`.
  - Done: `saveSettings`/`restoreSettings` persist model (+custom), system
    prompt, temperature, max tokens, reasoning effort, stream/tools/JSON/Context7
    toggles, JSON schema, chunk size, top chunks, and base URL under
    `usai.settings.v1`; restored after `loadConfig`/`loadModels`, with dependent
    UI (schema box, stream-disable, Context7 button) re-synced.

- [x] **5. Copy buttons**
  - Copy a whole message, and copy individual code blocks.
  - Files: `app.js`, `styles.css`.
  - Done: `addCopyButton` adds a hover "Copy" button per bubble (copies the raw
    text stashed in `dataset.rawText`); `enhanceCodeBlocks` adds a "Copy" button
    to each `pre.md-pre` code block. `copyToClipboard` uses the async Clipboard
    API with a legacy `execCommand` fallback for non-secure contexts.

- [ ] **6. Edit & resend / regenerate**
  - Regenerate the last assistant turn; edit a previous user message and re-run.
  - Files: `app.js`, `styles.css`.

## Medium effort

- [ ] **7. Real embeddings for RAG**
  - Replace keyword matching with embeddings + cosine similarity for file search.
  - Files: `app.js`, possibly `server.py` (embeddings proxy/cache).

- [ ] **8. More file types (PDF/DOCX)**
  - Extract text from PDF and DOCX uploads, not just plain text.
  - Files: `app.js` (upload handling), possibly a parser library.

- [ ] **9. Streaming + tool calling together**
  - Accumulate `delta.tool_calls` fragments so tool mode can stream.
  - Files: `app.js` (`streamChatApi`, `runWithTools`).

- [ ] **10. Export / import conversations**
  - Download a session as JSON/Markdown; re-import later.
  - Files: `app.js`, possibly `server.py`.

- [ ] **11. Reasoning / thinking display**
  - Show reasoning-model thinking content in a collapsible block.
  - Files: `app.js`, `styles.css`.

- [ ] **12. Prompt templates / saved system prompts**
  - A small library of reusable system prompts.
  - Files: `app.js`, `index.html`, `styles.css`.

## Larger / later

- [ ] **13. Custom user-defined tools**
  - Let users register their own tool definitions.
- [ ] **14. Model comparison (side-by-side)**
- [ ] **15. Voice input / TTS output**

## Front-end design (UI/UX)

- [x] **20. Front-End Design (UI/UX) agent**
  - A quality-axis role that keeps `index.html`/`styles.css` modern, accessible,
    and user-friendly, using Context7 (preferred reference: **USWDS**
    `/uswds/uswds-site`) — adapting principles to our vanilla-CSS token system, with
    **no new frontend deps/framework/build step**.
  - Done: auto-attached rule `.continue/rules/ui-ux-design.md` (scoped via `globs`
    to `index.html`/`styles.css`) + QA check `.continue/checks/ui-ux-review.md`
    (contrast, `:focus-visible`, semantic/ARIA, reduced-motion, responsive,
    token-driven, cache-bust). Documented in `docs/testing-and-agents-strategy.md`
    and wired into `AGENTS.md`.
  - Files: `.continue/rules/ui-ux-design.md`, `.continue/checks/ui-ux-review.md`,
    `docs/testing-and-agents-strategy.md`, `AGENTS.md`.

- [x] **21. Accessibility + modern-UI design pass (use the #20 agent)**
  - Apply the Front-End Design agent to audit and refresh the actual UI: verify
    WCAG AA contrast in both themes, add `:focus-visible` rings, audit ARIA on
    icon-only controls (sidebar toggle, attach, send), add a reduced-motion guard,
    and tastefully adopt modern vanilla CSS (fluid `clamp()` type, `color-mix()`
    state tints) — all token-driven. Bump `styles.css?v=N`.
  - Done (USWDS-guided via Context7, `?v=20`): global `:focus-visible` ring
    (`--focus-ring` tokens, `color-mix`), `prefers-reduced-motion` guard, `.sr-only`
    utility, accessible names + `aria-hidden` glyphs on send/attach/sidebar-toggle
    (with synced `aria-expanded`), semantic landmarks/live regions (sidebar label,
    `role="log"` conversation, `role="list"` history), AA contrast fix for
    light-theme secondary text (`#6b6b76`→`#595963`), and removed hardcoded
    `#b4b4b7` inline colors. `color-mix()` state tints / fluid `clamp()` type left
    as an optional future polish.

## Model routing / tiering

> Use higher-reasoning models only where they pay off, and cheap/fast models for
> routine work. Two separate efforts — one for the Continue dev workflow, one for
> the USAi web app. **Prereq for both:** confirm the exact model IDs the gateway
> accepts for each tier (candidates from `index.html`: high=`claude_opus_4`,
> medium=`claude_sonnet_4`, low=`claude_3_haiku`).
>
> Reality check (from Continue docs / Context7): Continue assigns models to fixed
> **roles** (`chat`/`edit`/`apply`/`autocomplete`/`embed`/`rerank`), **not** to our
> custom pipeline agents. There is no built-in automatic per-agent model selection,
> so the dev-workflow side (#18) is *guided* (tiers + manual dropdown switch); the
> truly *automatic* router belongs in the app (#19).

- [ ] **18. Continue dev-workflow model tiers (guided)**
  - Define three model tiers in a Continue `config.yaml` so the five-role pipeline
    can use the right level of reasoning: **high** (Opus) for Code Planner on
    complex/architectural work + hard QA review; **medium** (Sonnet) for default
    Development SME / test writing; **low** (Haiku) for trivial edits, docs, and
    quick fixes. Switching is **manual** via the model dropdown (Continue has no
    auto per-agent routing); the role rules should *advise* which tier to pick.
  - Deliver a **sample** `docs/continue-config.sample.yaml` (don't touch the user's
    global `~/.continue/config.yaml`, which may hold secrets) + a short "model
    tiers" section in `docs/testing-and-agents-strategy.md`, and a one-line tier
    hint in each role rule (`code-planner`, `development-sme`,
    `continuous-improvement`).
  - Files: `docs/continue-config.sample.yaml` (new),
    `docs/testing-and-agents-strategy.md`, `.continue/rules/*`.

- [ ] **19. USAi web-app automatic model router**
  - Add a real per-message **model router** to the app: a `routeModel(text, opts)`
    helper classifies each message by complexity (length, presence of code,
    keywords like architect/refactor/debug/prove, tools enabled) and auto-selects a
    tier — **high** (Opus) for heavy reasoning, **medium** (Sonnet) default, **low**
    (Haiku) for trivial. Add a Settings control: **Auto** (router on) plus a manual
    override (Off/High/Medium/Low); persist it in `usai.settings.v1`. Surface the
    chosen tier in the message note (e.g. `Model: Sonnet (auto)`).
  - Keep it dependency-free; gate behind the toggle; make `routeModel` a pure
    function with `node --test` cases (high/medium/low + forced override). Run the
    full Plan → Implement → Test → `/check` pipeline.
  - Files: `app.js` (router + tier map + note), `index.html` (Auto/override
    control), `styles.css`, `tests/js/app.test.mjs`.

## Testing & agent automation

- [~] **17. Unit testing + five-role agent pipeline**
  - Establish a zero-new-dependency test suite and a Continue-native agent
    pipeline that automates planning, implementation, testing, QA review, and
    continuous improvement as we make changes.
  - **Full plan:** [`docs/testing-and-agents-strategy.md`](docs/testing-and-agents-strategy.md).
  - **Test stack (no new deps):** Python `unittest` (stdlib) for `server.py`;
    Node 18+ `node --test` for `app.js` pure functions; `node --check` /
    `python3 -m py_compile` as syntax gates. Tests live in `tests/python` and
    `tests/js`.
  - **Five roles:** Code Planner → Development SME → Full Test Suite → QA Review
    → Continuous Improvement (closed loop; learnings recorded to Obsidian).
  - **Implemented as:** rules (`.continue/rules/`), checks (`.continue/checks/`
    run via `/check`), optional agents/modes (`.continue/agents/`), wired through
    `AGENTS.md`.
  - **Rollout (incremental):**
    - [x] Strategy doc + this backlog item.
    - [x] Rules: `code-planner`, `development-sme`, `testing-standards`,
      `continuous-improvement`.
    - [x] Checks: `test-coverage`, `security-review`, `code-quality-review`,
      `docs-in-sync` (in `.continue/checks/`, run via `/check`).
    - [x] `tests/` scaffold + starter tests (`renderMarkdown`, `extractJson`,
      `formatUsage`, `getExcludedParams`, `buildResponseFormat` in JS;
      `get_memory_dir` traversal guard + `_slugify` in Python) + a Node-only
      `module.exports` guard in `app.js` so helpers are importable. `run-tests.sh`
      runs all 22 tests + syntax gates.
    - [x] `AGENTS.md` workflow wiring (5-role pipeline + run `/check`) +
      README/CONTINUE.md "Running tests" sections.
    - [ ] Optional: dedicated `planner`/`improver` agent modes.
    - [x] CI: GitHub Actions workflow (`.github/workflows/tests.yml`) runs the
      suite on push/PR (JS via `node --test`; Python `unittest` on 3.9 + 3.11).
      A pre-commit git hook remains an optional future add.
  - Files: `docs/testing-and-agents-strategy.md`, `.continue/rules/*`,
    `.continue/checks/*`, `.continue/agents/*`, `tests/*`, `AGENTS.md`,
    `README.md`, `.continue/rules/CONTINUE.md`.

## Memory / "second brain"

- [~] **16. Obsidian long-term memory (second brain)**
  - Use an Obsidian vault as persistent long-term memory so the assistant can
    recall facts/preferences/decisions across conversations.
  - **Phase 1 (done):** direct vault file I/O in `server.py` (no MCP/Node dep).
    - `.env`: `OBSIDIAN_VAULT_PATH`, `OBSIDIAN_MEMORY_SUBDIR` (default `USAi`).
    - Memories stored as tagged, frontmatter'd Markdown in
      `<vault>/<subdir>/memories/`, writes confined to that folder (no traversal).
    - Endpoints: `GET /memory/search`, `GET /memory/list`, `GET /memory/read`,
      `POST /memory/save`. `/config` exposes `has_obsidian`.
    - Tools: `search_memory`, `save_memory` in `TOOL_REGISTRY`, gated behind a
      new **Obsidian Memory** toggle (requires Tool calling on + vault configured).
  - **Phase 2 (backlog):** optional `obsidian-mcp` bridge for rich tag/note
    management (rename-tag, move-note, multi-vault) and reuse with Claude Desktop.
  - **Phase 3:**
    - [x] Auto-recall: opt-in **Auto-recall memories** toggle injects top-N
      relevant memories before each message (in `prepareContextMessages`, like
      the file-RAG path); adds a `Memory: N note(s)` segment to the context note.
    - [x] Manual **💾 Remember** button on every message (hover) for one-click
      saves via `saveMemory` → `POST /memory/save` (tagged `manual`). Shown only
      when a vault is configured; independent of the tool/auto-recall toggles.
    - [ ] Embeddings-based memory search (ties into item #7).
  - Files: `server.py`, `app.js`, `index.html`, `styles.css`.
