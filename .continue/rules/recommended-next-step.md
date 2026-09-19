---
alwaysApply: true
---

# Rule: Recommended Next Step (mandatory closing hand-off)

> **Canonical definition:** [`docs/rail-pipeline.md`](../../docs/rail-pipeline.md)
> § "Recommended Next Step — the closing hand-off (mandatory)". That document is the
> single source of truth for the format, the selection criteria, and the constraints.
> This file is the *Continue-specific* wiring only.

Every task must end by telling the user **what should happen next and why** — never
leave them guessing at the sequence. This is the hand-off artifact of a completed RAIL
cycle, and it pairs with the Continuous Improvement role (Role 5): the retro looks
*backward*, this section looks *forward*.

## When Continue emits it

At the end of **every** task turn that hands control back to the user — after the work
is summarised and after the QA gate (`/check` or `./scripts/cli-check.sh`) has been run.
Emit it even when:

- the task was small (a one-file edit still has a logical successor),
- the QA gate **failed** (then the recommended step is the fix that would make it pass),
- the task was analysis or documentation rather than code.

Order at the end of a task: **work summary → retro/learning note (Continuous
Improvement) → `Recommended Next Step`.** It is the last thing in the message.

## Required format

```markdown
## Recommended Next Step

**Next Step:** <one clearly stated action>

**Why this should happen next:** <reasoning grounded in the verified current state>

**What this enables:** <capability, decision, validation, or work this unlocks>

**Impact if not completed:** <risk, delay, technical debt, or uncertainty of skipping>
```

All four labelled parts are required — do not drop one because it feels obvious.

## The traps to avoid

- **Don't default to coding.** Requirements clarification, architecture, data modeling,
  security design, validation, testing, documentation, and infrastructure are all
  equally valid next steps. Choose what is *logically required next*.
- **Don't offer a menu.** One primary action. Alternatives only when genuinely necessary.
- **Don't recommend blocked work.** If item #N depends on an unfinished prerequisite,
  recommend the prerequisite.
- **Don't write filler.** "Continue development", "add more tests", "review the code"
  are rejected — name the backlog item, the file, or the specific gap.
- **Don't guess at state.** Base the recommendation on what the gates actually reported
  in this turn, plus `backlog.md` and the working tree — not on a generic roadmap.

## Relationship to the other rules

| Rule | Interaction |
|------|-------------|
| `continuous-improvement.md` | Runs first (backward-looking retro); this rule closes the turn (forward-looking) |
| `agile-workflow.md` | The recommended step should be consistent with backlog priority order |
| `keep-docs-in-sync.md` | If docs were left stale, syncing them is a strong candidate for the next step |

## Model tier

**Low (Haiku)** is sufficient for routine closings. Use **High (Opus)** when the correct
next step is genuinely ambiguous — e.g. several partly-blocked backlog items, or a
failing gate whose root cause is unclear. See `docs/rail-pipeline.md` § "Model tiers".

---

*Cline equivalent: `.clinerules/recommended-next-step.md` · shared contract: `AGENTS.md`*
