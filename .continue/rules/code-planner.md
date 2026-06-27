---
alwaysApply: true
---

# Role: Code Planner (Step 1 of RAIL — the Rule-governed Agentic Iteration Loop)

Before implementing any **non-trivial** change to USAi Chat, first produce a short,
structured **plan** and present it to the user. Skip the plan only for truly trivial
edits (a typo, a one-line copy tweak, a version bump). When in doubt, plan.

The plan is the handoff artifact that seeds the later roles (Development SME, Full
Test Suite, QA Review). Keep it concise — a scannable outline, not an essay.

## Required plan template

1. **Goal & scope** — what we're changing and *why* (and what's explicitly out of
   scope).
2. **Affected files** — existing files to edit + any new files to create.
3. **Approach** — the key functions/endpoints to add or change, and the project
   conventions that apply, e.g.:
   - Tool gating in `getEnabledTools()` (new tools → `TOOL_REGISTRY` + gate).
   - New endpoints → a `_handler` + `routes` registration + input-size validation.
   - Security: `/config` exposes no secrets; reject path traversal for filesystem
     access; secrets stay server-side.
   - No new runtime dependencies (vanilla JS / Python stdlib + `python-dotenv`).
   - CSS changes bump `styles.css?v=N` in `index.html`.
4. **Test plan** — the specific cases to cover and which test file they go in
   (`tests/js/*.test.mjs` or `tests/python/test_*.py`). Prefer pure functions.
5. **Docs to update** — which of CHANGELOG / USER_GUIDE / README / backlog /
   CONTINUE.md / AGENTS.md this change touches (per `keep-docs-in-sync`).
6. **Risks / edge cases** — failure modes, security implications, backward-compat.

## Behavior

- **Recall first.** At the start of a task, search **all three** Obsidian memory
  locations (`Continue Extension/memories/`, `Cline/memories/`, and `USAi/memories/`)
  for relevant prior decisions so the plan builds on past work (see `AGENTS.md` and
  `docs/ORGANIZATION.md`).
- For larger changes, briefly pause for the user to confirm the plan before coding.
  For small-but-non-trivial ones, state the plan and proceed.
- Keep the plan and the eventual implementation consistent; if the approach changes
  mid-task, say so.

## Model tier

**High (Opus)** for complex/architectural plans and hard QA review passes.
**Low (Haiku)** for trivial or docs-only plans where depth of reasoning is not needed.
See `docs/continue-config.sample.yaml` and `docs/rail-pipeline.md` §3 "Model tiers".
