# TDD Evidence Gate

Use for non-trivial testable logic and bug fixes.

## Required evidence

| Evidence type | Required when | Evidence |
|---|---|---|
| Red evidence | New testable behavior or bug fix |  |
| Green evidence | After implementation |  |
| Refactor evidence | After cleanup |  |
| Regression evidence | Bug fix |  |
| No-test justification | Test not practical |  |

## Red evidence

Record the failing test/check before implementation:

```text
Command or check:
Expected failure:
Actual failure:
Why this proves the behavior is missing or broken:
```

## Green evidence

Record passing evidence after implementation:

```text
Command or check:
Result:
Relevant output:
```

## Refactor evidence

Record checks after cleanup:

```text
Refactor performed:
Checks rerun:
Result:
```

## No-test justification

Use only when automation is not practical:

```text
Why no automated test is practical:
Manual verification performed:
Risk accepted:
Follow-up automation opportunity:
```

## Blocking failures

- Missing Red evidence for a practical bug regression test.
- Missing Green evidence after implementation.
- No-test decision without justification.
