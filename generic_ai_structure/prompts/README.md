# Prompts

Store every reusable prompt as a real versioned file.

## Subfolders

| Folder | Purpose |
|---|---|
| `system/` | Durable operating instructions and role behavior. |
| `tasks/` | Reusable task templates for specs, plans, reviews, and retrospectives. |
| `tools/` | Prompt-level policies for using project tools safely and consistently. |

## Prompt template

Use `prompt-template.md` for reusable prompts. Each prompt should include:

- Name, version, owner, status, and changelog entry.
- Related RAIL role.
- Related evals and datasets.
- Input constraints and output contract.
- Guardrails, known failure modes, and eval coverage.

## RAIL guidance

Prompts should make the expected RAIL role explicit:

- Product Owner for readiness and acceptance criteria.
- Planner for scope, affected files, tests, docs, and risks.
- SME or Developer for design and implementation.
- Tester for test strategy and evidence.
- Security for threat review and deterministic scans.
- Reviewer for final gap analysis.
- Continuous Improvement for lessons and process updates.

Prompt changes should run `../evals/tests/prompt-change-checklist.md` and link to relevant eval evidence.
