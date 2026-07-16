# Evals

Store proof that the AI system, workflow, or project change works.

## Subfolders

| Folder | Purpose |
|---|---|
| `tests/` | Test plans, expected behaviors, fixtures, gates, and manual checklists. |
| `traces/` | Execution logs, decision traces, prompt-response examples, retrospectives, and review evidence. |
| `scorecards/` | Rubrics and completed evaluation scorecards. |

## Core RAIL gates

Use these files as the default high-assurance review contract:

- `tests/definition-of-ready.md` for readiness before feature/product work begins.
- `tests/full-check-suite.md` for required deterministic and manual checks.
- `tests/spec-compliance-check.md` for comparing delivered artifacts against the task spec.
- `tests/tdd-evidence.md` for Red → Green → Refactor or regression evidence.
- `tests/security-review.md` for secrets, boundaries, dependencies, logging, and abuse cases.
- `tests/eval-dataset-quality.md` for dataset provenance, splits, labels, and expected outputs.
- `tests/prompt-change-checklist.md` for prompt metadata and eval linkage.
- `tests/housekeeping-checklist.md` for leave-no-trace review.
- `tests/definition-of-done.md` for final completion criteria.
- `tests/gap-list-template.md` for review-fix-rerun loops.
- `tests/rail-review-checklist.md` for the consolidated final review.

## Evidence artifacts

Every non-trivial task should leave behind enough evidence for a reviewer to answer:

- What was supposed to happen?
- What was changed?
- What checks were run?
- What passed?
- What failed or was deferred?
- What should improve next time?

Use `traces/trace-template.md` for task evidence, `traces/retro-template.md` for retrospectives, and `traces/follow-up-log.md` for deferred work.

## Scorecards

- `scorecards/rail-scorecard.md` scores per-task RAIL execution and includes automatic fail conditions.
- `scorecards/governance-scorecard.md` scores project-level drift and process health on a cadence.
