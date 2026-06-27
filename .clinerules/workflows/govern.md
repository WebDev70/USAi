# Workflow: /govern
# Cline RAIL — Governance Board Audit

> **Concern: Cline dev harness** — this workflow is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Mode:** ACT MODE (or PLAN MODE for report preview before filing)

**Purpose:** Run the four Governance Board roles across the **entire USAi Chat
project** — codebase, docuWhatmentation, backlog, pipeline artifacts, and Scrum notes —
to produce a dated governance report with classified findings (BLOCKING / ADVISORY /
INNOVATION). Findings flow into `backlog.md` and the self-improvement log.

**Canonical reference:** [`docs/governance.md`](../../docs/governance.md)
**Cadence:** every sprint close (auto-triggered from `.clinerules/scrum-artifacts.md`)
OR on demand when the user types `/govern`.

---

## Pre-flight

Before starting the audit:

1. **Load context.** Read the following files completely:
   - `docs/governance.md` — role charters, rubrics, and classification rules
   - `docs/rail-pipeline.md` — pipeline to be assessed
   - `docs/principles.md` — principles the Architect audits against
   - `docs/ARCHITECTURE.md` — architecture the Architect reviews
   - `backlog.md` — the Business Analyst and Process Specialist review this
   - `CHANGELOG.md` — recent changes inform all four roles
   - `.clinerules/workflows/build.md`, `review.md`, `loop.md`, `spec.md` — process artifacts

2. **Recall prior governance.** Check for previous governance reports in the vault:
   ```
   <OBSIDIAN_VAULT_PATH>/Cline/scrum/governance/
   ```
   Load the most recent report to identify recurring findings (a finding recurring
   across two or more audits should be escalated to BLOCKING if Advisory, or
   escalated to a permanent `.clinerules/` rule if process-related).

3. **Recall sprint artifacts.** Check the current/recent sprint note:
   ```
   <OBSIDIAN_VAULT_PATH>/Cline/scrum/sprints/
   <OBSIDIAN_VAULT_PATH>/Cline/scrum/sprint-index.md
   ```

4. **Recall self-improvement log.** Read:
   ```
   <OBSIDIAN_VAULT_PATH>/Cline/memories/self-improvement-log.md
   ```
   Note any recurring mistakes relevant to the audit dimensions.

---

## Role 1 — Senior Business Analyst (SBA)

**Charter:** Are we building the *right* thing in the *right* order?

Walk through each item in the rubric. Score 1–5 and record a brief finding for each:

### SBA-1: Backlog grooming completeness
- Open `backlog.md`. For every open (non-done) item: does it have a user story + testable acceptance criteria?
- Note any items in the "Medium effort / Larger / later" sections still in the parking lot without AC.
- **Pass bar:** ≥ 80% of open active items have explicit AC.

### SBA-2: Priority ordering by business value
- Are the top 3–5 open items the highest-value items for current users?
- Is there scope creep (items that add complexity without clear user value)?
- Is there gold-plating (over-engineering a feature beyond what users need)?

### SBA-3: Acceptance criteria testability
- Sample 3–5 open items' AC at random. Are each AC binary (pass/fail)?
- Are ACs observable by test or demonstrable in the running app?
- Flag any AC that is vague ("improve performance", "feels better") — rewrite as testable.

### SBA-4: User Guide accuracy
- Scan `docs/USER_GUIDE.md`. Does every documented feature exist and work as described?
- Are any recently shipped features (from CHANGELOG) missing from the guide?

### SBA-5: Roadmap coherence
- Does the backlog tell a coherent product story? Are features sequenced sensibly?
- Are there dependency gaps (a later feature assumes an earlier one that's not done)?
- Are there duplications (two items that solve the same user problem)?

**SBA output:** Score table + list of findings with classification (🚨 / 📋 / 💡).

---

## Role 2 — Senior Architect (SA)

**Charter:** Is the technical architecture sound and forward-ready?

### SA-1: Architecture accuracy
- Read `docs/ARCHITECTURE.md`. Spot-check the component map against `server.py` (endpoint catalog), `app.js` (tool registry, key helpers), and `Dockerfile`.
- Are there recent additions (from CHANGELOG) not reflected in the architecture doc?
- Are the data-store descriptions (`.chat_sessions/`, `.chunk_cache/`, memory paths) current?

### SA-2: Principle adherence
- Read `docs/principles.md` §1–4. For each principle:
  - **Minimal runtime surface:** check `requirements.txt` — are all runtime deps still the minimum necessary? Are they all pinned with hashes?
  - **DevSecOps:** is `scripts/security-scan.sh` complete and passing? Are all CI jobs aligned with local gates?
  - **IaC:** does `Dockerfile`/`docker-compose.yml`/`Makefile` fully describe the environment? Is `.env.example` in sync?
  - **Agile:** are Product Owner gates being applied at sprint boundaries?

### SA-3: Design consistency
- Scan `server.py` for new endpoints added since the last audit. Do they follow the `_handler` + `routes` dict pattern? Do they all use the SSRF guard and path-traversal guard?
- Scan `app.js` for new tools. Are they in `TOOL_REGISTRY` and gated by `getEnabledTools()`?
- Are there any hardcoded host/port/paths that should be config?

### SA-4: Dependency hygiene
- All entries in `requirements.txt`: are they justified, pinned, and hash-verified?
- No new entries in `package.json` or `node_modules` (there shouldn't be any — this project has no package.json). Flag if found.
- Any unjustified runtime dep? Flag immediately as 🚨 BLOCKING.

### SA-5: Forward readiness
- Review the top 3 upcoming backlog items (by priority). Can they be implemented without major structural rework?
- Is `server.py` growing monolithically? At what point would it benefit from module splitting (without adding runtime deps)?
- Flag any forward-compatibility risks as ADVISORY items for the backlog.

**SA output:** Score table + list of findings with classification (🚨 / 📋 / 💡).

---

## Role 3 — Senior Engineer (SE)

**Charter:** Is the codebase high quality, and are there innovation opportunities?

### SE-1: Code quality
- Scan `server.py` and `app.js` for:
  - Functions longer than ~60 lines (candidates for extraction)
  - Comments that only say *what* (not *why*)
  - Duplicated logic (DRY violations)
  - Error handling gaps (bare `except Exception`, swallowed errors)
  - Inconsistent naming conventions

### SE-2: Test quality
- Open `tests/python/` and `tests/js/`. Scan for:
  - Tests with no assertions or trivially passing assertions
  - Missing tests for recently added endpoints/helpers (cross-check with CHANGELOG)
  - Tests that test implementation detail rather than behavior
  - Integration tests that make live network calls (should be zero)
- Check `.coverage-thresholds` — are the thresholds higher than they were 2 audits ago (ratcheting)?

### SE-3: Security pattern consistency
- Every endpoint added since last audit: does it use `get_memory_dir` path-traversal guard (for FS endpoints) and `is_safe_upstream_url` (for proxy endpoints)?
- Does `/config` still expose only non-secret fields + `has_*` booleans? (Run a quick mental check against any recent `server.py` changes.)
- Are there any new `console.log()` calls in `app.js` that might echo sensitive data?
- Any new `add_log()` calls in `server.py` that log tokens, keys, or vault contents?

### SE-4: Coverage gate trajectory
- Read `.coverage-thresholds`. Compare `py_line`, `py_branch`, `js_branch` to prior audit (from governance report or sprint note).
- Are any gates stagnant at the minimum for 2+ audits? Recommend a ratchet bump.
- Are any gates at risk of regression (close to the threshold)?

### SE-5: Innovation opportunities
- Identify 1–3 concrete, low-risk innovation opportunities within project constraints:
  - Modern vanilla CSS (container queries, `:has()`, `color-mix()`, View Transitions)?
  - Python 3.11+ features (`tomllib`, `ExceptionGroup`, improved `match`)?
  - Modern JS patterns (`structuredClone`, `ReadableStream`, `Promise.withResolvers`)?
  - Testing improvements (`node --test` snapshot testing, `unittest.mock` coverage)?
  - Developer experience (faster test feedback, better error messages)?
- Each opportunity: concrete, filtered through the runtime-surface rule, sized S/M/L.

**SE output:** Score table + list of findings with classification (🚨 / 📋 / 💡).

---

## Role 4 — Senior Process Management Specialist (SPMS)

**Charter:** Is the development process sound and maturing?

### SPMS-1: RAIL pipeline discipline
- Review the last 2–3 sprint notes in `Cline/scrum/sprints/`. Were:
  - TDD Red receipts recorded in memory notes before production code?
  - Memory notes written at session end?
  - `/review` run before declaring done?
  - Security scans clean at sprint close?
- Note any recurring skips — these are BLOCKING if a pattern (2+ occurrences).

### SPMS-2: Scrum artifact completeness
- `Cline/scrum/sprint-index.md` — is it current (most recent sprint has its end date, velocity, and outcome filled)?
- `Cline/scrum/sprints/` — do all completed sprints have Review + Retrospective sections?
- `Cline/scrum/product-backlog.md` — does it match the open/done items in `backlog.md`?
- `Cline/scrum/definition-of-ready.md` and `definition-of-done.md` — are they current (match the live RAIL criteria)?

### SPMS-3: Backlog health
- Count open vs. done items. Is the backlog growing faster than it's being resolved?
- Are there items in the parking lot (no AC, no size) that have been sitting for > 2 sprints?
- Are the top priority items DoR-compliant (ready to pull into a sprint)?

### SPMS-4: Workflow clarity
- Scan `.clinerules/workflows/spec.md`, `build.md`, `review.md`, `loop.md`.
- Are any instructions ambiguous or contradictory?
- Are there gaps exposed by recent sprint retros that haven't been fixed in the workflow files?
- Is the dispatch table in `build.md` (frontend/backend SME routing) clear and complete?

### SPMS-5: Self-improvement effectiveness
- Read `Cline/memories/self-improvement-log.md`.
- **Mistake-driven track:** Count entries added since the last audit. Is the log growing?
  Are any prevention rules reflected as actual `.clinerules/` changes?
  Are there recurring mistake patterns (same root cause in 2+ entries) not yet promoted to a permanent rule?
- **Proactive/efficiency-driven track (Mode B):** For each session memory note written since the last audit,
  check whether it records either a workflow proposal or an explicit "no improvement found" note.
  - If session notes lack any Mode B outcome → flag as ADVISORY (the process is being silently skipped).
  - Are workflow improvement proposals accumulating in `backlog.md` or `Cline/memories/` without being acted on?
    If a proposal has sat unresolved for 2+ audits → escalate to BLOCKING.
- **Workflow evolution:** Have any `.clinerules/workflows/*.md` files been updated to reflect
  lessons from the self-improvement log or Mode B proposals? A stagnant workflow file is a signal.

**SPMS output:** Score table + list of findings with classification (🚨 / 📋 / 💡).

---

## Synthesis — compile the governance report

After all four roles complete their review, compile the findings into a governance report:

### Report structure

```markdown
# Governance Report — YYYY-MM-DD

**Sprint:** Sprint NN (if applicable)
**Triggered by:** Sprint close | On demand
**Auditors:** SBA · SA · SE · SPMS

## Executive Summary
One paragraph: overall health, top 3 findings, recommended next actions.

## Score Summary
| Role | 1 | 2 | 3 | 4 | 5 | Avg |
|------|---|---|---|---|---|-----|
| SBA  | . | . | . | . | . |  .  |
| SA   | . | . | . | . | . |  .  |
| SE   | . | . | . | . | . |  .  |
| SPMS | . | . | . | . | . |  .  |

## 🚨 Blocking Findings
(Must be resolved before new feature work)
- [BLOCKING-NN] <title> — <role> — <finding> — <proposed backlog item>

## 📋 Advisory Findings
- [ADVISORY-NN] <title> — <role> — <finding> — <proposed action>

## 💡 Innovation Opportunities
- [INNOV-NN] <title> — <role> — <opportunity> — <size: S/M/L>

## Comparison to Prior Audit
(Findings from last report: resolved / persisted / escalated)

## Proposed backlog.md additions
(Copy-paste ready items — user approves before adding)
```

---

## Filing the report

1. **Save to vault:**
   ```
   <OBSIDIAN_VAULT_PATH>/Cline/scrum/governance/YYYY-MM-DD-HHMMSS-governance-report.md
   ```
   Use YAML frontmatter:
   ```yaml
   ---
   title: "Governance Report — YYYY-MM-DD"
   created: YYYY-MM-DDTHH:MM:SS
   tags: [usai-chat, scrum, governance, sprint-NN]
   source: cline
   sprint: NN
   ---
   ```

2. **Append governance section to the active sprint note** (`Cline/scrum/sprints/sprint-NN.md`):
   ```markdown
   ## Governance Board Audit — YYYY-MM-DD
   - Score summary: SBA X.X / SA X.X / SE X.X / SPMS X.X
   - Blocking findings: N
   - Advisory findings: N
   - Innovation opportunities: N
   - See: [[governance/YYYY-MM-DD-HHMMSS-governance-report]]
   ```

3. **Add BLOCKING items to `backlog.md`** (after user confirms):
   - Insert at the **top of the "Open items" section** with a `🚨 BLOCKING` prefix.
   - Include a back-reference to the governance report date.

4. **Add ADVISORY and INNOVATION items to `backlog.md`** (after user confirms):
   - Insert at appropriate priority level with a `📋 ADVISORY` or `💡 INNOVATION` prefix.

5. **Add process findings to self-improvement log:**
   - Append to `Cline/memories/self-improvement-log.md`.
   - If a process fix is warranted: **propose** the `.clinerules/workflows/` edit to the user (do not auto-apply).

6. **If this is a sprint-close audit:** update `Cline/scrum/sprint-index.md` with governance outcome column.

---

## Non-negotiables

- **Never auto-apply** changes to code, workflow files, or backlog items. Present findings and proposed changes; wait for user approval.
- **Never log** API keys, vault paths with personal data, or any secret in the governance report.
- **Blocking authority:** if a BLOCKING finding is confirmed by the user, announce clearly:
  > "⛔ New feature work is paused. The following must be resolved first: [finding]. Once resolved, run `/loop` to clear it."
- **Escalation rule:** if the same finding appears in two consecutive governance reports without resolution, automatically escalate from ADVISORY → BLOCKING (and note the escalation in the report).
