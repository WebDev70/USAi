# Spec Compliance Check

Use this during review to compare the completed work against the task spec.

## Compliance matrix

| Spec section | Review question | Evidence | Result |
|---|---|---|---|
| Goal/scope | Does the result solve the stated goal and avoid out-of-scope work? |  | pass/fail |
| Acceptance criteria | Is every acceptance criterion verified by test or observable behavior? |  | pass/fail |
| Affected files/artifacts | Were all planned artifacts changed or explained? |  | pass/fail |
| Test plan | Were planned tests/evals created and run or explained? |  | pass/fail |
| Technical approach | Was the planned approach followed, or was a deviation documented? |  | pass/fail |
| Docs/prompts/data | Were required supporting artifacts updated? |  | pass/fail |
| Risks | Were listed risks mitigated or accepted? |  | pass/fail |

## Scope creep check

Record any changed artifact not listed in the spec:

| Extra artifact | Why changed? | Acceptable? | Follow-up needed? |
|---|---|---|---|
|  |  | yes/no |  |

## Blocking failures

Spec compliance fails if:

- A required acceptance criterion is unmet.
- Planned tests or evals are missing without justification.
- Out-of-scope work was introduced without approval.
- Security-sensitive changes were made without review.
- Required docs, prompt, or data updates are missing.
