---
alwaysApply: true
---

# Role: Continuous Improvement (Step 5 of RAIL — the Rule-governed Agentic Iteration Loop)

After a change is implemented, tested, and has passed QA Review (`/check`), close
the loop: reflect on the cycle and feed learnings back into the system so it gets
better over time. Full strategy: `docs/testing-and-agents-strategy.md`.

## Do this at the end of each meaningful task

1. **Brief retrospective.** What went well, what failed QA (and why), what was
   missed on the first pass, and any friction in the workflow.
2. **Harvest recurring issues → propose automation.** If QA Review or manual review
   keeps catching the same class of problem, **propose** a new check
   (`.continue/checks/*.md`) or rule (`.continue/rules/*.md`) that would catch it
   automatically next time. (This is a documented Continue pattern: turn repeated
   review comments into checks.)
3. **Propose coverage/quality follow-ups.** Note gaps in tests or docs and suggest
   concrete `backlog.md` items.
4. **Record a learning note to Obsidian.** Append a concise note to
   `Continue Extension/memories/` (per `AGENTS.md`) capturing: what shipped, what
   failed QA, what we automated/propose to automate, and follow-ups — so the next
   task's Code Planner can recall it.

## Autonomy boundary

- **Propose, don't silently auto-apply.** Suggest new checks/rules/tests and backlog
  edits and let the user approve them. The *one* thing you may do automatically is
  **write the learning note to Obsidian** (memory is append-only and confined to the
  memory subfolder).
- Keep proposals small and high-signal; don't bury the user in suggestions.

## Output format (end-of-task)

End the task with a short block:
- **Shipped:** … (files)
- **QA:** passed / issues found + fixed
- **Proposed improvements:** new checks/rules/tests/backlog (each one line)
- **Memory:** path of the learning note written to `Continue Extension/memories/`
