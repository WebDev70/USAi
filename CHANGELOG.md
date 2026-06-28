## [Unreleased]

### Fixed (2026-06-27 — Wire all remaining fetch() calls through loggedFetch)

- **`app.js`**: All 23 remaining bare `fetch()` call-sites converted to `loggedFetch()`.
  Every network call in the app now produces a structured log entry (URL, method, HTTP
  status, latency_ms, and full error on throw) visible in the Debug panel and persisted to
  `logs/*.jsonl`. Covered endpoints: `/context7`, `/memory/save` (tool + saveMemory),
  `/mcp/tool`, `/mcp/vaults`, `getLogs`/`getLogFiles`/`readLogFile`/`clear` (Logger
  class), `/chunk-cache` (save/delete/restore/list), `/sessions` (save/list/delete/restore),
  `/chat-history` (save/load), `/new-chat-session`, `/api/v1/models`.
  The two intentional non-converted sites are: the raw `fetch('/logs', …)` inside
  `Logger.log()` itself (to prevent infinite recursion — it's already guarded by the
  `isSelfLog` check in `loggedFetch`) and the `fetch(url, options)` inside `loggedFetch`
  itself (it *is* the wrapper).
- **84 JS tests green. 170 Python tests green. Security scan clean.**



**Root cause:** During Sprint #50 (Log File Viewer), the `_get_log_files()` method was
inserted into `server.py` but the orphaned body of the former `_post_logs()` handler was
left inside it as unreachable code — and the `def _post_logs(self):` header itself was
deleted.  The `do_POST` routes dict still referenced `self._post_logs`, which no longer
existed.  Every chat message the browser sent resulted in:
```
AttributeError: 'EnvConfigHTTPRequestHandler' object has no attribute '_post_logs'
```
The server thread threw, the connection was dropped, and the browser showed
`Network error: Failed to fetch`.  **This was not a real network / API problem** — the
upstream `api.gsa.usai.gov` was never contacted.

- **`server.py`**: Restored `def _post_logs(self):` method (with proper `def` header and
  indentation), containing the 413 guard, JSON parse, `add_log()` call, and 200/400
  responses. Added `GET /logs` → `_get_logs()` which returns `server_logs` as a JSON
  array (it was previously missing from `do_GET` routes, causing a 301 redirect).

### Added (2026-06-27 — Full observability / "catch everything" logging)

- **`server.py` `_proxy_api`**: Now logs every proxy lifecycle event via `add_log`:
  - `→ METHOD /path` with `{model, stream, body_bytes}` on request start.
  - `← STATUS /path` with `{status, bytes, latency_ms}` on success.
  - `← stream N /path` + `stream complete` with `{bytes_relayed, elapsed_ms}` for
    SSE streaming (also logs client-disconnect mid-stream as `warn`).
  - `upstream HTTP NNN` with `{status, latency_ms, upstream_error: first 500 bytes}`
    on `HTTPError` — so the exact upstream message (e.g. 401, 422, model-not-found)
    is visible in the Debug panel immediately, no guessing.
  - `upstream unreachable` with `{error, latency_ms, upstream}` on `URLError`
    (DNS failure, connection refused, timeout).
  - `SSRF guard rejected` / `base_url not configured` as `error` level.
  - API key / Authorization header is **never** logged anywhere.
- **`app.js`**: Global uncaught-error capture — two new event listeners:
  - `window.addEventListener('error', …)` — routes all synchronous JS exceptions
    through `logger.error('uncaught', …)` so they appear in the Debug panel and
    persisted JSONL file.
  - `window.addEventListener('unhandledrejection', …)` — same for unhandled promise
    rejections (the typical source of "Failed to fetch" disappearing silently).
- **`app.js`**: New `loggedFetch(url, options)` helper — drop-in `fetch()` wrapper that:
  - Logs `→ METHOD URL` at `info` level on start.
  - Logs `← STATUS METHOD URL` + `latency_ms` on completion (error-level when !ok).
  - Logs error message + latency on network failure (`throw`) before re-throwing.
  - Never logs the `Authorization` header.
  - Self-referential `/logs` POSTs are excluded to avoid infinite recursion.
  - Wired into `callChatApi`, `streamChatApi`, and `loadConfig` (`/config`).
- **`tests/python/test_server_branches.py`**: 2 new regression tests in `LogsTests`:
  - `test_get_logs_returns_list` — `GET /logs` returns a JSON array containing POSTed entries.
  - `test_all_post_routes_resolve_to_real_methods` — asserts every route referenced in
    `do_POST`'s routes dict maps to a real method on the handler class.  This is the test
    that would have caught the `#50` regression before it shipped.

### Added (2026-06-27 — Log file viewer in Debug panel #50)
- **`server.py`**: New `GET /logs/files` endpoint.
  - `GET /logs/files` → list session log files newest-first with `{enabled, files:[{name,size,modified}]}`.
  - `GET /logs/files?name=<file>` → read entries from one file as `{name, entries:[...]}`.
  - Path-traversal guard: names containing `/`, `\`, or starting with `.` return 400.
  - Returns `{enabled:false, files:[]}` when `PERSIST_LOGS` is off (never 404 on list).
  - Large files capped at 500 entries (newest lines); malformed JSONL lines skipped silently.
  - `_json_response()` now sets `Content-Length` header so HTTP/1.0 responses parse correctly.
  - `/logs/files` registered in `do_GET` routes dict.
- **`app.js`**: `Logger` class gains `getLogFiles()`, `readLogFile(name)`, `renderFilesTab()`.
  Tab-switch listener wires the two `.debug-tab` buttons (Live / Log Files) — toggling
  `#debugLogs` vs `#debugFiles`, hiding filter controls on the files tab, and calling
  `renderFilesTab()` when the files tab is activated.
- **`index.html`**: Debug panel gains `.debug-tabs` strip (Live / Log Files buttons) and
  `#debugFiles` div below `#debugLogs`; `styles.css?v=24` → `?v=25`.
- **`styles.css`**: `.debug-tabs`, `.debug-tab`, `.debug-tab.active`, `.debug-files`,
  `.log-file-row`, `.log-file-name`, `.log-file-meta`, `.log-file-loading/empty`,
  `#debugFileEntries` — all new styles for the files tab.
- **`tests/python/test_server_branches.py`**: 4 new tests `LogFilesViewerTests` (LV-1…LV-4):
  list-when-enabled, list-when-disabled, read-file-entries, path-traversal-rejected.


- **`logs/`** — New tracked directory with `.gitkeep` and `logs/README.md`
  (naming convention, format, rotation, enabling via env, security note).
- **`server.py`**: Opt-in JSONL log file persistence.
  - `LOGS_DIR` (`logs/`) created at import time alongside other runtime dirs.
  - `_LOG_SESSION_STAMP` — ISO timestamp captured once at import; shared by all
    `add_log()` calls within a single server run.
  - `_persist_log(entry)` — appends one JSON line per `add_log()` call to
    `logs/<stamp>-server.jsonl` when `PERSIST_LOGS=true`. Write failures are
    always swallowed (same defensive posture as `_capture_raw_response`).
    Rotation: oldest `*.jsonl` files (excluding the current session file) are
    pruned when the count reaches `LOG_FILE_MAX` (default 20).
  - `add_log()` now calls `_persist_log(log_entry)` after the in-memory append.
  - `load_config()` gains `persist_logs` and `log_file_max` from `PERSIST_LOGS`
    and `LOG_FILE_MAX` env vars (both opt-in / off by default).
  - `_get_config()` exposes `persist_logs: bool` (non-secret derived boolean).
- **`.env.example`**: new `PERSIST_LOGS=false` / `LOG_FILE_MAX=20` section under
  "Optional: Log file persistence".
- **`.gitignore`**: `logs/*.log` and `logs/*.jsonl` added (runtime state);
  `logs/.gitkeep` and `logs/README.md` remain tracked.
- **`docs/ARCHITECTURE.md`**: §3d table gains "Server logs" row; §3e Logging
  description updated to reflect actual `add_log` signature, in-memory cap, and
  new optional disk persistence.
- **`docs/USER_GUIDE.md`** §10 Troubleshooting: new "How do I preserve server
  logs across restarts?" entry with setup steps and example output.
- **`tests/python/test_server.py`**: 4 new tests (PL-1…PL-4) in `AddLogTests`:
  write-when-enabled, no-op-when-disabled, failure-swallowed, file-rotation.
  `setUp`/`tearDown` extended to save/restore `LOGS_DIR` and `_LOG_SESSION_STAMP`.


- **`server.py`**: New opt-in raw API response capture feature.
  - `RAW_RESPONSES_DIR` (`.raw_responses/`) — new on-disk rotating store; one JSON
    file per non-streaming `/api/*` proxy response.
  - `_capture_raw_response(meta, raw_bytes)` — pure helper that writes the full
    upstream response envelope (`id`, `model`, `usage`, `finish_reason`, `choices`,
    HTTP status, timestamp, etc.) to `.raw_responses/`. Capture failure is always
    non-fatal (wrapped in `try/except`). The `Authorization` header / API key is
    **never** stored — only the response body and neutral request metadata.
  - Capture hook in `_proxy_api()`: fires on every successful non-streaming response
    (including `HTTPError` responses) when `CAPTURE_RAW_RESPONSES=true`.
  - Rotation: oldest file deleted before each write when count ≥ `RAW_RESPONSES_MAX`
    (default 200).
  - `GET /raw-responses` — list metadata (newest-first, no `raw` payload).
  - `GET /raw-responses?id=` — read one full record including `raw` payload.
  - `DELETE /raw-responses?id=` — delete one record.
  - `DELETE /raw-responses` — clear all records.
  - Both new endpoints have identical path-traversal guards to `/sessions`.
  - `has_raw_capture` boolean added to `/config` (never exposes the flag value).
- **`.env.example`**: new `CAPTURE_RAW_RESPONSES=false` / `RAW_RESPONSES_MAX=200`
  section under "Optional: Raw API response capture".
- **`.gitignore`**: `.raw_responses/` added (runtime state, not tracked).
- **`tests/python/test_server_http.py`**: 4 new integration tests (RC-1…RC-4):
  capture-on creates file with correct metadata; list/read/delete round-trip;
  delete-all clears store; `/config` `has_raw_capture` boolean.
- **`tests/python/test_server_branches.py`**: 5 new branch/security tests (RC-5…RC-8):
  capture-off flag respected; rotation cap; path-traversal rejected on GET and DELETE;
  no API key in stored record.
- **`docs/ARCHITECTURE.md`**: `.raw_responses/` data-store row; 4 new endpoint rows.
- **`docs/specs/raw-response-capture.md`**: full feature spec written.

> Streaming SSE capture deferred to backlog #48-streaming (see backlog.md).

### Added (2026-06-27 — Reasoning token proof in message note)
- **`app.js` `formatUsage()`**: now reads
  `usage.completion_tokens_details.reasoning_tokens` (OpenAI-standard field) with
  a fallback to a top-level `reasoning_tokens` field used by some providers. When
  the value is present **and > 0** it is appended to the per-message token summary,
  e.g. `84 in · 51 out · 135 total · 32 reasoning tokens`. When absent or zero the
  output is **unchanged** — non-reasoning calls show no difference. This is the
  definitive, API-sourced proof that a reasoning effort setting actually engaged
  (vs. being ignored by a model that doesn't support it). The 💭 Thinking block
  (feature #11) remains the secondary visual signal.
- **`tests/js/app.test.mjs`**: 4 new `FU-R*` test cases — `FU-R1` (reasoning
  tokens appended), `FU-R2` (zero count → no false positive), `FU-R3` (top-level
  fallback field), `FU-R4` (no details object → unchanged output). 84 JS tests
  green (was 79 before this sprint).

### Changed (2026-06-27 — Backlog #47 Ph1–Ph7 — RAIL Hardening Phase 2)
- **Ph1 — Fix §6e cross-reference bug** (`review.md`): added canonical §6e-BE /
  §6e-FE / §6e-DOCS blockquote with links to the three SME mandatory-gate tables;
  added new **§6f shift-left governance findings gate** requiring spec §4b to be
  filled (G-1/G-2/G-3) with advisory GAP for unfiled deferrals.
- **Ph2 — Prevention-rule recall receipt** (`build.md`, `spec.md`): both pre-flight
  sections now require reading `self-improvement-log.md` and emitting a one-line
  receipt before writing code or asking the first interview question.
- **Ph3 — Spec amendment mini-protocol** (`build.md`): new §3d "Spec amendment
  protocol" defines pause → propose → confirm → record → continue; `spec.md`
  template gains optional `## Spec changelog` section (populated during `/build`
  only if amendments occur).
- **Ph4 — §4b in review gate** (`review.md`): already part of Ph1 §6f above.
- **Ph5 — Clean-state guarantee** (`loop.md`): escalation block gains
  "Clean-state guarantee" with Option A (stash/branch) and Option B (revert);
  escalation memory note template gains `## Working-tree state` section.
- **Ph6 — Coverage ratchet self-advancement** (`loop.md`, `govern.md`): `/loop`
  Continuous Improvement section now calls the ratchet check explicitly and
  defines the ≥ 5pp threshold for proposing a bump; `govern.md` SE-4 gains a
  ratchet-rule verification check.
- **Ph7 — Wire mutation testing** (`loop.md`, `govern.md`): `/loop` Continuous
  Improvement section adds optional mutation audit step; `govern.md` SE-2 adds
  mutation-testing reference with 60% kill-rate advisory threshold.
- **Bonus fix — `rail-pipeline.md` convention duplication** (`.clinerules/`): the
  `getEnabledTools` inline reference replaced with a pointer to `docs/rail-pipeline.md`;
  `doc-consistency-check.sh` now exits 0 cleanly.
- No app code, runtime deps, tests, or CSS changed.
- Files: `.clinerules/workflows/review.md`, `.clinerules/workflows/build.md`,
  `.clinerules/workflows/spec.md`, `.clinerules/workflows/loop.md`,
  `.clinerules/workflows/govern.md`, `.clinerules/rail-pipeline.md`,
  `docs/specs/rail-hardening-phase2.md`.

### Changed (2026-06-27 — Backlog #46 — Shift-left governance in /spec)
- **`/spec` Step 2b — Shift-left SBA/SA-lite governance check** — Added a new
  lightweight pre-check step to `.clinerules/workflows/spec.md` that runs three
  advisory checks before the spec is written:
  - **G-1 AC testability (SBA-3):** each acceptance criterion must be binary and
    observable; vague ACs are rewritten before proceeding.
  - **G-2 Scope / value justification (SBA-2):** confirms every in-scope item
    maps to the stated goal, flagging scope creep or gold-plating as advisory.
  - **G-3 Dependency coherence (SBA-5-lite):** names any open backlog prerequisites
    the spec depends on, so they are declared rather than discovered mid-sprint.
- **Spec template §4b** — Added a shift-left governance findings table to the
  embedded spec template so results are recorded in the spec itself and visible
  to `/review`.
- **`govern.md` cadence note** — Added a shift-left cross-reference explaining
  that per-requirement SBA/SA checks run at `/spec`; the full four-role
  macro-assessment stays at sprint close / on demand.
- **`docs/governance.md` — "Relationship to RAIL" expanded** — Replaced the
  single-paragraph description with a two-level governance model: shift-left
  (per-requirement, advisory, inside RAIL) and Governance Board
  (macro-assessment, sprint cadence, outside RAIL), including a mapping table.
- All findings at Step 2b are **advisory** — they do not block Status: Ready.
  The full `/govern` cadence is unchanged.
- No app code, tests, runtime deps, or CSS changed.
- Files: `.clinerules/workflows/spec.md`, `.clinerules/workflows/govern.md`,
  `docs/governance.md`, `docs/specs/spec-shift-left-governance.md`.

### Added (2026-06-27 — Backlog #28 — Pre-commit git hook)
- **`make hooks` target** — one-command install of the git pre-commit hook:
  symlinks `.git/hooks/pre-commit` → `scripts/pre-commit.sh`; idempotent;
  documented in `README.md` (new "Git hooks" section) and `AGENTS.md`.
- **`tests/python/test_pre_commit.py`** — 6 regression tests (PC-1…PC-6)
  covering clean/bad Python, clean/bad JS, non-code files only, and
  `SKIP_GITLEAKS` escape-hatch; all green.
- **`docs/specs/pre-commit-hook.md`** — RAIL spec for backlog #28.
- No new runtime deps; no CSS change; no server-side change.
- Files: `Makefile`, `README.md`, `AGENTS.md`,
  `tests/python/test_pre_commit.py`, `docs/specs/pre-commit-hook.md`.

### Fixed (2026-06-27 — Backlog #19 bugfix — Auto Model Router wrong model ids)
- **Auto Model Router: corrected `TIER_MAP` fallback model ids** — the original
  hardcoded fallbacks (`claude-opus-4`, `claude-sonnet-4-5`, `claude-haiku-4-5`)
  used dashes which the GSA/USAi gateway does not accept, causing an upstream error
  on every routed message. Corrected to the underscored ids verified live against
  the gateway on 2026-06-26 alongside backlog #18:
  `claude_4_8_opus` / `claude_4_6_sonnet` / `claude_4_5_haiku`.
- **Wired `TIER_HIGH/MEDIUM/LOW_MODEL` env overrides end-to-end** — `server.py`
  `load_config()` now reads these three optional env vars; `_get_config()` forwards
  them as non-secret `tier_*_model` fields so deployments with different model
  aliases can override the client-side `TIER_MAP` without touching source code.
  `.env.example` documents the new vars with a comment describing the defaults.
- **Tests strengthened:**
  - JS RM-9 tightened to assert exact underscored ids (was "any non-empty string").
  - JS RM-10 added: `appConfig` tier override precedence over hardcoded fallback.
  - Python `LoadConfigTests.test_reads_env_and_applies_defaults` extended: tier
    keys default to `''`.
  - Python `ConfigEndpointTests.test_config_includes_tier_model_fields` added:
    `GET /config` response includes all three `tier_*_model` keys.
- **No new runtime deps; no CSS change; no new endpoints.**
- Files: `app.js`, `server.py`, `.env.example`, `tests/js/app.test.mjs`,
  `tests/python/test_server.py`, `tests/python/test_server_http.py`.

### Added (2026-06-27 — Backlog #19 — Auto Model Router)
- **Auto Model Router** — client-side per-message model routing with zero new
  runtime dependencies.
  - `app.js`: `routeModel(text, opts)` pure classifier returns `'high' | 'medium' | 'low'`
    based on message length (>800 chars), code presence (fences / `function` / `class` /
    `def` / `import`), and keywords (`architect`, `refactor`, `debug`, `prove`,
    `theorem`, `optimize`, `security`, `implement`, `design`). Tools-enabled flag
    floors the tier at `'medium'` (AC-5). `opts.override` of
    `'high' | 'medium' | 'low'` wins unconditionally; `'off'` returns `'medium'`
    as a neutral pass-through. `TIER_MAP` resolves a tier to a concrete model id,
    reading optional `appConfig.tier_{high,medium,low}_model` overrides with
    hardcoded Claude defaults. Integrated in `sendMessage()`: router runs before
    the API payload is built, param-exclusion logic (`getExcludedParams`) operates
    on the **resolved** model, and a `Model: <name> (auto|manual)` note part is
    injected into all three send paths (3a tools / 3b stream / 3c non-stream).
  - `index.html`: `<select id="modelTierSelect">` (Router: Off / Auto / High /
    Medium / Low) added to the composer toolbar, between `#composerModel` and
    `#composerReasoning`. Defaults to `Auto`. No CSS change needed (reuses
    `.composer-select`).
  - `app.js` `saveSettings()` / `restoreSettings()`: `modelTier` persisted in
    `usai.settings.v1`; old settings without the key default to `'auto'`.
  - `app.js` `appConfig`: three new tier-model fields (`tier_high_model`,
    `tier_medium_model`, `tier_low_model`) — empty strings that TIER_MAP
    `||`-fallbacks bypass when unset.
  - `tests/js/app.test.mjs`: 9 new RM-* tests (RM-1 … RM-9) — low greeting,
    high long, high code-fence, override high/low, medium plain, tools floor,
    off passthrough, TIER_MAP fallbacks. All 79 JS tests green.
  - `routeModel` and `TIER_MAP` exported via the Node-only `module.exports` guard.


- **Backlog #44 — LoadConfigTests MCP bridge assertions**: 2 assertions added.
  Resolves ADVISORY-04. — `tests/python/test_server.py`
- **Backlog #41 — ARCHITECTURE.md MCP bridge doc update**: 4 endpoint rows + 3 tool
  rows + routes-dict example updated. Resolves ADVISORY-01. — `docs/ARCHITECTURE.md`
- **Backlog #43 — Flakey proxy test isolation documented**: Added 15-line comment
  block in `run-tests.sh` naming `ProxySsrfGuardTests` and `ProxyIncrementalStreamingTests`
  as SSL-context-sensitive, explaining the CONFIG-pollution root cause, and documenting
  the two-pass `--append` workaround. Resolves ADVISORY-03.
  — `run-tests.sh`, `docs/specs/flakey-proxy-test-isolation.md`
- **Backlog #42 — Auto model router spec (#19)**: Wrote `docs/specs/auto-model-router.md`
  (Status: Ready) with user story + 8 binary ACs, `routeModel()` design, `TIER_MAP`,
  settings control spec, and 7 RM-* test cases. Resolves ADVISORY-02 (unblocks #19
  for Sprint 10). — `docs/specs/auto-model-router.md`

### Added (prior — Backlog #16 Ph2 — Obsidian-MCP Bridge)
- Optional `obsidian-mcp` Node subprocess
  Gated entirely on a new `OBSIDIAN_MCP_PATH` env var — no behaviour change when unset.
  - `server.py`: `call_obsidian_mcp()` helper, `_mcp_enabled()`, `MCP_TOOL_ALLOWLIST`,
    four handler methods (`_post_mcp_tool`, `_post_mcp_rename_tag`, `_post_mcp_move_note`,
    `_get_mcp_vaults`), two new routes, two new CONFIG keys (`obsidian_mcp_path`,
    `obsidian_node_path`), `has_mcp_bridge` added to `/config` response.
  - `app.js`: `callMcpTool()` async helper, three new `TOOL_REGISTRY` entries
    (`obsidian_rename_tag`, `obsidian_move_note`, `obsidian_list_vaults`), MCP gate
    added to `getEnabledTools()` (requires `has_mcp_bridge` + Obsidian Memory toggle).
  - `.env.example`: `OBSIDIAN_MCP_PATH` and `OBSIDIAN_NODE_PATH` env vars documented.
  - `tests/python/test_server_mcp.py`: 17 new tests (T-1…T-13 from spec + T-14…T-17
    success-path coverage); all green.
  - Security: subprocess args use only admin-configured env vars (no user input),
    `nosec B603 B607` suppressions with justification; `bandit -ll` clean (no medium+).
  - Coverage: server.py line 90.6% ✅ (≥90%), branch 88% ✅ (≥80%); JS branch 72.49% ✅.

### Added (prior)
- **Backlog #7 — Embeddings RAG for uploaded files**: `getRelevantChunks` is now
  async and embedding-aware. When `EMBED_MODEL` is configured server-side and the
  semantic-search toggle is on, chunks are re-ranked by cosine similarity to the
  query embedding instead of plain keyword scoring. Falls back gracefully to
  keyword order on any failure (embed model missing, toggle off, `/embeddings`
  error). New `semanticSearchEnabled` module-level flag driven by the
  `#semanticToggle` checkbox (wired up in a future UI sprint).  
  Exported `_getRelevantChunksTest` hook enables full unit-test isolation — 5 new
  JS tests (JS-1…JS-5) cover cosine path, keyword fallback, toggle-off, error
  fallback, and sort order.

### DX
- **Backlog #18 — Continue dev-workflow model tiers (guided)**: Three guided model
  tiers defined for the RAIL pipeline roles — High (`claude_4_8_opus`), Medium
  (`claude_4_6_sonnet`), Low (`claude_4_5_haiku`) — verified live against the
  gateway on 2026-06-26. Delivers:
  - `docs/continue-config.sample.yaml` — sample Continue `config.yaml` with all
    three tiers, YAML anchors, and explanatory comments.
  - "Model tiers (guided)" subsection added to `docs/rail-pipeline.md` §3 with a
    tier→role→model table and manual-switching note.
  - One-line tier hints appended to `.continue/rules/code-planner.md`,
    `development-sme.md`, and `continuous-improvement.md`.


### Embeddings-based memory search — #16 Ph3 (2026-06-26)

Added client-side semantic re-ranking to memory search so results are ordered by
vector similarity when an embedding model is configured.

**server.py:**
- `load_config()` now reads `EMBED_MODEL` and `EMBED_INPUT_TYPE` from `.env`,
  exposes `has_embeddings` in `GET /config`.
- `GET /memory/search` response always includes `embed_available: bool`.
- New `POST /embeddings` endpoint: validates payload (size, input array, model
  configured, base_url present), passes SSRF guard, proxies to
  `<base_url>/v1/embeddings`, forwards upstream status on HTTP errors.

**app.js:**
- `cosineSimilarity(a, b)` — dot-product cosine; returns 0 on null/mismatch.
- `embedTexts(texts, fetchFn)` — batch-embed via `POST /embeddings`; injectable
  fetch for isolated testing.
- `embedMemorySearch(query, k, fetchFn)` — fetches keyword results from
  `/memory/search`, then re-ranks by cosine similarity when
  `appConfig.has_embeddings && embed_available`; silently falls back to keyword
  order on any error.
- Both `memorySearch` call sites (sidebar search + `memory_search` tool) now use
  `embedMemorySearch`.
- `appConfig`, `cosineSimilarity`, `embedTexts`, `embedMemorySearch`, and
  `_embedMemorySearchTest` shim exported for tests.

**Tests:**
- JS: MS-1 (re-rank), MS-2 (embedTexts fallback), MS-3 (has_embeddings=false) — all pass.
- Python: MS-4 (`embed_available` field), MS-5 (400 no model), MS-6 (502 SSRF),
  plus 7 additional branch tests (413, empty input, >512 input, no base_url,
  happy-path proxy, URLError, HTTPError forwarding).
- Coverage: `server.py` 93% lines / 93% branches ✅ (gates: 90% / 80%).

Files: `server.py`, `app.js`, `tests/python/test_server_branches.py`,
`docs/specs/embeddings-memory-search.md`.
Backlog item #16 Ph3 ✅.


### Prompt Templates — close coverage gap with PT-11/PT-12 (2026-06-26)

Added 2 additional unit tests to close the JS branch coverage gate for item #12:

- **PT-11** (`deleteUserTemplate` — corrupted localStorage catch branch): exercises the
  `try/catch` fallback when `localStorage` contains invalid JSON — verifies no throw.
- **PT-12** (`deleteUserTemplate` — non-array JSON normalisation branch): exercises the
  `if (!Array.isArray(...))` normalisation path in `deleteUserTemplate`.

These 2 tests push JS branch coverage from **68.42% → 70.95%**, clearing the ≥70%
gate. All 47 JS tests pass; `./run-tests.sh --coverage` green across all gates.

Files: `tests/js/app.test.mjs`.
Backlog item #12 ✅.


### Streaming + tool calling together — `runWithTools` final-answer streaming (#9) (2026-06-26)

Refactored `runWithTools()` in `app.js` to stream the final assistant answer when
`streamFinalAnswer=true`, and hardened the full tool-loop with injectable `callFn`/
`streamFn`/`onDelta` for isolated unit testing (no network). 10 new `ST-*` tests
bring JS branch coverage from 66.5% to **70.56% ✅**.

**What shipped:**
- `runWithTools()` accepts `{ streamFinalAnswer, callFn, streamFn, onDelta }` opts;
  `streamFn` is called for the final answer round when `streamFinalAnswer=true`
  (both after tool-use rounds and when the model returns text directly without tools).
- `_runWithToolsTest` export added to `module.exports` — injects a no-op `test_tool`
  stub so the full tool loop is exercised in Node without a live TOOL_REGISTRY match.
- Abort/error propagation verified across all paths: round 0 callFn error/abort,
  round > 0 streamFn abort, and MAX_TOOL_ROUNDS safety-net abort/error.
- `onDelta(delta, full)` forwarding: passed through from `_runWithToolsTest` opts to
  `streamFn` so incremental token callbacks reach the UI.
- 13 new unit tests (ST-1 … ST-13) in `tests/js/app.test.mjs` — TDD-first (Red ✓
  → Green ✓ → Refactor); all 44 JS tests pass.
- Gates: server.py line 94% ✅, server.py branch 94% ✅, JS branch 70.56% ✅,
  security scan clean ✅.
- Spec: `docs/specs/streaming-tool-calling.md`.
- Backlog item #9 ✅.


### Premium UI Polish — Inter font, glassy surfaces, shadow scale, micro-interactions (2026-06-24)

CSS-only upgrade of `styles.css` + `index.html` (`?v=24`). No logic, no backend, no
tests changed — all 116 tests pass.

**What shipped:**

- **Inter web font** — `<link>` preconnect + stylesheet added to `index.html`;
  `--font-sans` token points to Inter with full system-stack fallback;
  `font-feature-settings: 'cv02','cv03','cv04','cv11'` for optical Inter tuning;
  `-webkit-font-smoothing: antialiased` on `body`.

- **Token refresh** — new CSS custom-properties: `--color-accent-gradient` (135deg
  green), `--color-accent-glow`, `--color-accent-soft`, `--color-bg-glass`,
  `--font-sans`, `--ease-out`, `--transition-lg`; 4-stop layered shadow scale
  (`--shadow-xs/sm/md/lg/xl`) with heavier dark-mode values; full `--radius-*` scale
  (`xs/sm/md/lg/xl/pill`); `--focus-ring` / `--focus-ring-offset` a11y tokens.

- **Glassy / frosted surfaces** — `.chat-header`, `.input-area` (in-conversation),
  `.debug-panel` use `backdrop-filter: blur(14–16px) saturate(1.4–1.5)` where
  supported; solid fallback via `@supports not (backdrop-filter: blur(1px))`;
  `.chat-header` is `position: sticky; z-index: 100`.

- **Empty-state icon** — gradient circle + ambient glow ring (`box-shadow` accent-soft
  halo) with hover scale; greeting bumped to `1.75rem / 700 / letter-spacing: -0.03em`.

- **Send button** — `background: var(--color-accent-gradient)`; glow
  `box-shadow: 0 4px 14px var(--color-accent-glow)` on hover; `scale(0.93)` press.

- **Example-prompt chips** — `border-radius: var(--radius-lg)`; accent border + bg on
  hover; `translateY(-2px)` lift; `translateY(0)` active press.

- **New-chat / sidebar buttons** — `box-shadow: var(--shadow-sm)` at rest; lift + accent
  border on hover; shadow collapse on active.

- **Active session item** — 3px left accent stripe + `--color-accent-soft` background.

- **Sidebar action buttons** — `background: var(--color-accent-gradient)` + glow on hover.

- **Message input pill** — `border-radius: var(--radius-xl)`; `--shadow-md` at rest;
  `--shadow-lg + 4px accent-soft ring` on `:focus-within`.

- **Micro-interactions** — all interactive elements: `0.15s cubic-bezier(0.4,0,0.2,1)`;
  `@keyframes fade-in` on empty-chat-area; `@keyframes msg-in` on message groups;
  `@keyframes debug-slide-in` on debug panel.

- **Refined scrollbars** — `scrollbar-width: thin`; padded thumb with hover tint.

- **Reduced-motion gate** — `@media (prefers-reduced-motion: reduce)` collapses all
  animations/transitions to `0.001ms`.

- **CSS version bump** — `styles.css?v=23` → `styles.css?v=24` in `index.html`.

**Files changed:** `styles.css`, `index.html`
**Spec:** `docs/specs/premium-ui-polish.md`

---

### RAIL Phase 7 — Ratchet sentinel, proxy adversarial tests, CI branch gate (#37, #38, #39) (2026-06-24)

Implements backlog items #37, #38, and #39 from the QA review findings
(`docs/specs/qa-testing-review.md`).

**What shipped:**

- `tests/js-coverage.mjs` — writes the measured JS branch % to a sentinel file
  (`/tmp/usai-js-branch-pct`) so `run-tests.sh` passes the LIVE value to the
  ratchet guard instead of always falling back to `$JS_MIN=70`. Fixes the latent
  bug where the JS ratchet always compared 70 vs 70 and could never detect a real
  regression. The write is non-fatal (warns on failure so read-only CI envs are safe).

- `run-tests.sh` — reads the sentinel file (`/tmp/usai-js-branch-pct`) and passes
  the actual measured branch % to `scripts/ratchet-check.sh` as `--js-branch`. Falls
  back to `$JS_MIN` only when the file is absent (e.g. Node < 22 coverage skip).

- `tests/python/test_scripts.py` — two new TDD tests (T-10a, T-10b):
  - `T-10a` (TestJsSentinelWritten): sentinel file exists and contains a numeric value
    after `node tests/js-coverage.mjs` runs.
  - `T-10b` (TestJsSentinelMatchesOutput): sentinel value matches the branch % reported
    in stdout to within 1%.

- `tests/python/test_server_proxy.py` — new `ProxyAdversarialTests` class (T-11a/b/c):
  - `T-11a` (test_malformed_upstream_json_does_not_crash_proxy): upstream replies with
    invalid JSON → proxy responds with a defined status (not 500/crash). The proxy
    passes the raw 200 body through; what we assert is that no unhandled exception
    produces a 500.
  - `T-11b` (test_unreachable_upstream_returns_502_not_500): connection-refused
    (URLError path) → 502. Exercises the URLError branch in isolation.
  - `T-11c` (test_upstream_http_error_returns_upstream_status_not_502): upstream HTTP
    500 (HTTPError path) is relayed as 500, NOT converted to 502. Asserts the two
    error code paths are distinct.
  Also hardened `test_streaming_response_is_relayed` against a race condition where
  `chunk0` could arrive before the socket read loop starts (now passes if any of
  chunk0/1/2 is present, in addition to `[DONE]`).

- `.github/workflows/tests.yml` — Python job updated to mirror `run-tests.sh
  --coverage`: now runs `coverage run --branch`, enforces `--fail-under=90`
  (line gate), and extracts branch % from `coverage json` to enforce the 80% branch
  gate independently. Fixes the CI gap where a branch-coverage regression would pass
  CI but fail locally (#39).

- `backlog.md` — items #37, #38, #39 marked done.

### RAIL Phase 6 — SSRF guard tests + branch coverage push to 93% (2026-06-24)

Implements backlog item #36 (SSRF guard unit tests) from the RAIL Improvements
spec (`docs/specs/rail-improvements.md`).

**What shipped:**
- `tests/python/test_server.py` — added `TestIsSafeUpstreamUrl` class (TDD Red→Green)
  covering: `http://` and `https://` public hosts → safe; `file://`, `gopher://`,
  `ftp://` → rejected; `http://169.254.169.254`, `http://127.0.0.1`, `http://[::1]`
  → rejected; empty string / malformed → rejected.
- `tests/python/test_server_proxy.py` — added `ProxySsrfGuardTests` class verifying
  that `_proxy_api` returns 400 when the configured `base_url` is a private/loopback
  address (SSRF rejection end-to-end). All proxy fixtures now set
  `_test_allow_loopback: True` so the existing integration tests continue to work
  against the loopback stub server.
- `tests/python/test_server_branches.py` — large expansion: `PayloadTooLargeTests`
  (413 for `/sessions`, `/chat-history`, `/chunk-cache`, `/logs`),
  `MemoryWithVaultTests` (memory list/read/save/search/save-tag-dedup round-trips
  against a real temp vault), `SessionsRoundTripTests` (createdAt branch),
  `DeleteSessionFileNotExistsTests`, `DeleteChunkCacheFileNotExistsTests`,
  `StaticFileTests` (super().do_GET() path).
- Coverage: `server.py` line 93% / branch 94% — both coverage gates pass.
- `backlog.md` — item #36 marked done.

### RAIL Phase 5 — Security depth: supply-chain hash pin + memory-note secret scan (2026-06-24)

Implements Phase 5 of the RAIL Improvements spec (`docs/specs/rail-improvements.md`
AC-5-a through AC-5-c): closes the remaining supply-chain and secret-handling gaps
without touching any app code.

**What shipped:**
- `server.py` — added `# nosec B310` inline suppression comments on both
  `urlopen()` call sites (lines 147, 345). Bandit B310 fires because `urlopen`
  can accept `file://` or custom schemes; both calls here use URLs sourced from
  `.env` (`base_url`, `context7_base_url`) which are admin-configured and
  constrained to `http/https`. The suppression is documented with a justification
  comment explaining the guard. `scripts/security-scan.sh` now exits 0 cleanly.
- `requirements.txt` — pinned `python-dotenv` to exact version `1.0.1` with a
  sha256 wheel hash. `pip install --require-hashes` will reject any tampered or
  substituted package. The existing GHSA advisory ignore and Python 3.9 note are
  preserved with updated commentary.
- `scripts/security-scan.sh` — renumbered from 3 scanners to 4/4. New block
  **4/4 Memory-note secret scan** greps `$OBSIDIAN_VAULT_PATH/Cline/memories/*.md`
  for secret patterns (`sk-[A-Za-z0-9]`, `Bearer [A-Za-z0-9]`, `api_key\s*=`,
  `password\s*=`) and exits non-zero on a hit. Skips cleanly (exit 0) when
  `OBSIDIAN_VAULT_PATH` is unset or the `Cline/memories` directory does not exist
  — safe in CI environments without a vault. Added `SKIP_GITLEAKS`, `SKIP_BANDIT`,
  and `SKIP_PIP_AUDIT` env-var bypass hooks so test isolation does not depend on
  calling external tools.
- `.clinerules/workflows/loop.md` — memory-note template gains a **Memory-note
  safety checklist** section (no API keys/Bearer tokens/passwords, no `sk-`
  values, security-scan 4/4 passes).
- `.clinerules/workflows/review.md` — memory-note section gains a **Secret safety
  reminder** block listing the four patterns to check before saving a note.
- `tests/python/test_scripts.py` — 4 TDD tests (T-8a–T-8d, Red-first) covering:
  clean vault passes, `sk-` key triggers failure, Bearer token triggers failure,
  unset `OBSIDIAN_VAULT_PATH` skips cleanly (exit 0).

### RAIL Phase 4 — Ergonomics: change-type classifier, escalation memory note, dual-sink proposals (2026-06-24)

Implements Phase 4 of the RAIL Improvements spec (`docs/specs/rail-improvements.md`
AC-4-a through AC-4-c): reduces friction for non-feature changes, ensures loop
escalations are persisted, and wires improvement proposals to durable sinks.

**What shipped:**
- `.clinerules/workflows/spec.md` — new mandatory **Question 0** ("What type of
  change is this? `feature | bugfix | chore | docs | css`") added before the five
  existing interview questions. A role-skip mapping table documents which RAIL roles
  and gates apply per type (`feature` = full pipeline; `bugfix` = skip PO + require
  regression test; `chore`/`refactor` = skip PO; `docs` = skip PO + Tester/Security
  when no code changed; `css` = skip PO + require CSS bump gate). The spec template
  gains a **`Type:`** field immediately after **`Status:`** so every spec records
  its type.
- `.clinerules/workflows/build.md` — pre-flight check gains step 5: read the
  `Type:` field and apply the role-skip table. Missing `Type:` defaults to `feature`
  and is flagged as a gap.
- `.clinerules/workflows/loop.md` — escalation block (after 5 iterations) now
  **writes an interim memory note** to `Cline/memories/` capturing the gap list and
  iteration history before stopping. Post-loop "Propose improvements" section updated
  to dual-sink: add each proposal to `backlog.md` **and** write a tagged Obsidian
  note — not left as inline chat suggestions.
- `.clinerules/workflows/self-improve.md` — new "Proposing improvements" section
  requiring every structural improvement surfaced by `/self-improve` to land in both
  `backlog.md` (new entry with size estimate) and `Cline/memories/` (tagged note
  with rationale + backlog link). "Never leave a proposal as a chat suggestion only."

**No app code changed** — tooling/harness only.

---

### RAIL Phase 3 — Convention deduplication + doc-consistency-check + harness-parity table (2026-06-24)

Implements Phase 3 of the RAIL Improvements spec (`docs/specs/rail-improvements.md`
AC-3-a through AC-3-c): single source of truth for all USAi coding conventions,
a machine-enforced duplication detector wired into `cli-check.sh`, and a
harness-parity table for the 10 RAIL QA checks.

**What shipped:**
- `scripts/doc-consistency-check.sh` — new script; scans `AGENTS.md`,
  `.clinerules/rail-pipeline.md`, and `docs/tooling/*.md` for verbatim copies of
  convention phrases that belong only in `docs/rail-pipeline.md`.  Exits non-zero
  on first duplicate found; human-readable gap list with fix instructions.
- `AGENTS.md` — **Coding conventions** section replaced with a canonical pointer to
  `docs/rail-pipeline.md §3`; verbatim `styles.css?v=N`, `TOOL_REGISTRY`,
  `getEnabledTools`, `_handler`, and `is_safe_upstream_url` fragments removed.
  **Security** section similarly trimmed (SSRF / path-traversal detail deferred to
  the canonical source).
- `.clinerules/rail-pipeline.md` — **Architect** role (§2) reduced to a reference
  link; duplicate convention prose removed.
- `docs/tooling/cline.md` — **Coding conventions** section replaced with canonical
  pointer.
- `docs/tooling/continue.md` — **Coding conventions** section replaced with
  canonical pointer.
- `scripts/cli-check.sh` — new gate block after spec-check: runs
  `doc-consistency-check.sh` when the `--review` mode is active, so the convention-
  duplication rule is machine-enforced on every QA pass.
- `docs/rail-pipeline.md` — new **Harness-parity table** (§3 QA Review subsection)
  mapping each of the 10 Continue check files to the corresponding Cline `/review`
  gate step. Single reference for parity status.
- `tests/python/test_scripts.py` — 3 new tests (T-6/T-7) for
  `doc-consistency-check.sh`: pass when phrases only in canonical source, fail when
  duplicated in `AGENTS.md`, fail when duplicated in `.clinerules/rail-pipeline.md`.
  TDD Red-first (confirmed failing before implementation).

**Verification:** `bash scripts/doc-consistency-check.sh` now exits 0 (✓ PASS —
all 5 convention phrases confined to `docs/rail-pipeline.md`).

---

### RAIL Phase 2 — Python branch coverage gate + threshold ratchet guard (2026-06-24)

Implements Phase 2 of the RAIL Improvements spec (`docs/specs/rail-improvements.md`
AC-2-a through AC-2-d): machine-enforced Python branch coverage measurement,
per-metric branch threshold gate, and committed ratchet guard that prevents
any threshold from being silently lowered.

**What shipped:**
- `run-tests.sh --coverage` — now explicitly runs `coverage run --branch` and adds
  a second gate enforcing `PY_BRANCH_MIN=80%` branch coverage (extracted from
  `coverage json`). Line and branch gates are independent so each can be reported
  and enforced separately.
- `scripts/ratchet-check.sh` — new Bash 3.2-compatible script that reads
  `.coverage-thresholds` and compares live line/branch/JS values; exits non-zero
  if any live value is *lower* than the committed threshold. Called automatically
  by `run-tests.sh --coverage` at the end of the coverage block.
- `.coverage-thresholds` — new committed file recording the high-water marks
  (`python_line=90`, `python_branch=80`, `js_branch=70`). Ratchet rule: values
  only go up over time; never lower to make a change pass.
- `.coveragerc` — clarified comment: `fail_under = 88` is the safety-net combined
  metric; per-metric gates in `run-tests.sh` (PY_MIN=90, PY_BRANCH_MIN=80) are
  the authoritative thresholds. `branch = True` (already present) documented.
- `tests/python/test_scripts.py` — 7 new tests (T-9a/T-9b/T-9c) for
  `ratchet-check.sh`: pass-when-live≥threshold, fail-per-metric-dropped,
  and edge cases (missing file, missing key). TDD Red first, then Green.

**Current live coverage (2026-06-24):**
- Python line: 90% (492/542)
- Python branch: 85.85% (91/106) — well above the 80% gate
- JS branch: 71.43%

**Files changed:**
- `scripts/ratchet-check.sh` — new
- `.coverage-thresholds` — new
- `run-tests.sh` — branch gate + ratchet invocation added
- `.coveragerc` — comment clarification
- `tests/python/test_scripts.py` — 7 T-9a/T-9b/T-9c tests added

---

### RAIL Phase 1 — Spec↔Build verification tooling (2026-06-24)

Implements Phase 1 of the RAIL Improvements spec (`docs/specs/rail-improvements.md`
AC-1-a through AC-1-e): machine-enforced spec compliance check, Red-receipt TDD
discipline, and memory-note existence gate.

**What shipped:**
- `scripts/spec-check.sh` — new Bash 3.2-compatible script that parses a spec's §3
  Affected files and §5 Test plan, then verifies every declared file/test appears in
  `git diff HEAD`. Hard exits 1 for missing items; warns (non-blocking) for scope
  creep. Exempt paths: `docs/`, `CHANGELOG.md`, `backlog.md`, and the spec itself.
- `tests/python/test_scripts.py` — 4 new Python tests (T-1…T-4) covering pass,
  missing §3 file, scope-creep warning, and missing §5 test file scenarios (TDD Red
  first, then Green with the script implementation).
- `.clinerules/workflows/review.md §6a` — replaced the manual table scan with a call
  to `./scripts/spec-check.sh`; result interpretation table added.
- `.clinerules/workflows/loop.md` — added memory-note-exists gate to Done criteria;
  instructions to check `Cline/memories/` before declaring done.
- `.clinerules/workflows/build.md §3a` — added "Red receipt" instruction requiring
  failing-test output to be pasted into the session memory note before writing
  production code; noted as a GAP if missing in `/review`.
- `scripts/cli-check.sh` — added optional `SPEC_FILE=…` env-var gate that runs
  `spec-check.sh` as part of the full check suite.

**Files changed:**
- `scripts/spec-check.sh` — new
- `tests/python/test_scripts.py` — new
- `.clinerules/workflows/review.md` — §6a updated
- `.clinerules/workflows/loop.md` — Done criteria updated
- `.clinerules/workflows/build.md` — §3a Red receipt added
- `scripts/cli-check.sh` — spec-check gate added

---

### Style — User bubble vertical stack + green accent outline (2026-06-23)

User prompt bubbles now stack their contents vertically (bubble on top, ✎ Edit
button underneath, right-aligned) matching the assistant-turn layout change
made earlier in this session. A green `var(--color-accent)` border is also added
to each user bubble so it stands out clearly against the chat background in both
light and dark themes — no extra colour token needed.

**Files changed:**
- `styles.css` — `.message-group.user` changed from `justify-content: flex-end`
  (row) to `flex-direction: column; align-items: flex-end` (column, right-anchored);
  added `border: 1px solid var(--color-accent)` to `.message-group.user .message-bubble`.
  CSS cache version bumped v22 → v23.
- `index.html` — updated `styles.css?v=23`.

---

### Style — Assistant metadata & Regenerate button moved below response (2026-06-23)

The "Context7 + Memory: … total tokens" note and the ↻ Regenerate button now
appear **underneath** each assistant response (flush-left) instead of in a
side column to the right. This matches the layout convention of modern chat UIs
and eliminates the tall, narrow column that was cramping the response text.

**Files changed:**
- `styles.css` — added `flex-direction: column; align-items: stretch` to
  `.message-group.assistant` so the response, metadata note, and action buttons
  stack vertically; added `.message-group.assistant .message-note { text-align: left }`
  so the note aligns with the response text. CSS cache version bumped v21 → v22.
- `index.html` — updated `styles.css?v=22`.

---

### Feature — Sidebar collapse toggle: discoverability & persistence (2026-06-23)

The ☰ sidebar toggle button in the chat header now has a dynamic tooltip and
`aria-label` ("Collapse sidebar" / "Expand sidebar") so users can discover its
function at a glance, and the collapsed/expanded state is persisted to
`localStorage` so it is restored on every page reload without a flash.

**Files changed:**
- `app.js` — added `applySidebarCollapsed()` helper (testable, DOM-injectable);
  updated the click handler to persist state; restored state on `DOMContentLoaded`
  via `_testInit()`; exported helpers for unit tests.
- `index.html` — updated `title`/`aria-label` on `#sidebarToggle` to
  "Collapse sidebar" (JS keeps it current thereafter).
- `tests/js/app.test.mjs` — six new unit tests (T-1…T-6) covering helper
  behaviour, localStorage persistence, and init-time restore.

---

### Chore — Archive orphaned docs (2026-06-23)


Moved two spent/orphaned files to `archive/` to keep `docs/` tidy. No app
code, behavior, or active-docs changed.

**Files moved to `archive/`:**
- `docs/testing-and-agents-strategy.md.old` — superseded when the file was
  renamed to `docs/rail-pipeline.md`; preserved here only for reference.
- `docs/generate-continue-md-prompt.md` — a one-time Continue config
  generation prompt (formerly `Claude.md`); no longer needed in active docs.

---

### Docs — Architecture & engineering reference document (2026-06-23)

Added `docs/ARCHITECTURE.md` — a concise, overview-level architecture and engineering
reference for the USAi Chat application (concern #1 only). Covers system overview,
Mermaid request-flow and tool-calling diagrams, backend routing pattern, endpoint
catalog, config loading, on-disk data stores, frontend tool registry, streaming
paths, RAG pipeline, Obsidian memory integration, session management, settings
persistence, Markdown rendering, security architecture, and infrastructure.

A deep-detail companion note was written to `Cline/memories/` in the Obsidian vault.
Spec written to `docs/specs/architecture-doc.md`.

**Files changed:**
- `docs/ARCHITECTURE.md` — new
- `docs/specs/architecture-doc.md` — new spec
- `docs/ORGANIZATION.md` — added `ARCHITECTURE.md` row to file table and
  "Where to put new things" table

---

### Docs — Fix stale USER_GUIDE.md path references across agent docs (2026-06-23)

`USER_GUIDE.md` was moved to `docs/USER_GUIDE.md`, but many agent instruction files
still referenced the old root path. Updated all forward-looking references to use
the correct `docs/USER_GUIDE.md` path.

**Files updated** (bare `USER_GUIDE.md` → `docs/USER_GUIDE.md`):
- `README.md` — "Update USER_GUIDE.md" instruction in docs section
- `backlog.md` — docs-to-update checklists in spec template and multiple backlog items
- `AGENTS.md` — Housekeeping section
- `.clinerules/rail-pipeline.md` — Developer role docs-in-sync bullet + spec template §6
- `.clinerules/workflows/build.md` — Role 3d docs-in-sync list
- `.clinerules/workflows/review.md` — 6c documentation gate checklist
- `.clinerules/workflows/spec.md` — spec template §6 + handoff note
- `.continue/rules/CONTINUE.md` — project structure table, contribution guidelines, keep-docs table, References section
- `.continue/rules/keep-docs-in-sync.md` — update target bullet
- `.continue/checks/docs-in-sync.md` — pass criteria bullet
- `.continue/checks/acceptance-criteria.md` — user-facing docs criterion

Historical CHANGELOG entries that mention `USER_GUIDE.md` as prose (not instructions)
were left unchanged — they describe file names as they existed at the time.

---

### Docs — Deeper doc split: three-concern documentation refactor (backlog #30) (2026-06-23)

Completed the doc-split refactor planned in backlog item **#30**. Every concern's
documentation now lives in its own file; shared docs are genuinely harness-agnostic.

**`docs/testing-and-agents-strategy.md` → renamed `docs/rail-pipeline.md`**
Rewrote as a **harness-agnostic** RAIL pipeline + TDD strategy reference. All
Continue-only or Cline-only language removed; the doc now describes the shared RAIL
concept, test stack, coverage gates, and roles without favouring either harness. The
old file is preserved as `docs/testing-and-agents-strategy.md.old` for git history.

**`docs/tooling/continue.md` (new)**
Continue-only reference: `.continue/` directory layout, how Continue implements RAIL
(rules/checks/agents), running `/check` via VS Code and `cli-check.sh` from the CLI,
Obsidian memory write path, MCP setup and troubleshooting ritual.

**`docs/tooling/cline.md` (new)**
Cline-only reference: `.clinerules/` directory layout, how Cline implements RAIL
(Plan/Act workflows), all five slash-command workflows and their modes, the spec
document structure, Obsidian memory write path.

**`docs/ORGANIZATION.md` (updated)**
Replaced the "What's not here / backlog #30" placeholder section with the now-complete
file table. Continue and Cline harness sections updated to reference their new
`docs/tooling/` guides. "Where to put new things" table extended with `docs/tooling/`
entries. Removed the stale forward-looking note.

**Cross-references updated** in all of the following:
`AGENTS.md`, `README.md`, `docs/principles.md`, `.clinerules/rail-pipeline.md`,
`.continue/rules/CONTINUE.md`, `.continue/rules/testing-standards.md`,
`.continue/rules/tdd-workflow.md`, `.continue/rules/continuous-improvement.md`,
`.continue/rules/agile-workflow.md`, `.continue/checks/test-coverage.md`,
`run-tests.sh`, `scripts/cli-check.sh`.

**`backlog.md` (updated)**
Item **#30** marked `[x]` done with full summary of what was done.

---

### Docs — Three-concern project organization clarification (2026-06-23)

The project has three separate concerns that were getting mixed up in documentation:
(1) the USAi Chat app itself, (2) the VS Code Continue dev harness, and (3) the VS Code
Cline dev harness. This change makes the separation explicit throughout the codebase.

**`docs/ORGANIZATION.md` (new)**
Master reference map of the three concerns. Explains what lives where, who writes to
which Obsidian memory subfolder, and how the RAIL pipeline is shared while each harness
has its own config directory. Single source of truth for "what goes where."

**`AGENTS.md` (updated)**
Rewritten to be a genuinely harness-agnostic shared contract. Added explicit table of
the three memory subfolders (USAi/Continue Extension/Cline) and direct pointers to
harness-specific docs. Removed Continue-only language from the shared contract.

**`.clinerules/rail-pipeline.md` (updated)**
Fixed memory directive: Cline now writes to `Cline/memories/` (not
`Continue Extension/memories/`). Added concern banner marking this as Cline-only.

**`.clinerules/workflows/*.md` (updated: spec, build, review, loop, self-improve)**
All five Cline workflow files now carry a concern banner at the top stating they are
Cline-harness-only and pointing to `docs/ORGANIZATION.md`. Fixed memory note paths in
`review.md` and `loop.md` to use `Cline/memories/` instead of `Continue Extension/memories/`.

**`README.md` (updated)**
Obsidian memory section now documents all three writers (app / Continue / Cline) in a
table. RAIL/agent narrative trimmed to a short pointer to `docs/ORGANIZATION.md`.

**`backlog.md` (updated)**
Added item **#30** — a deeper doc-split refactor (rename `testing-and-agents-strategy.md`,
create `docs/tooling/continue.md` and `docs/tooling/cline.md`) — as a new top-priority
"Project organization" section.

---

### Hardened — RAIL quality gates: strict security scan, full check list, drift guard, CI alignment

Five targeted improvements to tighten the automated quality gates without changing
any app behavior:

**1 — `scripts/cli-check.sh`: full ten-check QA gate**
Added the three missing Product-Owner-gated check files (`definition-of-ready.md`,
`acceptance-criteria.md`, `definition-of-done.md`) to `CHECK_FILES[]`. All ten
checks described in `docs/testing-and-agents-strategy.md` are now passed as rules
to `cn review --review` and are reachable from the CLI.

**2 — `--strict` security scan in true QA-gate paths**
`scripts/cli-check.sh` now calls `./scripts/security-scan.sh --strict` instead of
the lenient default. A missing gitleaks/bandit/pip-audit installation no longer lets
the gate silently pass. `Makefile`: `check` now depends on the new `scan-strict`
target (plain `scan` remains lenient for quick local runs); `scan-strict` is also
listed in the help comment.

**3 — `.env.example` drift guard extended to cover `HOST` / `PORT`**
`server.py`'s `resolve_bind_address()` reads `HOST` and `PORT` via `os.getenv` but
neither variable was documented in `.env.example`, so the IaC drift test silently
missed them. Fixed on both sides:
- Added `HOST=` and `PORT=` (commented, with an IaC/container note) to `.env.example`.
- Extended `tests/python/test_env_example_sync.py` to union env vars from both
  `load_config()` *and* `resolve_bind_address()` (new `_env_vars_from_source(fn)`
  helper + `_env_vars_read_by_server()`), with explicit sanity assertions for
  `HOST` and `PORT`. Test passes (2/2).

**4 — CI / `make check` alignment documented**
`.github/workflows/tests.yml` header rewritten to state clearly that this workflow
IS the CI contract and mirrors `make check`. Makefile comments updated to describe
`scan` vs. `scan-strict` vs. `check`.

**5 — `maxTokens` input ceiling raised to 131072**
`index.html` `<input id="maxTokens">` `max` attribute changed from `96768` →
`131072` (128K, a clean power-of-two-aligned value that comfortably covers
large-output models). The field can still be left blank to omit the parameter
entirely. No behavior change — the actual model still enforces its own real limit
server-side.

### Docs — Sync RAIL docs to the expanded (6-role + cross-cutting) pipeline

After elevating RAIL to a top-tier Agile + DevSecOps + IaC pipeline, several docs
still described the original *five-role* shape. Reconciled the wording everywhere so
the docs match the implemented rules/checks/agents (no code/behavior change):

- **`docs/testing-and-agents-strategy.md`** — rewrote the "What we call this — RAIL"
  callout to explain the name still fits as the pipeline grows (it names the *shape*,
  not a head-count), retitled §3 "RAIL — the **role-based** agent pipeline" with the
  Product-Owner-bookended diagram, split the roles into **sequential roles** (0–5,
  adding the Product Owner) + a **cross-cutting concerns** table (DevSecOps / IaC /
  Observability), expanded the QA-Review checks list to all ten checks, refreshed the
  rollout plan + references, and dropped stale "five-role" phrasing.
- **`README.md`** — the "Running tests" pointer now names the Product-Owner-bookended
  RAIL roles + cross-cutting concerns and links `docs/principles.md`.
- **`backlog.md`** — renamed #17 to "role-based agent pipeline"; updated the RAIL
  summary line, the `AGENTS.md`-wiring note, and #18's tier description to "RAIL
  roles" instead of "five-role pipeline."
- **`CHANGELOG.md`** — fixed the earlier "retitled §3 … five-role" line.
- **Obsidian guide `Continue Extension/guides/RAIL-Pipeline-Guide.md`** — added a
  "What changed (2026-06-20 update)" callout, the Product-Owner-bookended diagram +
  cross-cutting note, a **Step 0 — Product Owner** role section and a **§4a
  Cross-cutting concerns** subsection, the full ten-check QA table, and refreshed the
  trigger-types table, quick-reference, and supporting-files list; tags + `updated`
  date bumped.

### Added — RAIL → top-tier Agile + DevSecOps + IaC pipeline

Elevated the **RAIL** agent pipeline from "rules + 5 checks" to a top-tier pipeline
where security and infrastructure are **machine-enforced gates**, not just prose. A
new principles doc reframes the long-standing constraint, and several gates are now
deterministic (run the same way every time) rather than LLM-judgment only. **No new
*runtime* dependency** — all new tooling is dev/CI-only and ships nothing in the app.

- **New `docs/principles.md`** — the canonical "why." §1 reframes "zero runtime
  dependencies" as **"minimal, audited *runtime* surface"** with an explicit
  RUNTIME-vs-DEV/CI litmus test (dev/CI tooling that ships nothing into the app is
  allowed and encouraged); §2 DevSecOps (shift-left, machine-enforced); §3
  Infrastructure as Code; §4 Agile (value-first, vertical slices, Ready/Done).

- **DevSecOps (deterministic security gates).**
  - **`scripts/security-scan.sh`** — secret scanning (**gitleaks**), SAST
    (**bandit** on `server.py`), and dependency CVE audit (**pip-audit**). Missing
    scanners are skipped locally with install hints; CI installs them so the gate
    is real. A documented, reviewed `--ignore-vuln` covers GHSA-mf9w-mj56-hr94
    (python-dotenv `set_key`/`unset_key` symlink issue, fixed in 1.2.2) — **not
    exploitable here** (the app only ever calls `load_dotenv()`), and we keep the
    3.9 baseline so can't pin >=1.2.2 (which needs 3.10).
  - **SSRF hardening (`server.py`)** — new pure `is_safe_upstream_url()` confines
    the `/api/*` proxy and `/context7` to **http(s)** upstreams (refuses
    `file://`/etc. with 502), resolving bandit B310. Unit + integration tested.
  - **CI `security` job** (`.github/workflows/tests.yml`) runs gitleaks + bandit +
    pip-audit on every push/PR.
  - **New checks** `dependency-and-supply-chain-review.md` and (security woven
    through) `devsecops.md` rule.

- **Infrastructure as Code.**
  - **`Dockerfile`** (non-root user, no secret baked in, `/config` HEALTHCHECK) +
    **`docker-compose.yml`** (`.env` injected via `env_file`) + **`Makefile`**
    (`make run|test|coverage|scan|check|docker-up`) — one declarative, reproducible
    bootstrap used locally and in CI.
  - **`server.py`** now honors `HOST`/`PORT` via new pure `resolve_bind_address()`
    (safe local default `127.0.0.1:8000`; container sets `HOST=0.0.0.0`).
  - **Config-as-code drift guard** — new `tests/python/test_env_example_sync.py`
    fails if `load_config()` reads an env var that `.env.example` doesn't document.
  - **New check** `iac-review.md` + rule `infrastructure-as-code.md`.

- **Agile + Product Owner.**
  - **New rules** `product-owner.md` (bookends RAIL: Definition of Ready →
    acceptance) and `agile-workflow.md` (vertical slices, backlog discipline, a
    single **Definition of Done**).
  - **New checks** `definition-of-ready.md`, `acceptance-criteria.md`, and the
    meta-gate `definition-of-done.md`.

- **Agentic maturity.** Populated the empty `.continue/agents/` with role modes:
  `product-owner.yaml`, `planner.yaml`, `security.yaml`, `improver.yaml` (each loads
  its rule(s) + handy prompts). New `observability.md` rule (structured `add_log`,
  never log secrets, `/config` liveness).

- **Wiring.** `scripts/cli-check.sh` now also runs `./scripts/security-scan.sh` and
  passes the new checks as `cn review` rules.

- **Tests.** +new unit tests (`is_safe_upstream_url`, `resolve_bind_address`,
  env-example sync) + 2 SSRF integration tests; suite now **68 Python + 25 JS**,
  `server.py` coverage **90%**, all gates green.

### Added — `scripts/cli-check.sh`: CLI equivalent of the `/check` QA gate

The extension's `/check` workflow (which runs the `.continue/checks/*.md` review
files) is **extension-only** — the Continue CLI (`cn`) has no `/check` slash command.
Added **`scripts/cli-check.sh`** so RAIL's QA-Review step (Step 4) is usable from the
terminal / headless. It (1) runs the real automated validation those checks enforce
(`./run-tests.sh --coverage` — syntax gates + JS/Python tests + coverage thresholds),
and optionally (2) runs `cn review` with the repo's `.continue/checks/*.md` passed in
as `--rule`s so the AI review applies the same standards. Usage:
`./scripts/cli-check.sh` (gate only), `--review` (also AI review), `--review-only`.
The script only attaches check files that exist, falls back to
`npx @continuedev/cli --config ~/.continue/config.yaml` when `cn` isn't on `PATH`
(npx install), and exits non-zero on gate failure (CI/pre-push friendly). Documented
in `docs/testing-and-agents-strategy.md` and `.continue/rules/CONTINUE.md`. No app
code/behavior change.

### Docs — Complete RAIL pipeline guide (Obsidian) — backlog #22

Wrote the full, detailed RAIL guide that backlog **#22** called for, stored in the
Obsidian vault at `Continue Extension/guides/RAIL-Pipeline-Guide.md`. It explains the
pipeline end-to-end for a newcomer: **Rules vs. Checks**, the four **rule trigger
types** (Always / Auto-attached via `globs`/`regex` / Agent-requested via
`description` / Manual via `@mention`) with which of our rules use which, the five
roles + the TDD inner loop + the UI/UX quality axis, how `/check` runs the gates, the
zero-dependency test stack + `run-tests.sh` + coverage gates + CI, the Obsidian
memory loop, and a **concrete worked example** (the streaming HTTP/1.1 fix walked
through all five roles). The earlier `Agent-Pipeline-Workflow.md` (2026-06-17) is
marked **superseded** in place (status tag + a callout linking to the new guide).
The repo's `docs/testing-and-agents-strategy.md` remains the source of truth; the
guide links back to it. No code/behavior change.

### Docs — Named the agent pipeline "RAIL"

The five-role agent pipeline now has an official name: **RAIL** (*Rule-governed
Agentic Iteration Loop*). The acronym captures its two defining traits — it is
**Rule**-governed (each role is an always-on rule in `.continue/rules/` plus
pass/fail `/check` gates in `.continue/checks/`) and **Agentic** (the LLM, not a
controller program, self-sequences the roles); "Iteration **Loop**" spans both the
inner TDD cycle (Red → Green → Refactor) and the outer Continuous-Improvement
feedback loop, and evokes the *guardrails* the rules/checks provide. Documented the
name and rationale across the project (no code/behavior change):

- **`docs/testing-and-agents-strategy.md`** — added a "What we call this — RAIL"
  callout and retitled §3 "RAIL — the role-based agent pipeline."
- **`AGENTS.md`** — renamed the workflow section to "Agent pipeline — RAIL" and
  introduced the term where the pipeline is described.
- **`README.md`** — references RAIL in the "Running tests" pointer to the strategy
  doc.
- **`backlog.md`** — items #17 and #22 now name RAIL.
- **Role rules** (`.continue/rules/code-planner.md`, `development-sme.md`,
  `testing-standards.md`, `continuous-improvement.md`, `tdd-workflow.md`) — each
  role header now reads "Step N of RAIL — the Rule-governed Agentic Iteration Loop."

### Fixed — Streaming responses delayed (whole reply appeared at once)

Streamed replies took a long time (seconds — up to a minute or two for long
generations) and then appeared **all at once** instead of token-by-token, even
though the upstream model was already emitting tokens. The frontend SSE reader
(`app.js`) was fine — the **proxy was buffering**. Three server-side causes, all in
`server.py`'s `_proxy_api` streaming branch:

- **HTTP/1.0 response (the real culprit).** `SimpleHTTPRequestHandler` defaults to
  `protocol_version = HTTP/1.0`, which has no streaming framing — so the browser's
  `fetch()` `ReadableStream` cannot surface any bytes until the whole connection
  closes (i.e. the entire reply lands at once after the model finishes). **Fix:**
  for streaming responses, switch to **HTTP/1.1** and emit the body with
  **`Transfer-Encoding: chunked`** (each upstream block wrapped as
  `<hex-len>\r\n<data>\r\n`, terminated by `0\r\n\r\n`) so tokens reach the browser
  as they arrive. Verified end-to-end against the live gateway (was `HTTP/1.0 200`,
  now `HTTP/1.1 200` + `Transfer-Encoding: chunked`).
- **Buffered upstream reads.** The relay read from `urlopen(...).read(1024)`, but
  `http.client.HTTPResponse.read(n)` is block-buffered (blocks until it can fill its
  buffer). **Fix:** read from the **raw, unbuffered** stream
  (`resp.fp.raw.read(8192)`, fallback to `resp.read`).
- **Nagle's algorithm.** TCP coalesced the many tiny SSE writes (~40ms each).
  **Fix:** `EnvConfigHTTPRequestHandler.disable_nagle_algorithm = True`
  (`TCP_NODELAY`).
- **Regression test:** new `ProxyIncrementalStreamingTests` in
  `tests/python/test_server_proxy.py` drives a *slow* fake upstream (0.3s between 4
  SSE chunks) through the proxy over a **raw socket** and asserts (a) the response
  is `HTTP/1.1` with `Transfer-Encoding: chunked`, and (b) the first chunk reaches
  the client well before the last (first→last gap > 0.4s). Before the fix the proxy
  replied HTTP/1.0 and the gap was ~0.0s; the test now fails if the proxy ever
  reverts to buffering or HTTP/1.0. Suite: **57 Python + 25 JS** tests pass.

### Added — Test-Driven Development workflow + thorough QA (coverage-gated)

A major lift of the quality bar — TDD is now the enforced default and coverage is
measured and gated, all **without adding any runtime dependency** (coverage tooling
is dev-only and never ships).

- **New always-on rule `.continue/rules/tdd-workflow.md`** — Red → Green → Refactor:
  write the failing test first, implement minimally, refactor under green. Defines
  when TDD applies, the test layers, the coverage gates, and a "definition of done."
- **HTTP integration tests for `server.py` (zero deps).** Three new suites boot the
  **real** `ThreadingHTTPServer` on an ephemeral port and exercise handlers
  end-to-end with stdlib `urllib`:
  - `tests/python/test_server_http.py` — `/config` redaction + `has_*` flags, the
    `/memory/*` lifecycle (save/list/read/search, string-tag handling, auto-tagging,
    5 MB size limit, traversal 404), `/sessions` & `/chunk-cache` round-trips +
    delete, and input-size limits.
  - `tests/python/test_server_branches.py` — unconfigured-state branches (memory/
    context7 → 400), chunk-cache GET/DELETE-all, `/chat-history` + `/new-chat-session`
    archiving, `/logs` + `/logs/clear`, malformed-body 400s, and routing 404s.
  - `tests/python/test_server_proxy.py` — the `/api/*` proxy and `/context7` against
    a **fake stdlib upstream**: server-key injection, client-auth passthrough, SSE
    **streaming relay**, upstream-error relay (500), unreachable-upstream (502), and
    missing-`base_url` (503).
- **More `server.py` unit tests** — `_resolve_memory_file` (traversal→basename),
  `add_log` (rotation at `MAX_LOGS`), and `load_config` (env + defaults).
- **More `app.js` pure-helper tests + exports** — exposed `safeTrim`,
  `enforceStrictSchema`, `scoreChunkByKeywords`, `chunkText`, `normalizeAssistantText`
  via the Node-only `module.exports` guard and added 11 cases (now 25 JS tests),
  covering strict-schema recursion, fenced-JSON extraction, and XSS-safety
  (raw-HTML escaping, `javascript:` link rejection).
- **Coverage measurement + enforced gates (dev-only tooling).**
  - **`.coveragerc`** — `coverage.py` config with `fail_under = 88` and exclusions
    for un-unit-testable bootstrap glue (`run()`, `install_dependencies()`,
    `__main__`) and defensive `except` branches. `server.py` currently measures
    **90%**.
  - **`tests/js-coverage.mjs`** — a dev-only JS coverage gate using Node ≥ 22's
    built-in `--experimental-test-coverage`; gates **branch coverage of the exported
    helpers ≥ 70%** (currently 73%). Whole-file line-% is intentionally low because
    browser DOM wiring isn't unit-tested.
  - **`run-tests.sh --coverage`** — new mode that runs both gates; default mode
    unchanged. `.gitignore` now excludes coverage artifacts (`.coverage*`, `htmlcov/`).
- **CI upgraded** (`.github/workflows/tests.yml`) — JS job now runs on **Node 22**
  and enforces the JS coverage gate; Python job installs dev-only `coverage` and
  enforces the `server.py` gate (still on Python 3.9 + 3.11).
- **Updated the `test-coverage` QA check** to require tests-first/regression tests,
  integration tests for handler changes, and passing coverage gates.
- **Docs synced** — `docs/testing-and-agents-strategy.md` rewritten for the TDD
  workflow + integration layer + coverage gates; `AGENTS.md`, `.continue/rules/CONTINUE.md`,
  and `README.md` "Running tests" sections updated; tracked as backlog **#25**.
  Test count: **56 Python + 25 JS** (was 8 + 14), all passing.

### Changed — Agent memory: prefer direct filesystem I/O over `obsidian-mcp`

- **`AGENTS.md` / `.continue/rules/CONTINUE.md`:** reworked the Continue-agent
  memory directive so **direct filesystem I/O is now the PRIMARY access route**
  (read/write notes with normal file tools under
  `<vault>/Continue Extension/memories/`), with `obsidian-mcp` demoted to an
  **optional/secondary** route for richer tag/note operations. Rationale: the
  stdio MCP server intermittently times out with JSON-RPC `-32001` — and this was
  observed even with a **single, lone process** (no duplicates), so "exactly one
  process" is necessary but not sufficient. Direct file I/O needs no Node child or
  stdio pipe, never wedges, and Obsidian auto-indexes the files (the same approach
  the USAi app's own `/memory/*` layer already uses). The `CONTINUE.md`
  troubleshooting row for `-32001` now documents the single-process wedge and the
  "reload again / use the filesystem" remedy. No app code changed.

### Fixed — Obsidian MCP write timeouts (`-32001`) — Node 20 pin + single-instance ritual

- **`.continue/mcpServers/new-mcp-server.yaml`**: pinned the Obsidian stdio server
  to **Node 20 LTS**. `command` is now the explicit `.../v20.20.2/bin/node` binary
  (not bare `node`, which resolves to whatever Node is active in PATH — previously
  the non-LTS v24) and `args[0]` points at the obsidian-mcp build installed under
  v20. Also renamed the Context7 server `Remote HTTP Server` → `Context7` and moved
  its API key from a (no-op for remote servers) `env` block to an HTTP `headers`
  block referencing `${{ secrets.CONTEXT7_API_KEY }}` (verified against the official
  Context7 docs via Context7).
- **Root cause (backlog #24):** Continue's `obsidian-mcp` requests timed out with
  `-32001` (notably on `create-note` *writes*). The real culprit was **orphaned
  duplicate processes** — each Continue reload/reset spawned a new server without
  killing the old one, so 2–3 instances piled up and contended for the same vault
  stdio pipe. (Backlog #23's npx→global-node change *reduced* but did not eliminate
  the orphaning.) Direct JSON-RPC tests against the binary always succeeded, proving
  the server itself was healthy. The reliable fix/ritual: **kill all processes
  (`./scripts/kill-stale-obsidian-mcp.sh`) → fully quit VS Code (Cmd+Q) → reopen →
  confirm exactly ONE process via `ps aux`.** A harmless `-32601 Method not found`
  at load (Continue probing for "resource templates" the server doesn't implement)
  is cosmetic. Documented in `CONTINUE.md` troubleshooting and backlog #24.

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

- **Edit & resend / regenerate.** Each message now shows hover actions: assistant
  turns get a **↻ Regenerate** button and user turns get an **✎ Edit** button
  (inline editor with Send/Cancel). Both `regenerateFromUser(index, override?)`
  and `startEditUserMessage(group, index)` in `app.js` truncate
  `conversationHistory`/`chatDisplayHistory` back to the chosen user turn,
  re-render the conversation (`rerenderConversation`), restage any attached
  images, and re-send through `sendMessage()`. Actions are wired via
  `addMessageActions()` in `appendMessage`/restore paths and are no-ops while a
  request is in flight. **`styles.css`**: added `.msg-actions`/`.msg-action-btn`
  and inline-editor (`.msg-edit-*`) styles with `:focus-visible` rings.
  **`index.html`**: bumped to `?v=21`.

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