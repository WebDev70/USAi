# Tool Use Policy

Use tools deliberately and record evidence.

## General rules

- Prefer read-only inspection before modification.
- Explain destructive or irreversible actions before running them.
- Use the smallest tool action that can complete the task safely.
- Record commands and outcomes in the task trace.
- Never paste secrets into prompts, traces, logs, datasets, or examples.

## Manual RAIL tool rhythm

1. Intake: inspect only what is needed to understand the request.
2. Plan: identify files, commands, checks, and risks before editing.
3. Build: make small changes and keep artifacts in the right folder.
4. Test: run targeted checks first, then the full check suite when appropriate.
5. Review: compare results with the spec and acceptance criteria.
6. Improve: update prompts, evals, checklists, datasets, or follow-ups when gaps repeat.

## Safety checks before destructive actions

- What exact path, record, account, dataset, or environment will be affected?
- Is there a backup, rollback, or dry run?
- Is explicit user approval required?
- Could this expose secrets or private data?
- Is the action recorded in the trace?

## Evidence requirements

For each material tool action, capture:

- Tool or command name.
- Purpose.
- Input target.
- Output summary.
- Pass/fail result.
- Link to detailed evidence when available.
