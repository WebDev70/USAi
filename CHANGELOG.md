## [Unreleased]

### Changed
- **`#74` coverage floors ratcheted to current reproducible coverage.** Python line
  remains **90%**, Python branch rises **80% → 90%**, and JS branch rises
  **70% → 75%** across `.coverage-thresholds`, `run-tests.sh`, and GitHub Actions.
  `scripts/ratchet-check.sh` now emits a non-failing per-metric advisory whenever
  passing coverage has at least 5 percentage points of unused headroom, preventing
  future coverage growth from leaving stale floors unnoticed. Regression tests pin
  local/CI threshold consistency plus the inclusive 5.00-point advisory boundary.

### Fixed
- **GitHub Actions now mirrors the local coverage and security contracts.** CI
  installs the lockfile-pinned jsdom test dependency, measures Python explicitly
  with `--source=backend`, and invokes the canonical production-only Bandit/CVE
  gate rather than scanning test fixtures. The canonical Bandit scope is now
  recursive, so new backend modules cannot escape SAST. DOCX parsing explicitly
  rejects DTD/entity declarations before its reviewed stdlib XML parse.
- **`#76(a)` pre-commit verification contract corrected.** A direct source audit found
  that `scripts/quality-gate.sh` is a 50-line neutral review-manifest validator, while
  live Cline/Continue docs falsely claimed it ran coverage, security, doc consistency,
  and AI review. That mismatch was the process-level cause of the prior unverified gate
  report. `/review` now invokes all four deterministic commands explicitly and requires
  current-run exit statuses, test totals, and coverage values; inherited PASS claims or
  substitute commands fail closed. Tooling docs now describe the validator truthfully,
  and two policy regression tests pin the command list and evidence requirement.


- **`#87` follow-up 2 — `docs/` tier added to the stale-path guard; a documented-but-nonexistent
  test guard was implemented rather than the docs downgraded.**
  `SCAN_DIRS` gained `docs/quality`, and a new `SCAN_EXTRA_FILES` list adds `README.md`
  plus the nine top-level `docs/*.md` files. Wide-guard scope: **29 → 49 files**.

  `docs/specs/` is deliberately **excluded** — those are completed specs, i.e. historical
  records that legitimately cite the paths and commands correct at the time of writing.
  Scanning them would force rewriting the record to satisfy a guard. Pinned by
  `test_docs_specs_are_excluded_as_historical` so a future "just scan all of `docs/`"
  change has to confront the boundary rather than silently falsify history.

  Notably, this put **`docs/rail-pipeline.md` — the canonical source every other file is
  told to defer to — inside the scan for the first time.** It had never been checked
  against its own rules.

- **The `.env.example` drift guard now exists.** Six live-policy references across four
  files (`docs/rail-pipeline.md` lines 70/234/291, `docs/principles.md`,
  `docs/quality/review-checks/iac-review.md`, `.continue/rules/infrastructure-as-code.md`)
  asserted that `backend/tests/python/test_env_example_sync.py` enforces config sync, and
  `iac-review.md` instructed reviewers not to "weaken" it. Confirmed absent from **every
  commit in git history** (`git rev-list --all` tree scan, not just `git log`). Because the
  invariant was sound and already held — 23 env vars read, 23 documented — the guard was
  **written** rather than those docs downgraded. It walks `server.py`'s AST for
  `os.getenv()` calls (no `.env` needed, no server started, and it catches the `HOST`/`PORT`
  reads outside `load_config()`), and includes two extractor sanity tests so a silent parse
  failure cannot make it vacuously pass. Verified by planting an undocumented `os.getenv`
  read: fails with the offending name, passes once documented. `os.getenv`/`os.environ`
  appears in `server.py` only across all non-test backend modules, so walking that one
  file is complete coverage today — revisit if the #45 module split moves config reads
  into a handler.

- **Stale-path matcher rewritten as boundary-aware EREs — two defects found by *running*
  the widened guard, not by reading it.**
  1. **False positive:** `tests/js-coverage.mjs` (a real file at the repo root, used by
     `run-tests.sh`) was reported as stale `tests/js`. The previous trailing-slash phrase
     had prevented this *by accident*; dropping the slash in follow-up 1 removed the
     protection along with the bug it was hiding.
  2. **False negative:** the `grep -F stale | grep -vF correct` pipeline discarded any line
     containing *both* a stale and a correct reference, masking genuine drift.

  Patterns now require a non-path character before the match (so `backend/tests/python` is
  excluded structurally, not by subtraction) and a non-identifier character after it (so
  `js-coverage.mjs` is excluded). **Both fixes verified by mutation** — reverting the matcher
  makes exactly the two new `TestStalePathMatcherBoundaries` tests fail. The same-line test
  initially survived mutation because the fixture also tripped the referenced-path guard, so
  its assertion was tightened from exit-code-only to the specific stale-path message.

- **Stale paths fixed:** `docs/quality/review-checks/iac-review.md`
  (`tests/python/` → `backend/tests/python/`) and `.continue/rules/infrastructure-as-code.md`
  (manual-review note → the now-real guard).

  `_setup_drift_tree` now creates a minimal repo skeleton (`scripts/quality-gate.sh`,
  `frontend/app.js`, `backend/server.py`) because the canonical doc it writes cites them and
  is now itself scanned. 7 new tests (`TestLiveDocsInScanScope`, `TestStalePathMatcherBoundaries`);
  `test_scripts.py` 48 tests OK; full Python suite **429 OK**; guard PASSes; security scan clean.

- **`#87` follow-up — `.continue/rules/` added to the guard scope + 12 stale paths fixed.**
  The repaired guard was asymmetric: it watched all 13 `.clinerules/*.md` files and
  **zero** `.continue/rules/*.md` files, even though `AGENTS.md` treats both harnesses
  as equal peers. That blind spot had let 12 stale paths accumulate across 7 files.

  Corrected in `.continue/rules/`: `CONTINUE.md`, `testing-standards.md`,
  `tdd-workflow.md`, `code-planner.md`, `development-sme.md`, `observability.md`
  (`tests/js/` → `frontend/tests/js/`, `tests/python/` → `backend/tests/python/`,
  `node --check app.js` → `node --check frontend/app.js`, `py_compile server.py` →
  `py_compile backend/server.py`, plus `PYTHONPATH=backend` on the `unittest discover`
  invocations so the documented command actually resolves imports).

  `infrastructure-as-code.md` claimed a `test_env_example_sync.py` drift guard
  "enforces" `.env.example` sync. **That file had never existed in git history** and
  nothing else validated `.env.example` either — the rule was instructing Continue not
  to weaken a guard that was never written. Initially downgraded to an explicit
  "manual review step" note; **the guard has since been implemented** (see the
  `docs/` tier entry below), so the rule now names it again and correctly.

  `.continue/rules` added to `SCAN_DIRS`, taking the wide-guard scope from 15 → **29
  files**. 3 new tests (`TestContinueRulesInScanScope`) pin the new coverage, including
  a regression for the phantom-test-file case.

- **Stale-path guard widened to catch slash-less references.** Adding `.continue/rules`
  surfaced a latent gap: the guard matched `tests/python/` *with* a trailing slash, so
  `unittest discover -s tests/python` — no trailing slash, the form that appeared in
  `testing-standards.md` — slipped past it. Both the stale phrases and their correct
  substitutes now match without the trailing slash, so directory-argument and
  file-path forms are both caught. This was found by a test failing for the right
  reason, not by inspection.

  All corrected commands were executed to confirm they work — including catching that
  `node --test frontend/tests/js` (a bare directory) fails on Node 24 with
  `Cannot find module`, so `development-sme.md` now uses the repo-canonical
  `node --test $(find frontend/tests/js -name '*.test.mjs')`. Full suite: **418 tests OK**.

- **`#87` — restored `doc-consistency-check.sh` scan scope (option (ii)).** The
  uncommitted refactor had collapsed the guard's **three distinct per-guard scopes**
  into a single `ENFORCING_FILES` list and swapped `.clinerules` → `.roo` (which does
  not exist on `main`), dropping the scan from **15 files to 3** and leaving all 13
  live Cline rule/workflow files unguarded while still reporting `✓ PASS`.

  The root cause was scope *conflation*, not merely narrowing. The committed guard
  deliberately used different scopes per guard: the convention-phrase guard ran against
  a curated 4-file list, while the stale-path / mandatory-gate / referenced-path guards
  walked `.clinerules/` and `docs/tooling/` recursively. Once unified, the wide dirs
  *had* to be dropped — adding `.clinerules` back to the single list produces **24
  false positives**, because workflow files legitimately name `TOOL_REGISTRY`,
  `getEnabledTools`, `styles.css?v=N` etc. as instructions to the agent.

  Resolution keeps the `.roo`-aware refactor but restores the tiering as three named
  scopes (`PHRASE_FILES`, `SCAN_DIRS`, `ROLE_COUNT_FILES`) with a comment explaining
  why they must stay separate. `.roo/` remains optional — an absent scan dir is skipped,
  not an error — so the script works unchanged on both `main` and `feat/zoo-migration`.
  The role-count guard stays narrow by design: `.clinerules/workflows/govern.md`
  legitimately says "five roles" for the governance board while Cline's RAIL model is
  0–6, and the guard exists to enforce exactly that distinction.

  Verified: guard PASSes with real coverage; a planted stale path + missing
  `backend/…` reference + "quality-gate.sh is optional" line in
  `.clinerules/workflows/` now yields **3 errors** (previously 0). Regression parity
  confirmed against the committed guard. 6 new scope-pinning tests restore the 5
  deleted assertions and add `.roo`-absent and phrase-scope-narrowness cases;
  `test_scripts.py` + `test_pre_commit.py` = **44 tests OK**.

  Note: the backlog's "restoring `.clinerules` would surface **28** violations" figure
  was **stale** — those had already been fixed by earlier sessions, so the restore was
  clean. Unblocks **`#76(a)`**, which would otherwise have committed the weakened guard.

### Changed
- **Backlog grooming pass (2026-09-18):** thorough Product-Owner grooming of
  `backlog.md`. `#77` (verify-and-close flaky proxy test isolation) **closed** —
  the proxy suite was run in isolation and returned `Ran 26 tests … OK` with all
  11 test classes carrying `setUpClass`/`tearDownClass` `server.CONFIG`
  save/restore, so `docs/specs/flakey-proxy-test-isolation.md` moves to
  `Status: Done`. Added a "🎯 Ready to pull next" DoR-verified sprint-order table
  and a suggested Sprint 19 composition. `#74` now carries re-measured live
  coverage numbers (python_line 90%, python_branch 92.31%, js_branch 75.19%)
  plus explicit acceptance criteria — note js_branch has silently drifted down
  from 77.75%, which is precisely the regression an un-ratcheted gate conceals.
  Explicit testable acceptance criteria were written for `#79`, `#82`, `#83`,
  `#84` and `#85`, and build-time convention reminders for `#70`/`#71`, so
  "ready" is verifiable rather than asserted. `#67`, `#68`, `#13`, `#14`, `#15`,
  `#57` explicitly marked **not yet Definition of Ready** with the specific open
  design questions each `/spec` must answer. `#76` re-scoped against a measured
  working tree with a per-step checklist. Stale "highest-assigned ID is 82"
  header corrected to **87** and given a copy-pasteable verification command;
  two further stale notes fixed (the "#7–#15 lack ACs" banner, when #7–#12 are
  all Done, and a `.continue/checks/` path that moved to
  `docs/quality/review-checks/`).
- **`#76` severity raised from ADVISORY to BLOCKING.** A second-pass check cloned
  `main` HEAD (`7e25ee5`) to a scratch directory and ran the gates *there* instead of
  in the dirty working tree: `./run-tests.sh` exits **1** (`Ran 361 tests … FAILED
  (failures=21, errors=11)`) and `./scripts/quality-gate.sh` exits **1** (manifest
  `docs/quality/review-checks/README.md` not found). The uncommitted tree is
  load-bearing, not cosmetic — the committed `test_server_branches.py` calls
  `server.generate_embeddings`, which exists only in the working-tree `server.py`.
  `#76(a)` is now the repo's highest-priority item.
- **Zoo/Roo harness WIP parked on `feat/zoo-migration`** (commit `08cfd61`, 26 files):
  `.roo/`, `.roomodes`, `plans/`, `scripts/find_delegations.py`,
  `scripts/delegation-policy-check.py`, `backend/tests/python/test_delegation_policy.py`.
  No application code is involved, so the runtime surface and the approved dependency
  allow-list are unaffected. This clears the WIP out of `main`'s working tree
  (`#76(b)`) while keeping the work reviewable as `#86`.

### Added
- **New always-on Cline rule — `Recommended Next Step`** (`.clinerules/recommended-next-step.md`).
  Every Cline task must now close with a `Recommended Next Step` section
  immediately after the Completed Summary, carrying four mandatory labelled
  parts: `Next Step`, `Why this should happen next`, `What this enables`, and
  `Impact if not completed`. The rule requires *one* primary action chosen by
  weighing dependency importance, risk reduction, project value, sequencing
  necessity, and unblocking power — and explicitly forbids a coding bias, so the
  recommended step may equally be requirements clarification, architecture, data
  modeling, security design, validation, testing, documentation, or
  infrastructure. An anti-pattern table rejects filler such as "continue
  development" or "add more tests". Wired into the pipeline in three places:
  a 🧭 row in the `rail-pipeline.md` always-on non-negotiables table, a new
  `/loop` Done-criteria checkbox, and step 4 of the `/review` PASS verdict.
  Harness docs (`docs/ORGANIZATION.md`, `docs/tooling/cline.md`) list the new
  rule file. Cline harness config only — no application runtime impact.
  *Second pass (self-audit):* the initial pass wired only 3 of 7 workflows. Coverage
  extended to **all 7** with an explicit terminal/non-terminal Scope table — `/spec`,
  `/loop` (incl. the 5-iteration escalation path), `/govern` (step 7), `/housekeep`
  (step 9e), `/self-improve`, standalone `/review`, and ad-hoc tasks all emit the
  section; a **mid-loop `/build` deliberately does not**, because it hands off to
  `/review` inside the same task rather than back to the user, and a mid-loop
  recommendation would be based on unverified state. The Scrum
  `Cline/scrum/definition-of-done.md` gained a matching "Process closing" addendum so
  the vault DoD does not drift from the `/loop` Done criteria.
  *Third pass (cross-harness promotion):* the rule was promoted to a **harness-agnostic
  canonical definition** in `docs/rail-pipeline.md` § "Recommended Next Step — the
  closing hand-off (mandatory)" (format table, selection criteria, constraints,
  anti-patterns, harness-wiring table), matching the repo's single-source-of-truth
  pattern enforced by `scripts/doc-consistency-check.sh`. Both harness rule files are
  now thin pointers that carry only harness-specific wiring:
  `.clinerules/recommended-next-step.md` keeps the Cline per-workflow terminal/
  non-terminal scope table, and a **new** `.continue/rules/recommended-next-step.md`
  (`alwaysApply: true`) wires the same rule into the Continue harness — so both
  extensions now close tasks identically instead of only Cline. `AGENTS.md` gained a
  "Closing hand-off (both harnesses)" paragraph under the RAIL roles;
  `.continue/rules/CONTINUE.md` gained an enforced-rule subsection;
  `docs/ORGANIZATION.md` and `docs/tooling/continue.md` list the new Continue rule.
- **Backlog `#87` — restore `doc-consistency-check.sh` scan scope.** The
  tracked-but-modified `scripts/doc-consistency-check.sh` in the working tree scans
  **3** enforcing files where the committed version scans **15**: its scan dirs are
  `.roo` + `docs/tooling`, and `.roo/` does not exist on `main`, so all twelve live
  `.clinerules/*.md` rule and workflow files are currently unguarded. Five guard tests
  were deleted from `backend/tests/python/test_scripts.py` alongside it (including
  `test_exits_nonzero_when_phrase_duplicated_in_cline_rules` and
  `test_fails_when_stale_path_in_clinerules`). Verified by planting a stale path and a
  missing `backend/…` reference in a `.clinerules/*.md` file: the committed script
  reports 3 errors and exits non-zero, the working-tree script exits 0. The narrowing is
  intentional for the Zoo migration (`plans/zoo-only-migration-plan.md` §1.2) but that
  work is parked as `#86`, so `#87` must be decided **before** `#76(a)` commits the
  weakened guard to `main`.
- **Backlog `#86` — Zoo/Roo harness migration.** The untracked Zoo/Roo agent-harness
  experiment (governance `ADVISORY-08`) is now a tracked backlog item rather than
  undocumented working-tree drift. It is *kept*, not deleted:
  `plans/zoo-only-migration-plan.md` is an approved architecture plan and
  `scripts/delegation-policy-check.py` already has a passing test
  (`test_delegation_policy.py`). Flagged not-yet-DoR, with the 7-role-vs-role-count
  conflict against `scripts/doc-consistency-check.sh` (#58) called out as the
  blocking design question.
- **`.env.example`: `EMBED_MODEL` and `EMBED_INPUT_TYPE`.** Both are read by
  `backend/server.py` (`_build_config`) but were absent from the example file, so
  a fresh clone had no way to discover that semantic search is opt-in. Documented
  with the keyword-only fallback behavior. (`#76(e)`)

### Removed
- **Scratch files cleared from the working tree** (`#76(c)`/`#76(d)`): `200`
  (0 bytes), `delegation_report.csv` (header row only, no data rows),
  `docs/roo_audit_report.md`, `docs/roo_audit_report.html`, and the tracked
  `implementation_plan.md` (committed in `3246e2a`, superseded by
  `docs/specs/server-module-split.md`) via `git rm`.

### Fixed
- **`docs/specs/obsidian-mcp-bridge.md` pointed at a deleted file.** Its "Prior context"
  line said *"See `implementation_plan.md` for full architecture detail"* — a dangling
  reference the moment `#76(d)` removed that scratch file. `doc-consistency-check.sh`
  Guard 4 only validates `backend/`, `frontend/` and `scripts/` paths, so a bare
  root-level filename slipped through. Rewritten to record the removal and point at the
  surviving architecture record, `docs/specs/server-module-split.md`. (`#76(d)`)
- **`run-tests.sh` on `main` invoked a script that only exists on a branch.** The
  syntax gate had been edited to call `scripts/delegation-policy-check.py`, part of
  the untracked Zoo/Roo experiment — so moving that WIP to its own branch (see *Changed*
  above) would have broken `main`'s own test suite. The invocation is now a comment pointing
  at `#86`; the accompanying `backend/*.py` glob compile is *kept*, since it is a real
  improvement — the previous hand-maintained module list silently stopped covering the
  modules introduced by the `#64` server split. (`#76(b)`)
- **`.env.example` stale `DEFAULT_MODEL`:** was `claude_3_haiku`, a model id that
  `#62` had already corrected everywhere else; now `claude_4_5_haiku` to match the
  verified tier defaults documented a few lines below it. (`#76(e)`)
- **`.gitignore` now ignores `.vscode/`** — editor-local, machine-specific
  settings were showing up as untracked noise in every `git status`. (`#76(f)`)
- **Blank canvas after "＋ New chat" from a project detail view:** `_showChatView`
  cleared the inline `display:none` it had set on `.chat-area` but not the one on
  `.empty-chat-area`. Because `.empty-chat-area` has no `display` rule of its own
  outside `.main-content.in-conversation`, the stale inline style left the main
  pane permanently empty after leaving a project detail view. Both overrides are
  now reset. Regression test: `PD-JS-6`.

- **Proxy dropped the first SSE frame of a streaming response (intermittent):**
  The relay read tokens via `resp.fp.raw.read`, bypassing the `BufferedReader`
  that `http.client` had already used to parse the status line and headers. When
  an upstream flushed its headers and first SSE frame in the same TCP segment,
  those body bytes sat in the buffer and were never relayed — losing the first
  token, and making `ProxyReasoningStreamTests` /
  `ProxyIncrementalStreamingTests` fail in roughly 1 run in 12. The relay now
  reads via `resp.fp.read1`, which drains the buffer before touching the socket
  while still performing at most one socket read per call, so streaming stays
  incremental (measured first→last gap unchanged at ~upstream pacing). New
  deterministic regression class `ProxyFirstFrameNotDroppedTests` (2 tests) uses
  an upstream that coalesces headers + first frame into a single `write()`.

- **Sprint 18 backlog-ID collision in code comments:** `frontend/app.js`,
  `frontend/styles.css`, and `backend/tests/python/test_server_http.py` labelled
  the attachment tray as `#79` and the project detail view as `#80`. The correct
  ids are **#80** (attachment tray) and **#81** (project detail view) — `#79` is
  the unrelated INNOV-01 grep-redaction item. Comments corrected.
  CSS: `styles.css?v=32`.

### Changed
- **De-duplicated PDF/DOCX text extraction in the frontend:** the multipart
  `POST /extract-text` + error-unwrap + `.txt` filename-rewrite logic existed in
  three near-identical copies (`uploadProjectFile`, `handleFileUpload`, and the
  `_handleFileUploadTest` shim — which had silently drifted, discarding the
  backend's error message). All three now call a single
  `extractTextServerSide(file, fetchFn)` helper with an injectable fetch.
  3 new tests: `AT-JS-9` (`.txt` rewrite keeps earlier dots), `AT-JS-10`
  (backend `{error}` surfaced), `AT-JS-11` (non-JSON error body degrades to a
  generic message).

### Added
- **Composer attachment tray (#80):** File attachments are now shown as chip
  pills directly above the composer textarea — visible at all times, not buried
  in the collapsed sidebar. Uploads are **additive** (a second attach adds a chip
  rather than wiping the first). Each chip has a per-file ✕ remove button.
  PDF and DOCX files are now accepted by the composer 📎 button and routed
  through the server-side `/extract-text` endpoint (same as project file uploads).
  After a message is sent the tray clears and attachment provenance is stored on
  the user turn so restored chats can still show `📄 report.pdf` even though the
  chunks are not re-hydrated. The hidden `#uploadedFilesDisplay` sidebar element
  is retired. CSS: `styles.css?v=31` (later bumped to `?v=32`). New test-surface
  exports: `removeAttachedFile`, `addUploadedFile`, `_handleFileUploadTest`,
  `_persistExchangeTest`, `extractTextServerSide`.
  8 new AT-JS-* unit tests green (later extended to 11).

- **Project detail view (#81):** Clicking a project now opens a **detail view**
  in the main pane showing the project name, instructions snippet, and a list of
  its saved chats. Each chat row is clickable to restore the session. A **"＋ New
  chat"** button lets the user start a fresh project-scoped chat explicitly
  (replacing the old "open = instant new blank chat" behaviour). Project chats
  are now visible in the sidebar too — grouped under their project row as a
  `.project-sub-list` below each project item (no longer hidden from "Chats").
  Backend: `GET /sessions?projectId=<id>` filter added (traversal-safe via
  `_safe_project_id`); returns 400 on traversal, 200 + `[]` for unknown ids.
  3 new PD-PY-* Python tests + 5 PD-JS-* JS tests green (later extended to 6).
  *Partially delivered:* the ⚙ Settings button re-uses the existing create-modal
  handler-swap and there is no delete action in the detail view — both tracked as
  backlog item **#82**.

- **Document #69 retrieval features in USER_GUIDE.md (#75):** Expanded §7 of
  `docs/USER_GUIDE.md` to describe structure-aware chunking, hybrid lexical+semantic
  retrieval, Reciprocal Rank Fusion (RRF), per-chunk semantic fallback, neighbour
  expansion, chunk-citation provenance labels, and chunk-size as an upper bound.

### Fixed
- **ARCHITECTURE.md drift (#73):** Two stale references updated — §3a inline
  comments and §4 cascade-delete header corrected from removed query-param form
  (`/projects?id=<id>`) to current path-style (`/projects/<id>`); §3b DELETE row
  updated to match. §8 module count corrected from "6 focused modules" to "7",
  and `file_parser_handlers.py` / `FileParserHandlerMixin` row added to the
  module table and MRO block.

### Chore
- **Commit `scripts/quality-gate.sh` + doc-sync QA-gate invocation (#78):**
  `scripts/quality-gate.sh` was untracked; it is now committed. Updated all
  forward-looking invocation instructions in `docs/tooling/cline.md`,
  `docs/tooling/continue.md`, `.clinerules/workflows/review.md`, and
  `.clinerules/rail-pipeline.md` from `./scripts/cli-check.sh --review` to
  `./scripts/quality-gate.sh`. `scripts/cli-check.sh` is preserved as a
  compatibility wrapper that delegates to `quality-gate.sh`.

### Added
- **Move chat into project (#66):** Users can now move any existing chat into
  a different project (or out of all projects) directly from the sidebar.
  - **`PATCH /sessions/<id>`** endpoint — updates the session file's `projectId`
    field. Rejects path-traversal attempts in both the session id and the
    `projectId` body parameter (400). Returns 404 when the session doesn't exist.
  - **Session ⋯ context menu** — a three-dot `⋯` button now appears on hover
    next to every chat row in the sidebar. Clicking it opens a "Move to project…"
    dropdown.
  - **Move-to-project picker** — selecting "Move to project…" opens a modal
    listing all available projects plus a "No project" option to clear the
    assignment. Confirming the choice calls `PATCH /sessions/<id>` and refreshes
    the sidebar instantly.
  - **Active-session consistency** — if the moved chat is the one currently open,
    `currentProjectId` is updated in memory and `loadProjectChunks` is re-invoked
    (or cleared) so RAG context stays in sync without a page reload.

### Fixed
- **Memory-note secret scan false positives (backlog #72):** Check 4/4 now requires
  a bounded, secret-shaped value for `sk-`, Bearer, `api_key=`, and `password=`
  detectors. Safety-checklist prose and benign identifiers such as `task-…` no
  longer fail the gate. Findings report only `path:line: [REDACTED]`, so a detected
  value is never echoed into terminal or CI logs. Housekeeping now invokes this
  canonical scan rather than maintaining a divergent broad grep.

### Added
- **Retrieval foundations (backlog #69):** Document retrieval is now
  structure-aware and hybrid.
  - **Structure-aware chunking** — `chunkTextStructured()` splits uploads on
    Markdown ATX headings, blank-line paragraph breaks, and whole fenced code
    blocks (never mid-fence). The chunk-size setting (default 200 lines, 50–1000)
    is now an **upper bound** rather than an exact window; only an oversized single
    section falls back to a bounded line split. The legacy `chunkText()` splitter
    is retained as a reference/rollback path.
  - **Versioned chunk-cache schema (v2)** — chunks now carry `schemaVersion`,
    `ordinal`, `startLine`/`endLine`, `headingPath`, `sectionType`, and
    `previousChunkId`/`nextChunkId`. Legacy caches are normalized in memory on read
    by `normalizeChunkCache()` (no batch migration, no on-disk rewrite until the
    next write).
  - **Per-chunk semantic fallback** — the all-or-nothing gate is gone. Every chunk
    is scored lexically; chunks with a vector from the *currently configured* model
    are additionally scored by cosine similarity. A single un-embedded chunk (or one
    embedded by a different model) no longer disables semantic ranking for the whole
    merged per-chat + project set.
  - **Reciprocal Rank Fusion** — lexical and semantic rankings are fused by
    `1/(60 + rank)` instead of comparing raw keyword counts against cosine scores;
    ties break deterministically by `ordinal` then `fileName`.
  - **Neighbour expansion** — each fused top-N seed pulls in its adjacent
    same-file chunks, deduplicated and re-sorted into `(fileName, ordinal)` source
    order, with the 120,000-char context budget enforced by dropping whole
    low-score seed groups rather than truncating mid-chunk.
  - **Context provenance** — injected blocks are labelled by `formatChunkLabel()`
    with file, heading path, and line range, and expanded neighbours are marked
    `(context)`; the prompt/UI header now reports the retrieval method that actually
    ran (`describeRetrievalMethod()`).
  - **Backend:** `POST /generate-embeddings` now stamps the configured
    `embed_model` onto each embedded chunk as `embedModel`, which is what makes the
    client-side model-compatibility check above possible.
  - Tests: RET-1…RET-12 + INT-2 in `frontend/tests/js/app.test.mjs`; INT-1/INT-3
    schema round-trip and legacy-cache integration tests plus an `embedModel`
    regression test in `backend/tests/python/test_server_http.py`.
  - Spec: `docs/specs/advanced-document-retrieval.md` (§3, §4.1–4.5, §4.9).
    Whole-document analysis (#70) and optional reranking (#71) remain unshipped.

### Docs
- **Retrieval docs updated to shipped behavior (#69):** `docs/ARCHITECTURE.md` §4d
  now describes structure-aware chunking, the v2 schema, per-chunk fallback, RRF
  fusion, and neighbour expansion (and explicitly notes #70/#71 as not yet
  implemented). `docs/EMBEDDINGS_GUIDE.md` §6 flow diagram and "Key points in the
  flow" table replaced the "all-or-nothing gate" row with per-chunk fallback, rank
  fusion, and neighbour-expansion rows. `docs/USER_GUIDE.md` now documents "Chunk
  size" as a maximum and explains neighbour context + excerpt labelling.
- **Advanced document retrieval — architecture spec (backlog #69/#70/#71):**
  added `docs/specs/advanced-document-retrieval.md`, the shared architecture
  for structure-aware chunking, per-chunk semantic fallback (replacing the
  current all-or-nothing embedding gate), lexical/semantic hybrid rank fusion
  (RRF), neighbor-chunk expansion, a versioned chunk-cache schema with legacy
  normalization, adaptive full-document context, and hierarchical map-reduce
  whole-document analysis. No implementation yet — this is the `/spec` output
  only; `backlog.md` gained items #69 (In Progress), #70, and #71.
- **Doc-drift fix:** `docs/ARCHITECTURE.md` §4d and `docs/EMBEDDINGS_GUIDE.md`
  ("Key points in the flow" table) previously described chunking as
  "overlapping" and omitted the all-or-nothing semantic gate. Both are now
  corrected to describe the actual current behavior (fixed-size,
  non-overlapping line chunks; semantic scoring disabled entirely if any one
  chunk in the candidate set lacks an embedding), with pointers to the new
  spec for the planned fix.

### Security

- **`/extract-text` upload DoS guard (fix):** The file-upload endpoint now
  enforces a documented 25 MB size cap. It returns **413 Payload Too Large**
  before reading the request body when `Content-Length` exceeds the cap, and
  **400 Bad Request** when `Content-Length` is missing or non-integer (instead
  of raising an unhandled error). This prevents an unbounded-memory
  denial-of-service via a very large or spoofed upload.

### Fixed
- **Flaky `EMB-3` upstream test (chore):** the fake upstream in
  `test_emb3_full_project_upload_round_trip` responded without draining the
  request body, so it intermittently reset the connection mid-write and the
  endpoint returned 500 (`[Errno 54] Connection reset by peer`). The stub now
  reads `Content-Length` bytes before responding.
- **Repository hygiene (chore):** `.gitignore` now excludes the runtime
  `.projects/` data directory (user project files created by the server) and
  Python bytecode caches (`__pycache__/`, `*.py[cod]`), so runtime data and build
  artifacts can no longer be committed by accident.
- **Test suite green again:** The coverage tool was scoped to a non-existent
  module (`--source=server` instead of `--source=backend`), which masked low
  coverage on newly added handler modules. Corrected the scope and added direct
  unit tests for `server.generate_embeddings`, `is_safe_upstream_url`,
  `_mcp_enabled`, `_resolve_memory_file`, and `get_project_memory_dir` so
  `server.py` line coverage is back above the 90% gate (now 95%).
- **PDF/DOCX extraction test:** `test_fe1_extract_text_from_pdf_and_docx` now
  posts a real `multipart/form-data` body and generates a valid PDF with
  extractable page text (hand-built content stream), so it runs and asserts
  extracted content instead of skipping.

### Changed
- **Harness-neutral quality gate (chore):** The ten review checks moved from
  `.continue/checks/` to `docs/quality/review-checks/` so they are owned by the
  documentation tree instead of one editor extension. `scripts/quality-gate.sh` is
  the new neutral runner; `scripts/cli-check.sh` and
  `scripts/doc-consistency-check.sh` were slimmed to stop depending on
  Continue/Cline files, and `docs/rail-pipeline.md` is now the single authority for
  the RAIL role order. Agent behaviour moved to `.roomodes` + `.roo/rules*`.
  Tracked in `plans/zoo-only-migration-plan.md`, covered by
  `backend/tests/python/test_migration.py` and the rewritten `test_scripts.py`.
- **Breaking API change (Projects):** The project update endpoint changed from
  `PUT /projects?id=<id>` to `PUT /projects/<id>`. The previous query-parameter
  form has been removed.
- **Project behavior change:** A project's `memoryMode` can now be edited after
  creation through Project Settings and `PUT /projects/<id>`.
- **Breaking project metadata change:** The unused `icon` field has been dropped
  from stored project metadata and API responses.

### Added
- **Projects remediation — 10-point plan (feature/fix):** Closed the gaps between
  the Projects feature's documented behavior and its actual behavior:
  - **Single-project endpoint:** Added `GET /projects/<id>` so the UI can fetch one
    project without listing them all.
  - **Session ↔ project linkage:** Session summaries now carry their `projectId`, so
    a restored chat re-associates with the right project.
  - **Chunk reload on restore:** Restoring a chat now re-loads that project's uploaded
    file chunks so file search keeps working after a reload.
  - **Project-scoped memory everywhere:** Every `/memory/*` call now threads the
    project id, so search/save/list respect the active project.
  - **Editable memory mode:** `PUT /projects/<id>` now accepts `memoryMode`, so a
    project can be switched between "default" and "project-only" after creation.
  - **Project Settings & Files UI:** Wired the project context menu to a Settings
    modal (rename, memory mode, instructions) and a per-project file uploader.
  - **PDF/DOCX extraction:** `POST /extract-text` now returns plain text from PDF and
    DOCX uploads; frontend upload flow updated. PDF text uses the single new runtime
    dependency `pypdf`; DOCX is parsed with the **standard library only**
    (`zipfile` + `xml.etree`) rather than `python-docx`, which would have pulled in
    the large, platform-specific `lxml` wheel. `requirements.txt` stays fully
    hash-pinned (`python-dotenv`, `pypdf`, and its transitive `typing_extensions`),
    and `backend/tests/python/test_file_parser.py` covers the stdlib DOCX paths
    (runs, tabs/breaks, tables, missing document part, oversized-body guard).
  - **Project embeddings:** Added `POST /generate-embeddings` to embed a project's
    file chunks, and replaced the all-or-nothing semantic-search gate so keyword
    ranking is used as a graceful fallback when embeddings are unavailable. The
    `/memory/search` response now always reports an `embed_available` flag so the
    client can choose keyword-only vs embedding-ranked results.
    Closes backlog **#65**, scoped as an MVP to files uploaded going forward —
    project files uploaded *before* this change keep their `embedding: null` and
    stay on the keyword-fallback path until a separate backfill item (**#68**)
    is implemented. Spec: `docs/specs/project-chunk-embeddings.md`.

- **UX & UI SME — explicit two-discipline split (#60, docs):** Elevated the
  existing "Front-End Design (UI/UX)" quality axis into a formal **UX & UI SME**
  with clearly separated sub-disciplines across all harness documentation:
  - **UX sub-discipline** (how it works): user-need framing, user-flow mapping,
    information architecture & placement (cross-checked against `docs/USER_GUIDE.md`),
    friction audit, and task-completion verification.
  - **UI sub-discipline** (how it looks): unchanged vanilla CSS, token system,
    WCAG AA, USWDS/Context7, motion guard, CSS cache-bust rules.
  - Updated files: `.clinerules/workflows/sme-frontend.md` (UX/UI pre-impl
    checklists + dual gate tables), `docs/rail-pipeline.md` §3 (updated "Quality axis
    — UX & UI SME" section), `.continue/rules/ui-ux-design.md` (UX sub-discipline
    block added), `.continue/checks/ui-ux-review.md` (3 new UX failing criteria:
    user goal absent, flow undescribed, wrong IA placement).
  - Directly encodes Self-Improvement Entry 002 (UI control placement / doc-HTML
    drift) as an automated review criterion.
  - Spec: `docs/specs/ux-ui-sme-role.md`.

- **Referenced-path existence guard (#59, chore):** Extended `scripts/doc-consistency-check.sh`
  with **Guard 4** — automatically detects when `.clinerules/` or `docs/tooling/` markdown
  files reference a `backend/`, `frontend/`, or `scripts/` path that no longer exists on disk.
  - Glob tokens (`*`) and shell variable tokens (`$`) are skipped to avoid false positives.
  - Bare directory references (token ending in `/`) are skipped.
  - 3 new regression tests added to `backend/tests/python/test_scripts.py`
    (`TestRefPathExistenceGuard`: T-14a, T-14b, T-14c).
  - Stale reference fixed: `.clinerules/workflows/sme-backend.md` updated to point to
    `test_dev_deps.py` (correct test file) instead of `test_env_example_sync.py` (non-existent).
  - Spec: `docs/specs/ref-path-existence-guard.md`.

- **Doc-drift guards (#58, chore):** Extended `scripts/doc-consistency-check.sh` with three
  deterministic Bash guards so the doc-drift classes fixed manually earlier are now
  machine-enforced by the existing `cli-check.sh --review` gate and pre-commit hook:
  - **Guard 1 (Stale-path):** Fails if deprecated flat test paths (`tests/js/`,
    `tests/python/`, `node --check app.js`, `py_compile server.py`) appear in
    `.clinerules/` or `docs/tooling/` files.
  - **Guard 2 (Role-count consistency):** Fails if `The RAIL roles (0–6)` heading is
    absent from `.clinerules/rail-pipeline.md`, or if conflicting count phrases
    (`five roles`, `six roles`, `seven roles`) appear in `docs/tooling/` or `AGENTS.md`.
  - **Guard 3 (Mandatory-gate):** Fails if `optional` appears on the same line as
    `cli-check.sh --review` in any Cline doc.
  - 7 new regression tests added to `backend/tests/python/test_scripts.py`
    (`TestStalePathGuard`, `TestRoleCountGuard`, `TestMandatoryGateGuard`).
  - Spec: `docs/specs/doc-drift-guards.md`.

### Fixed
- **quality-gate.sh manifest parsing (chore):** The manifest parser only matched
  Markdown table rows (`| 1. | \`file.md\` |`). It now also matches the numbered-list
  style (`1. \`file.md\``) the docs use interchangeably, so the missing-file and
  empty-file checks fire correctly. Fixes the two `test_migration.py` failures.
- **pypdf CVE bump (security):** Upgraded `pypdf` from `4.2.0` to `6.18.1` in
  `requirements.txt` to clear 40 known advisories flagged by `pip-audit`. Extraction
  code is unchanged; only the pinned version moved.
- **Project-file embedding upload contract (fix):** The Project Settings file
  uploader posted `projectId` in the JSON body with no `chunkIds`, but
  `POST /generate-embeddings` reads `projectId` from the URL query string and only
  embeds chunks whose id is in `chunkIds` — so real uploads generated no embeddings.
  `uploadProjectFile` now returns `{ filename, chunkIds }` and the uploader posts
  `projectId` in the query string plus the full `chunkIds` list in the body.
  Verified by frontend regression test `PFU-3` and new hermetic backend integration test `EMB-3`.
- **RAIL doc drift (chore):** Reconciled all stale test paths (`tests/python/` →
  `backend/tests/python/`, `tests/js/` → `frontend/tests/js/`) across
  `.clinerules/rail-pipeline.md`, `spec.md`, `govern.md`, `sme-backend.md`, and
  `sme-frontend.md`.
- **loop.md:** Removed duplicated "Continuous Improvement" block; restructured as
  an ordered five-step checklist (Steps 1–5) with clean "Step 5" memory-note prose.
- **review.md:** Replaced misleading `cn` fallback note — corrected to accurately
  describe that `./scripts/cli-check.sh --review` is **fail-closed**: it always
  attempts the AI review pass (`cn` or `npx @continuedev/cli` fallback) and the
  full gate fails if the review command fails. Removed incorrect "optional / skip"
  language that contradicted the script's `set -euo pipefail` behaviour.
- **docs/specs/doc-drift-guards.md:** Added explanatory note to §4 Guard 3 clarifying
  the fail-closed policy so the spec's own prose matches the corrected workflow wording.


### Docs (2026-07-15 — RAIL doc-drift cleanup)
- **`.clinerules/rail-pipeline.md`** — Renamed "The six RAIL roles" heading to
  "The RAIL roles (0–6)" with an explicit note that Role 0 is features-only and
  the remaining six run on every build. Eliminates conflicting role-count language
  across the Cline workflow files.
- **`.clinerules/workflows/build.md`** — Fixed stale test-runner paths throughout:
  `tests/js/` → `frontend/tests/js/`; `tests/python/` → `backend/tests/python/`
  (with correct `PYTHONPATH=backend` prefix); `node --check app.js` →
  `node --check frontend/app.js`; `py_compile server.py` →
  `py_compile backend/server.py`. Added explicit §3a step to *create* the session
  memory note before the Red receipt is appended (previously the note was referenced
  but never defined as needing creation). Renumbered Role 3 sub-sections to remain
  consistent (3a–3g).
- **`.clinerules/workflows/review.md`** — Added mandatory §6a gate:
  `./scripts/cli-check.sh --review` is now the canonical first check-suite step in
  Cline's `/review` workflow. Renumbered subsequent sub-sections (§6b–§6i) to match.
  The standalone `./run-tests.sh --coverage` gate is retained as §6c with a note
  that its values are verified from §6a output.
- **`.clinerules/workflows/loop.md`** — Clarified that the end-of-loop memory note
  *appends to* the session file created in `/build` §3a rather than creating a new
  duplicate note.
- **`docs/tooling/cline.md`** — Fixed `/build`→`/review` role split in the flow
  diagram (was "Roles 1–4: Planner, SME, Tester, Security"; now correctly "Roles
  1–4: Planner→Architect→Developer→Tester" for `/build` and "Roles 5–6:
  Security→Reviewer/QA" for `/review`). Updated `/review` workflow table entry and
  "Running QA gates" section to reflect `./scripts/cli-check.sh --review` as the
  primary gate; added `./scripts/spec-check.sh` to the gate list. Removed stale
  commented-out optional `cli-check.sh` block; replaced with canonical gate
  invocation showing all four internal stages.

### Docs (2026-07-08 — /review docs sweep)
- **`docs/rail-pipeline.md`** — Updated all test-path references from old flat
  `tests/python/` and `tests/js/` to correct `backend/tests/python/` and
  `frontend/tests/js/` paths following the backlog #56 directory reorg. Also
  updated `tests/js-coverage.mjs` layout entry in the tree diagram.
- **`docs/USER_GUIDE.md`** — Corrected server start command to
  `.venv/bin/python backend/server.py` (from bare `python server.py`).
- **`docs/EMBEDDINGS_GUIDE.md`** — Corrected server restart command to
  `.venv/bin/python backend/server.py`.
- **`docs/rail-pipeline.md` (IaC table)** — `test_env_example_sync.py` path
  updated to `backend/tests/python/test_env_example_sync.py` in both the
  cross-cutting concerns table and the harness-parity table.
- **`docs/principles.md` §3 (IaC)** — `test_env_example_sync.py` path updated
  to `backend/tests/python/test_env_example_sync.py`.


### Fixed (2026-07-08 — flaky backend test isolation)
- **`ProxySsrfGuardTests.setUpClass` (`test_server_proxy.py`)** — `test_server_mcp.py`
  runs before `test_server_proxy.py` in alphabetical discovery order and leaves
  `_test_allow_loopback: True` in the shared `server.CONFIG` global. The SSRF guard
  tests then silently bypassed the guard and crashed with `RemoteDisconnected` instead
  of the expected 502. Fixed by adding `server.CONFIG.pop('_test_allow_loopback', None)`
  at the top of `ProxySsrfGuardTests.setUpClass` so the loopback bypass is always
  cleared before the SSRF server boots.
- **`test_pr2_list_projects_sorted_newest_first` (`test_server_http.py`)** — Two rapid
  `POST /projects` calls in the same millisecond generated identical IDs
  (`project_<ms_timestamp>`), causing the second project to overwrite the first on disk.
  `GET /projects` then returned 1 project instead of 2, failing the assertion.
  Fixed in `projects_handlers.py` by switching the ID generation to microsecond
  precision plus a 6-char UUID hex suffix
  (`project_<µs_timestamp>_<uuid_hex[:6]>`), making IDs collision-proof.

### Fixed (2026-07-08 — _ServerProxy KeyError when launched as backend/server.py)
- **`_ServerProxy.__getattr__` in all 5 handler mixins** — When the server is launched
  as `python backend/server.py`, Python registers the module under `__main__` (not
  `'server'`) in `sys.modules`. The hard-coded `sys.modules['server']` lookup in each
  mixin's `_ServerProxy.__getattr__` therefore raised `KeyError: 'server'` on the first
  real request, producing an empty reply and a "Network error: Failed to fetch" in the
  browser. Fixed by changing the lookup to
  `sys.modules.get('server') or sys.modules.get('__main__')` in all five files:
  `proxy_handlers.py`, `session_handlers.py`, `memory_handlers.py`,
  `mcp_handlers.py`, `projects_handlers.py`. All endpoints (`/sessions`, `/projects`,
  `/config`, etc.) now respond correctly regardless of how the server is started.

### Refactor (2026-07-06 — frontend/backend directory reorg, backlog #56)
- **`backend/`** — Moved all Python server modules (`server.py`, `proxy_handlers.py`,
  `memory_handlers.py`, `session_handlers.py`, `mcp_handlers.py`, `projects_handlers.py`)
  into `backend/`. `backend/server.py` resolves `STATIC_DIR` to `../frontend` relative
  to its own directory so it continues to serve the frontend correctly.
- **`frontend/`** — Moved frontend assets (`index.html`, `app.js`, `styles.css`) into
  `frontend/`.
- **`backend/tests/python/`** — Python test files relocated (via `git mv`) from
  `tests/python/`.
- **`frontend/tests/js/`** — JS test files relocated (via `git mv`) from `tests/js/`.
- **Tooling patches** — `run-tests.sh`, `.coveragerc`, `Dockerfile`, `Makefile`,
  `scripts/security-scan.sh`, `scripts/cli-check.sh` all updated to reference the new
  paths. `make run` now starts `backend/server.py`.
- **Docs patches** — `README.md`, `AGENTS.md`, `docs/ORGANIZATION.md`,
  `.github/workflows/tests.yml` all updated to reference the new `frontend/` and
  `backend/` paths.
- **Verification** — 316 tests pass; JS tests green (0 failures); security scan clean;
  `GET /` returns HTTP 200. Pre-existing failures (SSRF SSL cert + project-sort +
  reasoning-field) confirmed identical to those on the commit before this change.

### Changed (2026-07-05 — doc sync: model catalogue references)
- **`docs/USER_GUIDE.md` §4 "Built-in model choices"** — Updated the provider list to match the current gateway catalogue (Google: 2.5 Flash/Flash-Lite/Pro + 2.0 Flash; Anthropic: Haiku/Sonnet/Opus 4.x; OpenAI: GPT-5.2/5.4/5.5; Meta: Llama 4 Maverick; Cohere: English v3). Removed stale entries (Gemini 2.0 Pro, Claude 3.5/3.7/Sonnet 4/Opus 4, Llama 3.2 11B).
- **`README.md` sample `.env`** — Changed `DEFAULT_MODEL=claude_3_haiku` → `claude_4_5_haiku` to match a valid current gateway ID.
- **`backlog.md` model-routing note** — Updated tier candidates to `claude_4_8_opus` / `claude_4_6_sonnet` / `claude_4_5_haiku`.

### Changed (2026-07-05 — model dropdown refresh)
- **`index.html` model list** — Updated `#modelSelect` to match the current gateway model catalogue. Removed stale IDs (`claude_3_haiku`, `claude_sonnet_3_7`, `claude_sonnet_4`, `claude_opus_4`, `llama3211b`, `gemini-2.0-pro`). Added new groups and correct IDs:
  - **Google**: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-pro`, `gemini-2.0-flash`
  - **Anthropic**: `claude_4_5_haiku`, `claude_4_5_sonnet`, `claude_4_6_sonnet`, `claude_4_5_opus`, `claude_4_7_opus`, `claude_4_8_opus`
  - **OpenAI** *(new group)*: `gpt-5.2-latest-guardrails-defaultv2`, `gpt-5.4-latest-guardrails-defaultv2`, `gpt-5.5-latest-guardrails-defaultv2`
  - **Meta**: `llama_4_maverick`
  - **Cohere** *(new group)*: `cohere_english_v3`
  - `TIER_MAP` fallbacks and `MODEL_PARAM_EXCLUSIONS` patterns were already correct — no changes needed. 105 JS tests pass.

### Fixed (2026-07-05 — circular-import startup crash, #45 regression)
- **Circular-import startup crash** — `server.py` crashed immediately on start when
  run as `python server.py` because each handler-mixin module (`proxy_handlers`,
  `memory_handlers`, `session_handlers`, `mcp_handlers`, `projects_handlers`) imported
  `server` at module-import time, hitting Python's partially-initialised module object.
  Fixed by replacing the top-level `import server as _server` in every handler file
  with a lazy `_ServerProxy` wrapper that defers attribute lookup to
  `sys.modules['server']` at call time. The server now starts cleanly.
- **`server.py` `__main__` — respects `HOST`/`PORT` env vars** — Added
  `os.getenv('HOST', '127.0.0.1')` / `os.getenv('PORT', '8000')` reads in the
  `if __name__ == '__main__'` block so callers and CI test subprocesses can bind to
  a free port without modifying source.

### Tests (2026-07-05 — startup regression test)
- **`tests/python/test_server_startup.py`** (new) — Subprocess-level regression test
  (`TestServerSubprocessStartup.test_server_starts_without_import_error`) launches
  `server.py` as a real subprocess with `PYTHONUNBUFFERED=1`, binds to an
  OS-assigned free port, and asserts the "Serving on" startup banner is printed
  within 12 s. Catches the circular-import class of bug that in-process tests cannot
  detect. 1 new test; completes in ~0.4 s.

### Refactor / Architecture
- **`server.py` module split — backlog #45** — Split the 1,871-line `server.py` (BLOCKING-02 governance) into 6 focused Python modules using mixin classes with ZERO behavior changes. All 315 existing tests continue to pass without modification.
  - `server.py` reduced to ~630 lines (scaffold, config, routing, helpers, entrypoint)
  - `proxy_handlers.py` — `ProxyHandlersMixin` (~430 lines): `_proxy_api`, `_get_context7`, `_post_embeddings`, `_get_raw_responses`, `_delete_raw_responses`
  - `session_handlers.py` — `SessionHandlersMixin` (~400 lines): 14 session/cache/log handler methods
  - `memory_handlers.py` — `MemoryHandlersMixin` (~265 lines): 5 Obsidian memory handler methods
  - `mcp_handlers.py` — `McpHandlersMixin` (~127 lines): 5 MCP bridge handler methods
  - `projects_handlers.py` — `ProjectsHandlersMixin` (~178 lines): 5 projects CRUD handler methods
  - Class MRO: `ProxyHandlersMixin, SessionHandlersMixin, MemoryHandlersMixin, McpHandlersMixin, ProjectsHandlersMixin, SimpleHTTPRequestHandler`
  - All module-level names (`CONFIG`, `SESSIONS_DIR`, `add_log`, etc.) remain in `server.py` — no test files modified
  - `run-tests.sh` syntax gate updated to include all 5 new handler files
  - `scripts/security-scan.sh` bandit scan updated to cover all 6 Python modules
  - Spec: `docs/specs/server-module-split.md`
  - Coverage: line 92.6% (≥90%), branch 87.5% (≥80%)

### Process / Tooling
- **RAIL pipeline — SHK (Senior Housekeeping & Hygiene Steward) role added** — Closed the housekeeping gap in the RAIL pipeline by adding a dedicated Housekeeping SME role at three levels of the process:
  - **Per-item (lightweight):** `/review §6h` leave-no-trace gate added to `review.md` — checks spec Status header, scratch files, untracked TODOs, and CHANGELOG freshness after every build.
  - **Per-item (Done criteria):** `/loop` Done checklist extended with the leave-no-trace gate; `definition-of-done.md` (vault) updated with a new **Housekeeping** section.
  - **Sprint-close (full sweep):** SHK added as Role 5 in `/govern` (after SBA/SA/SE/SPMS); `scrum-artifacts.md` sprint-close step updated to reference all five roles; `govern.md` Synthesis report template updated with SHK score row.
  - **On-demand:** New standalone `/housekeep` workflow created at `.clinerules/workflows/housekeep.md` — 9-step sweep covering spec/backlog reconciliation, Done-pile hygiene, dead-code/scratch-file audit, log/cache bloat, doc-consistency drift, dependency freshness, and vault memory hygiene.
  - **Always-on non-negotiable:** 🧹 Housekeeping row added to `.clinerules/rail-pipeline.md` always-on table with cross-references to all three levels.

### Docs
- **`docs/ARCHITECTURE.md`** — Updated for Projects v1 (#27 Slices 1–4): added `/projects` CRUD + `/chunk-cache?projectId` + project-scoped `/memory/*` endpoint rows to §3b catalog; expanded §3a routes dict; new §3d persistence rows for `.projects/` metadata and project-scoped chunk/memory paths; new §3e section documenting `_safe_project_id`, `get_project_memory_dir`, `_project_memory_dirs`, `composeSystemPrompt` 3-layer prompt path, and cascade-delete; §4c extended with 3-layer system-prompt composition; §4d updated for `projectChunks` merge and cascade-delete; §4e expanded with project-scoped memory data flow + Mermaid diagram (Default dual-read vs Project-only isolation); §4f updated for `currentProjectId`, sectioned sidebar (Pinned/Projects/Chats), and legacy migration; §5 security table updated for `/projects` and `/logs/files` path-traversal guards. Resolves BLOCKING-01 from 2026-07-01 governance audit. (#54)

### Fixed
- **`docs/USER_GUIDE.md`** — Filled missing content in the "Project files" subsection (§8): accepted file types now listed (`.txt`, `.md`, `.pdf`, `.docx`, `.json`, `.csv`); "How project files are searched" bullets replaced with plain-English descriptions; context-note example (`Files: 5 chunk(s)`) added. No code changes.

### Added
- **Projects — Slice 4: Project Files (shared knowledge)** — Upload files to a project so every chat searches them via RAG, without re-uploading per session. `POST/GET/DELETE /chunk-cache?projectId=<id>` endpoints; `projectChunks` array merged at query time; "Project files" section in the project Settings modal; cascade-delete on project removal. 7 Python integration tests (PF-1..PF-7) + 4 JS unit tests (PCJ-1..PCJ-4). Completes Projects v1. (#27 Slice 4)


### Added (2026-07-01 — #55 Slice 3 Memory Modes: project-scoped memory dirs)

- **`server.py`** — Project-scoped memory directories:
  - `get_project_memory_dir(project_id)` — returns `<vault>/<subdir>/projects/<id>/memories` Path.
  - `_project_memory_dirs(project_id)` — reads the project JSON, determines `memoryMode`
    (`'default'` → `[global, project]`; `'project-only'` → `[project]`); missing key treated as `'default'`.
  - `_memory_search()` — applies `_project_memory_dirs` scoping; deduplicates results by absolute path.
  - `_memory_list()` — applies `_project_memory_dirs` scoping.
  - `_memory_save()` — when `projectId` supplied, writes note to project dir instead of global dir.
- **`app.js`** — Forwards `projectId` into memory API calls:
  - `embedMemorySearch(query)` — appends `&projectId=<currentProjectId>` when a project is open.
  - `saveMemory(title, content, tags)` — adds `projectId` to POST body when a project is open.
  - `prepareContextMessages()` — passes `projectId` to `embedMemorySearch`.
- **`tests/python/test_server_http.py`** — `ProjectsSlice3MemoryModeTests` class (8 tests MM-3…MM-8):
  - MM-3: default-mode search merges global + project dirs.
  - MM-4: project-only search excludes global dir.
  - MM-5: global search never surfaces project-only notes.
  - MM-6: save with projectId writes to project dir only.
  - MM-7: list (project-only mode) returns only project-dir notes.
  - MM-8: project JSON missing `memoryMode` key is treated as `'default'`.
  Spec: `docs/specs/projects-workspaces-slice3.md`.

### Added (2026-06-30 — #54 Slice 2 Project instructions: 3-layer system-prompt concat)

- **`server.py`** — Project instructions field:
  - `_post_projects()`: accepts optional `instructions` string (max 8 192 bytes); stored in `.projects/<id>.json`. Returns 400 `{'error': 'instructions too long'}` when cap exceeded.
  - `_put_project(id)`: allows updating `instructions` (same 8 KB cap); `memoryMode` remains immutable.
  - Legacy project JSON files without `instructions` field load without error; field defaults to `''`.
- **`app.js`** — 3-layer system-prompt composition:
  - `currentProjectInstructions` module-level variable — mirrors the open project's instructions string.
  - `composeSystemPrompt(projectInstructions, perChatPrompt)` — pure exported helper; concatenates non-empty layers with `'\n\n'`; returns single layer without extra whitespace; returns `''` if both empty.
  - `sendMessage()` uses `composeSystemPrompt(currentProjectInstructions, inputs.systemPrompt)` — regenerate and edit-resend inherit it automatically.
  - `openProject()` populates `currentProjectInstructions` from the project record.
  - `restoreSession()` fetches the project record to re-populate `currentProjectInstructions`; clears to `''` when session has no project.
  - New-chat / no-project flow resets `currentProjectInstructions` to `''`.
- **`index.html`** — Instructions `<textarea>` (optional) with 8 192-char counter in Create Project modal; `styles.css?v=28`.
- **`styles.css`** — New v28 classes: `.modal-textarea`, `.modal-char-counter`, `.modal-label-hint`, `.over-limit`.
- **`tests/python/test_server_http.py`** — Three new project-instructions tests PR-9…PR-11: create with instructions (201 + field in response), update instructions (200 + persisted), instructions > 8 192 bytes → 400.
- **`tests/python/test_server.py`** — PR-12: legacy project JSON without `instructions` field loads as `''` without error.
- **`tests/js/app.test.mjs`** — Eight new tests PJ-7…PJ-14: `composeSystemPrompt` four edge cases, `currentProjectInstructions` getter/setter export, `sendMessage` uses composed prompt, `openProject` populates instructions, `restoreSession` populates instructions.
  Spec: `docs/specs/projects-workspaces-slice2.md`.

### Added (2026-06-30 — #27 Slice 1 Projects CRUD + sidebar sections + `currentProjectId` plumbing)

- **`server.py`** — Projects CRUD API (`/projects` GET/POST/PUT/DELETE):
  - `_post_project()`: creates `.projects/<id>.json` with server-generated `project_<epoch-ms>` id.
  - `_get_projects()`: lists all projects sorted by `createdAt` desc.
  - `_put_project(id)`: updates `name`/`pinned`; silently ignores any `memoryMode` change (immutable after creation).
  - `_delete_project(id)`: removes project file + sweeps `.chat_sessions/` to clear `projectId` on orphaned sessions; does NOT delete sessions or vault notes.
  - `_safe_project_id()`: path-traversal guard (pattern `project_<digits>` only; rejects `../`, embedded `/`, etc.) → 400.
  - `_post_new_chat_session()`: now stamps `projectId` from request body onto the archived session JSON.
  - `has_projects: true` added to `/config` response.
- **`app.js`** — Projects frontend:
  - `currentProjectId` module-level state variable.
  - `archiveCurrentSession()`: stamps `projectId` onto POST `/sessions` body.
  - `showSessionsList()`: rewritten into three collapsible sections — **Pinned**, **Projects** (≤5 shown with "Show more"), and **Chats**.
  - `createProject()`, `openProject()`, `updateProject()`, `deleteProject()`: full CRUD wiring.
  - `_renderProjectItem()`: project row with folder icon + ⋯ context menu (Rename / Pin / Delete).
  - `restoreSession()`: re-populates `currentProjectId` from session's `projectId` field.
  - `New Chat` handler resets `currentProjectId` to `null`.
- **`index.html`** — Create/Rename Project modal (`#createProjectModal`) with name input + memory-mode selector; modal script block wires save/cancel/rename flows. `styles.css?v=27`.
- **`styles.css`** — New v27 classes: `sidebar-section-heading`, `project-item`, `project-name`, `project-icon`, `project-menu-btn`, `show-more-btn`, `project-ctx-menu`, `ctx-menu-item`, `modal-overlay`, `modal-box`, `modal-btn`, `modal-btn--primary`, etc.
- **`tests/python/test_server_http.py`** — `ProjectsCRUDTests`: 16 integration tests (PR-1…PR-8 + extended set) covering create, list, put, delete, orphan-on-delete, traversal guard, 404, 413, idempotent delete.
- **`tests/js/app.test.mjs`** — 6 new JS unit tests PJ-1…PJ-6: `currentProjectId` export, `archiveCurrentSession` stamps `projectId`, session restore re-populates `currentProjectId`, `has_projects` in config, new-chat resets `currentProjectId`, `has_projects` in `/config` response.
  Spec: `docs/specs/projects-workspaces-slice1.md`.

### Added (2026-06-30 — #53 Projects CRUD coverage: branch tests to push server.py to 90%)

- **`tests/python/test_server_branches.py`** — New test classes:
  - `ProjectsCRUDTests`: 17 HTTP integration tests covering `GET/POST/PUT/DELETE /projects`
    including traversal guards, 413 too-large, 404 not-found, idempotent delete, and
    session `projectId` clear-on-delete.
  - `ProjectsDirectUnitTests`: 4 targeted unit tests for hard-to-reach exception-handler
    branches: `_safe_project_id('')` → None (line 1522); corrupt JSON in projects dir
    silently skipped (lines 1534–1535); malformed PUT body → 400 (lines 1604–1606);
    corrupt session JSON during delete scan silently ignored (lines 1644–1645).
  - `RawResponsesPathTraversalDeleteTests`: covers DELETE `/raw-responses?id=<valid>`
    with file present/absent (lines 1454–1458).
  - Total new tests: 193 (was 144). `server.py` now **90% line / 28% branch** ✅.

### Added (2026-06-29 — #48b follow-up: disconnect partial capture + exception non-fatal tests)

- **`tests/python/test_server_proxy.py`** — Two new tests in `ProxyStreamingCaptureTests`:
  - `test_disconnect_triggers_partial_capture` (RCS-7): client abruptly closes socket
    after first SSE chunk (using `_SlowStreamUpstreamHandler`); proxy must write a partial
    capture file with `streamed=true`. Covers lines 488–491 (the `except BrokenPipeError`
    best-effort path).
  - `test_rcs6_streaming_capture_exception_is_non_fatal` (RCS-6): patches
    `_capture_raw_response` to raise `RuntimeError`; verifies the exception is swallowed
    (lines 502–503), a `warn` log is emitted, relay still delivers `[DONE]`, and no
    capture file is written. Key fix: kept the mock active for 0.3s *inside* the `with`
    block after the request returns (race: the client sees `[DONE]` before the server
    thread completes the post-loop capture call).
  - Lines 488–491 and 502–503 are now covered. `server.py` stays at **90% line / 88.8% branch** ✅.

### Added (2026-06-29 — #48b Raw API response capture, streaming SSE v2)


  `_proxy_api` streaming branch accumulates SSE chunks into a `bytearray` (only when
  `CAPTURE_RAW_RESPONSES=true`) and writes a capture file after the stream ends.
  Zero relay-latency impact: chunks are flushed to the client *before* being appended
  to the buffer. Best-effort partial capture on client disconnect.
  Spec: `docs/specs/raw-response-capture-streaming.md`.
- **`tests/python/test_server_proxy.py`** — New `ProxyStreamingCaptureTests` class
  (RCS-1…RCS-5): streaming capture creates file with `streamed=true`; metadata correct;
  capture-off writes nothing; non-streaming capture regression (`streamed=false`); list/read
  endpoints surface streaming captures. Also added `test_proxy_non_streaming_capture_via_fake_upstream`
  to `ProxyAndContext7Tests` and `test_non_streaming_proxy_capture_writes_file_when_enabled`
  to `ProxyUpstreamErrorTests` to cover the non-streaming capture code path end-to-end.
  Coverage: `server.py` **90% line / 88.8% branch** (gates ≥ 90% / ≥ 80% ✅).

### Fixed (2026-06-29 — #11d reasoning proxy integration test, genuinely implemented)

### Added (2026-06-28 — RAIL log analysis, closing the runtime→QA loop, #52)

- **`scripts/analyze_logs.py`** (new): stdlib Python log analyzer. Reads all
  `logs/*.jsonl` files (capped at 5000 lines per file), counts entries by `level`
  and `component`, identifies the top-3 most frequent error messages, and collects
  `fetch` entries with `latency_ms > 2000ms` as latency outliers. Sensitive patterns
  (`sk-`, `Bearer `, `api_key=`, `password=`) are scrubbed to `[REDACTED]` in all
  output. Exits `1` if any `"level":"error"` entries found; `0` otherwise.

- **`scripts/analyze-logs.sh`** (new): shell wrapper for the Python analyzer.
  Auto-detects the project `.venv`; falls back to system `python3`. Accepts an
  optional `[log-dir]` argument. Called by `/review` §6g, `/build` step 3b, and
  `/govern` SE-5.

- **`tests/python/test_analyze_logs.py`** (new): 8 TDD tests (AL-1…AL-8) covering
  empty dir, all-info, single error, multiple errors same component, latency outlier
  present/absent, secret scrubbing, and malformed JSON line skipping.

- **`.clinerules/workflows/review.md` — §6g** (new): advisory "Runtime log review"
  gate runs `analyze-logs.sh` at every `/review` pass. Exit 1 surfaces as
  `ADVISORY [logs]:` lines in the gap list — never converts PASS to FAIL.

- **`.clinerules/workflows/build.md` — pre-flight step 3b** (new): "Runtime log
  recall" step runs `analyze-logs.sh` before touching any component files.
  Informational only — never blocks the build.

- **`.clinerules/workflows/govern.md` — SE-5** (new): "Log-trend audit" step at
  sprint close. A component with errors → ADVISORY + backlog proposal. Same
  component errors in two consecutive governance reports → BLOCKING + append to
  `self-improvement-log.md`.

- **`.continue/rules/observability.md`** updated: Observability is now defined as
  *writing* AND *reading and acting on* runtime logs. Added "Analyzing logs" section
  documenting `analyze_logs.py`, `/review §6g`, `/build step 3b`, and `/govern SE-5`.

- **`docs/rail-pipeline.md` §5** updated: entry #11 added documenting the RAIL log
  analysis rollout.

- **`docs/USER_GUIDE.md` §10 Troubleshooting** updated: new "Analyzing log files
  with RAIL (developer use)" subsection explaining how to run `analyze-logs.sh`,
  what it reports, and how exit codes map to RAIL review/govern behavior.


- **`tests/js/app.behavior.test.mjs`** (new): 15-test jsdom-based behavior suite
  covering the previously-untested orchestration layer of `app.js`:
  - B-01–B-03: `callChatApi` — happy path, 4xx error, network error (throw)
  - B-04–B-05: `streamChatApi` — SSE delta streaming, 429 error before body
  - B-06–B-07: `appendMessage` — user/assistant DOM output + markdown-body class
  - B-08+B-09: `saveSettings` / `restoreSettings` — round-trip through localStorage
  - B-13–B-14: `saveMemory` — 200 ok/400 error paths
  - B-15–B-16: `archiveCurrentSession` — empty/non-empty history guard
  - B-17–B-18: `loadChatHistory` — 2-turn render / empty-turns no-op
  - B-19: global `unhandledrejection` handler — does not propagate exceptions
  
  **Strategy:** uses Node's built-in `vm.runInContext` to load `app.js` inside a
  real jsdom window so module-scope `function` declarations land in the jsdom context
  and are callable directly (e.g. `win.callChatApi()`). `fetch` is replaced with a
  per-test stub; no real network calls.

- **`package.json`** (new): dev-only manifest (`"private": true`, no `"type":"module"`)
  with `"devDependencies": { "jsdom": "^25.0.0" }`. Never ships in the running app.

- **`run-tests.sh`**: Added separate jsdom-guarded behavior-test step:
  ```
  ── JS behavior tests (jsdom, dev-only) ──────────────
    node --test tests/js/app.behavior.test.mjs  (or: ⚠ jsdom not installed — skip)
  ```
  Pure-helper unit tests now run in a separate `node --test` invocation (excluding
  `app.behavior.test.mjs`) to prevent `vm.createContext` from interfering with
  the existing `require()`-based test loader.

- **`.gitignore`**: Added `node_modules/` and `package-lock.json` (dev tooling, never tracked).

- **`backlog.md`**: Item #51 marked Done.
- **`docs/specs/frontend-behavior-tests.md`**: Status updated to Done.

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