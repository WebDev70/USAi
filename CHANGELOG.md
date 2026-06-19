## [Unreleased]

### Fixed — CI JS test discovery

- **GitHub Actions "JS unit tests" job failed** with `Could not find
  'tests/js/**/*.test.mjs'`. The `**` glob is a zsh feature; CI's non-interactive
  bash has globstar off, so the literal pattern reached Node. Passing the directory
  (`node --test tests/js`) needs Node ≥ 21, but CI runs Node 20 — so the portable
  fix enumerates the files with `find`: `node --test $(find tests/js -name
  '*.test.mjs')`. Applied consistently in `.github/workflows/tests.yml`,
  `run-tests.sh`, `README.md`, `AGENTS.md`, and
  `docs/testing-and-agents-strategy.md`.

### Changed — Accessibility & modern-UI design pass (UI/UX agent, USWDS-guided)

First use of the new Front-End Design (UI/UX) agent (backlog #21), informed by
**USWDS** accessibility guidance via Context7. All token-driven; no new deps.
`styles.css` cache-bust bumped to `?v=20`.

- **Global keyboard focus ring** (`styles.css`): added `--focus-ring` /
  `--focus-ring-offset` tokens (theme-aware via `color-mix()`) and a single
  `:focus-visible` rule covering links, buttons, inputs, selects, textareas,
  `summary`, and `[tabindex]`. Fixes the prior `outline:none` regressions so
  keyboard/AT users always get a visible, consistent focus indicator (USWDS:
  controls must have a visible keyboard focus state). Pointer users are unaffected.
- **Reduced-motion support** (`styles.css`): added
  `@media (prefers-reduced-motion: reduce)` to neutralize non-essential animation,
  transitions, and smooth scrolling.
- **Accessible names on icon-only controls** (`index.html`): send (`↑`), attach
  (`📎`), and sidebar-toggle (`☰`) now wrap the glyph in `aria-hidden="true"` and
  keep an `aria-label`; the sidebar toggle reports `aria-expanded`, kept in sync in
  `app.js`. Added an `.sr-only` utility (USWDS `usa-sr-only`) + a visually hidden
  label for the message textarea.
- **Semantic landmarks / live regions** (`index.html`): sidebar `aria-label`, a
  screen-reader "Chat history" heading + `role="list"`, and the conversation
  container marked `role="log"` `aria-live="polite"`.
- **Contrast fix** (`styles.css`): bumped light-theme `--color-text-secondary`
  `#6b6b76` → `#595963` so secondary text clears WCAG AA on both `#f4f4f4`
  (4.79 → 6.29:1) and `#ffffff` (5.26 → 6.92:1). Replaced two hardcoded `#b4b4b7`
  inline colors in `index.html` with `var(--color-text-secondary)` (now AA in dark
  too).

### Added — Front-End Design (UI/UX) agent

- **New auto-attached rule `.continue/rules/ui-ux-design.md`** (scoped via `globs`
  to `index.html`/`styles.css`) defining a Front-End Design SME role: keep the UI
  modern, **accessible** (WCAG AA contrast in both themes, `:focus-visible`,
  semantic landmarks + ARIA on icon-only controls, `prefers-reduced-motion`,
  adequate hit targets), responsive, and **token-driven** using modern *vanilla*
  CSS (`clamp()` type, `color-mix()`, logical properties, container queries /
  `:has()`, View Transitions) — with **no new frontend deps/framework/build step**.
  Consults Context7 for guidance, preferring **USWDS** (`/uswds/uswds-site`), and
  cites what it applied.
- **New QA check `.continue/checks/ui-ux-review.md`** (`/check`, frontend-only) that
  flags new frontend dependencies, a missing `styles.css?v=N` bump, hardcoded design
  values that bypass tokens, accessibility regressions (missing focus/aria, broken
  semantics/contrast, motion ignoring reduced-motion), and likely responsive breaks.
- **Documented** the role as a quality axis in
  `docs/testing-and-agents-strategy.md` and wired it into `AGENTS.md`. Tracked as
  backlog **#20** (done); an actual a11y/modern-UI design pass is backlog **#21**.

### Backlog

- **Added model-routing/tiering items #18 and #19** to `backlog.md`: (#18) a
  *guided* set of Continue dev-workflow model tiers (Opus/Sonnet/Haiku mapped to
  the five pipeline roles, switched manually — Continue has no auto per-agent
  routing) delivered as a sample `config.yaml`; and (#19) a real *automatic*
  per-message model router in the USAi web app (`routeModel` by complexity, with an
  Auto + manual-override setting). Both are blocked on confirming the gateway's
  exact model IDs per tier.

### Added — Testing & agent pipeline strategy (planning)

- **New `docs/testing-and-agents-strategy.md`** documenting (1) a zero-new-dependency
  unit-testing stack (`unittest` for `server.py`, `node --test` for `app.js` pure
  functions, with `node --check` / `py_compile` syntax gates) and (2) a five-role
  Continue-native agent pipeline: **Code Planner → Development SME → Full Test
  Suite → QA Review → Continuous Improvement** (closed loop; learnings recorded to
  Obsidian). Roles map to rules (`.continue/rules/`), checks (`.continue/checks/`
  run via `/check`), and optional agents (`.continue/agents/`), wired via
  `AGENTS.md`. Tracked as backlog **#17** (status `[~]`).
- **Added four agent-role rules** (always-on, `.continue/rules/`): `code-planner`
  (plan before non-trivial changes), `development-sme` (implement idiomatically),
  `testing-standards` (zero-dep test stack + what/how to test), and
  `continuous-improvement` (reflect, propose automation, record a learning note).
- **Added a runnable test scaffold (no new deps).**
  - `tests/js/app.test.mjs` — 14 `node --test` cases for pure helpers
    (`escapeHtml`, `renderMarkdown` incl. XSS-safety, `extractJson`, `formatUsage`,
    `getExcludedParams`, `buildResponseFormat`). To enable importing, `app.js` now
    ends with a Node-only `module.exports` guard (no-op in the browser); the test
    stubs the few DOM globals `app.js` touches at load.
  - `tests/python/test_server.py` — 8 `unittest` cases for `get_memory_dir`
    (incl. the **path-traversal guard**) and `_slugify`.
  - `run-tests.sh` — one command that runs the syntax gates + both suites.
  - All 22 tests pass.
- **Added four QA-review checks** (`.continue/checks/`, run via `/check`):
  `test-coverage` (new code has tests, no new test framework), `security-review`
  (no secret leaks, `/config` stays redacted, path-traversal guards, input limits,
  XSS-safe rendering), `code-quality-review` (no new runtime deps, tool gating,
  endpoint pattern, CSS `?v` bump), and `docs-in-sync` (the right docs updated).
- **Wired the pipeline into `AGENTS.md`** (new "Agent pipeline" section + "run
  `/check` after changes") and updated the **README**/**CONTINUE.md** "Running
  tests" sections (replacing the old "no automated test suite" note).
- **Added GitHub Actions CI** (`.github/workflows/tests.yml`): on every push / PR
  it runs the JS suite (`node --test`) and the Python suite (`unittest`) on Python
  3.9 + 3.11, plus the syntax gates — the same checks as `./run-tests.sh`. Only
  install is `python-dotenv` (matches `requirements.txt`); no other deps.

### Changed — Sidebar layout

- **Moved the settings sections (Prompt & Parameters, MCP & Plugins, File Uploads)
  to the bottom of the sidebar**, just above the Light/Dark Mode button, so the
  chat history list can grow and show more sessions. `index.html`: relocated the
  `.sidebar-settings` block below the sessions list. `styles.css`: `.sessions-list`
  now `flex: 1 1 auto` with no `max-height` (was capped at `35vh`), and
  `.sidebar-settings` gets `margin-top: auto` to pin it (and the footer) to the
  bottom. Bumped `styles.css?v=19`.

### Tooling / Docs

- **Added a "keep docs in sync" rule.** New always-on Continue rule
  `.continue/rules/keep-docs-in-sync.md` requires docs to be updated in the same
  turn as the change that affects them (maps change types → CHANGELOG / USER_GUIDE
  / README / backlog / CONTINUE.md / AGENTS.md). Referenced from CONTINUE.md's
  Development Workflow.
- **Added `AGENTS.md`** — concise agent operating rules (Obsidian long-term-memory
  directive with the two-writer split, security rules, coding conventions, run/
  validate steps). `CONTINUE.md`'s memory section now points to it to avoid
  duplication.
- **Two memory destinations by writer:** the USAi app writes to `USAi/memories/`
  (`OBSIDIAN_MEMORY_SUBDIR=USAi`); the Continue extension writes its dev-session
  notes to `Continue Extension/memories/`. Documented in `README.md`,
  `USER_GUIDE.md`, and `AGENTS.md`.
- **`README.md`:** added an Obsidian-memory `.env` section + two-writer table;
  modernized run/stop instructions to use the venv; fixed stale Usage steps.
- **`.continue/mcpServers/new-mcp-server.yaml`:** split into two valid servers
  (Context7 streamable-http + Obsidian stdio); moved the Context7 key to a
  `${CONTEXT7_API_KEY}` env var instead of hardcoding it.
- **`.gitignore`:** added `.venv/`, `.continue/mcpServers/`, runtime state
  (`chat_history.json`, `.chat_sessions/`, `.chunk_cache/`), and `.DS_Store`.
- **Moved** `Claude.md` → `docs/generate-continue-md-prompt.md` (it's a one-time
  prompt template, not Continue config).

### Added — Obsidian long-term memory ("second brain")

A new persistent memory layer backed by an Obsidian vault, so the assistant can
recall facts/preferences/decisions across conversations. Memories are stored as
tagged Markdown notes; all reads/writes are confined to a single subfolder.

- **`server.py`**: New `.env` settings `OBSIDIAN_VAULT_PATH` and
  `OBSIDIAN_MEMORY_SUBDIR` (default `USAi`). `get_memory_dir()` resolves
  `<vault>/<subdir>/memories` with path-traversal guards. New endpoints
  `GET /memory/search` (keyword search, title/tags weighted), `GET /memory/list`,
  `GET /memory/read`, and `POST /memory/save` (create-only, YAML frontmatter with
  title/created/tags/source, auto-tagged `usai-memory`). `/config` now reports
  `has_obsidian`.
- **`app.js`**: Three usage paths —
  1. **Tools** `search_memory` / `save_memory` in `TOOL_REGISTRY`, gated behind
     the **Obsidian Memory** toggle (requires Tool calling on + vault configured).
  2. **Auto-recall** — opt-in **Auto-recall memories** toggle; `prepareContextMessages`
     searches the vault and injects top-N notes before each message, adding a
     `Memory: N note(s)` segment to the context note.
  3. **Manual** — `addRememberButton`/`saveMemory` add a hover **💾 Remember**
     button to every message (tagged `manual`), shown only when a vault exists.
  - New `memoryEnabled` / `memoryAutoRecall` state, persisted in `usai.settings.v1`
    and restored on load; `applyConfig` disables/dims the toggles when no vault.
- **`index.html`/`styles.css`**: **Obsidian Memory** + **Auto-recall memories**
  toggles and a hint in MCP & Plugins; `.remember-msg-btn` styling.

### Changed — UI polish & model handling

- **Composer toolbar**: Model and Reasoning-effort selectors moved into the
  composer row next to the 📎 attach button (mirror the canonical sidebar selects).
- **Sidebar slimmed (Option B)**: API Configuration & Model sections hidden via
  `.settings-hidden` (elements kept in the DOM); a settings modal to fully replace
  them is tracked in `backlog.md` (Option C).
- **Per-model parameter exclusions**: `MODEL_PARAM_EXCLUSIONS` /
  `getExcludedParams` omit unsupported params (e.g. `temperature` for Claude Opus
  and OpenAI o-series/GPT-5) so requests don't 400; `updateParamFieldStates`
  greys out the affected fields. Temperature/Max-tokens default to blank.
- **Context7 tool gating fix**: `getEnabledTools` now also requires the Context7
  toggle to be checked, so the model can't call `fetch_context7` when it's off.
  The misleading "No external context" note is suppressed when tools were used.

### Added — OpenAI Chat Completions capabilities

These features expand the app beyond the original minimal request/response flow.
They were added incrementally, each building on the previous.

#### 1. Streaming responses (Server-Sent Events)
- **`app.js`**: New `streamChatApi(payload, onDelta)` reads the response body as a
  `ReadableStream`, buffers across chunk boundaries, parses SSE `data:` frames,
  ignores `[DONE]`, and accumulates `choices[0].delta.content`. Tokens render
  live into the assistant bubble with a blinking cursor.
- `appendMessage` now returns `{ group, bubble, noteEl }`; added `renderBubbleText`
  helper. Refactored `updateChatUI` into `persistExchange` + `normalizeAssistantText`
  so streaming and non-streaming paths share history logic.
- `sendMessage` renders the user bubble immediately, streams into an empty
  assistant bubble, and disables the send button while in flight.
- **`server.py`**: Switched to `ThreadingHTTPServer` so log/history POSTs during a
  stream don't block. `_proxy_api` detects `"stream": true` and relays the
  upstream body in 1 KB chunks with `flush()`, setting `text/event-stream`,
  `Cache-Control: no-cache`, and `X-Accel-Buffering: no`; handles client
  disconnects gracefully.
- **`index.html`**: Added "Stream responses" toggle (checked by default).
- **`styles.css`**: Added `.message-bubble.streaming` blinking-cursor animation.

#### 2. Token usage display
- **`app.js`**: `callChatApi` now returns `usage`; `streamChatApi` sends
  `stream_options: { include_usage: true }` and captures the final usage chunk.
- New `formatUsage(usage)` (tolerates `prompt_tokens`/`input_tokens` naming) and
  `setMessageNote(group, noteEl, parts)` helpers. Token counts appear in the
  per-message note (e.g. `84 in · 51 out · 135 total tokens`) and in the debug
  panel. Usage survives history/session reloads.

#### 3. Vision / image input
- **`app.js`**: New `pendingImages` array, `readFileAsDataURL`, and
  `showPendingImages` (removable thumbnails above the input). `handleFileUpload`
  splits images (base64-encoded for vision) from text files (chunked for RAG).
  `sendMessage` builds the multimodal `content` array
  (`{type:'text'}` + `{type:'image_url', image_url:{url:dataUrl}}`).
  `appendMessage`/`renderBubbleText` render an in-bubble image gallery without
  clobbering streamed text. Images persist and re-render on reload.
- **`index.html`**: Upload button relabeled "Upload Files / Images" with an
  `accept` filter; added `#pendingImages` container.
- **`styles.css`**: Added `.message-images`/`.message-image` and
  `.pending-image*` styles; updated streaming-cursor selector to target
  `.message-text`.

#### 4. Tool / function calling
- **`app.js`**: New `TOOL_REGISTRY` with three built-in tools —
  `fetch_context7` (auto-fetches Context7 docs; only advertised when configured),
  `search_uploaded_files` (top-k keyword search over uploads), and `calculator`
  (whitelisted arithmetic only). Added `getEnabledTools`, `executeToolCall`, and
  `runWithTools` which performs up to `MAX_TOOL_ROUNDS` (5) rounds of
  model → `tool_calls` → execute → feed results back. `callChatApi` now also
  returns the full `message` object so `tool_calls` can be inspected. A live
  "🔧 Using tools" indicator (`appendToolActivity`) shows active tools, and the
  message note gains a `Tools: …` segment. `runWithTools` includes guards for an
  empty tool list and a missing `message`, plus per-round diagnostic logging.
- **`index.html`**: Added "Tool calling" toggle.
- **`styles.css`**: Added `.tool-activity`/`.tool-chip` styles.
- **Interaction note:** enabling Tool calling auto-disables the Stream toggle,
  since tool calling needs the complete response to read `tool_calls`.

#### 5. Structured outputs + reasoning effort
- **`app.js`**: `getChatInputs` now reads `reasoningEffort`, `jsonMode`, and
  `jsonSchema`. New `buildResponseFormat(inputs)` produces a `response_format`
  of `json_object` (no schema) or `json_schema` (accepts either a full
  `{ name, schema, strict }` wrapper or a bare JSON Schema object). `sendMessage`
  attaches `reasoning_effort` (low/medium/high) and `response_format` to the
  payload; in JSON mode the response runs non-streamed, is pretty-printed when it
  parses, and the note shows `JSON ✓` / `JSON ✕`. Added live schema validation
  and toggle listeners.
- **`index.html`**: Added a "Reasoning effort" dropdown, a "Structured output
  (JSON)" toggle, a JSON Schema textarea (shown when enabled), and a validation
  status line.
- **`styles.css`**: Added `#jsonSchema` textarea styling.
- **Interaction note:** enabling Structured output auto-disables the Stream
  toggle so the full JSON can be validated/pretty-printed.
- **Gateway fallback:** because many OpenAI-compatible gateways ignore
  `response_format`, `sendMessage` also injects a system instruction telling the
  model to output raw JSON (embedding the schema), and `extractJson` robustly
  recovers JSON from fenced/` ```json `-wrapped or prose-surrounded replies.

### Security

- **Fixed: `/config` no longer exposes secrets.** `_get_config` now returns only
  non-secret fields (`base_url`, `default_model`, `default_system_prompt`,
  `context7_base_url`/`path`/`method`) plus `has_api_key` and `has_context7`
  booleans. `app.js` removed `api_key`/`context7_api_key` from `appConfig`, sends
  the `Authorization` header only when the user explicitly types a key
  (otherwise the proxy injects the server-side key), and shows a placeholder
  indicating a server key is in use. The API key is never sent to the browser.

### UI / rendering

- **Markdown rendering for assistant messages.** Added a dependency-free,
  XSS-safe `renderMarkdown(src)` in `app.js`: it HTML-escapes all text first,
  then converts a whitelist of constructs (fenced/inline code, headings, bold,
  italic, links restricted to http(s)/mailto, ordered/unordered lists,
  blockquotes, horizontal rules, paragraphs). Assistant messages now render as
  Markdown (`appendMessage`/`renderBubbleText` gained an `asMarkdown` path);
  user messages remain plain escaped text. During streaming, partial tokens
  render as plain text and the final message is re-rendered as Markdown.
  Structured-output JSON is wrapped in a ```` ```json ```` block so it shows as
  a formatted code block. **`styles.css`**: added `.markdown-body` and `.md-*`
  styles. **`index.html`**: bumped stylesheet to `?v=7`.

- **Stop / cancel button.** Added a shared `activeAbortController` in `app.js`,
  passed as the `signal` to both `callChatApi` and `streamChatApi` fetches. While
  a request is in flight the send button turns into a red ■ Stop button
  (`setSendButtonState`); clicking it calls `cancelActiveRequest()` to abort.
  `AbortError` is handled gracefully — non-stream/tool paths report "Request
  cancelled," and the streaming path **keeps the partial response** generated so
  far (persisting it with a "cancelled" note) or removes the empty bubble if
  nothing arrived. `runWithTools` propagates an `aborted` flag through all call
  sites. Enter/Ctrl+Enter shortcuts are ignored while busy. **`styles.css`**:
  added `.send-button.is-stop` styling. **`index.html`**: bumped to `?v=8`.

- **Persisted UI settings.** Added `saveSettings()`/`restoreSettings()` in
  `app.js` backed by `localStorage` key `usai.settings.v1`. Persists model
  (and custom model id), system prompt, temperature, max tokens, reasoning
  effort, the stream/tools/JSON/Context7 toggles, the JSON schema, chunk size,
  top-chunks, and base URL. Settings are restored after `loadConfig()` and again
  after `loadModels()` repopulates the model dropdown, and the relevant state
  variables (`streamEnabled`, `toolsEnabled`, `context7Enabled`, `chunkLineSize`,
  `topChunksPerQuery`) plus dependent UI (JSON schema box visibility, stream
  toggle disabling, Context7 fetch button) are re-synced. `applyDefaultModel()`
  defers to a saved model preference when present. Change/input listeners on the
  controls call `saveSettings()`.

- **Copy buttons.** Each message bubble gets a hover-revealed "Copy" button
  (`addCopyButton`) that copies the original un-rendered text (stashed on
  `bubble.dataset.rawText`), and every rendered code block gets its own "Copy"
  button (`enhanceCodeBlocks`). A shared `copyToClipboard` helper uses the async
  Clipboard API with a legacy `execCommand('copy')` fallback for non-secure
  contexts, and `flashCopied` shows a brief "Copied!" confirmation. Buttons are
  attached idempotently in `appendMessage`/`renderBubbleText` (skipped during
  streaming for performance, then added on the final render). **`styles.css`**:
  added `.copy-msg-btn`/`.copy-code-btn` styles. **`index.html`**: bumped to
  `?v=9`.

### Previously known issue (now resolved)
- **Known issue: `/config` exposes secrets to the browser.** The server's
  `/config` endpoint returns the full `CONFIG` dict, including `api_key` and
  `context7_api_key`, and `app.js` stores the key client-side. Despite the
  proxy's ability to inject the key server-side, the key is currently reachable
  by any client. Fix: return only non-secret fields from `/config` and rely on
  the proxy's server-side key injection.
  *(Confirmed from QA review item #8 after reviewing `server.py`.)*
```

### README — corrected Security notes

```markdown README.md
## Security notes

- Do not commit your API key or `.env` file to the repository.
- The Python server includes an API proxy that can inject the server-side
  `API_KEY` into upstream requests, so the key **can** be kept off the client.
- **Known issue:** the `/config` endpoint currently returns the full
  configuration (including `API_KEY` and `CONTEXT7_API_KEY`) to the browser, and
  the frontend stores it. Until this is fixed, the key is effectively exposed
  client-side. Limit `/config` to non-secret values and rely on the proxy.
- The server binds to `127.0.0.1` by default (localhost only). Do not bind to
  `0.0.0.0` or deploy publicly without authentication and hardening.
- This setup is intended for local development.