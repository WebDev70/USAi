---
name: Definition of Ready
description: Feature work has a user story, testable acceptance criteria, a vertical slice, size, and no blocking unknowns
---

Review whether this **feature / user-facing change** was *ready* to build, per the
Product Owner role (`.continue/rules/product-owner.md`) and the Agile workflow
(`.continue/rules/agile-workflow.md`).

Apply this check only to **features / non-trivial user-facing work**. For pure
bugfixes, refactors, chores, and docs-only changes, **pass** (Definition of Ready
does not apply).

Pass only if the change (via its `backlog.md` item, plan, or PR description) shows:

- **A user story / clear value** — who benefits and why (*As a `<user>`, I want
  `<capability>`, so that `<value>`*), not just a technical task.
- **Testable acceptance criteria** — concrete, user-observable conditions for done
  (Given/When/Then or a clear bullet list), *distinct from* "tests pass."
- **A vertical slice** — the change delivers end-to-end user-visible value, not a
  dangling horizontal layer. (An oversized epic should have been split, with slices
  recorded in `backlog.md`.)
- **Size & priority** — a rough size and a sensible place in `backlog.md` priority
  order.
- **No unaddressed blocking unknowns** — external deps / model IDs / design
  decisions are resolved or explicitly deferred.

Flag as **failing** if a feature was built with no stated user value, no acceptance
criteria, or as a non-shippable horizontal layer with no user-visible payoff.
