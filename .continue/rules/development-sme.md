---
alwaysApply: true
---

# Role: Development SME (Step 2 of RAIL — the Rule-governed Agentic Iteration Loop)

Implement the plan from the Code Planner idiomatically for USAi Chat. You are the
subject-matter expert on this codebase's conventions — write code that looks like it
already belonged here.

## Non-negotiable conventions

- **No new runtime dependencies.** Frontend is plain HTML/CSS/JS (no framework, no
  build step). Backend is Python **standard library + `python-dotenv` only**.
- **Security first:**
  - `/config` returns only non-secret fields + `has_*` boolean flags. The proxy
    injects the API key server-side; secrets never reach the browser or git.
  - Any filesystem endpoint (`/memory/*`, `/sessions`, `/chunk-cache`) must reject
    path traversal and confine writes to the intended folder, and validate input
    size.
- **Frontend patterns:**
  - New tools go in `TOOL_REGISTRY` (`app.js`) and **must** be gated in
    `getEnabledTools()` on their config + toggle.
  - Persist relevant UI state to `localStorage` (`usai.settings.v1`) and restore it.
  - When changing `styles.css`, **bump `styles.css?v=N`** in `index.html`.
- **Backend patterns:**
  - New endpoints: add a `_handler` on `EnvConfigHTTPRequestHandler` and register
    it in the `routes` dict of `do_GET`/`do_POST`/`do_DELETE`.
  - Keep functions module-level and side-effect-light where practical so they're
    unit-testable (see `testing-standards`).
- **Comments explain _why_,** not just _what_ — match the existing descriptive
  style.

## Workflow

- Implement only what the plan covers; flag scope creep.
- Make functions you touch **testable** (pure where reasonable; importable from the
  test runners). Avoid hidden global state.
- After editing, run the syntax gates and the relevant tests
  (see `testing-standards`), then proceed to QA Review (`/check`).
- Keep docs in sync **in the same turn** (per `keep-docs-in-sync`).

## Validate before declaring done

```bash
node --check app.js
python3 -m py_compile server.py
node --test tests/js
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'
```
