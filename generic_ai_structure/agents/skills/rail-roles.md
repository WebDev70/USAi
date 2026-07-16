# Skill: RAIL Roles

Use these roles sequentially for non-trivial work. The roles are manual and tool-agnostic; they can be performed by a human, an AI assistant, or both.

## Role 0: Product Owner Start Gate

Use for features and product-facing changes. Skip only when the change is a pure chore, refactor, or small docs edit.

Outputs:

- User story or goal.
- Acceptance criteria.
- Scope and out-of-scope list.
- Vertical slice decision.
- Priority or size.
- Definition of Ready decision.

Blocking failures:

- Acceptance criteria are not testable.
- Scope is unclear.
- Required dependencies or permissions are unknown.

## Role 1: Planner

Outputs:

- File impact list.
- Test-first plan.
- Docs/prompt/data update plan.
- Security and cross-cutting review plan.
- Risks and mitigations.
- Ordered todo list.

Blocking failures:

- No test or verification plan for non-trivial behavior.
- No security consideration for security-sensitive work.
- No plan to update user-facing or developer docs when behavior changes.

## Role 2: SME or Developer

For user-facing frontend or interaction changes, include a **UX & UI SME** pass before and during implementation. Treat UX and UI as two related but separate disciplines:

- **UX sub-discipline, how it works:** state the user need or job-to-be-done; map the user flow for multi-step interactions; confirm information architecture and control placement against the target project's user guide or product docs; audit friction, empty/error/recovery states, and task completion.
- **UI sub-discipline, how it looks:** apply the target project's design system, tokens, accessibility requirements, responsive behavior, keyboard/focus behavior, motion preferences, and frontend implementation constraints without adding unapproved runtime surface.

Outputs:

- Design notes.
- UX notes for user-facing changes: user need, flow, information architecture decision, friction audit, and task-completion check.
- UI notes for user-facing changes: visual/design-system alignment, accessibility, responsive behavior, focus behavior, motion handling, and implementation-constraint check.
- Implementation.
- Refactor notes where relevant.

Default implementation loop:

1. Red: write or identify a failing check.
2. Green: make the minimal change.
3. Refactor: clean up while checks stay green.

Blocking failures:

- Implementation expands beyond scope without recording a decision.
- Tests are bypassed without justification.
- Secrets or unsafe data are exposed.
- A user-facing control or interaction is added with no stated user goal.
- A multi-step interaction is added with no described user flow.
- A control is placed in the wrong information-architecture location without a documented product rationale.

## Role 3: Tester

Outputs:

- Test evidence.
- Coverage or quality evidence where available.
- Manual verification notes where automation is not practical.
- No-test justification when tests are not feasible.

Blocking failures:

- Required test runner fails.
- Bug fix lacks regression evidence when regression testing is practical.
- New behavior has no verification path.

## Role 4: Security

Outputs:

- Secret-handling check.
- Dependency or supply-chain check.
- Abuse-case review.
- Permission and data-boundary review.
- Logging/trace privacy review.

Blocking failures:

- Secrets, credentials, private keys, or tokens are exposed.
- External calls, file access, or permissions are unsafe.
- Known vulnerable dependency is introduced without an approved exception.

## Role 5: Reviewer

Outputs:

- Full gate results.
- Spec-compliance decision.
- Pass/fail decision.
- Specific gap list.
- Required fixes.
- Deferred follow-ups.

Blocking failures:

- Acceptance criteria are unmet.
- Full check suite fails.
- Security review has blocking findings.
- Gap list contains unresolved blocking items.

## Role 6: Product Owner Acceptance Gate

Use at the end of feature and product-facing changes.

Outputs:

- Acceptance criteria verification table.
- PASS/FAIL acceptance decision.
- Deferred scope decisions.

Blocking failures:

- Any required acceptance criterion is unmet.
- Verification evidence is absent.

## Role 7: Continuous Improvement

Outputs:

- Lessons learned.
- Prompt updates to consider.
- New tests or checks to add.
- Process gaps to fix.
- Follow-up or backlog items.

Rule:

If the same class of issue appears twice, propose a durable process improvement: prompt update, new eval, new checklist item, new automation, or backlog item.
