# Governance Board — USAi Chat

> **Concern: Cline dev harness** — this document defines the four standing governance
> advisory roles for the USAi Chat project. These roles operate at the **project level**,
> not the per-task level. They review the whole codebase, process, and direction on a
> periodic cadence — independent of any single feature sprint.
>
> The per-task RAIL pipeline remains unchanged. Governance Board findings flow INTO
> the RAIL pipeline as new backlog items and self-improvement rules.
>
> **Canonical RAIL reference:** [`docs/rail-pipeline.md`](rail-pipeline.md)
> **Cline workflow:** [`.clinerules/workflows/govern.md`](../clinerules/workflows/govern.md)

---

## Purpose

The Governance Board provides **standing oversight** of the USAi Chat project across
four critical dimensions:

| Dimension | Governed by |
|-----------|-------------|
| **Business alignment & requirements soundness** | Senior Business Analyst |
| **Architecture fitness & technical standards** | Senior Architect |
| **Engineering quality & innovation practices** | Senior Engineer |
| **Process maturity & methodology health** | Senior Process Management Specialist |

The Board:
- Reviews the **entire project** (codebase, docs, backlog, pipeline, artifacts) — not just the latest change.
- Operates **periodically** (every sprint close, and on demand via `/govern`).
- Is **advisory AND blocking**: findings are categorized as *Advisory* (recommendations for the backlog) or *Blocking* (must be resolved before new feature work proceeds).
- **Never auto-applies** changes — all findings go into `backlog.md` or the self-improvement log for human approval and RAIL execution.

---

## The four senior advisory roles

### 1. Senior Business Analyst (SBA)

**Charter:** Ensure the project builds the *right* thing in the *right* order — that
every feature, spec, and backlog item maps to genuine user value, is well-defined, and
that the product direction remains coherent and aligned.

**Scope of review:**
- `backlog.md` — are items properly groomed with user stories and acceptance criteria? Are priorities business-value-ordered? Is there scope creep or gold-plating?
- `docs/specs/` — do specs have clear, testable acceptance criteria? Are "out of scope" sections honored?
- `docs/USER_GUIDE.md` — does the documented experience match real user needs?
- Feature roadmap health — are we solving real problems or solving imaginary ones? Are there gaps (missing features users actually need)?
- Vertical-slice discipline — are we shipping user-visible value or horizontal layers?

**Rubric (score each 1–5):**
1. Backlog grooming completeness (all items have user stories + AC)
2. Priority ordering by business value (highest-value items at top)
3. Acceptance criteria testability (each AC is binary pass/fail)
4. User Guide accuracy (reflects current app behavior)
5. Roadmap coherence (features build on each other sensibly)

**Output:** Findings + recommendations → `backlog.md` items or governance report advisory notes.

---

### 2. Senior Architect (SA)

**Charter:** Ensure the technical architecture remains sound, consistent with stated
principles, free of design debt, and capable of supporting the next 12 months of planned work.

**Scope of review:**
- `docs/ARCHITECTURE.md` — is the architecture diagram accurate? Are component boundaries still clean?
- `docs/principles.md` — are the stated principles (minimal runtime surface, DevSecOps, IaC, Agile) being honored in practice?
- `server.py` + `app.js` — are there architectural anti-patterns (God objects, tangled concerns, hardcoded config, bypass of security guards)?
- `Dockerfile` / `docker-compose.yml` / `Makefile` — is the infrastructure declarative and reproducible?
- Dependency surface — has runtime surface crept up? Are all runtime deps justified and pinned?
- Technology standard fitness — is the chosen stack (vanilla JS + Python stdlib) still the right fit for the planned roadmap? Are there emerging standards that should be adopted?
- Forward compatibility — are planned features (e.g. Projects #27) architecturally supportable without rewrites?

**Rubric (score each 1–5):**
1. Architecture accuracy (docs match code reality)
2. Principle adherence (runtime surface, security, IaC discipline)
3. Design consistency (patterns are applied uniformly)
4. Dependency hygiene (no unjustified runtime deps; all pinned)
5. Forward readiness (architecture can accommodate backlog without structural rework)

**Output:** Findings + recommendations → `docs/ARCHITECTURE.md` updates, `backlog.md` architectural debt items, governance report.

---

### 3. Senior Engineer (SE)

**Charter:** Ensure the codebase maintains high engineering quality, applies innovation
best practices, and avoids technical debt accumulation. Identify opportunities to apply
new techniques that improve reliability, performance, or developer experience — within
the project's dependency constraints.

**Scope of review:**
- `server.py` + `app.js` — code quality: DRY, naming clarity, function length, comment quality (why not what), error handling completeness.
- `tests/` — test quality: are tests actually testing the right things? Are there obvious coverage gaps in security-critical paths? Is TDD discipline being maintained?
- `.coverage-thresholds` — are coverage gates improving over time (ratcheting up), or stagnating?
- `scripts/` — are automation scripts robust, idiomatic, and free of fragile shell patterns?
- Innovation opportunities — vanilla CSS features (container queries, `:has()`, `color-mix()`), Python 3.11+ features, modern JS (structuredClone, WeakRef, ReadableStream patterns); always filtered through the runtime-surface constraint.
- Security engineering — are SSRF guard, path-traversal guard, and `/config` redaction patterns consistently applied as new endpoints are added?

**Rubric (score each 1–5):**
1. Code quality (DRY, naming, function size, comment quality)
2. Test quality (right coverage of right things; TDD discipline)
3. Security pattern consistency (every FS/proxy endpoint uses the guards)
4. Coverage gate trajectory (gates ratcheting up, not stagnant)
5. Innovation fit (modern techniques applied where they add value, within constraints)

**Output:** Findings + recommendations → `backlog.md` engineering quality items, `self-improvement-log.md` entries, governance report.

---

### 4. Senior Process Management Specialist (SPMS)

**Charter:** Ensure the development process itself is sound, efficient, and maturing.
Review the RAIL pipeline health, Scrum artifact quality, and tooling effectiveness —
and identify process improvements that reduce friction, increase predictability, or
improve quality assurance.

**Scope of review:**
- RAIL pipeline health — are the six roles being applied consistently? Are there recurring gaps (e.g. TDD Red receipt regularly skipped? Memory notes missing?)?
- `Cline/scrum/` vault artifacts — are sprint notes, retrospectives, and the sprint index complete and up to date?
- `backlog.md` vs sprint velocity — are items being completed at a sustainable rate? Is the backlog growing faster than it's being resolved?
- `.clinerules/` workflow files — are `/spec`, `/build`, `/review`, `/loop` workflows clear, complete, and being followed?
- Self-improvement loop — is `self-improvement-log.md` growing with real learnings? Are prevention rules from the log actually preventing recurrence?
- Definition of Ready / Done quality — are DoR/DoD criteria being respected at sprint boundaries?
- Tooling effectiveness — are `run-tests.sh`, `security-scan.sh`, `cli-check.sh`, `spec-check.sh` running reliably? Are false positives/negatives being addressed?

**Rubric (score each 1–5):**
1. RAIL pipeline discipline (roles applied, TDD receipt, memory notes present)
2. Scrum artifact completeness (sprint notes, retros, index current)
3. Backlog health (velocity vs. growth rate; DoR compliance)
4. Workflow clarity (spec/build/review/loop instructions unambiguous)
5. Self-improvement effectiveness (log growing; prevention rules being applied)

**Output:** Findings + recommendations → workflow file updates, backlog process items, `Cline/scrum/` artifact updates, governance report.

---

## Governance cadence

| Trigger | When | Who initiates |
|---------|------|---------------|
| **Sprint-close audit** | At the close of every sprint (when `/loop` Done criteria are met for all sprint items) | Triggered automatically by the sprint-close step in `.clinerules/scrum-artifacts.md` |
| **On-demand audit** | Any time the user runs `/govern` | User-initiated |
| **Blocking escalation** | When a RAIL `/review` flags a systemic issue (not just a per-task gap) that warrants project-level review | Triggered by `/review` or `/loop` escalation |

---

## Blocking vs. Advisory findings

Each finding is classified at the time of the audit:

| Classification | Meaning | Action |
|----------------|---------|--------|
| 🚨 **BLOCKING** | A finding that indicates a systemic risk or quality failure significant enough that it should be resolved before new feature work proceeds. | Added to `backlog.md` with **BLOCKING** label at the TOP of the open items list. A note is appended to the active sprint in `Cline/scrum/sprints/`. |
| 📋 **ADVISORY** | A recommendation that improves quality, process, or architecture but does not halt feature work. | Added to `backlog.md` at appropriate priority, or to the self-improvement log. |
| 💡 **INNOVATION** | An opportunity to adopt a better technique, pattern, or standard within project constraints. | Added to `backlog.md` as a chore/improvement item. |

The user confirms or overrides all blocking classifications before work halts.

---

## Report format

Each governance audit produces a dated Markdown report saved to:

```
<OBSIDIAN_VAULT_PATH>/Cline/scrum/governance/YYYY-MM-DD-HHMMSS-governance-report.md
```

See the template at:
```
<OBSIDIAN_VAULT_PATH>/Cline/scrum/templates/governance-report-template.md
```

The Cline workflow that executes the audit is:
```
.clinerules/workflows/govern.md
```

---

## Where governance findings go

```
Governance Board audit
        │
        ├─ BLOCKING findings ──► backlog.md (top of open items, BLOCKING label)
        │                         + active sprint note (blocking callout)
        │
        ├─ ADVISORY findings ──► backlog.md (priority-ordered)
        │
        ├─ INNOVATION findings ► backlog.md (chore/improvement items)
        │
        ├─ Process findings ───► .clinerules/workflows/ (proposed edits)
        │                         + self-improvement-log.md
        │
        └─ Report ─────────────► Cline/scrum/governance/YYYY-MM-DD-report.md
                                  + sprint note (governance section appended)
```

---

## Relationship to the RAIL pipeline

The Governance Board sits **outside** the per-task RAIL loop but **feeds** it.
The two levels of governance operate at complementary scopes:

```
             ┌─────────────────────────────────────┐
             │        GOVERNANCE BOARD             │
             │  (periodic, whole-project review)   │
             │  SBA · SA · SE · SPMS               │
             └──────────────┬──────────────────────┘
                            │ findings → backlog.md + self-improvement
                            ↓
             ┌─────────────────────────────────────┐
             │           RAIL PIPELINE             │
             │  (per-task, iterating loop)         │
             │  PO → Planner → SME → Test →        │
             │  Security → Review → CI             │
             └─────────────────────────────────────┘
```

### Shift-left governance (per-requirement, inside RAIL)

A *per-requirement* subset of the SBA/SA rubric is applied during **`/spec`
Step 2b** — before any implementation begins:

| `/spec` check | Governance source | What it catches early |
|---------------|-------------------|-----------------------|
| G-1 AC testability | SBA-3 | Vague, non-binary ACs that would fail the Definition of Done |
| G-2 Scope / value | SBA-2 | Scope creep or gold-plating beyond the stated goal |
| G-3 Dependency coherence | SBA-5-lite | Undeclared prerequisites on open backlog items |

These findings are **advisory** — recorded in the spec’s §4b but do not block
Status: Ready. The intent is to catch requirement-level failures cheaply, at the
moment of authoring, rather than at sprint-close audit.

### Full Governance Board (macro-assessment, sprint cadence)

The full four-role `/govern` audit remains a **sprint-close / on-demand** activity.
Its rubrics (SBA cross-roadmap coherence, SA forward readiness and principle
adherence, SE code quality and innovation, SPMS process maturity) all require a
body of completed work to assess — they cannot be meaningfully evaluated per-spec
and would create excessive friction if run at that cadence.

The RAIL pipeline’s Continuous Improvement role (Role 5) produces **micro-learnings**
(per-task retros). The Governance Board produces **macro-assessments** (project health).
The `/spec` shift-left gate bridges the two: requirement soundness is checked early,
while structural and process health is assessed periodically.

All three levels feed `backlog.md` and the self-improvement log, and all write to
the Obsidian vault.

---

## References

- [`docs/rail-pipeline.md`](rail-pipeline.md) — RAIL pipeline concept + roles
- [`docs/principles.md`](principles.md) — engineering principles the SA audits against
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — architecture reference the SA reviews
- [`.clinerules/workflows/govern.md`](../clinerules/workflows/govern.md) — the `/govern` Cline workflow
- [`AGENTS.md`](../AGENTS.md) — shared agent operating contract
- `Cline/scrum/` (vault) — Scrum artifacts the SPMS reviews
- `Cline/scrum/governance/` (vault) — governance report archive
