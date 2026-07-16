# Agents

Store reusable agent behavior, skills, and tool descriptions here.

## Subfolders

| Folder | Purpose |
|---|---|
| `skills/` | Reusable capabilities, role descriptions, and operating procedures. |
| `tools/` | Tool contracts, manual tool checklists, and integration notes. |

## Core RAIL skills

- `skills/rail-roles.md` defines the role sequence from Product Owner readiness through Continuous Improvement.
- `skills/cross-cutting-concerns.md` defines security, configuration, observability, data, privacy, and UX concerns that apply inside every role.
- `skills/continuous-improvement.md` turns repeated gaps into durable process updates.
- `skills/governance-board.md` supports periodic project-level quality and drift review.
- `skills/housekeeping.md` keeps final artifacts discoverable and temporary work controlled.

## Tooling guidance

Use `tools/manual-tool-checklist.md` to record commands, manual checks, destructive-action safeguards, and full check-suite evidence.

## RAIL guidance

Agent files should answer:

- What role is this agent or skill playing?
- What inputs does it need?
- What outputs should it produce?
- What validation is required?
- What must it never do?
- Which cross-cutting concerns apply?
