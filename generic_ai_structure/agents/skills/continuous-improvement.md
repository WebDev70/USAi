# Skill: Continuous Improvement

Use this skill after each non-trivial RAIL task and after any repeated review failure.

## Purpose

Continuous Improvement turns review evidence into durable process changes. It prevents the same gaps from recurring by updating prompts, tests, checklists, datasets, documentation, or backlog items.

## Inputs

- Completed task trace.
- Review checklist result.
- Gap list, if any.
- RAIL scorecard.
- User or stakeholder feedback.

## Required outputs

- Lessons learned.
- Repeated-gap analysis.
- Process update decisions.
- Follow-up entries for deferred work.
- Links to changed prompts, evals, checklists, datasets, docs, or backlog items.

## Improvement decision table

| Signal | Required action |
|---|---|
| Same gap appears twice | Update a prompt, checklist, test, or template. |
| Test missed a defect | Add or improve an eval/test case. |
| Prompt caused ambiguity | Update prompt metadata, instructions, examples, or constraints. |
| Dataset produced unreliable results | Update dataset quality notes, labels, splits, or expected outputs. |
| Security issue was found late | Add a shift-left security check. |
| Manual review was inconsistent | Tighten pass/fail policy or evidence requirements. |
| Work was deferred | Add a follow-up entry with owner, due date, and blocking/advisory status. |

## Procedure

1. Read the completed trace and review findings.
2. Identify gaps that are systemic rather than one-off mistakes.
3. Classify each improvement target as prompt, eval, checklist, dataset, tool, doc, or backlog.
4. Apply small, auditable updates when scope allows.
5. Record deferred improvements in the follow-up log.
6. Link the retrospective to the original task trace.

## Blocking failures

- A blocking gap is deferred without owner, rationale, or follow-up location.
- A repeated gap is recorded but no process improvement is proposed.
- Lessons learned are vague and not actionable.
- The task claims done while known required gates remain unresolved.
