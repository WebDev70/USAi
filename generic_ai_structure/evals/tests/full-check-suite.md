# Full Check-Suite Gate

Every target project should define one full check-suite command or checklist that represents the minimum required verification before done.

## Tool contract

| Check | Command or method | Required? | Pass condition | Evidence location |
|---|---|---|---|---|
| Syntax/compile |  | yes/no |  |  |
| Unit tests |  | yes/no |  |  |
| Integration/e2e tests |  | yes/no |  |  |
| Lint/format |  | yes/no |  |  |
| Type check |  | yes/no |  |  |
| Coverage/quality threshold |  | yes/no |  |  |
| Security scan |  | yes/no |  |  |
| Dependency scan |  | yes/no |  |  |
| Documentation check |  | yes/no |  |  |
| Prompt/eval check |  | yes/no |  |  |

## Pass/fail policy

- If a required check fails, the review fails.
- If a required check is skipped, the review fails unless a written justification is approved.
- If a command is unavailable, record the reason and use an approved manual fallback.
- Full check-suite evidence should be linked from the task trace.

## Recommended project script

Target projects may implement a wrapper such as:

```text
scripts/check.sh
```

The wrapper should run the required checks in a reproducible order and return non-zero on blocking failures.
