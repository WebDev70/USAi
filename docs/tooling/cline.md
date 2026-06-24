# Cline Dev Harness — Reference Guide

> **Concern: Cline dev harness** — this document covers the VS Code
> [Cline](https://github.com/cline/cline) extension configuration only. It is NOT
> part of the USAi Chat app and NOT the Continue harness. See
> [`docs/ORGANIZATION.md`](../ORGANIZATION.md) for the full three-concern map.

The Cline extension reads `.clinerules/` to govern how it behaves while building
USAi Chat. Nothing in `.clinerules/` is part of the running application.

**Canonical cross-harness reference:** [`docs/rail-pipeline.md`](../rail-pipeline.md)
(RAIL concept + testing strategy, harness-agnostic).

---

## Directory layout

| Path | Role |
|------|------|
| `.clinerules/rail-pipeline.md` | Always-on RAIL rule — Cline's operating contract for this project |
| `.clinerules/workflows/spec.md` | `/spec` workflow — PLAN MODE interview → writes `docs/specs/<feature>.md` |
| `.clinerules/workflows/build.md` | `/build` workflow — ACT MODE implementation engine |
| `.clinerules/workflows/review.md` | `/review` workflow — compares build vs spec, runs QA gates |
| `.clinerules/workflows/loop.md` | `/loop` workflow — iterates `/build` → `/review` until clean |
| `.clinerules/workflows/self-improve.md` | `/self-improve` workflow — continuous-improvement retro |
| `docs/specs/` | Output of `/spec` — feature spec files consumed by `/build` |

---

## How Cline implements RAIL

Cline uses its **Plan/Act** model. The RAIL roles are expressed as slash-command
**workflows** rather than always-on rules files:

```
Goal
  ↓
/spec    (PLAN MODE — interview → write docs/specs/<feature>.md)
  ↓
/loop    (ACT MODE  — iterates /build → /review until clean)
  ├─ /build   (implement spec: Roles 1–4: Planner, SME, Tester, Security)
  └─ /review  (compare vs spec, run gates: Role 5 Reviewer — repeat if failing)
  ↓
Done (tests green, security scan clean, docs updated, memory note written)
```

### Workflows

| Workflow | Mode | What it does |
|----------|------|--------------|
| **`/spec`** | PLAN MODE | Interviews the user, captures requirements, produces a `docs/specs/<feature>.md` with goal, acceptance criteria, affected files, test plan, and risks. Serves as the Definition of Ready. |
| **`/build`** | ACT MODE | Executes the spec TDD-style: plan → Red → Green → Refactor → security check. |
| **`/review`** | ACT MODE | Compares the implementation against the spec, runs `./run-tests.sh --coverage` and `./scripts/security-scan.sh`, reports a gap list. Returns to `/build` if anything fails. |
| **`/loop`** | ACT MODE | Calls `/build` then `/review`; repeats until `/review` passes with zero gaps. |
| **`/self-improve`** | Either | Post-cycle retro: identifies patterns, proposes new rules/checks/tests, records a learning note to Obsidian. |

### Running QA gates in Cline

Cline's equivalent of Continue's `/check` is the **`/review`** workflow, which runs:

```bash
./run-tests.sh --coverage          # syntax gates + JS + Python + coverage enforcement
./scripts/security-scan.sh         # gitleaks + bandit + pip-audit
#./scripts/cli-check.sh --review    # optional: cn review with all check files as rules
```

Pass criteria (same as the shared RAIL Definition of Done):
- Tests green + coverage gates met
- Security scan clean
- Docs updated (CHANGELOG, USER_GUIDE, README as applicable)
- Acceptance criteria met (features)
- Memory note queued

---

## The spec document (`docs/specs/<feature>.md`)

The `/spec` workflow produces a spec file with this structure:

```markdown
# Spec: <Feature Name>

**Status:** Draft | Ready | In Progress | Done
**Created:** YYYY-MM-DD
**Author:** (Cline/user)

## 1. Goal & scope
## 2. User story & acceptance criteria
## 3. Affected files
## 4. Technical approach
## 5. Test plan
## 6. Docs to update
## 7. Risks / edge cases
## 8. Review checklist (filled by /review)
```

Spec files are the output of `/spec` and the primary input to `/build`. They are
committed to the repo in `docs/specs/` and serve as the feature's Definition of Ready.

---

## Obsidian memory (Cline's own)

Cline writes session notes to **`Cline/memories/`** in the vault — its own subfolder,
separate from both the app (`USAi/memories/`) and Continue
(`Continue Extension/memories/`). Prefer direct filesystem I/O over the MCP server.

```
<your OBSIDIAN_VAULT_PATH>/
└── Cline/
    └── memories/                   ← Cline writes here
        └── YYYY-MM-DD-HHMMSS-title.md
```

Recall: at the start of any non-trivial task, search **all three** memory subfolders
(`USAi/memories/`, `Continue Extension/memories/`, `Cline/memories/`) for relevant
prior context before answering.

Record: at the end of the task, write a session note with YAML frontmatter, tags
(`usai-chat`, `conversation-log`, + topic tags), and a concise summary of decisions,
files changed, and follow-ups.

---

## Coding conventions

> **Canonical source:** [`docs/rail-pipeline.md` §3](../rail-pipeline.md)
> lists all USAi coding conventions (CSS cache-bust, tool gating, endpoint
> pattern, SSRF guard, minimal runtime surface). This section is a concise
> pointer — the rail-pipeline doc is the single source of truth.

- **No new runtime deps.** Frontend = vanilla JS; backend = stdlib + `python-dotenv`.
- **Security first.** Secrets stay server-side; `/config` returns only `has_*` flags;
  path traversal rejected on all FS endpoints; SSRF guard on all upstream calls.
- **Docs in same turn.** CHANGELOG always; USER_GUIDE for user-facing; README for
  setup/config; backlog items checked off.
- **TDD.** Red → Green → Refactor; regression test before every bug fix.
- For CSS bump, tool gating, new-endpoint pattern, and SSRF guard details see
  [`docs/rail-pipeline.md` §3 — Code Planner approach](../rail-pipeline.md).

---

## References

- [`docs/rail-pipeline.md`](../rail-pipeline.md) — shared RAIL concept + testing strategy
- [`docs/ORGANIZATION.md`](../ORGANIZATION.md) — three-concern map
- [`docs/tooling/continue.md`](continue.md) — Continue harness reference
- [`.clinerules/rail-pipeline.md`](../../.clinerules/rail-pipeline.md) — always-on Cline operating contract
- `AGENTS.md` — shared operating contract (memory, security, conventions)
