# Generic AI Project Structure with High-Assurance Manual RAIL

This folder is a portable, tool-agnostic project structure for running RAIL manually in any AI-assisted project.

RAIL means Rule-governed Agentic Iteration Loop. It is a quality system for moving from a request to reviewed, tested, documented, secure, and continuously improved work.

## Folder model

```text
generic_ai_structure/
├── prompts/
│   ├── system/
│   ├── tasks/
│   └── tools/
├── data/
│   ├── raw/
│   └── processed/
├── agents/
│   ├── skills/
│   └── tools/
└── evals/
    ├── tests/
    ├── traces/
    └── scorecards/
```

## How RAIL maps to the four folders

| Folder | Job | RAIL use |
|---|---|---|
| `prompts/` | Versioned prompt files | Stores reusable system prompts, task prompts, prompt templates, and tool-use policies. |
| `data/` | Inputs the AI reads | Stores raw source material, processed context packs, eval datasets, and durable follow-up/backlog context. |
| `agents/` | Agent configs, skills, tools | Stores role definitions, cross-cutting skills, governance skills, and manual tool contracts. |
| `evals/` | Proof the AI actually works | Stores readiness/done gates, QA checks, traces, scorecards, gap lists, retros, and evaluation evidence. |

## High-assurance manual RAIL lifecycle

1. Intake: classify the request, confirm value, and identify whether a Product Owner gate is required.
2. Definition of Ready: confirm user story, testable acceptance criteria, vertical slice, scope, size, risks, and dependencies.
3. Spec: write a short task spec for non-trivial work.
4. Plan: identify affected files, tests to write first, docs, security concerns, data impacts, and risks.
5. Build: implement in small slices using Red → Green → Refactor for testable logic.
6. Review: run the full check suite, spec-compliance check, QA gates, security review, and housekeeping gate.
7. Product Owner acceptance: verify each acceptance criterion with test evidence or observable behavior.
8. Definition of Done: confirm all blocking gates pass and all deferred items are tracked.
9. Continuous Improvement: record lessons, update prompts/tests/checklists, and capture follow-ups.
10. Cadence review: periodically run governance and housekeeping checks for project-level drift.

## Start here

1. Read `prompts/system/rail-system.md`.
2. Use `prompts/tasks/rail-task-template.md` for each non-trivial task.
3. Use `agents/skills/rail-roles.md` to step through the roles.
4. Use `evals/tests/definition-of-ready.md` before implementation.
5. Use `evals/tests/rail-review-checklist.md` during review.
6. Use `evals/tests/definition-of-done.md` before declaring done.
7. Use `evals/traces/trace-template.md` and `evals/traces/retro-template.md` to preserve evidence and lessons.
8. Score the outcome with `evals/scorecards/rail-scorecard.md`.

## Blocking vs advisory findings

- Blocking findings must be fixed before the task is marked done.
- Advisory findings may be deferred only when they are recorded in `evals/traces/follow-up-log.md` or the target project's backlog.
- Security secrets, unmet acceptance criteria, missing required tests without justification, and failed full-check-suite gates are blocking by default.
