# Workflow: /review
# Cline RAIL — Quality Gate & Gap Analyzer

> **Concern: Cline dev harness** — this workflow is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Mode:** ACT MODE

**Purpose:** Compare the build against the spec, run all automated gates, and either
declare the build **PASS** or produce an actionable **gap list** for `/build` to fix.
This workflow covers **Role 5 (Security) + Role 6 (Reviewer / QA)** in the RAIL
pipeline, with each role's Execute → Review → Improve → Approve sub-cycle.

---

## Pre-flight

1. **Identify the spec.** Default: `docs/specs/<feature>.md`. Read it fully.
2. **Confirm the build ran first.** If `/build` hasn't been run, stop and say so.
3. **Confirm working directory** is the project root (where `run-tests.sh` lives).

---

## Role 5 — Security (deterministic scan)

Run the security scan *before* any AI review — machines first, judgment second:

```bash
./scripts/security-scan.sh
```

This runs **gitleaks** (secret detection) + **bandit** (Python static analysis) +
**pip-audit** (dependency vulnerability check).

**Evaluate results:**

| Finding | Action |
|---------|--------|
| Hardcoded secret / key | FAIL — must be moved to `.env` before proceeding |
| Bandit HIGH severity | FAIL — must be fixed |
| Bandit MEDIUM severity | FAIL unless explicitly documented + justified in the gap list |
| pip-audit vulnerability | FAIL unless ignore is documented + justified |
| Bandit LOW / informational | Note it; does not block |
| New runtime dependency added | FAIL — only stdlib + python-dotenv allowed |

**Do not weaken or disable a scanner to make it pass — fix the finding.**

If security scan passes: ✅ Security — PASS
If any item fails: add it to the Gap List (§ below) and stop further gates.

---

## Role 6 — Reviewer / QA (spec vs. build diff + check gates)

### 6a. Full check-suite gate (mandatory)

Run the full Cline check suite *before* the spec-compliance review — this is
the canonical QA gate for Cline's `/review`:

```bash
./scripts/cli-check.sh --review
```

This runs: `./run-tests.sh --coverage` (syntax + tests + coverage gates) +
`./scripts/security-scan.sh --strict` + `./scripts/doc-consistency-check.sh` +
the `cn review` AI review pass against all `.continue/checks/*.md` criteria.

| cli-check.sh result | Action |
|---|---|
| Exit 0 | ✅ Full check suite — PASS; proceed to spec compliance checks below |
| Exit non-zero (any stage) | **FAIL** — add to Gap List, do not proceed to spec checks |

> **Note:** `./scripts/cli-check.sh --review` **always attempts the AI review** as part
> of the full gate, using `cn` (Continue CLI) if available, or an `npx @continuedev/cli`
> fallback if `cn` is not on PATH. Because the script runs under `set -euo pipefail`, the
> full `--review` gate **fails if the AI review command fails** — there is no skip path.
> To control which CLI is used, pre-install `cn` (`npm i -g @continuedev/cli`) or set the
> `CN_CMD` env var to override the default.

### 6b. Spec compliance check

Run the machine-enforced spec↔build checker next — its output replaces the
manual table scan for §3 and §5:

```bash
./scripts/spec-check.sh <path-to-spec>
# e.g. ./scripts/spec-check.sh docs/specs/rail-improvements.md
```

**Interpret results:**

| spec-check.sh result | Action |
|---|---|
| Exit 0 + `✓ PASS` | §3 and §5 files confirmed — proceed to §4 and TDD checks below |
| Exit 1 (missing §3 file) | **GAP** — add to Gap List, return to `/build` |
| Exit 1 (missing §5 test) | **GAP** — add to Gap List, return to `/build` |
| `WARNING` scope-creep line | Review — add to Gap List only if the extra file was NOT intentional |

After the script passes (exit 0), manually verify the remaining items:

| Spec item | Verified? | Note |
|---|---|---|
| Each function/endpoint in §4 | ✅ / ❌ | |
| Tests written first (TDD — Red receipt in memory note)? | ✅ / ❌ | |
| No out-of-scope code added? | ✅ / ❌ | |

### 6c. Test suite gate

> Note: `./run-tests.sh --coverage` is already run as part of `./scripts/cli-check.sh --review`
> above (§6a). This gate confirms the reported values meet the thresholds:

Pass criteria (verified from §6a output):
- All tests green (zero failures)
- `server.py` ≥ **90%** line coverage
- JS exported helpers ≥ **70%** branch coverage

### 6d. Documentation gate

Cross-check spec §6 (Docs to update):
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` updated (if user-facing feature)
- [ ] `README.md` updated (if setup/env/config changed)
- [ ] `AGENTS.md` / `CONTINUE.md` updated (if conventions changed)
- [ ] **`backlog.md` lifecycle complete** — verify the backlog entry:
  - Status is `[x]` (not `[ ]` or `[~]`)
  - Entry includes a Done date (`Done (YYYY-MM-DD)`), a one-line outcome, and a spec link
  - Expected format:
    ```
    - [x] **N. <title>** *(size)* — Done (YYYY-MM-DD): <one-line outcome>.
          Spec: docs/specs/<kebab-name>.md
    ```
  - If the entry is still `[ ]` or `[~]`, or lacks date/outcome/spec link: emit
    `GAP-N [docs]: backlog.md item #N not closed — flip to [x] with Done date,
    outcome, and spec link.`
- [ ] **Scrum mirror parity** (`Cline/scrum/product-backlog.md`): item appears in the
  Completed table. If absent: emit `GAP-N [docs]: scrum product-backlog.md not updated
  — move item to Completed table.`

### 6e. Acceptance criteria gate

From spec §2, verify each acceptance criterion:

| AC | Verified by | Result |
|----|------------|--------|
| AC-1 | <test name or observable behavior> | ✅ / ❌ |
| AC-2 | ... | ✅ / ❌ |

### 6f. USAi convention gate

| Convention | Compliant? |
|---|---|
| No new runtime dependency | ✅ / ❌ |
| New endpoint: `_handler` + `routes` + size validation | ✅ / N/A / ❌ |
| New tool: `TOOL_REGISTRY` + `getEnabledTools()` gate | ✅ / N/A / ❌ |
| `/config` exposes no secrets | ✅ / N/A / ❌ |
| Filesystem endpoint rejects path traversal | ✅ / N/A / ❌ |
| CSS change bumps `styles.css?v=N` | ✅ / N/A / ❌ |
| Comments explain *why* | ✅ / ❌ |

> **§6f-BE / §6f-FE / §6f-DOCS:** When the spec touches domain-specific files,
> the relevant SME mandatory gates apply within this section:
> - **§6f-BE** (backend): re-run the "Mandatory back-end gates" table from `sme-backend.md`
> - **§6f-FE** (frontend): re-run the "Mandatory front-end gates" table from `sme-frontend.md`
> - **§6f-DOCS** (docs/memory): re-run the "Mandatory documentation gates" table from `sme-docs.md`
>
> If the spec does not touch the domain, mark the subsection N/A.

### 6g. Shift-left governance findings gate (§4b)

Confirm the spec's §4b table is filled:

| §4b check | Present? | Advisory finding addressed or deferred? |
|-----------|----------|----------------------------------------|
| G-1 AC testability | ✅ / ❌ | ✅ addressed / deferred to #N / N/A |
| G-2 Scope / value | ✅ / ❌ | ✅ addressed / deferred to #N / N/A |
| G-3 Dependency coherence | ✅ / ❌ | ✅ addressed / deferred to #N / N/A |

- If §4b is missing entirely: emit `GAP [docs]: spec §4b not filled — add shift-left findings table.`
- If a ⚠️ finding has no deferral backlog item: emit as an **advisory GAP** (non-blocking):
  `ADVISORY [process]: §4b G-N finding recorded but no deferral backlog item named.`

### 6h. Leave-no-trace gate (housekeeping — lightweight)

A per-item subset of the SHK sweep. Run these four checks for the item just built:

| Check | Pass condition | Action if failing |
|-------|---------------|-------------------|
| **Spec status header** | The spec for this item has `Status: Done` if the backlog item is `[x]` | Emit `GAP [housekeeping]: spec Status not updated to Done` |
| **Scratch files** | No new scratch/temp files committed (`implementation_plan.md` in root, `*.tmp`, `*.bak`, stray `wip-*.md`) | Emit `GAP [housekeeping]: committed scratch file — remove or move to docs/specs/` |
| **Untracked inline TODOs** | Any new `TODO`/`FIXME`/`HACK` comments added by this build are either (a) tracked in `backlog.md` or (b) removed | Emit `ADVISORY [housekeeping]: untracked TODO/FIXME in <file>:<line> — add backlog item or resolve` |
| **CHANGELOG freshness** | `CHANGELOG.md [Unreleased]` has at least one entry referencing this item | Emit `GAP [housekeeping]: CHANGELOG not updated for this item` |

**Advisory findings do not convert PASS to FAIL.** GAP findings do.

> This is the *lightweight per-item* gate. The full 7-step SHK sweep runs at sprint
> close via `/govern` (Role 5) or on demand via `/housekeep`.

### 6i. Runtime log review (advisory)

Run the log analyzer if `PERSIST_LOGS` is enabled:

```bash
./scripts/analyze-logs.sh
```

| Result | Action |
|--------|--------|
| Exit 0 | ✅ Log review — clean |
| Exit 1 (errors found) | Append `ADVISORY [logs]: N error entries — top: <list>` to gap list |
| No files / disabled | Note "log review skipped (persistence disabled)" — not a gap |

**Advisory only — never converts PASS to FAIL.**

---

## Verdict

### If ALL gates pass → PASS

Emit:

```
✅ REVIEW — PASS

Security scan: clean
Tests: all green | server.py coverage: XX% | JS branch coverage: XX%
Spec compliance: all §3–5 items implemented
Docs: in sync
Acceptance criteria: all met
Conventions: compliant

Filling in spec §8 Review checklist...
```

Then:
1. Check off all items in the spec's **§8 Review checklist**.
2. Update spec **Status → Done**.
3. Trigger the memory note (or remind the `/loop` orchestrator to do so).

### If ANY gate fails → GAP LIST

Emit:

```
❌ REVIEW — FAIL

Gap List (return to /build):
──────────────────────────────
GAP-1 [security/code/test/docs/convention]: <description>
  → Fix: <specific action required>

GAP-2 [...]: <description>
  → Fix: <specific action required>
```

**The gap list must be specific and actionable.** Vague gaps like "fix tests" are
not acceptable — name the test file, function, line, or criterion.

Return the gap list to `/build` (or to `/loop` which will re-run `/build`
automatically).

---

## Memory note

Whether PASS or FAIL, record what happened for the Continuous Improvement role.
The `/loop` orchestrator will write the final memory note on PASS — on a standalone
`/review` run, append a brief note to the current session memory file:

```
<OBSIDIAN_VAULT_PATH>/Cline/memories/YYYY-MM-DD-HHMMSS-<feature>.md
```

Include: what was reviewed, what failed (if anything), what was fixed, final verdict.

> **Secret safety reminder:** Before saving the memory note, verify it contains no
> API keys, Bearer tokens, or other secrets. Patterns to check: `sk-`, `Bearer `,
> `api_key=`, `password=`. The `scripts/security-scan.sh` 4/4 block will catch
> these automatically — ensure that scan passes after the note is written.
