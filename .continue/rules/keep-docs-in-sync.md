---
alwaysApply: true
---

When you make a meaningful change to this project (USAi Chat), update the relevant documentation IN THE SAME turn as the code change — never leave docs stale. Treat docs as part of "done."

Update targets (only the ones a change actually affects):
- **CHANGELOG.md** — add an entry under `## [Unreleased]` for any notable code/behavior change (what changed + which files). This is the default for almost every change.
- **USER_GUIDE.md** — update when a USER-FACING feature is added/changed (new toggle, button, setting, workflow). Keep it end-user friendly.
- **README.md** — update when setup, `.env` variables, run/stop commands, or high-level architecture change.
- **backlog.md** — check off `[x]` items you complete (or mark `[~]` in progress); add new follow-ups discovered along the way.
- **.continue/rules/CONTINUE.md** — update when project structure, key concepts, conventions, common tasks, or troubleshooting change.
- **AGENTS.md** — update only when agent operating rules, security rules, coding conventions, or the memory directive change.

Conventions:
- Match each doc's existing style/format and section structure; don't restructure unnecessarily.
- When you change \`styles.css\`, also bump \`styles.css?v=N\` in \`index.html\` (and you may note it in CHANGELOG).
- Keep entries concise and explain WHY, not just WHAT.
- If a change touches nothing user-facing (pure refactor), at minimum add a CHANGELOG line.
- At the end of a task, briefly tell the user which docs you updated (or state "no doc updates needed" and why).
- Do not duplicate the same content across docs — link between them (e.g. AGENTS.md ↔ CONTINUE.md) instead.
