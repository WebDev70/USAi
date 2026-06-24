---
name: Acceptance Criteria Met
description: Each stated acceptance criterion for a feature is satisfied and verifiable (product done, not just engineering done)
---

Review whether this **feature / user-facing change** actually meets its
**acceptance criteria**, per the Product Owner role
(`.continue/rules/product-owner.md`). This is the *product* gate — engineering green
(tests + other `/check`s) is necessary but **not sufficient**.

Apply this check only to **features / non-trivial user-facing work**. For pure
bugfixes (covered by a regression test), refactors, chores, and docs-only changes,
**pass**.

Pass only if **all** of these hold:

- **Every acceptance criterion is addressed.** Each criterion from the backlog item
  / plan maps to either an automated test or a clearly described, observable
  behavior in the change.
- **The behavior is user-observable.** The criteria describe what the *user* can
  see/do (a new toggle works, a button performs the action, an error is handled
  gracefully) — not merely that internal code exists.
- **No criterion is silently dropped.** If a criterion couldn't be met, the change
  explicitly says so and was re-scoped/deferred with the user's awareness (not
  quietly omitted).
- **User-facing docs reflect it.** New user-facing behavior is described in
  `docs/USER_GUIDE.md` (ties to `docs-in-sync`).

Flag as **failing** if a feature ships without satisfying its stated acceptance
criteria, if criteria were dropped without acknowledgement, or if "done" rests only
on passing tests with no demonstration of the user-visible outcome.
