# Skill: Governance Board

Use this skill on a cadence, before major releases, or when project direction changes.

## Purpose

The Governance Board checks that the project is still aligned, secure, maintainable, and evidence-driven. It is not a replacement for per-task review; it detects drift across many tasks.

## Inputs

- Recent task traces.
- Follow-up log.
- RAIL and governance scorecards.
- Current roadmap, backlog, or release plan.
- Current prompts, datasets, evals, and agent skills.
- Security, dependency, and infrastructure evidence.

## Review areas

| Area | Questions |
|---|---|
| Strategy | Are current tasks aligned to user value and project goals? |
| Architecture | Are decisions coherent, documented, and reversible where possible? |
| Quality | Are test/eval gates improving confidence or accumulating blind spots? |
| Security | Are secrets, dependencies, permissions, and data handling controlled? |
| Data | Are raw and processed datasets traceable, labeled, and privacy-safe? |
| Prompts | Are prompt changes versioned, evaluated, and linked to expected behavior? |
| Operations | Are runbooks, configuration, and check commands current? |
| Housekeeping | Are stale specs, scratch files, and deferred items actively managed? |

## Procedure

1. Select a review window, such as the last sprint or last release.
2. Sample completed traces and gap lists.
3. Score the project with the governance scorecard.
4. Identify systemic risks and repeated quality failures.
5. Convert accepted recommendations into backlog items or immediate process updates.
6. Record decisions, owners, and due dates.

## Outputs

- Governance scorecard.
- Risk register updates or backlog items.
- Accepted process changes.
- Rejected recommendations with rationale.
- Next cadence date.

## Automatic escalation conditions

- Repeated blocking security gaps.
- Unreviewed prompt or dataset changes used in production decisions.
- Required checks skipped without documented approval.
- Follow-up items aging past their due date without owner response.
- Architecture or data-flow changes without an updated spec.
