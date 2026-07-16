# Manual Tool Checklist

Use this checklist when a project does not have automated agent-tool integration.

## Tool inventory

| Tool or command | Purpose | Risk level | Required evidence |
|---|---|---|---|
|  |  | low/medium/high |  |

## Full check-suite contract

Before declaring a non-trivial task done, identify the target project's one-command check or write the manual equivalent from `../../evals/tests/full-check-suite.md`.

Record:

- Command or manual check name.
- Working directory or environment.
- Expected outcome.
- Actual outcome.
- Failure output or screenshot location, if applicable.
- Justification for any skipped check.

## Per-task evidence

- Tools used:
- Commands run:
- Files read:
- Files changed:
- Checks performed:
- Results:
- Follow-up required:

## Tool safety

Before destructive actions:

- Confirm target path or system.
- Confirm backup or rollback plan.
- Confirm user approval if data loss is possible.
- Record action in the task trace.

## Security constraints

- Do not paste secrets into prompts or traces.
- Redact private values from command output.
- Prefer read-only commands during discovery.
- Treat unexpected external network access as a security review item.
