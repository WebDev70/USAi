# Backlog

Planned improvements, ordered roughly by priority. We work through these one at
a time; each item is checked off when implemented and recorded in `CHANGELOG.md`.

## Status legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Done

> **Note on IDs:** Item numbers are **stable identifiers** (referenced in
> `CHANGELOG.md` and other docs), not sequential order. Gaps indicate items
> that were renumbered, merged, or retired; the highest-assigned ID is **39**.

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

- [ ] **35. RAIL pipeline improvements — close trust-vs-verification gaps** *(M, 5 independent phases)*
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

> ⚠️ **Parking lot — not yet refined to Definition of Ready.** Items #7–#15
> lack user stories, acceptance criteria, test plans, and size estimates. They
> must go through a Product Owner grooming pass (per
> `.continue/checks/definition-of-ready.md`) before being pulled into a sprint.

- [ ] **7. Real embeddings for RAG** *(M)*
  - Replace keyword matching with embeddings + cosine similarity for file search.
  - Files: `app.js`, possibly `server.py` (embeddings proxy/cache).
  - *depends on: nothing (but #16 embeddings-based memory search is a related
    sub-task that also depends on this)*

- [ ] **8. More file types (PDF/DOCX)** *(S–M)*
  - Extract text from PDF and DOCX uploads, not just plain text.
  - Files: `app.js` (upload handling), possibly a parser library.

- [ ] **9. Streaming + tool calling together** *(M)*
  - Accumulate `delta.tool_calls` fragments so tool mode can stream.
  - Files: `app.js` (`streamChatApi`, `runWithTools`).
  - *related to: #11 (both touch the streaming path)*

- [ ] **10. Export / import conversations** *(S)*
  - Download a session as JSON/Markdown; re-import later.
  - Files: `app.js`, possibly `server.py`.

- [ ] **11. Reasoning / thinking display** *(S–M)*
  - Show reasoning-model thinking content in a collapsible block.
  - Files: `app.js`, `styles.css`.
  - *related to: #9 (both touch the streaming path)*

- [ ] **12. Prompt templates / saved system prompts** *(S)*
  - A small library of reusable system prompts.
  - Files: `app.js`, `index.html`, `styles.css`.

### Larger / later

> ⚠️ **Parking lot — not yet refined to Definition of Ready** (same note as
> above applies; #27 is the exception — it is fully groomed).

- [ ] **13. Custom user-defined tools** *(L)*
  - Let users register their own tool definitions.

- [ ] **14. Model comparison (side-by-side)** *(L)*

- [ ] **15. Voice input / TTS output** *(L)*

- [ ] **27. Projects (ChatGPT-style workspaces) — group chats + shared instructions, files & memory scope** *(L)*
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
    - **Slice 2 — Project instructions:** 3-layer system-prompt concatenation,
      applied in message-build + regenerate/edit/restore.
    - **Slice 3 — Memory modes:** Default (dual-read global+project) vs
      Project-only (isolated + excluded from global), immutable, server-enforced.
    - **Slice 4 (defer):** Project files (shared knowledge) via `projectChunks`.
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
> accepts for each tier (candidates from `index.html`: high=`claude_opus_4`,
> medium=`claude_sonnet_4`, low=`claude_3_haiku`).
>
> Reality check (from Continue docs / Context7): Continue assigns models to fixed
> **roles** (`chat`/`edit`/`apply`/`autocomplete`/`embed`/`rerank`), **not** to our
> custom pipeline agents. There is no built-in automatic per-agent model selection,
> so the dev-workflow side (#18) is *guided* (tiers + manual dropdown switch); the
> truly *automatic* router belongs in the app (#19).

> ⚠️ **Needs grooming:** #18 and #19 have solid descriptions and file lists but
> lack explicit acceptance criteria in the standard AC format. Complete an AC
> pass before pulling into a sprint.

- [ ] **18. Continue dev-workflow model tiers (guided)** *(S)*
  - Define three model tiers in a Continue `config.yaml` so the RAIL roles
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

- [ ] **19. USAi web-app automatic model router** *(M)*
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

---

## Completed / Archive

### Testing & agent automation

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

- [~] **16. Obsidian long-term memory (second brain)**
  - Use an Obsidian vault as persistent long-term memory so the assistant can
    recall facts/preferences/decisions across conversations.
  - *depends on: #7 (for sub-task: embeddings-based memory search)*
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
    - [ ] Embeddings-based memory search — *depends on #7*
  - Files: `server.py`, `app.js`, `index.html`, `styles.css`.

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

- [ ] **40. Obsidian "User Summaries" section — human-readable plain-English summaries of key project concepts** *(S)*
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

- [ ] **28. Pre-commit git hook for test/syntax gates** *(S)*
  - Add an optional `pre-commit` hook (`.git/hooks/pre-commit`) that runs
    `node --check app.js` and `python3 -m py_compile server.py` (and optionally
    the fast unit tests) before each commit, catching syntax errors locally.
    Document the manual install step in `README.md` or `AGENTS.md`.
  - *Deferred from #17 rollout; low priority given CI already covers this.*
