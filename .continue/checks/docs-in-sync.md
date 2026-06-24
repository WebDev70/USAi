---
name: Docs In Sync
description: Documentation was updated in the same change, per the keep-docs-in-sync rule
---

Review this change for **documentation sync**, per
`.continue/rules/keep-docs-in-sync.md`. Docs are part of "done."

Pass the check only if the docs that this change *actually affects* were updated in
the same change:

- **CHANGELOG.md** — an entry under `## [Unreleased]` exists for any notable
  code/behavior change (this is expected for almost every non-trivial change).
- **`docs/USER_GUIDE.md`** — updated when a user-facing feature was added/changed
  (new toggle, button, setting, or workflow).
- **README.md** — updated when setup, `.env` variables, run/stop commands, or
  high-level architecture changed.
- **backlog.md** — relevant items checked off (`[x]`) or marked in progress (`[~]`),
  and new follow-ups recorded.
- **.continue/rules/CONTINUE.md** — updated when project structure, key concepts,
  conventions, common tasks, or troubleshooting changed.
- **AGENTS.md** — updated when agent operating rules, security rules, conventions,
  or the memory directive changed.

Also flag as **failing** if the same content was duplicated across docs instead of
linking between them.

Flag as **failing** if a change clearly needed a doc update (e.g. a new feature with
no CHANGELOG entry, or a new `.env` var not documented in README) and none was made.
If the change is trivial (typo, comment-only) or touches nothing documented, pass.
