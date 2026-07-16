# Gap List Template and Loop Protocol

Use when review fails or advisory issues need tracking.

## Gap format

| Field | Value |
|---|---|
| Gap ID | GAP-001 |
| Category | readiness | spec | test | security | dependency | iac | code-quality | docs | ui-ux | housekeeping | process |
| Severity | blocking | advisory |
| Evidence |  |
| Affected artifact |  |
| Required fix |  |
| Owner |  |
| Status | open | fixed | deferred | accepted-risk |
| Verification method |  |

## Gap list

| ID | Severity | Category | Evidence | Required fix | Status |
|---|---|---|---|---|---|
| GAP-001 | blocking |  |  |  | open |

## Review-fix-rerun loop

1. Reviewer records specific, actionable gaps.
2. Builder fixes blocking gaps only after understanding the evidence.
3. Tester reruns targeted checks for the fix.
4. Reviewer reruns relevant gates and full check-suite when appropriate.
5. Loop repeats until no blocking gaps remain.
6. Advisory gaps may be deferred only if they are tracked in `evals/traces/follow-up-log.md` or the target project's backlog.

## Quality rule

A vague gap is invalid. Do not write “fix tests” or “improve docs.” Name the artifact, failing check, missing evidence, or criterion and the required fix.
