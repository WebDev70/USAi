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

### 6a. Spec compliance check

Run the machine-enforced spec↔build checker first — its output replaces the
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

### 6b. Test suite gate

```bash
./run-tests.sh --coverage
```

Pass criteria:
- All tests green (zero failures)
- `server.py` ≥ **90%** line coverage
- JS exported helpers ≥ **70%** branch coverage

### 6c. Documentation gate

Cross-check spec §6 (Docs to update):
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` updated (if user-facing feature)
- [ ] `README.md` updated (if setup/env/config changed)
- [ ] `backlog.md` item checked off (if applicable)
- [ ] `AGENTS.md` / `CONTINUE.md` updated (if conventions changed)

### 6d. Acceptance criteria gate

From spec §2, verify each acceptance criterion:

| AC | Verified by | Result |
|----|------------|--------|
| AC-1 | <test name or observable behavior> | ✅ / ❌ |
| AC-2 | ... | ✅ / ❌ |

### 6e. USAi convention gate

| Convention | Compliant? |
|---|---|
| No new runtime dependency | ✅ / ❌ |
| New endpoint: `_handler` + `routes` + size validation | ✅ / N/A / ❌ |
| New tool: `TOOL_REGISTRY` + `getEnabledTools()` gate | ✅ / N/A / ❌ |
| `/config` exposes no secrets | ✅ / N/A / ❌ |
| Filesystem endpoint rejects path traversal | ✅ / N/A / ❌ |
| CSS change bumps `styles.css?v=N` | ✅ / N/A / ❌ |
| Comments explain *why* | ✅ / ❌ |

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
