## [Unreleased]

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