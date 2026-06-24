---
alwaysApply: true
---

# Role: Agile Workflow (how we slice, size, and finish work)

This rule defines the **Agile working agreements** that wrap the RAIL pipeline
(`docs/rail-pipeline.md`). It complements the Product Owner role
(value & acceptance) with the team-level practices every change follows.

## Vertical slices over horizontal layers

Prefer changes that deliver **end-to-end, user-visible value** in one increment
(UI + endpoint + tests + docs) over building a layer that can't be used yet. If an
item is too big for one slice, split it into independently shippable slices and
record them in `backlog.md`.

## Backlog discipline (`backlog.md` is the single source of truth)

- Work items roughly in **priority order**; mark `[~]` when in progress and `[x]`
  when done (with a short "Done:" note of what shipped + files), per existing
  convention.
- When you discover follow-up work mid-task, **add a new backlog item** rather than
  silently expanding the current one (avoid scope creep).
- Each non-trivial feature item should carry **acceptance criteria** (Product Owner
  role) so "done" is unambiguous.

## Definition of Done (DoD) — the single finish line

A change is **Done** only when **all** of these hold (the `definition-of-done`
check asserts them):

1. **Tests-first & green.** New/changed logic has tests written first (TDD:
   Red→Green→Refactor); `./run-tests.sh` passes.
2. **Coverage gates pass.** `./run-tests.sh --coverage` meets thresholds
   (`server.py` ≥ 90%, JS branch ≥ 70%).
3. **Security gate passes.** `./scripts/security-scan.sh` is clean (or findings are
   triaged), and no runtime dependency was added (`docs/principles.md` §1).
4. **QA `/check` passes.** All applicable checks in `.continue/checks/` are green.
5. **Acceptance criteria met** (for features) — verified by the Product Owner role.
6. **Docs in sync** (`keep-docs-in-sync`): CHANGELOG always; USER_GUIDE/README/
   backlog/CONTINUE/AGENTS as applicable.
7. **Memory note recorded** to `Continue Extension/memories/` (Continuous
   Improvement role).

## Cadence & continuous improvement

- Treat each completed backlog item as a mini-iteration: finish it through the full
  DoD before starting the next.
- The Continuous Improvement role runs a brief retro and proposes new
  rules/checks/tests + backlog items — feeding the loop back to the Product Owner.
