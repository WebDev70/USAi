# Backlog

Planned improvements, ordered roughly by priority. We work through these one at
a time; each item is checked off when implemented and recorded in `CHANGELOG.md`.

## Status legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Done

> **Note on IDs:** Item numbers are **stable identifiers** (referenced in
> `CHANGELOG.md` and other docs), not sequential order. Gaps indicate items
> that were renumbered, merged, or retired; the highest-assigned ID is **95**.
>
> Before assigning a new ID, confirm the current maximum (see #85):
> ```bash
> grep -oE '^- \[.\] +\*\*[0-9]+\.' backlog.md | grep -oE '[0-9]+' | sort -n | tail -3
> ```

> **Last groomed:** 2026-09-18 — full grooming pass. Verified #77 complete
> (proxy suite runs clean in isolation, 26 tests OK); flipped to Done.
> Wrote explicit acceptance criteria for #79/#82/#83/#84/#85. Flagged #67, #68,
> #86, #13, #14, #15 and #57 as **not yet DoR**, each with its specific open
> design questions. #76 re-scoped against a measured working tree; steps (b)–(f)
> executed, only (a) "commit the shipped work" remains. Roo/Zoo experiment kept
> and tracked as **#86** (branch `feat/zoo-migration`), not deleted.
> Recommended near-term order:
> #76 → #74 → #85 → #79 → (#82, #83, #84) → (#70, #71, #68) → #67.
> Mirror: `Cline/scrum/product-backlog.md` in the Obsidian vault.
>
> **Second-pass verification (same day):** cloned `main` HEAD to a scratch dir and
> ran the gates there rather than in the working tree. **`main` is red:**
> `./run-tests.sh` exits 1 (21 failures / 11 errors) and `./scripts/quality-gate.sh`
> exits 1 (missing `docs/quality/review-checks/` manifest). #76 is therefore
> **BLOCKING, not advisory** — the uncommitted tree is load-bearing, not cosmetic.
> #74 is now explicitly **blocked by #76(a)** (its measured coverage includes two
> untracked test files). Also fixed a dangling `implementation_plan.md` reference in
> `docs/specs/obsidian-mcp-bridge.md` that #76(d)'s deletion orphaned.

---

## Project organization (do first)

- [x] **30. Deeper doc split — three-concern documentation refactor** *(M)*
  - **Done (2026-06-23):**
    - [x] `docs/testing-and-agents-strategy.md` renamed → `docs/rail-pipeline.md`
      (harness-agnostic RAIL concept + testing strategy).
    - [x] `docs/tooling/continue.md` created — Continue-only reference
      (`.continue/` layout, `/check`, `cli-check.sh`, agents, MCP setup).
    - [x] `docs/tooling/cline.md` created — Cline-only reference
      (`.clinerules/` layout, workflows, `/spec`→`/loop` flow).
    - [x] Cross-references updated across all files: `AGENTS.md`, `README.md`,
      `docs/ORGANIZATION.md`, `docs/principles.md`, `.continue/rules/CONTINUE.md`,
      `.continue/rules/testing-standards.md`, `.continue/rules/tdd-workflow.md`,
      `.continue/rules/continuous-improvement.md`, `.continue/rules/agile-workflow.md`,
      `.continue/checks/test-coverage.md`, `.clinerules/rail-pipeline.md`,
      `run-tests.sh`, `scripts/cli-check.sh`.
    - [x] `docs/ORGANIZATION.md` "What's not here" section removed (it's done);
      table of files and harness descriptions updated.

---

## Security (do first)

- [x] **26. RAIL → top-tier Agile + DevSecOps + IaC pipeline**
  - Elevate the RAIL agent pipeline so security and infrastructure are
    **machine-enforced gates**, not prose, and add Agile/Product-Owner rigor.
  - **Done:**
    - [x] `docs/principles.md` — reframes "zero runtime deps" as **minimal,
      audited runtime surface** (RUNTIME vs DEV/CI litmus) + DevSecOps/IaC/Agile.
    - [x] DevSecOps: `scripts/security-scan.sh` (gitleaks/bandit/pip-audit), CI
      `security` job, SSRF guard `is_safe_upstream_url()` (B310), new checks
      `dependency-and-supply-chain-review.md` + rule `devsecops.md`.
    - [x] IaC: `Dockerfile` + `docker-compose.yml` + `Makefile`,
      `resolve_bind_address()` (HOST/PORT), `.env.example` drift test, check
      `iac-review.md` + rule `infrastructure-as-code.md`.
    - [x] Agile/PO: rules `product-owner.md` + `agile-workflow.md`; checks
      `definition-of-ready.md`, `acceptance-criteria.md`, `definition-of-done.md`.
    - [x] Agent modes `.continue/agents/{product-owner,planner,security,improver}.yaml`;
      rule `observability.md`; `scripts/cli-check.sh` runs the security scan.
  - Files: `docs/principles.md`, `Dockerfile`, `docker-compose.yml`, `Makefile`,
    `scripts/security-scan.sh`, `server.py`, `.continue/rules/*`,
    `.continue/checks/*`, `.continue/agents/*`, `.github/workflows/tests.yml`,
    `tests/python/*`, `requirements.txt`.

- [x] **1. Fix `/config` secret exposure**
  - The `/config` endpoint returns the full `CONFIG` dict, including `api_key`
    and `context7_api_key`, to the browser. Return only non-secret fields and
    rely on the server-side proxy to inject the key.
  - Files: `server.py` (`_get_config`), `app.js` (`appConfig`, key usage).
  - Done: `/config` now returns only non-secret fields plus `has_api_key` /
    `has_context7` booleans; client sends Authorization only when the user types
    a key, otherwise the proxy injects it.

---

## Open items

### 🎯 Ready to pull next (groomed 2026-09-18)

Sprint-ready in the recommended order. Everything here passes
[`docs/quality/review-checks/definition-of-ready.md`](docs/quality/review-checks/definition-of-ready.md):
it has a bounded scope, a named file list, and testable acceptance criteria.

| # | Title | Size | Why now |
|---|-------|------|---------|
| 87 | Restore `doc-consistency-check.sh` scan scope | S | 🚨 Must be decided *before* #76(a) commits it — the working-tree guard scans 3 files instead of 15, leaving all 12 `.clinerules/*.md` unguarded, and 5 guard tests were deleted. |
| 74 | Ratchet coverage thresholds | S | Headroom re-measured; js_branch already drifted 77.75% → 75.19% unnoticed. **Do after #76(a)** — the measured numbers include two untracked test files. |
| 85 | Pre-flight backlog-ID check in `/spec` | XS | Cheapest guard; prevents the duplicate-ID bug that already happened once (#79). |
| 79 | Redact grep-output as a standing `/spec` rule | S | Same workflow file as #85 — batch the two together. |
| 82 | Project settings modal + detail-view delete | S | Unblocks #67; removes the fragile create-modal-reuse hack. |
| 83 | jsdom behavior tests for project detail view | S | Closes the DOM-coverage gap #81 shipped with. |
| 84 | Refactor `appendMessage` to a turn object | S | Retro action; 6-positional-arg signature is now the top regression source. |
| 70 | Whole-document analysis | L | Spec already written (`advanced-document-retrieval.md` §4.6–4.7). |
| 71 | Optional reranking | M | Spec already written (§4.8); verified `rerank` absent from code. |

**Not ready — needs `/spec` first:** #68 (M, schema changed under it),
#67 (L, 4 open design questions), #86 (L, new), #13 / #14 / #15 / #57 (parking lot).

**Suggested next sprint (Sprint 19):** #87 → #76 → #74 + #85 + #79 — one cohesive
"unbreak `main` and clear the governance debt" sprint, all S/XS, no app-code risk.
Note the hard ordering: **#87 gates #76(a)** (don't commit a weakened guard), and
**#76(a) gates #74** (don't ratchet coverage measured against untracked tests).
Then Sprint 20 takes the #82 / #83 / #84 detail-view cluster.

### Projects follow-up work (found 2026-09-13)

> Gaps found by reading the Projects code against the docs. None are started
> (`[ ]` = Not started). Listed highest priority first.

- [x] **61. Make project context actually load** *(S)* — Done (2026-09-15): Verified all 6 sub-items. `GET /projects/<id>` is implemented in `projects_handlers.py`. `_get_sessions` in `session_handlers.py` now includes `projectId`. `restoreSession` in `app.js` calls `loadProjectChunks`. `prepareContextMessages` and `saveMemory` are project-aware. `_put_project` now allows `memoryMode` edits.
  - A project can be created, but a chat inside it does not really pick up the
    project's files, instructions, or memory folder. Six fixes belong together:
    1. There is no `GET /projects/<id>` route on the backend, but the frontend
       `openProject` and `restoreSession` both call it.
    2. The session list response leaves out `projectId`, which the sidebar needs
       to group chats by project.
    3. `restoreSession` never calls `loadProjectChunks`, so project text is not
       loaded.
    4. `prepareContextMessages` and `saveMemory` leave out the active project ID,
       so the per-project memory folders are never used.
    5. The frontend sends `isolated` for memory mode, while the backend only
       expects the project-only value.
    6. `_put_project` ignores changes to `memoryMode`.
  - Files: `backend/projects_handlers.py`, `backend/session_handlers.py`,
    `frontend/app.js`.

- [x] **62. Documentation corrections — uploads, project icon, model IDs, env example** *(S)* — Done (2026-09-15): Verified all 4 sub-items. `USER_GUIDE.md` and `ARCHITECTURE.md` are updated. `.env.example` is correct.
  - Four places where the docs do not match the code:
    1. `docs/USER_GUIDE.md` says uploads create embeddings. They do not.
    2. `docs/ARCHITECTURE.md` documents a project icon that is never stored.
    3. `.env.example` lists `claude_3_haiku`, while newer docs use
       `claude_4_5_haiku`.
    4. `EMBED_MODEL` and `EMBED_INPUT_TYPE` are read by the server but are
       missing from `.env.example`.
  - Files: `docs/USER_GUIDE.md`, `docs/ARCHITECTURE.md`, `.env.example`.

- [x] **63. Project file UI wiring** *(M)* — Done (2026-09-15): Verified in `index.html` and `app.js` that the project files UI is correctly wired.
  - The block around `frontend/index.html` line 290 has no reachable entry
    point, and its event wiring is incomplete. Give it a way in and finish
    hooking up its controls.
  - Files: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`.

- [x] **64. Real PDF and DOCX extraction** *(M)* — Done (2026-09-15): Verified in `app.js` that `uploadProjectFile` calls `/extract-text`.
  - The UI advertises PDF and DOCX, but `uploadProjectFile` reads those binary
    files as plain text, so the stored text is garbage.
  - Files: `frontend/app.js`, `backend/projects_handlers.py`.

- [x] **65. Embeddings for project chunks** *(M)* — Done (2026-09-17): Scoped as
  an MVP covering new uploads only. `POST /generate-embeddings` generates and
  persists chunk embeddings; the Project Settings uploader calls it after
  `POST /project-files/<id>`; `getRelevantChunks` scores embedded chunks by
  cosine similarity and falls back to keyword ranking per-chunk when an
  embedding is missing or the call fails. Verified via EMB-1/EMB-3/EMB-3-negative
  Python tests and `PFU-*` JS tests (all green). Re-indexing files uploaded
  *before* this feature shipped was explicitly descoped — tracked as new item
  **#68** below.
  Spec: `docs/specs/project-chunk-embeddings.md`
  - Files: `frontend/app.js`, `backend/projects_handlers.py`,
    `backend/session_handlers.py`.

- [x]  **66. Move an existing chat into a project** *(M)* — Done (2026-09-18): `PATCH /sessions/<id>` endpoint + sidebar ⋯ context menu + move-to-project picker modal; active-session projectId/chunks re-sync on move.
       Spec: docs/specs/move-chat-into-project.md
  - Add `PATCH /sessions/<id>` endpoint (body: `{ projectId }`, validates with
    `_safe_project_id`, traversal-safe session id check). Add `do_PATCH` routing
    in `server.py`. Add "Move to project…" context-menu item on session rows with
    a project-picker overlay. On move of the active chat: update `currentProjectId`
    + reload `projectChunks`. Sidebar re-renders after any move.
  - Memory notes written before the move stay in their original vault folder
    (out-of-scope limitation; documented in USER_GUIDE).
  - Files: `backend/session_handlers.py`, `backend/server.py`,
    `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`.

- [ ] **67. Per-project model, tool, and reasoning settings** *(L)*
  - **Not yet DoR.** ⚠️ Needs `/spec` before any sprint pull: no user story, no
    acceptance criteria, no test plan. Open design questions to resolve in `/spec`:
    1. Where do overrides live — `.projects/<id>/project.json` (server-side, survives
       browsers) or `localStorage` under `usai.settings.v1` keyed by project id?
       Server-side is consistent with `instructions`/`memoryMode` already on the project.
    2. Which of the ~12 `saveSettings` keys are overridable? Recommend a *subset*
       (model/tier, temperature, maxTokens, reasoningEffort, tools, JSON mode) rather
       than all, to keep the merge surface small.
    3. Inherit-vs-override UX: a per-field "use global" tri-state, or a single
       "override global settings" checkbox per project?
    4. Interaction with #19's auto model router — does a project-pinned model win over
       `routeModel()`, or does the router win when tier is `Auto`?
  - Model choice, tool toggles, and reasoning effort are global today, saved by
    `saveSettings`. Let a project hold its own values. Projects inherit the
    global defaults unless a project overrides them.
  - **Related:** #82 (project settings modal) should land first — it replaces the
    fragile create-modal reuse this feature would otherwise have to extend.
  - Files: `frontend/app.js`, `frontend/index.html`,
    `backend/projects_handlers.py`.

- [ ] **68. Backfill embeddings for pre-existing project files** *(M)*
  - **Not yet DoR.** ⚠️ Needs `/spec` before any sprint pull: no spec doc, no
    acceptance criteria, and the detect-trigger (item 1 below) is still an open
    decision. **Recommendation for `/spec`:** an explicit "Re-index files" button in
    the project settings/detail view, *not* an implicit on-project-open scan — an
    implicit scan makes opening a project silently expensive and hard to cancel.
  - **Sequencing note (added 2026-09-18):** #69 shipped a **v2 chunk schema** with
    legacy normalization and `embedModel` stamping on `/generate-embeddings`. This
    backfill must therefore target the v2 schema and *also* re-embed chunks whose
    stored `embedModel` differs from the currently configured `EMBED_MODEL` — not
    just chunks with a missing `embedding`. That widens the original scope and is
    the main reason this needs a fresh spec rather than direct implementation.
  - Backlog #65 shipped embeddings for project chunks as an MVP scoped to
    files uploaded *after* that feature — see
    `docs/specs/project-chunk-embeddings.md` §1 "Explicitly out of scope".
    Project files uploaded *before* #65 shipped have chunk-cache entries with
    no `embedding` field and are permanently keyword-only until this item is
    done. Cover:
    1. A way to detect chunks with a missing/null `embedding` (or a stale
       `embedModel`) in an existing project's chunk cache (explicit "re-index"
       action recommended — decide in `/spec`).
    2. Call `/generate-embeddings` for those chunks without requiring the user
       to delete and re-upload the file.
    3. Avoid re-embedding chunks that already have a current `embedding` (idempotent,
       cost-aware — don't re-call the provider for chunks already done).
    4. Surface progress/failure to the user (best-effort, non-blocking, same
       graceful-fallback behavior as #65).
  - **Independent of** #69/#70/#71 (no code dependency) but should land *after* #69
    (done) so it writes the v2 schema.
  - Files: `frontend/app.js`, `backend/session_handlers.py`,
    `backend/projects_handlers.py`.

- [x] **69. Retrieval foundations — structure-aware chunking, per-chunk fallback, hybrid fusion, neighbor expansion** *(L)* — Done (2026-09-17): structure-aware chunker, v2 chunk-cache schema with legacy normalization, per-chunk semantic fallback, RRF fusion, neighbor expansion, and labelled context provenance shipped; `/generate-embeddings` now stamps `embedModel`. Spec: `docs/specs/advanced-document-retrieval.md`
  - Replace `chunkText()`'s fixed-line splitter with a structure-aware
    chunker (Markdown headings, paragraphs, fenced code blocks) that respects
    the existing 50–1000 line setting as an *upper bound*. Replace
    `getRelevantChunks()`'s all-or-nothing semantic gate (one un-embedded
    chunk currently disables semantic scoring for the whole merged set) with
    a per-chunk fallback: embedded chunks score semantically, all chunks
    score lexically, and the two rankings are combined via Reciprocal Rank
    Fusion (RRF) instead of comparing incomparable raw scores. Add neighbor
    (adjacent-chunk) expansion around top-ranked seeds. Add a versioned
    chunk-cache schema (`schemaVersion`, `ordinal`, `headingPath`,
    `previous/nextChunkId`) with in-memory normalization of legacy caches on
    read (no batch migration).
  - See full architecture, schema, algorithms, and acceptance criteria in
    the spec. Independent of #68 — see spec §1a for the relationship and
    recommended ordering (#69 → #68 → #70 → #71).
  - Files: `frontend/app.js`, `frontend/tests/js/app.test.mjs`,
    `backend/tests/python/test_server_http.py`, `docs/ARCHITECTURE.md`,
    `docs/EMBEDDINGS_GUIDE.md`.

- [ ] **70. Whole-document analysis — adaptive full-document context + hierarchical map-reduce** *(L)*
  - Depends on #69 (uses its chunk schema + neighbor links). Add prompt-budget
    estimation (character-based, no tokenizer dependency) so a document that
    fits the budget is sent to the model in full instead of being truncated
    to a retrieval excerpt. Add a conservative, regex-based whole-document
    intent classifier ("summarize this document", "review the whole file",
    etc.) that routes matching queries — when the document doesn't fit the
    budget — through a hierarchical map-reduce pipeline (batch-summarize
    structural chunks, recursively reduce, then answer) instead of hybrid
    retrieval. Narrow/ambiguous queries keep using hybrid retrieval by
    default (never auto-triggers extra model calls).
  - See `docs/specs/advanced-document-retrieval.md` §4.6–4.7 for the full
    design (budget estimation, intent detection, map/reduce algorithm,
    cancellation, progress UI).
  - **Grooming note 2026-09-18:** DoR ✅ — the spec carries the ACs, so no `/spec` pass
    is needed. Two things to re-confirm at `/build` time because #69 shipped after the
    spec was written: (a) the budget estimator must read the **v2** chunk schema, and
    (b) map-reduce issues *extra model calls*, so the spec's "never auto-triggers" rule
    is the load-bearing safety property — keep its test.
  - Files: `frontend/app.js`, `frontend/tests/js/app.test.mjs`,
    `docs/ARCHITECTURE.md`, `docs/USER_GUIDE.md`.

- [ ] **71. Optional reranking — bounded second-stage reranker over fused retrieval results** *(M)*
  - Depends on #69 (reranks its fused seed set). Add an optional
    `rerank(query, candidates, fetchFn)` hook, disabled by default, gated by
    a new `appConfig.has_rerank` flag mirroring the existing
    `has_embeddings` pattern. When configured, reorders only the bounded
    fused top-N candidates (never the full corpus) via an
    OpenAI-compatible HTTP call; falls back to the pre-rerank fused order on
    any error, timeout, or malformed response — provably zero-regression
    when unconfigured.
  - See `docs/specs/advanced-document-retrieval.md` §4.8 for the full design.
  - **Grooming note 2026-09-18:** DoR ✅ (spec carries the ACs). Verified **not started** —
    no `rerank` symbol and no `has_rerank` flag exist anywhere in `backend/` or
    `frontend/app.js`, so the premise still holds. Reminder: `has_rerank` must be added to
    `/config` as a **non-secret boolean** only (the reranker URL/key stay server-side), and
    the outbound call must pass through `is_safe_upstream_url()` like every other proxy hop.
  - Files: `frontend/app.js`, `frontend/tests/js/app.test.mjs`,
    `docs/ARCHITECTURE.md`.

- [x] **72. Fix `security-scan.sh` memory-note false positives (check 4/4)** *(XS)* — Done (2026-09-17): tightened `sk-`/Bearer/`api_key=`/`password=` patterns to require bounded secret-shaped values, redacted finding output to `path:line: [REDACTED]`, and pointed `housekeep.md` at the canonical scan. Spec: docs/specs/memory-note-secret-scan-false-positives.md
  - Discovered 2026-09-17 while closing #69. With `OBSIDIAN_VAULT_PATH` exported,
    check 4/4 fails on ~30 existing notes because the patterns
    `Bearer [A-Za-z0-9]`, `api_key\s*=`, and `password\s*=` match *prose* in the
    per-note safety checklist line ("No API keys, Bearer tokens, or passwords in
    this note") rather than any real secret. Net effect today: the check is
    effectively never green locally, which trains people to ignore it. Direct
    inspection also confirmed the `sk-[A-Za-z0-9]` pattern matches a benign
    identifier substring (`task-1234567890123456`).
  - Tighten the patterns so they require a secret-looking *value* (e.g.
    `Bearer\s+[A-Za-z0-9._-]{16,}`, `api_key\s*=\s*\S{8,}`, a bounded `sk-`
    token) while keeping the `sk-` prefix rule as-is in spirit. **Do not** simply
    drop a pattern or re-scope the directory — that would weaken the gate.
    Redact any detected value from the scanner's own diagnostic output so a real
    finding is never echoed into logs.
  - Verify by running `OBSIDIAN_VAULT_PATH=... ./scripts/security-scan.sh` and
    confirming 4/4 passes with the existing notes untouched, and still fails on a
    deliberately planted fake token.
  - Files: `scripts/security-scan.sh`, `backend/tests/python/test_scripts.py`.


### 🔧 Governance findings (Sprint 19 close — 2026-09-19)

- [x] **89. 🚨 BLOCKING — fix the `mutmut` pin and make hash verification real** *(S)* — Done (2026-09-20): corrected the `mutmut==2.5.1` digest to the only published artifact hash; `scripts/dev-deps-check.sh` now runs `pip download --no-deps --require-hashes` so a wrong/tampered digest fails the gate; restored `make dev-setup` + `make mutation`; hermetic T-6/T-7/T-8 regressions (local wheels via `PIP_NO_INDEX`/`PIP_FIND_LINKS`) added, full suite 456 tests OK, coverage/security/quality/doc gates green. Spec: `docs/specs/dev-dependency-hash-verification.md`
  - Governance report 2026-09-19 (BLOCKING-01 / SE-3). Replace the fabricated
    `mutmut==2.5.1` digest with the verified published-artifact digest; make
    `scripts/dev-deps-check.sh` execute pip's hash enforcement; restore the promised
    `make dev-setup` and `make mutation` entry points; add hermetic regression coverage.
  - Files: `requirements-dev.txt`, `scripts/dev-deps-check.sh`, `Makefile`,
    `backend/tests/python/test_dev_deps.py`, `CHANGELOG.md`.

- [ ] **90. 🚨 BLOCKING — reconcile the Done pile with the code that actually exists** *(M)*
  - Governance report 2026-09-19 (BLOCKING-02 / SBA-4, ADVISORY-04, ADVISORY-07).
    Decide implement-or-strike for #10, #11a/#11c, #12, #29, and #34 sub-claims 3/5;
    correct dependent docs; reconcile stale/orphan/missing specs; archive the oversized Done pile.
  - Needs a dedicated `/spec` because the per-claim product decisions remain open.

- [ ] **91. 📋 ADVISORY — reconcile ARCHITECTURE §3b with the live routes** *(S)*
  - Governance report 2026-09-19 (ADVISORY-01 / SA-2). Remove or annotate absent routes,
    document omitted live routes and prefix dispatch, and fix `/logs/files?file=` to `?name=`.
    Consider generating the endpoint table to prevent recurrence.

- [ ] **92. 📋 ADVISORY — enforce Mode B self-improvement in session notes** *(XS)*
  - Governance report 2026-09-19 (ADVISORY-03 / SPMS-5). Require each session note to record
    either a workflow improvement proposal or an explicit "no improvement found" outcome.

- [ ] **93. 📋 ADVISORY — stop security-scan skips reading as passes** *(XS)*
  - Governance report 2026-09-19 (ADVISORY-05/06; third consecutive audit, escalates to
    BLOCKING next audit). Use strict scanner invocation where required or make skipped
    scanners and vault checks unambiguously non-passing.

- [x] **94. 🚨 BLOCKING — project isolation leak: foreign-project files injected into a chat** *(M)* — Done (2026-09-20): hard-scoped RAG retrieval by `projectId` in `getRelevantChunks()` + `loadProjectChunks()` tagging + `resetChatContextState()` on every switch entry point; regression suite PCI-1..PCI-5 reconstructs the eOffer scenario; backend AC-6 scope test; dry-run-first `scripts/purge-orphan-test-projects.sh`. Spec: docs/specs/project-context-isolation.md
  - **Reported by user (2026-09-20), with production urgency.** Asking *"How do the
    documents in this project differ?"* inside the `EmbeddingNegTest` project returned an
    answer that cited `eOffer Data Dictionary.xlsx` / `dataDictionary.csv` — a document
    that does **not** belong to the open project. The projects feature must isolate
    context per project before it can be trusted for production use.
  - **Confirmed on-disk evidence (not speculation):**
    - The chat `session_1789910567298` ("How do the documents in this project differ?")
      is stamped `projectId = project_1789910130524933_2f6d37`.
    - Project `2f6d37` contains **only** `FSSOnline as is state.txt` +
      `FAS Cloud Services Overview.txt`. `eOffer`/`dataDictionary` is **not** in it.
    - `eOffer` actually lives in a **different** project that is *also* named
      `EmbeddingNegTest`: `project_1789778243766721_30a89f`.
    - Token accounting proves the leak: turn 1 sent **8,219 input tokens** (≈ the two
      legitimate files); turn 3 jumped to **15,934 input tokens** — a ~7,700-token
      increase that matches `eOffer`'s 32,704 chars ÷ 4 ≈ 8,176 tokens. Foreign chunks
      were physically injected into the request.
  - **Likely contributing causes to investigate (open questions for `/spec`):**
    1. **Duplicate project display names.** 156 of 537 project dirs are all named
       `EmbeddingNegTest` (leftover negative-embedding test runs). The UI/retrieval can
       pick the wrong project by name; the sidebar and `openProject()`/`restoreSession()`
       path need to key strictly on `projectId`, never on name, and the app should not
       allow silent duplicate-name collisions that mislead the user.
    2. **`loadProjectChunks()` loads *every* file in a project dir** (`app.js` ~L435–456).
       If the active `projectId` is ever wrong, or if a stale `projectChunks` array is not
       cleared on project/session switch, foreign docs enter the context window. Audit the
       clear-on-switch invariants (`openProject`, `restoreSession`, move-out-of-project at
       ~L1775) for gaps.
    3. **Retrieval selects too broadly.** Open-project chunks have `embedding: false`, so
       `getRelevantChunks()` falls back to lexical ranking with a **120,000-char**
       (`CONTEXT_CHAR_LIMIT`, `app.js` ~L3264) window that sweeps in nearly everything
       loaded. Decide whether to (a) enforce embeddings for project files, (b) tighten the
       char/`topK` budget, and/or (c) hard-scope retrieval to the *current* project's
       chunk set only.
  - **Acceptance criteria (draft — finalize in `/spec`):**
    - [ ] A chat opened inside project P can only ever retrieve/inject files that belong
          to P; a regression test asserts a second project's file is never present in the
          composed context.
    - [ ] Project selection is keyed on `projectId`; duplicate display names cannot cause
          the wrong project's chunks to load (add a test with two same-named projects).
    - [ ] `projectChunks` is provably cleared on every project switch and session restore
          (unit/jsdom test for the clear-on-switch invariant).
    - [ ] Housekeeping: a documented, safe way to purge the 156 orphaned `EmbeddingNegTest`
          test projects (script or maintenance endpoint), leaving real projects intact.
    - [ ] Backend `/chunk-cache?projectId=` path-traversal + cross-project read guards
          re-verified (they exist for storage; confirm the read/list path is equally scoped).
  - **Needs a dedicated `/spec`** — the isolation model and the cleanup decision are open.
  - **Priority:** ahead of #90 per user request ("addressed immediately after" the current
    push). Recommend sequencing: publish `45dd1ae` → `/spec` #94 → then resume #90.

- [x] **95. 📋 ADVISORY — small default `max_tokens` truncates answers / clarify the cap** *(XS)* — Done (2026-09-20): Placeholder, label badge, tooltip, and USER_GUIDE.md updated to say "blank = model default (recommended)"; pure helper `shouldSendMaxTokens` extracted and exported; MT-1..MT-5 green.
       Spec: docs/specs/max-tokens-clarify-cap.md
  - **Reported by user (2026-09-20):** LLM responses felt "so small." Investigation: we do
    **not** hard-cap output — the frontend only sends `max_tokens` when the user sets it
    (`app.js` ~L3699–3703), and that value is the ceiling. Observed answers were 452 and
    323 output tokens, consistent with a low **Max tokens** setting. The `index.html`
    field (~L108) uses `placeholder="e.g. 512 (or leave blank)"`, which nudges users to a
    small value.
  - **Acceptance criteria (draft):**
    - [ ] Confirm/document that leaving Max tokens blank omits the cap (models use their
          own default); surface this clearly in the UI/USER_GUIDE.
    - [ ] Reconsider the `512` placeholder / default so it does not steer users into
          truncated answers (e.g. blank-by-default or a larger suggested value).
    - [ ] No behavior regression for reasoning models that reject `max_tokens`
          (existing `max_completion_tokens` exclusion logic must remain intact).

### 🔧 Governance findings (Sprint 16 close — 2026-09-18)

> Items below were identified by the Sprint 16 belated Governance Board audit.
> Evidence snapshot includes Sprint 17 state (both sprints closed same day).

> No items are blocking. See full report:
> `Cline/scrum/governance/2026-09-18-090116-governance-report.md`

- [x]  **73. Fix ARCHITECTURE.md drift: `/projects/<id>` path form + file_parser module** *(XS)*
  — **Done (2026-09-18):** §3a inline comments + §4 cascade-delete header updated from
  query-param form to path-style `/projects/<id>`; §3b DELETE row updated; §8 "6 focused"
  → "7 focused"; `file_parser_handlers.py` / `FileParserHandlerMixin` row added to module
  table and MRO block. Spec: (governance ADVISORY-01 — no separate spec doc).
  - Files: `docs/ARCHITECTURE.md`, `CHANGELOG.md`.

- [x]  **74. Ratchet coverage thresholds + add self-advancement guard** *(S)*
  — **Done (2026-09-19):** raised Python branch 80→90 and JS branch 70→75
  (Python line remains 90) across local, committed, and CI gates; added a
  non-failing advisory at ≥5 points of threshold headroom plus regression tests.
  Spec: `docs/specs/coverage-ratchet.md`.
  — 📋 ADVISORY-02 (gov 2026-09-18). `.coverage-thresholds` had never been
  ratcheted since creation (`bfd1f91`). **Live numbers re-measured 2026-09-18
  during the grooming pass** (`./run-tests.sh --coverage`, exit 0):

  | Metric | Live | Committed gate | Headroom | Proposed new gate |
  |--------|------|----------------|----------|-------------------|
  | `python_line` | 90% | 90 | 0 | **90** (leave — no headroom) |
  | `python_branch` | 92.31% | 80 | +12.31 | **90** |
  | `js_branch` | 75.19% | 70 | +5.19 | **75** |

  Note the live js_branch figure has *drifted down* since the Sprint 16 audit
  (77.75% → 75.19%), which is exactly the regression an un-ratcheted gate hides:
  a 7.75-point cushion absorbed a 2.5-point drop silently. Ratchet to 75 to lock
  in the current level, and leave `python_line` at 90 (it is exactly at the gate,
  so raising it would fail immediately — that is the correct, honest state).
  Add a `/loop` reminder or optional CI guard (INNOV-03) to prevent the gap recurring.
  - **Acceptance criteria:**
    1. `.coverage-thresholds` sets `python_branch=90` and `js_branch=75`; `python_line`
       unchanged at 90.
    2. `./run-tests.sh --coverage` still passes with the raised gates.
    3. A ratchet reminder exists in `.clinerules/workflows/loop.md` done-criteria, OR
       `scripts/ratchet-check.sh` gains an advisory "headroom ≥ 5 pts — consider
       ratcheting" warning that does not fail the build.
  - **Sequencing dependency resolved:** #76(a) was committed at `3131df5` and the
    clean-checkout coverage was reverified before these floors were raised.
  - Files: `.coverage-thresholds`, `run-tests.sh`, `.github/workflows/tests.yml`,
    `scripts/ratchet-check.sh`, `backend/tests/python/test_scripts.py`, `CHANGELOG.md`.

- [x]  **75. Document #69 retrieval features in USER_GUIDE.md** *(XS)*
  — **Done (2026-09-18):** Added "How retrieval works" subsection to §7 of
  `docs/USER_GUIDE.md` covering structure-aware chunking, hybrid lexical+semantic
  retrieval via Reciprocal Rank Fusion, per-chunk semantic fallback, neighbour expansion,
  chunk-citation provenance labels, and chunk-size as an upper bound. Spec: (governance
  ADVISORY-03 — no separate spec doc).
  - Files: `docs/USER_GUIDE.md`, `CHANGELOG.md`.

- [x]  **76. Working-tree hygiene: commit/segregate zoo-migration WIP; remove scratch files** *(S)* — Done (2026-09-19): committed the load-bearing Sprint 16–18 app, tests, review criteria, completed specs, and governance records to `main`; corrected the false quality-gate orchestration contract and made current-run gate evidence mandatory.
  — 📋 ADVISORY-04 (gov 2026-09-18); persisted & WORSENED at Sprint 17 audit (gov 2026-09-18-1159).
  **🚨 SEVERITY RAISED TO BLOCKING 2026-09-18 — `main` is currently broken.**
  Verified by cloning `main` HEAD (`7e25ee5`) to a scratch directory and running the gates:

  | Gate on a fresh clone of `main` | Result |
  |---|---|
  | `./run-tests.sh` | **exit 1** — `Ran 361 tests … FAILED (failures=21, errors=11)` |
  | `./scripts/quality-gate.sh` | **exit 1** — `Quality gate manifest not found at docs/quality/review-checks/README.md` |

  Root cause: this is **not** a hygiene nit — the uncommitted tree is load-bearing.
  `backend/server.py` in the working tree has `generate_embeddings()`; the *committed*
  `server.py` does not, while the *committed* `test_server_branches.py` already tests it
  (`AttributeError: module 'server' has no attribute 'generate_embeddings'`). Likewise
  `scripts/quality-gate.sh` is committed but the `docs/quality/review-checks/` manifest it
  reads is untracked. Anyone cloning this repo today gets a red build.
  **This makes (a) the highest-priority item in the backlog, ahead of everything else.**
  **Re-scoped 2026-09-18 (grooming pass).** Measured state: **69** `git status` entries
  (~47 modified/deleted tracked + ~19 untracked paths) uncommitted since 2026-09-13, mixing
  an in-flight Zoo-only migration with shipped Sprint 16/17/18 work.

  **Decision on the Roo/Zoo experiment (ADVISORY-08):** *keep and track, do not delete.*
  `plans/zoo-only-migration-plan.md` is a substantive approved architecture plan (source-of-truth
  hierarchy, canonical 7-role RAIL model, MCP migration), and `scripts/delegation-policy-check.py`
  already has a real test (`backend/tests/python/test_delegation_policy.py`). Deleting it would
  discard designed work. It is therefore promoted to its own tracked item **#86** and moved to a
  feature branch so it stops polluting `main`'s working tree.

  Remediation checklist (each independently verifiable):
  - [x] (a) Commit shipped Sprint 16/17/18 changes to `main`. Measured contents (2026-09-18):
        **52** tracked modified/deleted paths (app code, tests, docs, `.clinerules/`, `.continue/`,
        `backlog.md`, `CHANGELOG.md`, `.env.example`, `.gitignore`, `run-tests.sh`, and the
        `implementation_plan.md` deletion) plus **9** untracked paths:
        - `docs/quality/` — the review-check definitions that `docs/tooling/*.md` already references
        - six `docs/specs/*.md` for already-Done items: `advanced-document-retrieval`,
          `composer-attachment-tray`, `memory-note-secret-scan-false-positives`,
          `move-chat-into-project`, `project-chunk-embeddings`, `project-detail-view`
        - **two untracked test files** — `backend/tests/python/test_file_parser.py` (15 tests) and
          `backend/tests/python/test_migration.py` (4 tests). Verified green in isolation
          (`Ran 19 tests … OK`). These are real coverage that exists only on this machine:
          until committed, `#74`'s measured `python_line` 90% is **not reproducible from a
          fresh clone**, so (a) blocks `#74`.
  - [x] (b) Move the Zoo/Roo migration WIP to a `feat/zoo-migration` branch and track it as **#86**
        (`.roo/`, `.roomodes`, `plans/`, `scripts/find_delegations.py`,
        `scripts/delegation-policy-check.py`, `backend/tests/python/test_delegation_policy.py`).
        **Done (2026-09-18):** branch `feat/zoo-migration`, commit `08cfd61` — 26 files,
        4216 insertions, no app code touched. `main` no longer carries the WIP.
        *Side effect found and fixed:* `run-tests.sh` on `main` had been edited to invoke
        `scripts/delegation-policy-check.py`, which only exists on the branch — so `main`'s
        own test gate would have broken the moment the WIP moved. The invocation is now
        a comment pointing at #86; the `backend/*.py` glob compile (a genuine improvement
        over the hand-maintained module list) was kept.
  - [x] (c) Delete empty/scratch files: `200` (0 bytes), `delegation_report.csv` (header row only,
        no data), `docs/roo_audit_report.md`, `docs/roo_audit_report.html`. **Done (2026-09-18).**
  - [x] (d) Remove tracked scratch file `implementation_plan.md` (`git rm`; committed in `3246e2a`,
        superseded by `docs/specs/server-module-split.md`). **Done (2026-09-18).**
  - [x] (e) Reconcile `.env.example` — add `EMBED_MODEL` and `EMBED_INPUT_TYPE` (both read by
        `backend/server.py` lines 74–75 but absent from the example). **Done (2026-09-18).**
        *Note:* `DEFAULT_MODEL=claude_3_haiku` on line 8 is also stale (#62 corrected the docs but
        not this line) — fixed in the same pass.
  - [x] (f) Add `.vscode/` to `.gitignore` (editor-local, currently untracked noise).
        **Done (2026-09-18).**
  - **Verification (2026-09-19):** `quality-gate.sh` exit 0; `run-tests.sh --coverage`
    exit 0 (**431 Python tests**, server.py **94% lines / 92.31% branches**, JS branch
    **75.19%**); `doc-consistency-check.sh` exit 0; `security-scan.sh` exit 0 (Bandit,
    pip-audit, and memory scan clean; gitleaks unavailable and reported as skipped).
    A fresh-checkout gate run after the final commit verifies `main` independently of the
    original working tree.
  - Files: `200`, `delegation_report.csv`, `docs/roo_audit_report.*`,
    `implementation_plan.md`, `.env.example`, `.gitignore`, `.roo/`, `.roomodes`, `plans/`,
    `scripts/find_delegations.py`, `scripts/delegation-policy-check.py`,
    `backend/tests/python/test_delegation_policy.py`.

- [x]  **77. Verify-and-close flaky proxy test isolation (#43 reopened)** *(S)*
  — 📋 ADVISORY-05 (gov 2026-09-18); root cause FIXED at Sprint 17 audit (gov 2026-09-18-1159).
  The doc-note mitigation accepted when closing #43 was insufficient, but the structural fix
  has since landed: every proxy test class in `backend/tests/python/test_server_proxy.py` now
  carries `setUpClass`/`tearDownClass` with `dict(server.CONFIG)` save/restore, exactly as
  the advisory demanded. The Sprint 17 escalation-to-BLOCKING did NOT fire.
  **Done (2026-09-18):** Verify-and-close completed during the backlog grooming pass. Ran
  `PYTHONPATH=backend .venv/bin/python -m unittest backend.tests.python.test_server_proxy`
  in isolation → **Ran 26 tests … OK**, no `server.CONFIG` state-bleed between the 11 test
  classes. Confirmed all 11 classes carry the save/restore pair, and that
  `ProxyFirstFrameNotDroppedTests` (the Sprint 18 second-pass regression guard for the
  dropped-first-SSE-frame proxy bug that was the *real* cause of the perceived flakiness)
  is present and green. Spec `docs/specs/flakey-proxy-test-isolation.md` Status → Done.
  - Files: `backend/tests/python/test_server_proxy.py` (already fixed),
    `docs/specs/flakey-proxy-test-isolation.md` (Status: Done).

- [x]  **78. Fix `cli-check.sh --review` flag handling** *(XS)*
  — **Done (2026-09-18):** `scripts/quality-gate.sh` committed. Updated forward-looking
  QA-gate invocation instructions in `docs/tooling/cline.md`, `docs/tooling/continue.md`,
  `.clinerules/workflows/review.md`, and `.clinerules/rail-pipeline.md` from
  `./scripts/cli-check.sh --review` to `./scripts/quality-gate.sh`. `scripts/cli-check.sh`
  is preserved as a compatibility wrapper. Historical CHANGELOG entries and
  doc-drift-guard spec/test fixtures intentionally left unchanged to avoid breaking
  the mandatory-gate guard test in `test_scripts.py`. Spec: (governance ADVISORY-06 —
  no separate spec doc).
  - Files: `scripts/quality-gate.sh` (committed), `docs/tooling/cline.md`,
    `docs/tooling/continue.md`, `.clinerules/workflows/review.md`,
    `.clinerules/rail-pipeline.md`, `CHANGELOG.md`.

- [ ]  **79. Promote "redact grep-check output" to a permanent `/spec` requirement** *(S)*
  — 💡 INNOV-01 (gov 2026-09-18-1159). Sprint 17 retro + Entry 010 in self-improvement log
  identified that when writing any grep-based security check, the requirement to redact the
  matched value from diagnostic output ("A finding reports only path:line, never the matched
  value — the value is [REDACTED]") is typically only discovered mid-implementation rather than
  being written into the spec from the start. Fix: add a standing note to
  `.clinerules/workflows/spec.md` (or the security section of `docs/rail-pipeline.md`) that
  any spec for a grep-based security check must include this as an explicit AC and a
  hermetic test that confirms the matched value does NOT appear in the scanner's output.
  - **Acceptance criteria (added 2026-09-18):**
    1. `.clinerules/workflows/spec.md` contains a standing requirement that any spec for a
       grep/regex-based security check must carry a "reports `path:line` only — the matched
       value is `[REDACTED]`" acceptance criterion.
    2. The same requirement names the mandatory hermetic test: plant a fake token in a temp
       file, run the scanner, assert the scanner exits non-zero **and** that the planted
       token string is absent from stdout+stderr.
    3. The requirement is discoverable from the security section of `docs/rail-pipeline.md`
       (either inline or via an explicit cross-reference), so it applies to both harnesses.
    4. `./scripts/doc-consistency-check.sh` still passes (no stale-path/role-count/mandatory-gate
       guard regressions from the new text).
  - **Grooming note 2026-09-18:** verified not started — no `redact`/`REDACTED` text exists in
    `.clinerules/workflows/spec.md`. Batch with **#85** (same file, both XS/S doc-only edits).
  - Files: `.clinerules/workflows/spec.md` or `docs/rail-pipeline.md`, `CHANGELOG.md`.

- [ ]  **82. Dedicated project settings modal + detail-view delete** *(S)*
  — Descoped from #81 (2026-09-18). Two loose ends in the project detail view:
  1. `_showProjectSettingsModal` re-uses the **create-project** modal and swaps its
     submit handler at runtime. This is fragile (stale closures, title/button text
     patching). Replace with a dedicated `#projectSettingsModal` in `index.html`
     with its own submit handler.
  2. The detail view has no **Delete project** action (PD-7) — delete is only
     reachable from the sidebar ⋯ menu. Add a delete button that confirms and
     returns to the empty chat state.
  - **Acceptance criteria (added 2026-09-18):**
    1. `index.html` contains a dedicated `#projectSettingsModal`; `_showProjectSettingsModal`
       no longer mutates the create-project modal's title, button text, or submit handler.
    2. Saving the settings modal `PUT`s the project and re-renders the detail view with the
       new name/instructions without a page reload.
    3. The detail view has a Delete action that asks for confirmation, `DELETE`s the project,
       and lands the user on the empty chat state (never a blank canvas — the `PD-JS-6` class
       of bug).
    4. Cancelling the delete confirmation leaves the project intact.
    5. `styles.css` edited → `?v=N` bumped in `index.html` (CSS cache-bust convention).
    6. New behavior tests cover open→edit→save and open→delete→confirm;
       `./run-tests.sh --coverage` passes.
  - **Grooming note 2026-09-18:** verified `_showProjectSettingsModal` and `projectSettingsBtn`
    already exist in `frontend/app.js`, so the scope above is accurate as written.
    **Do this before #67** — #67 would otherwise have to extend the fragile modal reuse.
  - Files: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`,
    `frontend/tests/js/app.test.mjs`, `CHANGELOG.md`.

- [ ]  **83. jsdom behavior tests for the project detail view** *(S)*
  — Gap found in the Sprint 18 deep self-review (2026-09-18). `docs/specs/project-detail-view.md`
  §5 claims PD-JS-1 asserts "`showProjectDetail` renders project name in detail view"
  and PD-JS-2 asserts "＋ New chat calls blank-canvas path", but the shipped tests
  only re-implement the `sessionsByProject` grouping and `chatSessions` filter
  arithmetic — neither `showProjectDetail` nor `startNewProjectChat` is ever invoked.
  The DOM behaviour is genuinely uncovered (the `PD-JS-6` regression it hid was found
  by reading code, not by a failing test).
  Fix: add `#projectDetailView` (+ `.empty-chat-area`, `#projectDetailName`,
  `#projectDetailSessions`, `#projectNewChatBtn`) to the HTML skeleton in
  `frontend/tests/js/app.behavior.test.mjs` and add behavior tests that
  (a) `showProjectDetail` populates the name/instructions/session rows,
  (b) clicking a session row restores it and switches back to chat view,
  (c) `startNewProjectChat` leaves the empty state visible.
  - **Acceptance criteria (added 2026-09-18):**
    1. `frontend/tests/js/app.behavior.test.mjs`'s HTML skeleton gains `#projectDetailView`,
       `.empty-chat-area`, `#projectDetailName`, `#projectDetailSessions`, `#projectNewChatBtn`.
    2. A test **invokes `showProjectDetail`** (not a re-implementation of its arithmetic) and
       asserts the rendered project name and one session row appear in the DOM.
    3. A test clicks a rendered session row and asserts the view switches back to chat.
    4. A test invokes `startNewProjectChat` and asserts `.empty-chat-area` is still visible
       (the `PD-JS-6` blank-canvas regression class).
    5. `docs/specs/project-detail-view.md` §5 is corrected so its PD-JS-1/PD-JS-2 descriptions
       match what the tests actually assert.
    6. `./run-tests.sh --coverage` passes; js_branch does not regress below its (post-#74) gate.
  - Files: `frontend/tests/js/app.behavior.test.mjs`, `docs/specs/project-detail-view.md`,
    `CHANGELOG.md`.

- [ ]  **84. Refactor `appendMessage` to a turn-object signature** *(S)*
  — Carried over from the Sprint 18 retro. `appendMessage(container, text, role, note,
  images, attachments)` is at six positional parameters and every new turn-level
  feature (attachments in Sprint 18) adds another. Callers already pass `''`/`[]`
  placeholders for the middle arguments. Replace with
  `appendMessage(container, { text, role, note, images, attachments })` and update all
  call sites + `B-06`/`B-07` behavior tests.
  - **Acceptance criteria (added 2026-09-18):**
    1. `appendMessage` takes exactly two parameters: `container` and an options object.
    2. Every call site in `frontend/app.js` is updated — `grep -n 'appendMessage(' frontend/app.js`
       shows no remaining positional-placeholder call (`''`, `null`, `[]` filler args).
    3. Omitted option keys behave exactly as the old positional defaults did (no note, no
       images, no attachments) — covered by a test that passes only `{ text, role }`.
    4. `B-06`/`B-07` and the attachment tests (`AT-JS-*`) are updated and green.
    5. Pure refactor: no user-visible rendering change. `./run-tests.sh --coverage` passes with
       no js_branch regression.
  - Files: `frontend/app.js`, `frontend/tests/js/app.behavior.test.mjs`, `CHANGELOG.md`.

- [ ]  **85. Pre-flight backlog-ID check in the `/spec` workflow** *(XS)*
  — Sprint 18 assigned `#79`/`#80` to two items while `#79` was already taken by the
  INNOV-01 grep-redaction item, so the attachment tray and detail view shipped with
  wrong ids in code comments, spec titles, and the CHANGELOG (corrected 2026-09-18).
  Fix: add an explicit step to `.clinerules/workflows/spec.md` Step 3 that runs
  `grep -oE '^\- \[.\] +\*\*[0-9]+\.' backlog.md | grep -oE '[0-9]+' | sort -n | tail -3`
  and requires the new id to be strictly greater than the highest existing one.
  - **Acceptance criteria (added 2026-09-18):**
    1. `.clinerules/workflows/spec.md` Step 3 includes the max-ID command verbatim and states
       that the new id MUST be `max + 1`.
    2. The step also requires updating the "highest-assigned ID is **N**" line in
       `backlog.md`'s header note in the same turn (that line was 4 IDs stale until the
       2026-09-18 grooming pass caught it).
    3. The command is verified to work against the current `backlog.md` — it returns
       `84 / 85 / 86` today.
  - **Grooming note 2026-09-18:** the max-ID command was added to the `backlog.md` header note
    during the grooming pass, so this item now only needs to wire it into the workflow.
    Batch with **#79** (same file).
  - Files: `.clinerules/workflows/spec.md`, `CHANGELOG.md`.


- [ ]  **86. Zoo/Roo harness migration — track the untracked experiment** *(L)*
  — Promoted from #76(b) during the 2026-09-18 grooming pass. A Zoo/Roo agent-harness
  migration landed entirely untracked with no backlog item (gov 2026-09-18-1159 ADVISORY-08).
  Rather than delete it, this item tracks it as real work: `plans/zoo-only-migration-plan.md`
  is an approved architecture plan (Status: "Architecture approved for implementation handoff")
  and `scripts/delegation-policy-check.py` already has a passing test.
  - **Not yet DoR.** ⚠️ Needs `/spec` before any sprint pull: no user story, no acceptance
    criteria, no size validation, and one unresolved design conflict called out in the plan
    itself — the plan adopts a **7-role (0–6)** canonical RAIL model, which `docs/rail-pipeline.md`
    and `scripts/doc-consistency-check.sh`'s role-count guard (#58) must agree on before any
    doc edits land, or the guard will fail.
  - Inventory to bring under version control (currently untracked on `main`):
    `.roo/` (rules), `.roomodes`, `plans/zoo-only-migration-plan.md`,
    `plans/working-tree-stabilization-plan.md`, `scripts/find_delegations.py`,
    `scripts/delegation-policy-check.py`, `backend/tests/python/test_delegation_policy.py`.
  - Also decide: whether the Zoo harness *replaces* or *coexists with* the Cline harness —
    this determines whether `docs/ORGANIZATION.md`'s three-concern map becomes a four-concern
    map or the Cline concern is retired.
  - **Blocked-by:** #76(b) (move to `feat/zoo-migration` branch first, so `main` stays clean).
  - Files: `.roo/`, `.roomodes`, `plans/`, `scripts/find_delegations.py`,
    `scripts/delegation-policy-check.py`, `backend/tests/python/test_delegation_policy.py`,
    `docs/rail-pipeline.md`, `docs/ORGANIZATION.md`, `scripts/doc-consistency-check.sh`.

- [x]  **87. Restore `doc-consistency-check.sh` scan scope — the guard was silently narrowed** *(S)*
       — Done (2026-09-18): resolved via **option (ii)** — kept the `.roo`-aware refactor but
       restored per-guard tiered scopes so `.clinerules/` is scanned again (15 files vs 3).
       Root cause was scope *conflation*, not narrowing: the committed guard used three
       different scopes and the refactor collapsed them into one list. 6 new scope-regression
       tests added; 44 tests pass; guard PASSes with real coverage. No `CHANGELOG`-recorded
       violations remained — the "28 pre-existing violations" figure was stale (already fixed
       by earlier sessions). Spec: n/a (bugfix — RAIL role 0 skipped).
       **Follow-up 1 (2026-09-18):** `.continue/rules` added to `SCAN_DIRS` (15 → 29 files);
       12 stale paths fixed across 7 Continue rule files; stale-phrase matcher widened to catch
       slash-less `-s tests/python`; 3 new `TestContinueRulesInScanScope` tests.
       **Follow-up 2 (2026-09-18):** `docs/` tier added — `docs/quality` in `SCAN_DIRS` plus a new
       `SCAN_EXTRA_FILES` list (`README.md` + 9 top-level `docs/*.md`), taking the wide-guard scope
       29 → **49 files** and putting the canonical `docs/rail-pipeline.md` under its own rules for
       the first time. `docs/specs/` deliberately excluded as historical record (pinned by test).
       Matcher rewritten as boundary-aware EREs, fixing a false positive (`tests/js-coverage.mjs`
       flagged as stale) and a false negative (same-line stale+correct masked by `grep -vF`); both
       verified by mutation. The long-documented-but-nonexistent
       `backend/tests/python/test_env_example_sync.py` was **implemented** (AST walk of
       `os.getenv` vs `.env.example`, 4 tests) rather than the 6 references across 4 live
       policy files asserting it downgraded.
       7 new guard tests; `test_scripts.py` 48 OK; full Python suite 429 OK; JS 158 pass;
       `./run-tests.sh --coverage` PASS (ratchet: python_line 90/90, python_branch 92/80,
       js_branch 75.19/70); `./scripts/quality-gate.sh` PASS; security scan 4/4.
  — 🚨 **Found 2026-09-18 (grooming second pass). Must be resolved as part of #76(a), not after it.**
  `scripts/doc-consistency-check.sh` is a *tracked, modified* file in the working tree, so
  #76(a) would commit it as-is. Its uncommitted version **narrows the guard's own scan scope**:

  | | Committed (`7e25ee5`) | Working tree |
  |---|---|---|
  | Enforcing files scanned | **15** (`AGENTS.md` + 12 × `.clinerules/*.md` + 2 × `docs/tooling/*.md`) | **3** (`AGENTS.md` + 2 × `docs/tooling/*.md`) |
  | Scan dirs | `.clinerules`, `docs/tooling` | `.roo`, `docs/tooling` — and `.roo/` **does not exist on `main`** |
  | Guard tests in `test_scripts.py` | 30 | 32, but **5 deleted** incl. `test_exits_nonzero_when_phrase_duplicated_in_cline_rules` and `test_fails_when_stale_path_in_clinerules` |

  Demonstrated: plant a stale path *and* a missing `backend/…` reference in a
  `.clinerules/*.md` file — the committed script reports 3 errors and exits non-zero; the
  working-tree script exits **0**. All 12 live Cline rule/workflow files are currently
  unguarded.

  This is *intended* behaviour for the Zoo migration (the plan at
  `plans/zoo-only-migration-plan.md` §1.2 explicitly says "no script may consume
  `.continue` or `.clinerules`") — but that migration is parked on `feat/zoo-migration`
  as **#86**, so shipping its guard-narrowing half onto `main` leaves `main` with the
  weakened guard and none of the compensating Zoo structure. Restoring `.clinerules` to
  the scan today would surface **28** pre-existing violations, which is exactly the
  drift the guard exists to catch.

  - **Acceptance criteria:**
    1. Decide and record which of the three options applies, in `CHANGELOG.md`:
       (i) revert `scripts/doc-consistency-check.sh` + `backend/tests/python/test_scripts.py`
       to the committed versions and move the narrowing to `feat/zoo-migration`;
       (ii) keep the narrowing but add `.clinerules` back alongside `.roo` so both are
       scanned during coexistence; or (iii) accept the narrowing and open a follow-up to
       fix the 28 violations.
    2. Whichever option: the 5 deleted guard tests are either restored or explicitly
       replaced by equivalent coverage — `git diff backend/tests/python/test_scripts.py`
       shows no net loss of guard assertions.
    3. `./scripts/doc-consistency-check.sh` exits 0 and `PYTHONPATH=backend
       .venv/bin/python -m unittest backend.tests.python.test_scripts` passes.
  - **Blocks:** #76(a) — do not commit the working tree until this is decided, or the
    weakened guard ships to `main` silently.
  - **Related:** #58 (guard origin), #59 (Guard 4 / referenced-path existence), #86 (Zoo migration).
  - Files: `scripts/doc-consistency-check.sh`, `backend/tests/python/test_scripts.py`,
    `scripts/cli-check.sh` (now an 8-line wrapper → `quality-gate.sh`), `CHANGELOG.md`.


### 🔧 Governance findings (Sprint 09 close — 2026-06-26)

> Items below were identified by the inaugural Governance Board audit.

> No items are blocking. See full report:
> `Cline/scrum/governance/2026-06-26-233000-governance-report.md`

- [x] **41. Update ARCHITECTURE.md with MCP bridge endpoints + tools** *(S)* — Done (2026-06-26): Added 4 MCP endpoint rows to §3b endpoint catalog (`/mcp/vaults`, `/mcp/tool`, `/mcp/rename-tag`, `/mcp/move-note`) and 3 MCP tool rows to §4b tool registry (`obsidian_rename_tag`, `obsidian_move_note`, `obsidian_list_vaults`); updated §3a routes-dict example to include `/mcp/vaults`. Resolves ADVISORY-01 from 2026-06-26 governance audit.
       Spec: N/A (governance advisory — doc update).

- [x] **42. /spec for #19 auto model router — write ACs before Sprint 10** *(S)* — Done (2026-06-26): Wrote `docs/specs/auto-model-router.md` (Status: Ready) with user story + 8 binary ACs, full tech approach (`routeModel()`, `TIER_MAP`, settings control), 7 RM-* test cases, and risk table. Resolves ADVISORY-02 from 2026-06-26 governance audit.
       Spec: docs/specs/auto-model-router.md

- [x] **43. Fix flakey proxy test classes in combined coverage run** *(S)* — Done (2026-06-26): Added a 15-line SSL-context isolation comment block in `run-tests.sh` naming `ProxySsrfGuardTests` and `ProxyIncrementalStreamingTests` as the sensitive classes, explaining the CONFIG-pollution root cause, and documenting the two-pass `--append` workaround. Resolves ADVISORY-03 from 2026-06-26 governance audit.
       Spec: docs/specs/flakey-proxy-test-isolation.md

- [x] **44. Add `obsidian_mcp_path`/`obsidian_node_path` assertions to `LoadConfigTests`** *(XS)* — Done (2026-06-26): Added 2 assertions to `test_reads_env_and_applies_defaults` verifying both CONFIG keys load with correct defaults (`''` and `'node'`). Resolves ADVISORY-04 from 2026-06-26 governance audit.
       Spec: N/A (governance advisory — direct fix).

- [x] **54. Update `docs/ARCHITECTURE.md` for Projects v1** *(S)* — Done (2026-07-02): Added `/projects` CRUD + project-scoped `/memory/*` + `/chunk-cache?projectId` endpoint rows; new §3e (server helpers: `_safe_project_id`, `get_project_memory_dir`, `_project_memory_dirs`, `composeSystemPrompt`, cascade-delete); §4c 3-layer prompt path; §4d `projectChunks` RAG merge; §4e project-scoped memory data flow + Mermaid diagram; §4f `currentProjectId` + sectioned sidebar; §5 security table; §3a routes dict. Spec: `implementation_plan.md`.
  - `docs/ARCHITECTURE.md` is missing 10+ endpoints and features added by Projects v1 slices 1–4:
    `/projects` CRUD (GET/POST/PUT/DELETE), `instructions` field, `/project-files/<id>` CRUD,
    `projectId` param on `/memory/search`/`/memory/list`/`/memory/save`,
    `composeSystemPrompt` 3-layer prompt path, `get_project_memory_dir`/`_project_memory_dirs`
    helpers, `loadProjectFiles`/`projectChunks` RAG merge, and cascade-delete on project delete.
  - Also add prose + Mermaid description of project-scoped memory data flow
    (Default dual-read vs. Project-only isolation) to §Memory Integration (INNOV-02).
  - **Required before next sprint** (Governance BLOCKING-01, 2026-07-01 audit).
  - Files: `docs/ARCHITECTURE.md`, `CHANGELOG.md`.

- [x] **55. Create `sprint-10.md` retroactively** *(XS)* — Done (2026-07-02): Created `Cline/scrum/sprints/sprint-10.md` (Auto Model Router #19 + model-id bugfix; Goal, Backlog, Review, Retro sections; retroactive note). Sprint index already had correct row. Spec: `implementation_plan.md`.
  - `Cline/scrum/sprints/sprint-10.md` was never created. Sprint 10 shipped auto model
    router (#19) and the model-id bugfix. Create a brief, accurate sprint note to close
    the gap in the sprint audit trail.
  - Files: `Cline/scrum/sprints/sprint-10.md` (new — Obsidian vault).

- [x] **45. `server.py` module split** *(M)* — Done (2026-07-04); circular-import fix (2026-07-05): Split 1,871-line `server.py` (BLOCKING-02) into 6 focused modules using mixin classes with ZERO behavior changes. All 315 tests pass. Coverage: line 92.6% (≥90%), branch 87.5% (≥80%). Security scan: exit 0. All 6 files under 1,500 lines. `run-tests.sh` syntax gate + `scripts/security-scan.sh` bandit updated to cover all handler modules. BLOCKING-02 resolved. **2026-07-05 follow-up:** Fixed circular-import startup crash — each handler file had a top-level `import server as _server` that hit Python's partially-initialized module error; replaced with a lazy `_ServerProxy` wrapper in all 5 handler files. Added `tests/python/test_server_startup.py` subprocess regression test (316 tests total). `server.py` `__main__` now reads `HOST`/`PORT` env vars.
       Spec: docs/specs/server-module-split.md

- [x] **47. RAIL hardening Phase 2** *(M, 7 phases)* — Done (2026-06-27): Ph1 §6e cross-ref fix + §6f shift-left gate added to `review.md`; Ph2 prevention-rule recall receipts in `build.md` + `spec.md`; Ph3 spec-amendment protocol + `## Spec changelog` template section in `build.md`/`spec.md`; Ph5 clean-state guarantee in `loop.md` escalation block; Ph6 coverage ratchet self-advancement rule in `loop.md` + SE-4 in `govern.md`; Ph7 mutation-test cadence wired into `loop.md` + SE-2 in `govern.md`; bonus: `getEnabledTools` duplication fixed in `.clinerules/rail-pipeline.md` — `doc-consistency-check.sh` exits 0.
       Spec: docs/specs/rail-hardening-phase2.md

- [x] **48. Raw API response capture (non-streaming v1)** *(S)* — Done (2026-06-27): Opt-in capture of full upstream JSON envelopes (non-streaming only) to `.raw_responses/<ts>_<uid>.json`; `_capture_raw_response()` helper with rotating cap; `GET`/`DELETE /raw-responses` endpoints; `has_raw_capture` in `/config`; path-traversal guard; auth key never stored; 9 tests (RC-1…RC-8 + rotation) green; docs updated.
       Spec: docs/specs/raw-response-capture.md

- [x] **50. Log file viewer in Debug panel** *(S)* — Done (2026-06-27): `GET /logs/files` endpoint (list + read, path-traversal guard, 500-entry cap); `Log Files` tab in Debug panel with file list + clickable entry viewer; `Content-Length` fix in `_json_response()`; 4 new tests (LV-1…LV-4) green; CSS + `?v=25`; CHANGELOG updated.
       Spec: docs/specs/log-file-viewer.md

** *(S)* — Done (2026-06-27): `logs/` dir tracked (`.gitkeep` + `README.md`); `_persist_log()` helper wired into `add_log()`; opt-in via `PERSIST_LOGS=true`; per-run JSONL files with mtime-based rotation at `LOG_FILE_MAX=20`; `persist_logs` bool in `/config`; 4 new unit tests (PL-1…PL-4) green; docs updated.
       Spec: docs/specs/log-directory-persistence.md

- [x] **52. RAIL Log Analysis — Closing the Runtime→QA Loop** *(M)* — Done (2026-06-28): `scripts/analyze_logs.py` + `analyze-logs.sh` (stdlib Python, secret scrubbing, latency outlier detection, 5000-line cap); `/review` §6g advisory log gate (never blocks PASS); `/build` pre-flight step 3b log recall (informational); `/govern` SE-5 log-trend audit (recurring component errors → BLOCKING); `observability.md` extended (write AND analyze); `docs/rail-pipeline.md` §5 entry #11; `docs/USER_GUIDE.md` log analysis subsection; 8 tests AL-1…AL-8 green.
       Spec: docs/specs/rail-log-analysis.md

- [x] **48b. Raw API response capture (streaming SSE v2)** *(S)* — Done (2026-06-29): `_capture_raw_response` gains `streamed=False` kwarg; `_proxy_api` streaming branch accumulates SSE chunks into a `bytearray` (zero overhead when capture off) and writes capture file after relay ends; best-effort partial capture on client disconnect. 5 new proxy tests (RCS-1…RCS-5) + 2 additional coverage tests for non-streaming path. `server.py` 90% line / 88.8% branch ✅.
       Depends on: #48 (done). Spec: docs/specs/raw-response-capture-streaming.md

- [x] **53. Projects CRUD coverage — push server.py from 88.8% → 90% line** *(S)* — Done (2026-06-30): New test classes in `tests/python/test_server_branches.py`: `ProjectsCRUDTests` (17 HTTP integration tests for `GET/POST/PUT/DELETE /projects`); `ProjectsDirectUnitTests` (4 targeted unit tests for hard-to-reach exception-handler branches: `_safe_project_id('')` → None, corrupt JSON silently skipped, malformed PUT body → 400, corrupt session JSON during delete scan silently ignored); `RawResponsesPathTraversalDeleteTests` (DELETE `/raw-responses?id=<valid>` present/absent). Total tests raised 144 → 193. `server.py` now **90% line** ✅. Pre-existing `ProxySsrfGuardTests` errors (2 ERRORs) and `test_reasoning_fields_relayed_verbatim` FAIL confirmed pre-existing on HEAD before this change. CHANGELOG + backlog updated.

- [x] **46. Shift-left governance: add SBA/SA-lite checks to `/spec`** *(S)* — Done (2026-06-27):
  Added **Step 2b** to `.clinerules/workflows/spec.md` with three advisory checks
  (G-1 AC testability, G-2 scope/value justification, G-3 dependency coherence).
  Added **§4b** to the spec template to record findings. Updated `govern.md` cadence
  note and `docs/governance.md` "Relationship to RAIL" section with a shift-left
  vs. macro-audit split table. All findings are advisory; full `/govern` stays at
  sprint close. No app code, tests, or CSS changed.
  Spec: `docs/specs/spec-shift-left-governance.md`

### Testing strategy improvements (from QA review 2026-06-24)

- [x] **36. SSRF guard unit tests — `is_safe_upstream_url` has no dedicated test** *(S)*
  - **Finding (QA review P2):** `is_safe_upstream_url()` is referenced by `nosec B310`
    suppressions in `server.py` but has no dedicated test. The proxy integration tests
    exercise the happy path against a stub server, but no test calls the guard with
    `file://`, `gopher://`, `http://169.254.169.254` (AWS IMDS), `http://127.0.0.1`,
    or `http://[::1]`.
  - **Acceptance criteria:**
    1. A `TestIsSafeUpstreamUrl` class in `tests/python/test_server.py` covers:
       `http://` and `https://` → safe; `file://`, `gopher://`, `ftp://` → rejected;
       `http://169.254.169.254`, `http://127.0.0.1`, `http://[::1]` → rejected.
    2. `./run-tests.sh` passes; coverage gate unchanged or improved.
  - **Source:** `docs/specs/qa-testing-review.md` (Finding P2)
  - Files: `tests/python/test_server.py`.

- [x] **37. Wire JS branch-coverage ratchet sentinel** *(S)*
  - **Done (2026-06-24):** `tests/js-coverage.mjs` writes measured branch % to
    `/tmp/usai-js-branch-pct`; `run-tests.sh` reads it and passes live value to
    ratchet. T-10a/T-10b green. (`CHANGELOG.md` — RAIL Phase 7)
  - **Finding (QA review P3):** `run-tests.sh` substitutes the committed minimum
    (`$JS_MIN=70`) as the "live" JS branch % when `$JS_BRANCH_PCT` is unset.
    `tests/js-coverage.mjs` never exports the measured value, so the JS ratchet
    in `scripts/ratchet-check.sh` always compares 70 against 70 — it never detects
    a real regression.
  - **Acceptance criteria:**
    1. `tests/js-coverage.mjs` writes the measured branch % to a temp sentinel file
       (e.g., `/tmp/usai-js-branch-pct`).
    2. `run-tests.sh` reads that file and passes the actual measured value to the
       ratchet, replacing the current `JS_BRANCH_LIVE="${JS_BRANCH_PCT:-$JS_MIN}"`.
    3. `./run-tests.sh --coverage` passes; ratchet now correctly fails if the
       branch % drops below the committed threshold.
  - **Source:** `docs/specs/qa-testing-review.md` (Finding P3)
  - Files: `tests/js-coverage.mjs`, `run-tests.sh`.

- [x] **38. Proxy adversarial test cases** *(S)*
  - **Done (2026-06-24):** `ProxyAdversarialTests` class (T-11a/b/c) added to
    `tests/python/test_server_proxy.py`. `test_streaming_response_is_relayed`
    hardened against chunk0 race condition. (`CHANGELOG.md` — RAIL Phase 7)
  - **Finding (QA review P4):** The proxy test suite covers key injection, auth
    passthrough, error relay, 502/503, SSE streaming, and incremental delivery.
    Missing: malformed upstream JSON (non-streaming), header passthrough/stripping
    correctness, oversized streamed body, timeout vs. connection-refused distinction.
  - **Acceptance criteria:**
    1. A `ProxyAdversarialTests` class added to `tests/python/test_server_proxy.py`
       covers at minimum: malformed upstream JSON → proxy returns a defined status
       (not 500/crash); and the two connection-failure paths are distinct code paths.
    2. `./run-tests.sh` passes; branch coverage gate unchanged or improved.
  - **Source:** `docs/specs/qa-testing-review.md` (Finding P4)
  - Files: `tests/python/test_server_proxy.py`.

- [x] **39. Align CI Python job with `run-tests.sh --coverage` branch gate** *(S)*
  - **Done (2026-06-24):** `.github/workflows/tests.yml` Python job now runs
    `coverage run --branch`, enforces `--fail-under=90` line gate, and extracts
    branch % from `coverage json` to enforce the 80% branch gate independently.
    (`CHANGELOG.md` — RAIL Phase 7)
  - **Finding (QA review P5):** `.github/workflows/tests.yml` runs `coverage run +
    coverage report` directly — this uses the `.coveragerc` `fail_under=88` safety net
    but does NOT run the separate branch-coverage threshold (80%) that is only enforced
    by `run-tests.sh --coverage`. A branch-coverage regression passes CI but fails locally.
  - **Acceptance criteria:**
    1. The CI Python job step is updated to call `./run-tests.sh --coverage` (preferred)
       OR a dedicated CI step is added that extracts branch % from `coverage json`
       and fails if below 80%.
    2. All existing CI jobs pass on the main branch.
  - **Source:** `docs/specs/qa-testing-review.md` (Finding P5)
  - Files: `.github/workflows/tests.yml`, possibly `run-tests.sh`.

---

### RAIL pipeline hardening (highest priority)

- [x] **35. RAIL pipeline improvements — close trust-vs-verification gaps** *(M, 5 independent phases)*
  - RAIL currently relies on agent self-attestation for key quality claims (spec↔build
    compliance, TDD Red receipt, memory-note existence, doc drift, coverage depth, secret
    scanning of memory notes). This item adds machine-enforced scripts and tightens existing
    gates so those claims are actually verified, not just checked off by the agent.
  - **User story:** *As a developer using RAIL, I want automated scripts to verify that
    the spec↔build contract, coverage, documentation, and security claims are true —
    not just self-asserted — so quality gates cannot be silently skipped.*
  - **Spec:** [`docs/specs/rail-improvements.md`](docs/specs/rail-improvements.md)
  - **Phases (each ships as its own RAIL loop):**
    - [x] **Phase 1 — Verification gaps:** `scripts/spec-check.sh` (spec §3/§5 vs. git diff);
      TDD "Red receipt" instruction in `/build`; memory-note existence check in `/loop`.
      **Done (2026-06-24):** `scripts/spec-check.sh` (new, bash 3.2 compat, T-1…T-4 green);
      `tests/python/test_scripts.py` (4 tests TDD Red-first); `/review §6a` updated to use
      script; `/loop` done-criteria memory-note-exists gate added; `/build §3a` Red-receipt
      instruction added; `scripts/cli-check.sh` SPEC_FILE gate added.
    - [x] **Phase 2 — Coverage depth:** Python branch coverage (`--branch`) in
      `run-tests.sh`; branch threshold ≥ 80%; committed `.coverage-thresholds`
      ratchet guard so thresholds can only go up.
      **Done (2026-06-24):** `scripts/ratchet-check.sh` (new, bash 3.2 compat, T-9a/b/c
      green); `.coverage-thresholds` (new, py_line=90 py_branch=80 js_branch=70);
      `run-tests.sh` `--branch` + branch % gate (85.85% live, 80% threshold) +
      ratchet invocation; `.coveragerc` comment clarification; 7 new tests TDD Red-first.
    - [x] **Phase 3 — Drift/parity:** Canonical convention table in `docs/rail-pipeline.md`
      only (remove duplicates from `AGENTS.md`, `.clinerules/`, `docs/tooling/cline.md`);
      `scripts/doc-consistency-check.sh`; harness-parity table (10 checks × Cline step).
      **Done (2026-06-24):** `scripts/doc-consistency-check.sh` (new, T-6/T-7 TDD Red-first,
      3 tests green); AGENTS.md, .clinerules/rail-pipeline.md, docs/tooling/cline.md,
      docs/tooling/continue.md all deduplicated — pointer to canonical source only;
      `scripts/cli-check.sh` convention-duplication gate added; harness-parity table
      added to docs/rail-pipeline.md §3; doc-consistency-check.sh exits 0 on real repo.
    - [x] **Phase 4 — Ergonomics:** Change-type classifier in `/spec` (feature/bugfix/chore/
      docs/css) to fast-path trivial changes; escalation memory note on `/loop` timeout;
      `/self-improve` proposals wired to `backlog.md` + Obsidian.
      **Done (2026-06-24):** `.clinerules/workflows/spec.md` — mandatory Question 0 (change
      type) + role-skip mapping table + `Type:` field in spec template; `build.md` — step 5
      reads `Type:` and skips appropriate roles; `loop.md` — escalation block writes an interim
      memory note before stopping + post-loop proposals updated to dual-sink (`backlog.md` AND
      Obsidian note); `self-improve.md` — "Proposing improvements" section added requiring
      dual-sink for every structural improvement. No app code changed.
    - [x] **Phase 5 — Security depth:** Hash-pin `python-dotenv` in `requirements.txt`;
      memory-note secret scan in `scripts/security-scan.sh`; redaction reminder in
      `/loop` memory-note template.
      **Done (2026-06-24):** `requirements.txt` — pinned `python-dotenv==1.0.1` with
      sha256 hash (supply-chain integrity); `scripts/security-scan.sh` — 3-scanner
      renumbered to 4/4, new block (4/4) scans `$OBSIDIAN_VAULT_PATH/Cline/memories/`
      for secret patterns (`sk-*`, `Bearer`, `api_key=`, `password=`); skips cleanly
      when vault path unset (CI-safe); `SKIP_GITLEAKS/SKIP_BANDIT/SKIP_PIP_AUDIT`
      env-var bypass hooks added for test isolation; `loop.md` memory-note template
      gains **Memory-note safety checklist**; `review.md` gains secret-safety
      reminder after memory-note section; 4 TDD tests (T-8a–T-8d) in
      `tests/python/test_scripts.py` — all green. `server.py` — `# nosec B310`
      inline suppression on both `urlopen()` call sites (URLs are admin-configured
      `http/https`; guard documented); `security-scan.sh` now exits 0 cleanly.
  - **Anticipated files:** `scripts/spec-check.sh` (new), `scripts/doc-consistency-check.sh`
     (new), `.coverage-thresholds` (new), `run-tests.sh`, `.coveragerc`, `scripts/cli-check.sh`,
     `scripts/security-scan.sh`, `.clinerules/workflows/*.md`, `docs/rail-pipeline.md`,
     `AGENTS.md`, `.clinerules/rail-pipeline.md`, `docs/tooling/cline.md`, `requirements.txt`,
     `tests/python/test_scripts.py` (new), `CHANGELOG.md`.
  - **Done (2026-06-24):** All 5 phases shipped and verified. Spec `docs/specs/rail-improvements.md`
    Status: Done. All ACs (AC-1-a…AC-5-c) confirmed; `./run-tests.sh --coverage` passed;
    `./scripts/security-scan.sh` clean; CHANGELOG entries for Phases 1–5 + RAIL Phase 7
    (#36–#39) all recorded. See spec §8 for full review checklist.

---

### High value, low effort

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

- [x] **6. Edit & resend / regenerate**
  - Regenerate the last assistant turn; edit a previous user message and re-run.
  - Files: `app.js`, `styles.css`.
  - Done: per-message hover actions — "↻ Regenerate" on assistant turns and
    "✎ Edit" (inline editor) on user turns. Both truncate `conversationHistory`
    /`chatDisplayHistory` back to the chosen user turn, re-render the
    conversation, and re-send via `sendMessage()` (preserving any attached
    images). Guarded against running while a request is in flight. Buttons are
    attached in `appendMessage` paths and on history/session restore.

### Medium effort

> ✅ **Grooming status (2026-09-18):** every item in this subsection (#7–#12) is
> **Done**. The parking-lot warning that used to cover "#7–#15" now applies only
> to #13–#15 in *Larger / later* below.

- [x] **7. Real embeddings for RAG** *(M)* — Done (2026-06-26): `getRelevantChunks` now async + embedding-aware; cosine re-ranking via `/embeddings` when `EMBED_MODEL` set and `semanticSearchEnabled` toggle on; graceful keyword fallback on error/toggle-off; 5 JS tests (JS-1…JS-5) all green; coverage gates pass.
       Spec: docs/specs/embeddings-rag.md

- [x] **8. More file types (PDF/DOCX)** *(S–M)*
  - Extract text from PDF and DOCX uploads, not just plain text.
  - Files: `app.js` (upload handling), possibly a parser library.
  - **Done (2026-06-26):** `POST /extract-text` endpoint in `server.py` (`_extract_pdf_text`
    via `pypdf`, `_extract_docx_text` via stdlib `zipfile`/XML); `has_pdf` in `/config`;
    `extractTextServerSide()` in `app.js`; `.pdf`/`.docx` routing in `handleFileUpload`;
    `index.html` `accept=` extended; graceful warning for scanned/image-only PDFs; 13 Python
    tests + 6 JS tests. Gates: server.py 90% ✅, security scan clean ✅.
    Spec: `docs/specs/more-file-types.md`.

- [x] **9. Streaming + tool calling together** *(M)*
  - Accumulate `delta.tool_calls` fragments so tool mode can stream.
  - Files: `app.js` (`streamChatApi`, `runWithTools`).
  - *related to: #11 (both touch the streaming path)*
  - **Done (2026-06-26):** `runWithTools()` in `app.js` refactored to accept
    injected `callFn`/`streamFn`/`onDelta` for isolation; final answer after tool
    rounds is streamed via `streamFn` when `streamFinalAnswer=true`; abort/error
    propagation preserved across all paths including the MAX_TOOL_ROUNDS safety-net.
    `_runWithToolsTest` export added; 10 new ST-* unit tests (ST-1…ST-13) bring
    JS branch coverage to 70.56% ✅. Gates: server.py 94% ✅, security scan clean ✅.
    Spec: `docs/specs/streaming-tool-calling.md`.

- [x] **10. Export / import conversations** *(S)*
  - Download a session as JSON/Markdown; re-import later.
  - Files: `app.js`, possibly `server.py`.
  - **Done (2026-06-26):** Export button downloads dual-file package (`<title>.json` +
    `<title>.md` Markdown transcript); Import button file-picker → `POST /import-session`
    (≤512 KB guard, turns validation) → navigates to new session immediately. `slugify()`,
    `exportSessionData()`, `buildMarkdownExport()` added to `app.js`; `_post_import_session()`
    added to `server.py`; Export/Import buttons in `index.html` (`?v=28`); 5 JS unit tests
    (EX-1…EX-4) + 5 Python tests (T-5…T-9); `docs/USER_GUIDE.md` §8 added. Gates: server.py
    90% ✅, JS branch 71.27% ✅, security scan clean ✅.

- [x] **11. Reasoning / thinking display** *(S–M)*
  - Show reasoning-model thinking content in a collapsible block.
  - Files: `app.js`, `styles.css`.
  - *related to: #9 (both touch the streaming path)*
  - **Done (2026-06-26):** All sub-items complete.
  - **Sub-items:**
    - [x] **#11a** — Streaming SSE relay: `extractReasoningText()` + collapsible 💭 Thinking block in `app.js`/`styles.css`. Done (2026-06-26).
    - [x] **#11b** — Non-streaming path: reasoning block shown on completed non-stream responses. Done (2026-06-26).
    - [x] **#11c** — Persist + session restore: `persistExchange()` stores `reasoning` field; `restoreReasoningForTurn()` re-attaches 💭 block across `restoreSession()`, `loadChatHistory()`, `rerenderConversation()`. 77/77 JS tests ✅. Done (2026-06-26).
    - [x] **#11d** — Python proxy integration test: `ProxyReasoningStreamTests` + `_ReasoningStreamUpstreamHandler` in `tests/python/test_server_proxy.py` verifies the proxy relays `reasoning`/`reasoning_content` fields verbatim in SSE frames (T-11d-1…4). Done (2026-06-29). Spec: `docs/specs/reasoning-proxy-integration-test.md`.
    - [x] **#11e** — (included in earlier phases). Done (2026-06-26).

- [x] **12. Prompt templates / saved system prompts** *(S)* — Done (2026-06-26): Built-in + user-saveable prompt template library shipped; Templates button in UI, apply/save/delete/persist with `localStorage`; 12 PT-* tests (PT-1…PT-12); JS branch 70.95% ✅.
       Spec: docs/specs/prompt-templates.md

### Larger / later

> ⚠️ **Parking lot — not yet refined to Definition of Ready.** #13, #14, #15 and
> #57 have one-line descriptions only: no user stories, acceptance criteria, test
> plans, or validated size estimates. They must pass
> [`docs/quality/review-checks/definition-of-ready.md`](docs/quality/review-checks/definition-of-ready.md)
> via a `/spec` pass before any sprint pull. (#27 is the exception in this
> subsection — it was fully groomed and is Done.)

- [ ] **13. Custom user-defined tools** *(L)*
  - Let users register their own tool definitions.
  - **Not yet DoR.** ⚠️ Needs `/spec`. Security is the gating concern, not the UI:
    a user-supplied tool definition is an arbitrary outbound HTTP target, so this
    must go through the same SSRF guard (`is_safe_upstream_url()`) as the proxy, and
    must not become a path for exfiltrating the server-side API key. Decide in `/spec`
    whether tools are *declarative-only* (name/description/JSON-schema, executed by
    an existing allow-listed handler) or genuinely user-defined endpoints — the former
    is a far smaller and safer slice and is the recommended first cut.

- [ ] **14. Model comparison (side-by-side)** *(L)*
  - Run the same prompt against two or more models and show the responses side by side.
  - **Not yet DoR.** ⚠️ Needs `/spec`. Cost/latency multiplies by the number of panes,
    and it collides with the single-`conversationHistory` assumption throughout
    `app.js` (plus `archiveCurrentSession`, export/import, and the reasoning-block
    restore paths). Consider a read-only "compare" scratch mode that is never
    persisted as a session, as the smallest viable slice.

- [ ] **15. Voice input / TTS output** *(L)*
  - Dictate a message and have responses read aloud.
  - **Not yet DoR.** ⚠️ Needs `/spec`. Feasible with zero new runtime deps via the
    browser `SpeechRecognition` / `SpeechSynthesis` Web APIs — confirm that before
    scoping, because any cloud STT/TTS provider would instead need a new proxied
    endpoint plus a `has_*` config flag. Accessibility review (#21 axis) applies.

- [x] **27. Projects (ChatGPT-style workspaces) — Slice 1: CRUD + sidebar sections + `currentProjectId` plumbing** *(L)* — Done (2026-06-30): `/projects` GET/POST/PUT/DELETE; `_safe_project_id()` traversal guard; `_post_new_chat_session` stamps `projectId`; `currentProjectId` state in `app.js`; sectioned/collapsible sidebar (Pinned/Projects/Chats); create/rename/pin/delete project wiring; `has_projects` in `/config`; 16 integration tests + 6 JS tests green; security scan clean; USER_GUIDE §8 updated.
       Spec: docs/specs/projects-workspaces-slice1.md
  - Mirror chatgpt.com **Projects**: a named workspace that keeps **chats,
    files, custom instructions, and a memory scope** in one place. Detailed
    planning + a full critical quality review are captured in the Obsidian note
    `Continue Extension/memories/2026-06-20-223334-projects-feature-plan-and-review.md`
    — read that first to pick up where we left off.

  - **User story:** *As a USAi user, I want to organize chats into Projects —
    each with its own name, custom instructions, shared files, and a memory scope
    (shared vs. project-only) — so related work stays together and reuses
    context, with optional memory isolation.*

  - **What ChatGPT's UI does (from reference screenshots):**
    - **Create project** modal: name (+ optional emoji/icon), helper text
      ("Projects keep chats, files, and custom instructions in one place").
    - A **gear** in the create modal reveals a **Memory** mode that is
      **immutable after creation**:
      - **Default** — "Project can access memories from outside chats, and vice
        versa." (reads/writes the global memory pool).
      - **Project-only** — "Project can only access its own memories. Its
        memories are hidden from outside chats." (isolated).
    - **Project settings:** name, **Instructions** textarea, read-only Memory
      mode, **Delete project** (destructive).
    - **Context menu:** Share / Rename / Project settings / Project home /
      **Pin project** / Delete.
    - **Sidebar sections:** **Pinned**, **Projects** (collapsible, "Show more"),
      **Chats** (ungrouped).

  - **Acceptance criteria (v1):**
    1. Create a Project with a name and a **Memory mode** (Default / Project-only)
       that is **fixed at creation** (server enforces immutability).
    2. Sidebar shows **Pinned**, **Projects** (collapsible), and **Chats**
       sections.
    3. A chat started inside a Project inherits the Project's **instructions** as
       part of its system prompt.
    4. **Default** mode → memories use the global vault folder *plus* the project
       folder (both-ways); **Project-only** → memories use a project-scoped
       folder hidden from global recall.
    5. Rename, pin, open settings, and delete a Project. **Delete orphans its
       chats to "Chats" (does NOT delete them) and PRESERVES any Obsidian memory
       notes** (never destroy vault content) — decision per the review.
    6. Old sessions with no `projectId` still load and appear under **Chats**
       (backward-compatible migration).
    7. Dependency-free; secrets stay server-side; every new filesystem path
       (`projectId` in cache/memory paths) is server-generated + slugified +
       traversal-guarded.

  - **Critical-review findings to honor (see Obsidian note for full detail):**
    - **Active-chat model is a single global file** (`chat_history.json` +
      `conversationHistory`/`chatDisplayHistory`); sessions are lazy archives.
      Add first-class `currentProjectId` state and stamp `projectId` onto the
      session in **both** archive paths — JS `archiveCurrentSession()` **and**
      Python `_post_new_chat_session` (the latter archives with no project
      context today and would silently drop it).
    - **System prompt is now 3 layers:** `project.instructions` +
      (per-chat `systemPrompt` ?? `default_system_prompt`). Decided order:
      project instructions first, concatenated with `\n\n`. Applied in the
      message-build path and must survive **regenerate / edit-resend / session
      restore**.
    - **Memory modes are real merge/exclusion logic, not a path swap:**
      `get_memory_dir()` is shared by 4 endpoints + `has_obsidian` + auto-recall +
      the 💾 button. Add `get_memory_dir(project_id, mode)`; **Default** search
      must read **both** global + project folders; **Project-only** must be
      excluded from global searches. Immutability enforced server-side.
    - **Project files vs. per-chat uploads:** `fileChunks`/`uploadedFiles` reset
      on new-chat/restore/upload. Keep project chunks in a **separate**
      `projectChunks` array, loaded when a project opens, merged with per-chat
      chunks in `getRelevantChunks`/`prepareContextMessages`.
    - **Delete spans 4 stores:** `.projects/<id>.json`, sessions with that
      `projectId`, `.chunk_cache/projects/<id>/`, and
      `<vault>/.../projects/<id>/memories/` — memory notes preserved by default.
    - **Sidebar is a full `innerHTML` rebuild** (`showSessionsList`); the
      sectioned/collapsible rewrite must use semantic disclosure
      (`<details>`/`aria-expanded`) per the UI/UX rule + bump `styles.css?v=N`.

  - **Proposed storage model:**
    - `.projects/<projectId>.json` → `{id, name, icon?, instructions,
      memoryMode, pinned, createdAt}` (id generated server-side like
      `project_<timestamp>`).
    - `projectId` field added to each session JSON in `.chat_sessions/`.
    - project files → `.chunk_cache/projects/<projectId>/`.
    - project-only memories → `<vault>/<subdir>/projects/<projectId>/memories/`.

  - **Vertical slices (each runs the full RAIL loop; v1 = Slices 1–3):**
    - **Slice 1 — Projects as folders + sidebar sections + `currentProjectId`
      plumbing:** project CRUD + pin; `projectId` stamped on both archive paths;
      sectioned/collapsible sidebar (Pinned/Projects/Chats); legacy migration.
    - **[x] Slice 2 — Project instructions:** 3-layer system-prompt concatenation,
      applied in message-build + regenerate/edit/restore. — Done (2026-06-30): `composeSystemPrompt` helper prepends project instructions to per-chat prompt in all send paths; instructions field added to project CRUD; UI textarea with 8 KB cap; 12 new tests.
      Spec: docs/specs/projects-workspaces-slice2.md
     - **[x] Slice 3 — Memory modes:** Default (dual-read global+project) vs
       Project-only (isolated + excluded from global), immutable, server-enforced.
       Done (2026-07-01): `get_project_memory_dir`, `_project_memory_dirs`, scoped
       search/list/save; app.js forwards `projectId`; 8 tests MM-3…MM-8.
       Spec: docs/specs/projects-workspaces-slice3.md
     - **[x] Slice 4 — Project files:** shared knowledge per project via `projectChunks`; `.chunk_cache/projects/<id>/`; Settings modal upload/list/delete UI; merge with per-chat chunks at RAG time; cascade delete on project delete. Done (2026-07-01): 7 Python tests PF-1..PF-7 + 4 JS tests PCJ-1..PCJ-4; styles.css?v=29; index.html project files section; all 7 ACs met. Completes Projects v1. Spec: docs/specs/projects-workspaces-slice4.md
    - **Defer (polish):** Share project, emoji/icon picker, "Project home" view.

  - **Test plan (TDD-first):** projectId stamping on both archive paths; 3-layer
    prompt concat; Default dual-folder search; Project-only exclusion from global
    search; traversal guards on new project paths; legacy projectless-session
    migration; memory-mode immutability rejection on update.

  - Files (anticipated): `server.py` (`/projects` CRUD + project-aware
    `/memory/*` + `/chunk-cache` + `_post_new_chat_session`), `app.js`
    (`currentProjectId`, sidebar sections, prompt concat, `projectChunks`),
    `index.html` (create/settings modal, sidebar sections), `styles.css`
    (bump `?v=N`), `tests/python/*`, `tests/js/*`, plus docs
    (CHANGELOG/USER_GUIDE/README/CONTINUE).

### Model routing / tiering

> Use higher-reasoning models only where they pay off, and cheap/fast models for
> routine work. Two separate efforts — one for the Continue dev workflow, one for
> the USAi web app. **Prereq for both:** confirm the exact model IDs the gateway
> accepts for each tier (candidates from `index.html`: high=`claude_4_8_opus`,
> medium=`claude_4_6_sonnet`, low=`claude_4_5_haiku`).
>
> Reality check (from Continue docs / Context7): Continue assigns models to fixed
> **roles** (`chat`/`edit`/`apply`/`autocomplete`/`embed`/`rerank`), **not** to our
> custom pipeline agents. There is no built-in automatic per-agent model selection,
> so the dev-workflow side (#18) is *guided* (tiers + manual dropdown switch); the
> truly *automatic* router belongs in the app (#19).

> ⚠️ **Needs grooming:** #18 and #19 have solid descriptions and file lists but
> lack explicit acceptance criteria in the standard AC format. Complete an AC
> pass before pulling into a sprint.

- [x] **18. Continue dev-workflow model tiers (guided)** *(S)* — Done (2026-06-26): Three guided model tiers defined (`claude_4_8_opus`/`claude_4_6_sonnet`/`claude_4_5_haiku`, verified live); `docs/continue-config.sample.yaml` with YAML anchors; "Model tiers (guided)" subsection in `docs/rail-pipeline.md` §3; tier hints in all three role rules.
      Spec: docs/specs/continue-model-tiers.md

- [x] **19. USAi web-app automatic model router** *(M)* — Done (2026-06-27): `routeModel(text, opts)` pure classifier + `TIER_MAP` added to `app.js`; Router select (Off/Auto/High/Medium/Low) added to composer toolbar in `index.html` persisted under `usai.settings.v1.modelTier`; tier label surfaced in message notes (`Model: <name> (auto|manual)`) across all three send paths; 9 RM-* unit tests green (79 JS total); no new runtime deps.
       Spec: docs/specs/auto-model-router.md

---

## Completed / Archive

### Testing & agent automation

- [x] **88. `--ci-python` — reproduce the CI Python job locally** *(S)* — Done (2026-09-19):
  `run-tests.sh --ci-python` (plus `make ci-local` / `make ci-local-coverage`) hides
  `node_modules` and skips the JS suites so the Python suite is proven to pass with no
  npm packages installed, matching the GitHub Actions `python` job. Restore happens in a
  single `EXIT`/`INT`/`TERM` trap; flag parsing is order-independent and an unknown flag
  exits 2. Also fixed a latent `mktemp /tmp/coverage-XXXXXX.json` bug — BSD mktemp only
  substitutes trailing `X`s, so the literal file persisted and every *second*
  `--coverage` run failed with "File exists". 9 hermetic tests
  (`backend/tests/python/test_ci_local.py`, T-16a–T-16d) run the script against a
  throw-away tree so the suite never recurses into itself; all 5 mutants caught.
  Follow-on to #39 and the `REQUIRE_JSDOM` CI hardening in `aeadec6`.

- [x] **25. Test-Driven Development workflow + thorough QA (coverage-gated)**
  - Raise the quality bar to TDD-first with measured, **enforced** coverage —
    keeping the zero-runtime-dependency rule (coverage tooling is dev-only).
  - **Done:**
    - New always-on rule `.continue/rules/tdd-workflow.md` (Red → Green → Refactor,
      tests-first, layers, gates, definition of done).
    - **HTTP integration tests** (boot the real `ThreadingHTTPServer`, stdlib
      `urllib`): `tests/python/test_server_http.py`, `test_server_branches.py`,
      `test_server_proxy.py` (proxy + `/context7` against a fake stdlib upstream,
      incl. SSE streaming relay + 500/502/503 paths). More `server.py` unit tests
      (`_resolve_memory_file`, `add_log` rotation, `load_config`).
    - More `app.js` pure-helper tests + exports (`safeTrim`, `enforceStrictSchema`,
      `scoreChunkByKeywords`, `chunkText`, `normalizeAssistantText`); 25 JS tests.
    - Coverage gates: `.coveragerc` (`fail_under=88`, server.py at **90%**),
      `tests/js-coverage.mjs` (branch ≥ 70% of exported helpers, at **73%**),
      `run-tests.sh --coverage`, `.gitignore` for coverage artifacts.
    - CI upgraded to Node 22 + coverage gates (`.github/workflows/tests.yml`);
      `test-coverage` check tightened; docs synced (strategy doc, AGENTS.md,
      CONTINUE.md, README). 56 Python + 25 JS tests pass.
  - Files: `.continue/rules/tdd-workflow.md`, `.continue/checks/test-coverage.md`,
    `tests/python/test_server_*.py`, `tests/js/app.test.mjs`, `tests/js-coverage.mjs`,
    `.coveragerc`, `run-tests.sh`, `.github/workflows/tests.yml`, `.gitignore`,
    `docs/testing-and-agents-strategy.md`, `AGENTS.md`, `.continue/rules/CONTINUE.md`,
    `README.md`, `app.js` (exports only).

- [x] **17. Unit testing + RAIL (role-based agent pipeline)**
  - Establish a zero-new-dependency test suite and **RAIL** (*Rule-governed
    Agentic Iteration Loop*) — a Continue-native agent pipeline that automates
    planning, implementation, testing, QA review, and continuous improvement as
    we make changes.
  - **Full plan:** [`docs/testing-and-agents-strategy.md`](docs/testing-and-agents-strategy.md).
  - **Test stack (no new deps):** Python `unittest` (stdlib) for `server.py`;
    Node 18+ `node --test` for `app.js` pure functions; `node --check` /
    `python3 -m py_compile` as syntax gates. Tests live in `tests/python` and
    `tests/js`.
  - **Roles (RAIL):** Product Owner (bookends) → Code Planner → Development SME →
    Full Test Suite → QA Review → Continuous Improvement (closed loop; learnings
    recorded to Obsidian), with DevSecOps / IaC / Observability woven through.
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
    - [x] `AGENTS.md` workflow wiring (RAIL roles + run `/check`) +
      README/CONTINUE.md "Running tests" sections.
    - [x] Optional: dedicated `planner`/`improver` agent modes. **Done:** added
      `.continue/agents/{product-owner,planner,security,improver}.yaml` (backlog #26).
    - [x] CI: GitHub Actions workflow (`.github/workflows/tests.yml`) runs the
      suite on push/PR (JS via `node --test`; Python `unittest` on 3.9 + 3.11).
      A pre-commit git hook remains an optional future add (see #28).
  - *See also: #25 (which expanded coverage gates and superseded the in-progress
    parts of this item; #17 is now fully closed).*
  - Files: `docs/testing-and-agents-strategy.md`, `.continue/rules/*`,
    `.continue/checks/*`, `.continue/agents/*`, `tests/*`, `AGENTS.md`,
    `README.md`, `.continue/rules/CONTINUE.md`.

### Memory / "second brain"

- [x] **16. Obsidian long-term memory (second brain)**
  - Use an Obsidian vault as persistent long-term memory so the assistant can
    recall facts/preferences/decisions across conversations.
  - *depends on: #7 (for sub-task: embeddings-based memory search) — #7 is now Done ✅; Phase 3 embeddings sub-item is unblocked*
  - **Phase 1 (done):** direct vault file I/O in `server.py` (no MCP/Node dep).
    - `.env`: `OBSIDIAN_VAULT_PATH`, `OBSIDIAN_MEMORY_SUBDIR` (default `USAi`).
    - Memories stored as tagged, frontmatter'd Markdown in
      `<vault>/<subdir>/memories/`, writes confined to that folder (no traversal).
    - Endpoints: `GET /memory/search`, `GET /memory/list`, `GET /memory/read`,
      `POST /memory/save`. `/config` exposes `has_obsidian`.
    - Tools: `search_memory`, `save_memory` in `TOOL_REGISTRY`, gated behind a
      new **Obsidian Memory** toggle (requires Tool calling on + vault configured).
  - **Phase 2 (done):** optional `obsidian-mcp` bridge for rich tag/note
    management (rename-tag, move-note, multi-vault) and reuse with Claude Desktop.
    Done (2026-06-26): `call_obsidian_mcp()`, `_mcp_enabled()`, `MCP_TOOL_ALLOWLIST`,
    4 handler methods, 3 new routes (`/mcp/tool`, `/mcp/rename-tag`, `/mcp/move-note`,
    `/mcp/vaults`), `has_mcp_bridge` in `/config`; 3 new frontend tools
    (`obsidian_rename_tag`, `obsidian_move_note`, `obsidian_list_vaults`); 17 tests.
    Spec: `docs/specs/obsidian-mcp-bridge.md`.
  - **Phase 3:**
    - [x] Auto-recall: opt-in **Auto-recall memories** toggle injects top-N
      relevant memories before each message (in `prepareContextMessages`, like
      the file-RAG path); adds a `Memory: N note(s)` segment to the context note.
    - [x] Manual **💾 Remember** button on every message (hover) for one-click
      saves via `saveMemory` → `POST /memory/save` (tagged `manual`). Shown only
      when a vault is configured; independent of the tool/auto-recall toggles.
    - [x] Embeddings-based memory search — Done (2026-06-26): `POST /embeddings` proxy, `cosineSimilarity`, `embedTexts`, `embedMemorySearch` re-ranker; `embed_available` on `/memory/search`; `has_embeddings` on `/config`. 10 Python tests + 3 JS tests. Coverage 93%. Spec: `docs/specs/embeddings-memory-search.md`
  - **Done (2026-06-26):** All three phases complete. Phase 2 ships the obsidian-mcp
    bridge; Phase 1 + Phase 3 were shipped in prior sprints. Backlog item closed.
  - Files: `server.py`, `app.js`, `index.html`, `styles.css`, `tests/python/test_server_mcp.py`.

### Front-end design (UI/UX)

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

### Documentation

- [x] **22. Obsidian guide: how the Continue checks + rules workflow works**
  - Write a full, detailed guide (stored in the Obsidian vault under
    `Continue Extension/guides/`) explaining the RAIL agent pipeline
    (*Rule-governed Agentic Iteration Loop*) end-to-end: what
    **rules** (`.continue/rules/*`) vs **checks** (`.continue/checks/*`) are, the
    rule trigger types (Always / Auto-attached via `globs` / Agent-requested /
    Manual), how the role-based pipeline (Product Owner → Code Planner → Development
    SME → Full Test Suite → QA Review → Continuous Improvement) flows, how `/check`
    runs the gates, the UI/UX quality axis, how it ties to `AGENTS.md`, the test
    stack + `run-tests.sh`, CI, and the Obsidian memory loop. Include a concrete
    walkthrough of a real change going through the pipeline.
  - Done: wrote `Continue Extension/guides/RAIL-Pipeline-Guide.md` covering all of
    the above — Rules vs. Checks, the four rule trigger types (with which of our
    rules use each), the RAIL roles + TDD inner loop + UI/UX quality axis, the
    `/check` gates, the zero-dep test stack + `run-tests.sh` + coverage gates + CI,
    the Obsidian memory loop, and a concrete worked example (the streaming HTTP/1.1
    fix walked through the roles). Updated 2026-06-20 to match the expanded pipeline
    (Product Owner bookend + DevSecOps/IaC/Observability cross-cutting concerns).
    Marked the earlier `Agent-Pipeline-Workflow.md`
    **superseded** in place (status tag + callout linking to the new guide). The
    unblocking note below is moot — direct filesystem writes to the vault work
    reliably (the preferred path per `AGENTS.md`), so #23/#24 were not a true
    blocker.
  - Source material: `docs/testing-and-agents-strategy.md`, `AGENTS.md`,
    `.continue/rules/*`, `.continue/checks/*`.

### UI/UX polish

- [x] **80. Composer attachment tray** *(M)* — Done (2026-09-18): Attachment chip
  tray added above the composer; additive uploads; per-chip ✕ remove; PDF/DOCX routed
  through `/extract-text`; provenance record persisted on user turn; sidebar
  `#uploadedFilesDisplay` retired. `styles.css?v=32`. 11 AT-JS-* tests green
  (8 in-sprint + AT-JS-9…11 covering the shared `extractTextServerSide` helper).
  Spec: docs/specs/composer-attachment-tray.md

- [x] **81. Project detail view** *(M)* — Done (2026-09-18): Clicking a project opens
  a detail view (name, instructions, chat list, ＋ New chat, ⚙ Settings); project chats
  visible in sidebar sub-list; `GET /sessions?projectId=` backend filter (traversal-safe).
  6 PD-JS-* + 3 PD-PY-* tests green (PD-JS-6 added post-sprint for the blank-canvas
  regression in `_showChatView`). Spec: docs/specs/project-detail-view.md

- [x] **33. UI layout polish — assistant metadata below response + user bubble column layout** *(S)*
  - Two small layout improvements to match modern chat UI conventions:
    1. **Assistant metadata + Regenerate below response** — the "Context7 + Memory: …
       total tokens" note and the ↻ Regenerate button moved from a side column to
       below each assistant response (flush-left), eliminating the cramped narrow column.
    2. **User bubble vertical stack + green accent outline** — user prompt bubbles now
       stack vertically (bubble on top, ✎ Edit underneath, right-aligned) to mirror the
       assistant layout; a `var(--color-accent)` border added to distinguish user bubbles
       from the chat background in both themes.
  - Done (2026-06-23): CSS only — no JS or HTML changes.
    - `styles.css` `?v=21 → v22`: `flex-direction: column; align-items: stretch` on
      `.message-group.assistant`; `.message-note` left-aligned.
    - `styles.css` `?v=22 → v23`: `.message-group.user` switched from row to
      `flex-direction: column; align-items: flex-end`; `border: 1px solid
      var(--color-accent)` on `.message-group.user .message-bubble`.
    - `index.html` bumped to `?v=23`.
  - Files: `styles.css`, `index.html`.

- [x] **31. Sidebar collapse toggle — discoverability + persistence** *(S)*
  - The ☰ sidebar toggle lacked a tooltip and didn't remember its state across
    reloads (causing a flash of the wrong layout on page load).
  - **Acceptance criteria (met):**
    - Dynamic `aria-label` and `title` ("Collapse sidebar" / "Expand sidebar") keep the
      button self-describing.
    - Collapsed/expanded state persisted to `localStorage`; restored synchronously on
      `DOMContentLoaded` so there is no layout flash.
    - Six unit tests (T-1…T-6) cover helper behaviour, persistence, and init-time restore.
  - Done (2026-06-23): `applySidebarCollapsed()` helper (DOM-injectable, testable);
    click handler persists state; `_testInit()` restores on load; `#sidebarToggle`
    initial `aria-label` updated in `index.html`.
  - Spec: `docs/specs/sidebar-collapse-toggle.md`.
  - Files: `app.js`, `index.html`, `tests/js/app.test.mjs`.

### Documentation

- [x] **32. Architecture reference document** *(S)*
  - Added `docs/ARCHITECTURE.md` — a concise, overview-level architecture and
    engineering reference for the USAi Chat app (concern #1 only).
  - Covers: system overview, Mermaid request-flow + tool-calling diagrams, backend
    routing pattern, endpoint catalog, config loading, on-disk data stores, frontend
    tool registry, streaming paths, RAG pipeline, Obsidian memory integration, session
    management, settings persistence, Markdown rendering, security architecture,
    and infrastructure.
  - Done (2026-06-23): `docs/ARCHITECTURE.md` created; `docs/ORGANIZATION.md` updated
    (new row in file table + "Where to put new things" table); spec at
    `docs/specs/architecture-doc.md`.
  - Files: `docs/ARCHITECTURE.md` (new), `docs/specs/architecture-doc.md` (new),
    `docs/ORGANIZATION.md`.

### Tooling / environment

- [x] **34. RAIL quality-gate hardening** *(S)*
  - Five targeted improvements to tighten automated quality gates without changing any
    app behaviour:
    1. **`scripts/cli-check.sh` full 10-check gate** — added the three missing PO-gated
       check files (`definition-of-ready.md`, `acceptance-criteria.md`,
       `definition-of-done.md`) so all ten checks pass as rules to `cn review`.
    2. **`--strict` security scan in QA-gate paths** — `cli-check.sh` and `make check`
       now call `./scripts/security-scan.sh --strict`; missing scanners no longer
       silently pass.
    3. **`.env.example` drift guard extended** — added `HOST=` and `PORT=` to
       `.env.example`; extended `test_env_example_sync.py` to union env vars from
       `resolve_bind_address()` as well as `load_config()`.
    4. **CI / `make check` alignment documented** — `tests.yml` header rewritten;
       Makefile `scan` vs `scan-strict` vs `check` comments updated.
    5. **`maxTokens` input ceiling raised** — `index.html` `max` attribute bumped
       from `96768` → `131072` (128K) to cover large-output models.
  - Done (2026-06-23). Relates to #26 (which created these gates) but is a separate
    hardening pass.
  - Files: `scripts/cli-check.sh`, `scripts/security-scan.sh`, `Makefile`,
    `.env.example`, `tests/python/test_env_example_sync.py`,
    `.github/workflows/tests.yml`, `index.html`.

- [x] **23. Fix Obsidian MCP reliability (`Request timed out`, error -32001)**
  - The `obsidian-mcp` stdio server intermittently timed out. Root cause:
    **multiple stale `obsidian-mcp` processes** running at once (duplicate
    `npm exec`/`npx` launches), which contend for the same vault/stdio pipe so
    Continue's requests hang → `-32001`.
  - **Fix:** changed `.continue/mcpServers/new-mcp-server.yaml` to launch `node`
    directly against a **globally installed** obsidian-mcp
    (`npm i -g obsidian-mcp`) instead of `npx -y obsidian-mcp`. This removes the
    `npm exec` parent wrapper + per-launch package resolution that left orphans
    on MCP reload, so Continue owns exactly one cleanly-managed process at a
    stable path. Added `scripts/kill-stale-obsidian-mcp.sh` as a manual cleanup
    escape hatch, and a Troubleshooting row in `CONTINUE.md`. Verified the global
    binary boots ("Server running on stdio", all tools registered).
  - **Note:** the global build path is nvm-version-specific; switching Node
    versions requires re-running `npm i -g obsidian-mcp` and updating the path.
  - Files: `.continue/mcpServers/new-mcp-server.yaml`,
    `scripts/kill-stale-obsidian-mcp.sh` (new), `.continue/rules/CONTINUE.md`.

- [x] **24. Obsidian MCP: write timeouts (`-32001`) — Node 20 pin + single-instance ritual**
  - **Distinct from #23** (which fixed *duplicate* `npx` processes). Observed
    2026-06-17: Continue's `obsidian-mcp` requests timed out with `-32001`, most
    reliably on `create-note` **writes** (reads sometimes worked first).
  - **Root cause:** **orphaned duplicate processes** still piled up — each Continue
    reload/reset spawned a NEW obsidian-mcp process WITHOUT killing the old one
    (observed 2–3 simultaneous PIDs), and they contended for the same vault stdio
    pipe → every request hung. #23's npx→global-node change *reduced* but did not
    *eliminate* the orphaning, because Continue itself leaves old MCP children alive
    on reload/reset.
  - **Proof the server was healthy:** piping a raw JSON-RPC `initialize` (and a
    `tools/call` `create-note`) directly into the binary succeeded instantly and
    shut down cleanly — the hang only happened via Continue when duplicates existed.
  - **Fix / reliable ritual:**
    1. Pinned **Node 20 LTS** (was non-LTS v24): installed v20.20.2 + obsidian-mcp
       for v20; YAML now uses the explicit `.../v20.20.2/bin/node` binary + v20
       build path (not bare `command: node`).
    2. **kill-all → fully quit VS Code (Cmd+Q) → reopen → verify EXACTLY ONE
       process** (`ps aux | grep obsidian-mcp`). With a single clean instance,
       reads AND writes succeed.
  - **Harmless companion error:** `-32601 Method not found` at load = Continue
    probing for "resource templates"; obsidian-mcp exposes tools, not that optional
    capability. Not a fault.
  - **Fallback:** writing notes directly to the vault via the filesystem works when
    MCP is flaky (Obsidian auto-indexes them).
  - **Possible future hardening:** check whether Continue can be configured to
    terminate MCP children on reload; otherwise the kill-all ritual stands.
  - Files: `.continue/mcpServers/new-mcp-server.yaml`,
    `scripts/kill-stale-obsidian-mcp.sh`, `.continue/rules/CONTINUE.md`, `CHANGELOG.md`.

---

## Docs / DX

- [x] **40. Obsidian "User Summaries" section — human-readable plain-English summaries of key project concepts** *(S)* — Done (2026-06-26): Added `## User Summary` section to `self-improve.md` and `### User Summary (optional)` step to `spec.md` Step 4; both use `YYYY-MM-DD-<topic-slug>-user-summary.md` + `user-summary` tag + `Cline/User Summaries/` convention; non-blocking.
       Spec: docs/specs/user-summaries-workflow.md
  - The `/self-improve` session (2026-06-24) produced the first User Summary note
    (`Cline/User Summaries/2026-06-24-RAIL-Pipeline-User-Summary.md`) explaining the RAIL pipeline
    in plain English. This pattern (a dedicated `Cline/User Summaries/` folder for non-technical,
    human-readable overviews of project processes) is useful for onboarding and reference.
  - **Improvement identified:** formalize the convention so future `/self-improve` or `/spec` sessions
    automatically offer to write a User Summary alongside the technical spec or memory note.
    Add a User Summary step to `.clinerules/workflows/self-improve.md` and `.clinerules/workflows/spec.md`.
  - **Why identified:** surfaced during self-scoring of the RAIL pipeline rewrite — the human-readable
    output had clear standalone value separate from the session log.
  - Size: S

---

## Future / deferred

> **Note (not a backlog item, no ID):** Sharing and collaboration, a project
> home page, and project icons stay deferred on purpose, per
> `docs/specs/projects-workspaces-slice4.md` (around line 21). They are not new
> backlog items.

- [x] **56. Frontend/backend directory reorg** *(M)* — Done (2026-07-06): Moved Python backend files (`server.py`, `proxy_handlers.py`, `memory_handlers.py`, `session_handlers.py`, `mcp_handlers.py`, `projects_handlers.py`) into `backend/`, frontend assets (`index.html`, `app.js`, `styles.css`) into `frontend/`, and tests into `backend/tests/python/` and `frontend/tests/js/` respectively. `backend/server.py` resolves `STATIC_DIR` relative to `REPO_ROOT`; all patched files: `run-tests.sh`, `.coveragerc`, `Dockerfile`, `Makefile`, `scripts/security-scan.sh`, `scripts/cli-check.sh`. 316 tests pass; security scan clean; `GET /` returns HTTP 200. Pre-existing test failures (SSRF SSL + project sort) confirmed on HEAD~1. Spec: `implementation_plan.md`.

- [x] **58. Doc-drift guards: extend doc-consistency-check.sh with stale-path, role-count, and mandatory-gate guards** *(S)* — Done (2026-07-15): Three guards added (stale-path, role-count consistency, mandatory-gate); 7 new regression tests green; doc-consistency-check.sh exits 0 on actual repo. Spec: docs/specs/doc-drift-guards.md

- [x] **59. Referenced-path existence guard (deferred from #58)** *(S)* — Done (2026-07-15): Guard 4 added to doc-consistency-check.sh; detects stale backend/frontend/scripts/ path refs in .clinerules/ and docs/tooling/ markdown; 3 regression tests (T-14a/b/c); stale sme-backend.md ref fixed.
      Spec: docs/specs/ref-path-existence-guard.md


- [x] **60. UX & UI SME — elevate Front-End Design axis with explicit two-discipline split** *(S)* — Done (2026-07-20): Elevated the "Front-End Design (UI/UX)" quality axis into a formal UX & UI SME with separated sub-disciplines (UX: user-need framing, flow mapping, IA placement, friction audit; UI: unchanged vanilla CSS/token/WCAG/CSS-bump rules) across `.clinerules/workflows/sme-frontend.md`, `docs/rail-pipeline.md` §3, `.continue/rules/ui-ux-design.md`, and `docs/quality/review-checks/ui-ux-review.md` (3 new UX failing criteria). All AC-1…AC-6 verified present on disk.
      Spec: docs/specs/ux-ui-sme-role.md
- [ ] **57. Multi-server MCP connectors** *(L)* — Generalize `mcp_handlers.py` into a configurable connector registry that supports multiple named MCP servers, per-server tool allowlists, and CRUD management endpoints. Builds on the isolation achieved by #45.
  - ⚠️ **Parking lot — not yet DoR.** Needs `/spec`: no user story, no acceptance criteria,
    no test plan. **Grooming note 2026-09-18:** this item is *stranded* — it is the only
    `[ ]` entry inside the Completed/Archive section, so it is effectively invisible when
    picking work. It is now also listed in the consolidated parking lot in the Obsidian
    Scrum mirror. Leaving it in place (rather than moving it) to preserve the surrounding
    archive ordering, but the "Ready to pull next" table at the top of this file is the
    authoritative queue.
  - Design questions for `/spec`: per-server credentials must stay server-side (never in
    `/config`); each configured server's base URL must pass `is_safe_upstream_url()`; and
    a per-server tool allow-list has to compose with the existing `getEnabledTools()` gating
    rather than bypass it.

- [x] **29. Startup API key auth probe warning**
  - Fire a non-blocking probe at server startup that emits a loud `[WARNING]`
    log + stderr print when the configured API key is rejected (HTTP 401/403),
    so a bad/expired key is obvious immediately rather than surfacing later as a
    cryptic error in the chat UI.
  - Done: `probe_upstream_auth()` helper (SSRF-guarded, pure, unit-testable);
    `run_startup_auth_probe()` wired into `run()`; 10 unit tests (T-P1–T-P10);
    CHANGELOG + `docs/USER_GUIDE.md` (new Troubleshooting entry) updated.
  - Files: `server.py`, `tests/python/test_server.py`, `CHANGELOG.md`,
    `docs/USER_GUIDE.md`, `docs/specs/startup-auth-probe.md`.

- [x] **28. Pre-commit git hook for test/syntax gates** *(S)* — Done (2026-06-27): `make hooks` symlinks `.git/hooks/pre-commit` → `scripts/pre-commit.sh`; 6 regression tests (PC-1…PC-6) green; documented in `README.md` (Git hooks section) and `AGENTS.md`.
       Spec: docs/specs/pre-commit-hook.md

- [x] **51. Frontend behavior test layer (jsdom dev-only)** *(M)* — Done (2026-06-27): `package.json` (dev-only, no `"type":"module"`), `jsdom ^25` dev dep; `tests/js/app.behavior.test.mjs` — 15 passing tests (B-01…B-19) exercising `callChatApi`, `streamChatApi`, `appendMessage`, `saveSettings/restoreSettings`, `saveMemory`, `archiveCurrentSession`, `loadChatHistory`, and the global `unhandledrejection` handler via `vm.runInContext`; `run-tests.sh` updated with separate behavior-test step (jsdom-guarded, graceful skip); `.gitignore` adds `node_modules/` + `package-lock.json`; all 84 existing JS helper tests still green.
       Spec: docs/specs/frontend-behavior-tests.md
