# RAIL Pipeline — Cline Always-On Rule
# (Rule-governed Agentic Iteration Loop for USAi Chat)

> **Concern: Cline dev harness** — this file governs the *Cline* VS Code extension
> only. It is NOT part of the USAi Chat app and NOT the Continue harness.
> See `docs/ORGANIZATION.md` for the full three-concern map.
>
> **Canonical reference:** `docs/rail-pipeline.md` (RAIL concept, testing strategy,
> coding conventions — harness-agnostic). This file is the *Cline-specific*
> always-on operating contract.

---

## Core loop principle

> Never rely on a single prompt. Generate → Evaluate → Fix → Repeat until the
> output meets requirements.

```
Goal
  ↓
/spec   (PLAN MODE — interview → write docs/specs/<feature>.md)
  ↓
/loop   (ACT MODE  — iterates /build → /review until clean)
  ├─ /build  (implement spec exactly, TDD-style)
  └─ /review (compare vs spec, run gates — repeat if failing)
  ↓
Done (tests green, security scan clean, docs updated, memory note written)
```

---

## The six RAIL roles (apply in order)

Each role has its own Execute → Review → Improve → Approve sub-cycle before
handing off to the next.

### 0. Product Owner *(features only — skip for bugfix/chore/refactor)*
- Confirm a **Definition of Ready** before planning: user story, testable
  acceptance criteria, vertical slice, size estimate.
- Confirm **acceptance** at the end: every criterion met, verified by test or
  observable behavior.

### 1. Code Planner
- **Recall first:** search `Cline/memories/`, `Continue Extension/memories/`, and
  `USAi/memories/` in the Obsidian vault for relevant prior context.
- Produce a structured plan (Goal, Files, Approach, Tests, Docs, Risks) before
  editing any file. Output: `docs/specs/<feature>.md` (written by `/spec`).

### 2. Architect
- Validate the approach against USAi conventions (see `docs/rail-pipeline.md` §3):
  no new *runtime* dependencies (vanilla JS / stdlib Python + python-dotenv),
  SSRF guard, path-traversal rejection, CSS `?v=N` bump, `HOST`/`PORT` via
  `resolve_bind_address`, tool gating via `getEnabledTools`.
- Flag any design conflict before proceeding.

### 3. Developer (SME)
- Implement *exactly* what the spec covers — flag any scope creep.
- TDD: write the failing test first (Red), then minimum code (Green), then
  refactor under green.
- Comments explain *why*, not just *what* — match existing style.
- Keep docs in sync **in the same turn**: CHANGELOG always; `docs/USER_GUIDE.md`
  for user-facing; README for setup/config; **backlog lifecycle updated** (see
  "Backlog lifecycle" below).

### 4. Tester
- Write/update tests in `tests/js/*.test.mjs` or `tests/python/test_*.py`.
- Run the full suite + coverage gates:
  ```bash
  ./run-tests.sh --coverage
  ```
  Gates: `server.py` ≥ 90% lines; JS branch ≥ 70% on exported helpers.
- Regression test for every bug fix.

### 5. Security
- Run the deterministic security scan:
  ```bash
  ./scripts/security-scan.sh   # gitleaks + bandit + pip-audit
  ```
- Verify: no secrets in code/logs, no new runtime deps, no path traversal, no
  SSRF vectors.
- Never weaken or disable a scanner to make it pass — fix the finding instead.

### 6. Reviewer (QA)
- Run the full check suite:
  ```bash
  ./scripts/cli-check.sh --review
  ```
- Compare implementation against spec line-by-line; emit a gap list for any
  missing or broken items.
- **Pass only when ALL of:** tests green + coverage gates met + security scan
  clean + acceptance criteria met (features) + docs updated + memory note queued.
- On any failure: emit the gap list and return to Developer (Role 3).

---

## Always-on non-negotiables

| Rule | Detail |
|------|--------|
| 🔐 **Secrets** | Never commit or echo secrets. API keys live only in `.env`. |
| 📝 **Docs in sync** | CHANGELOG every substantive change; `USER_GUIDE.md` for user-facing; README for setup/config; **backlog lifecycle updated** (see "Backlog lifecycle" section below). |
| 🧠 **Memory** | Recall at task start from all three vault subfolders. Record session note to `Cline/memories/YYYY-MM-DD-HHMMSS-<title>.md` at task end. |
| 🎨 **CSS cache bust** | Any `styles.css` edit → bump `?v=N` in `index.html`. |

---

## Backlog lifecycle

Every feature moves through three states in `backlog.md`. This is not optional — the
backlog is the project's work-queue and its accuracy depends on the RAIL pipeline
keeping it current.

### Status format

```
- [ ]  **N. <title>** *(size)*                         ← Not started
- [~]  **N. <title>** *(size)* — spec: docs/specs/<kebab>.md   ← In Progress
- [x]  **N. <title>** *(size)* — Done (YYYY-MM-DD): <one-line outcome>.
       Spec: docs/specs/<kebab>.md                     ← Done
```

### When to transition

| RAIL step | Transition | Who |
|-----------|-----------|-----|
| `/spec` Step 3b | `[ ]` → `[~]` + append spec link | Code Planner (Role 1) |
| `/build` pre-flight | Verify `[~]`; fix to `[~]` if still `[ ]` | Developer (Role 3) |
| `/loop` Done criteria | `[~]` → `[x]` + Done date + one-line outcome + spec link | Developer (Role 3) |
| `/review` §6c gate | Verify `[x]` with date/outcome/spec link; emit GAP if missing | Reviewer (Role 6) |

### Scrum mirror

After each `[ ]` → `[~]` transition: move item to In-Progress table in
`Cline/scrum/product-backlog.md`.

After each `[~]` → `[x]` transition: move item to Completed table in
`Cline/scrum/product-backlog.md`.

Both mirrors must be kept in sync in the **same turn** as the `backlog.md` update.

---

## Spec document template (`docs/specs/<feature>.md`)

```markdown
# Spec: <Feature Name>

**Status:** Draft | Ready | In Progress | Done
**Created:** YYYY-MM-DD
**Author:** (Cline/user)

## 1. Goal & scope
What we're building and why. What is explicitly out of scope.

## 2. User story & acceptance criteria
As a <user> I want <goal> so that <value>.
- [ ] Criterion 1 (testable, observable)
- [ ] Criterion 2

## 3. Affected files
- `file.py` — change description
- `file.js` — change description
- `tests/python/test_*.py` — new/updated tests

## 4. Technical approach
Key functions/endpoints/components to add or change.
Conventions that apply (tool gating, path-traversal guards, CSS bump, etc.).

## 5. Test plan
| Test | File | Description |
|------|------|-------------|
| ... | tests/python/test_server.py | ... |

## 6. Docs to update
- [ ] CHANGELOG.md
- [ ] docs/USER_GUIDE.md (if user-facing)
- [ ] README.md (if setup/config changes)
- [ ] backlog.md (mark item done)

## 7. Risks / edge cases
- ...

## 8. Review checklist (filled by Reviewer role)
- [ ] Implementation matches spec sections 3–5
- [ ] `./run-tests.sh --coverage` passes
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (section 6)
- [ ] Memory note written
```

---

## Self-scoring rewrite loop (`/self-improve` sub-task)

Use this for any writing or coding sub-task where a single-pass output may not
be good enough:

> "Complete the task below. When finished, score your output from 1–10 on
> [correctness / clarity / coverage / style — pick relevant axes]. If your score
> is below 9, identify the top 1–3 weaknesses, rewrite the output to address
> them, and score again. Repeat until you reach 9 or higher, or until you have
> iterated three times, whichever comes first. Show only the final output and
> your last score."

Full workflow: `.clinerules/workflows/self-improve.md`

---

*References: `docs/ORGANIZATION.md` · `docs/rail-pipeline.md` · `docs/tooling/cline.md` · `AGENTS.md`*
