# RAIL Pipeline — Cline Always-On Rule
# (Rule-governed Agentic Iteration Loop for USAi Chat)

> **Concern: Cline dev harness** — this file governs the *Cline* VS Code extension
> only. It is NOT part of the USAi Chat app, and it is NOT the Continue extension
> config (`.continue/`). See `docs/ORGANIZATION.md` for the full three-concern map.

This rule is **always active** for Cline in this project. It mirrors the RAIL
pipeline defined in `docs/rail-pipeline.md` and `AGENTS.md`, adapted
for Cline's Plan/Act workflow model.

---

## Core loop principle

> Never rely on a single prompt. Generate → Evaluate → Fix → Repeat until the
> output meets requirements.

The loop has this shape for every non-trivial task:

```
Goal
  ↓
/spec   (PLAN MODE — interview → write docs/specs/<feature>.md)
  ↓
/loop   (ACT MODE  — iterates /build → /review until clean)
  ├─ /build  (implement spec exactly, TDD-style)
  └─ /review (compare vs spec, run gates — repeat if failing)
  ↓
Done (tests green, checks pass, docs updated, memory note written)
```

---

## The six RAIL roles (apply in every task, in order)

Each role has its own Execute → Review → Improve → Approve sub-cycle before
handing off to the next.

### 0. Product Owner *(features only — skip for bugfix/chore/refactor)*
- **Start gate:** confirm a Definition of Ready — user story, testable acceptance
  criteria, vertical slice, size estimate.
- **End gate:** acceptance — every criterion met, verified by test or observable
  behavior.
- *Check:* `.continue/checks/definition-of-ready.md` + `acceptance-criteria.md`

### 1. Code Planner
- Produce a structured plan (see template below) before editing any file.
- **Recall first:** search `Cline/memories/`, `Continue Extension/memories/`,
  and `USAi/memories/` in the Obsidian vault for relevant prior context.
- Output: `docs/specs/<feature>.md` (written by `/spec` workflow).
- *Check:* plan covers Goal, Files, Approach, Tests, Docs, Risks.

### 2. Architect
- Validate the technical approach against the USAi conventions:
  - No new runtime dependencies (vanilla JS / stdlib Python + python-dotenv).
  - New endpoints → `_handler` + `routes` registration + input-size validation.
  - New tools → `TOOL_REGISTRY` + `getEnabledTools()` gate.
  - Security: `/config` exposes no secrets; path traversal rejected on all FS
    endpoints; SSRF guard (`is_safe_upstream_url`) on upstream calls.
  - CSS changes bump `styles.css?v=N` in `index.html`.
- Flag any design conflict with existing architecture before proceeding.

### 3. Developer (SME)
- Implement *exactly* what the spec covers — flag any scope creep.
- TDD: write the failing test first (Red), then the minimum code (Green), then
  refactor under green.
- Comments explain *why*, not just *what* — match existing style.
- Keep docs in sync **in the same turn** (CHANGELOG always; `docs/USER_GUIDE.md` / README /
  backlog as applicable).

### 4. Tester
- Write/update tests in `tests/js/*.test.mjs` or `tests/python/test_*.py`.
- Run the full suite and coverage gates:
  ```bash
  ./run-tests.sh --coverage
  ```
  Gates: `server.py` ≥ 90% lines; JS branch ≥ 70% on exported helpers.
- Regression tests for every bug fix.

### 5. Security
- Run the deterministic security scan:
  ```bash
  ./scripts/security-scan.sh   # gitleaks + bandit + pip-audit
  ```
- Verify: no secrets in code/logs, no new runtime deps, no path traversal, no
  SSRF vectors.
- Do not weaken or disable a scanner to make it pass — fix the finding instead.

### 6. Reviewer (QA)
- Run the full check suite:
  ```bash
  ./scripts/cli-check.sh --review
  ```
- Compare implementation against spec line-by-line; list any gaps or bugs.
- Pass only when: tests green + coverage gates met + security scan clean +
  acceptance criteria met (features) + docs updated + memory note queued.
- On any failure: emit a gap list and return to Developer (Role 3).

---

## Always-on non-negotiables

- **Secrets:** never commit or echo secrets. API keys live only in `.env`.
- **Docs in sync:** CHANGELOG in every substantive change; `docs/USER_GUIDE.md` for
  user-facing features; README for setup/config; backlog items checked off.
- **Memory:** at the start of any non-trivial task, recall from the Obsidian
  vault (`Cline/memories/` + `USAi/memories/` + `Continue Extension/memories/`).
  At the end, record a session note to
  `Cline/memories/YYYY-MM-DD-HHMMSS-<title>.md`.
  (Cline writes to `Cline/memories/` only — see `docs/ORGANIZATION.md`.)
- **CSS cache bust:** any `styles.css` edit → bump `?v=N` in `index.html`.

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

## Self-scoring rewrite loop (single-paragraph prompt)

Use this snippet for any writing or coding sub-task that needs iterative
self-improvement without an explicit multi-step loop:

> "Complete the task below. When finished, score your output from 1–10 on
> [correctness / clarity / coverage / style — pick the relevant axes]. If your
> score is below 9, identify the top 1–3 weaknesses, rewrite the output to
> address them, and score again. Repeat until you reach 9 or higher or until
> you have iterated three times, whichever comes first. Show only the final
> output and your last score."

---

*Detailed reference: `docs/ORGANIZATION.md` (three-concern map),
`docs/rail-pipeline.md` (RAIL concept + testing strategy),
`docs/tooling/cline.md` (Cline-specific), `AGENTS.md`,
`.continue/checks/` (Continue harness — Cline's workflows live in
`.clinerules/workflows/`).*
