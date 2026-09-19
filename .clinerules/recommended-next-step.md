# Recommended Next Step — Cline Always-On Rule
# (Mandatory closing section on every terminal task)

> **Concern: Cline dev harness** — this rule governs the *Cline* VS Code extension
> only. It is NOT part of the USAi Chat app and NOT the Continue harness.
> See `docs/ORGANIZATION.md` for the full three-concern map.
>
> **Canonical definition:** `docs/rail-pipeline.md` § "Recommended Next Step — the
> closing hand-off (mandatory)" is the single source of truth for the required format,
> the selection criteria, the constraints, and the anti-patterns. **This file is the
> Cline-specific wiring only** — principally the per-workflow scope table below.
>
> **Related:** `.clinerules/rail-pipeline.md` (always-on operating contract) ·
> `.clinerules/workflows/loop.md` (Done criteria) ·
> `.clinerules/workflows/review.md` (verdict)

---

## The rule

At the end of **every terminal task**, after the closing summary of the work
performed, emit a section titled exactly:

```
Recommended Next Step
```

**Never omit it** — not on trivial edits, not on failed builds, not on escalations,
not on Q&A tasks that touched the codebase.

The four required parts, the selection criteria, the constraints, and the
anti-pattern table live canonically in `docs/rail-pipeline.md`. Read them there —
they are deliberately not restated here, so there is only one copy to keep correct.

Shape reminder (full spec in the canonical doc):

```markdown
## Recommended Next Step

**Next Step:** <one clearly stated action>

**Why this should happen next:** <reasoning grounded in the verified current state>

**What this enables:** <capability, decision, validation, or work this unlocks>

**Impact if not completed:** <risk, delay, technical debt, or uncertainty of skipping>
```

All four labelled parts are required. Do not drop a part because it feels
obvious — state it explicitly.

---

## Scope — which Cline workflows emit it

"Task" means **one complete user-facing turn that ends with Cline handing control
back to the user.** The section belongs on the *last* message of that turn only.

| Workflow | Terminal? | Emits the section? |
|----------|-----------|--------------------|
| `/spec` | Yes — PLAN MODE ends and hands off to the user | ✅ Yes |
| `/build` | **No** — hands off to `/review` within the same task | ❌ No (its own "Next step" handoff line stands) |
| `/review` | Only when run standalone | ✅ When standalone; ❌ when invoked by `/loop` |
| `/loop` | Yes — PASS **or** escalation | ✅ Yes |
| `/govern` | Yes | ✅ Yes |
| `/housekeep` | Yes | ✅ Yes |
| `/self-improve` | Yes | ✅ Yes |
| Ad-hoc task (no workflow) | Yes | ✅ Yes |

> **Why the distinction:** `/build` → `/review` is an *internal* pipeline handoff, not
> a hand-back to the user. Emitting the section mid-loop would produce a
> recommendation based on unverified state, which the canonical rule forbids.
> A mid-loop `/build` already ends with its own `> **Next step:** Run /review` line.

### What counts as the closing summary

Any closing summary of the work performed, whatever its exact heading —
`## Completed Summary`, `✅ REVIEW — PASS`, an escalation report, a governance
report, or a plain prose wrap-up. If Cline is describing finished work and
handing control back, the `Recommended Next Step` section follows it.

---

## Where this fits the RAIL pipeline

The Recommended Next Step is the **hand-off artifact** of a completed RAIL cycle.
It is emitted *after* the Done criteria in `.clinerules/workflows/loop.md` are
checked and *after* the memory note is written, so the recommendation reflects the
final verified state rather than a mid-loop guess.

On an **escalation** (loop stopped after 5 iterations) the section is still
required — in that case the recommended step is the concrete action that would
unblock the escalated gap.

---

*Canonical source: `docs/rail-pipeline.md` · Continue equivalent:
`.continue/rules/recommended-next-step.md` · shared contract: `AGENTS.md` ·
three-concern map: `docs/ORGANIZATION.md`*
