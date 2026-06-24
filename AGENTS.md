# AGENTS.md — Shared Operating Contract

> **Scope: ALL agent harnesses** — this file is read by both the *Continue* VS Code
> extension and the *Cline* VS Code extension. It defines the rules that apply
> regardless of which harness is in use. See `docs/ORGANIZATION.md` for the full
> three-concern map (USAi Chat app / Continue harness / Cline harness).

USAi Chat = a **static vanilla-JS frontend** (`index.html`, `app.js`, `styles.css`)
served by a **small Python stdlib backend** (`server.py`) that proxies an
OpenAI-compatible API and provides local persistence. No build step, no framework.

For harness-specific reference:
- **Continue harness** → `.continue/rules/CONTINUE.md` (rules, checks, agents)
- **Cline harness** → `.clinerules/rail-pipeline.md` (workflows: `/spec`, `/build`,
  `/review`, `/loop`)

---

## ⭐ Long-term memory (Obsidian "second brain") — ALWAYS

Treat the user's Obsidian vault as persistent long-term memory. Keep a running
history of conversations and key decisions there so context survives across
sessions.

- **Vault:** the path set in `OBSIDIAN_VAULT_PATH` in your `.env` (e.g. `/path/to/your/Obsidian Vault`)
- **Three separate writers — each writes to its OWN subfolder (NEVER the others'):**

| Writer | Saves to | Controlled by |
|--------|----------|---------------|
| **USAi Chat app** (💾 button + in-app tools) | `USAi/memories/` | `.env → OBSIDIAN_MEMORY_SUBDIR=USAi` |
| **Continue extension** (VS Code Continue sessions) | `Continue Extension/memories/` | This file (Continue reads it) |
| **Cline extension** (VS Code Cline sessions) | `Cline/memories/` | `.clinerules/rail-pipeline.md` (Cline reads it) |

- **Access routes (in priority order — applies to whichever harness is running):**
  1. **Direct filesystem I/O — PRIMARY (most reliable).** The vault is just a
     folder on disk. Read/write notes directly under the vault path. This needs no
     Node process or stdio pipe, never times out, and Obsidian auto-indexes the files.
     **Prefer this for memory reads/writes.**
  2. **`obsidian-mcp` server tools — OPTIONAL/SECONDARY.** Use `search-vault`,
     `create-note`, `edit-note`, `read-note`, `add-tags` only when you need richer
     tag/note operations. The stdio server is known to intermittently time out with
     JSON-RPC `-32001`; when it does, fall back to (1).
- **Recall first:** at the start of any non-trivial task, search **all three** memory
  locations (`USAi/memories/`, `Continue Extension/memories/`, `Cline/memories/`)
  for relevant prior context before answering.
- **Record continuously:** during/at the end of a task, save important facts,
  decisions, preferences, and a concise session summary to your harness's subfolder —
  without being asked.
- **Note conventions:** one note per session named `YYYY-MM-DD-HHMMSS-title.md`;
  **append** rather than spawning duplicates; include YAML frontmatter (`title`,
  `created`, `tags`, `source`); tag consistently (`usai-chat`, `conversation-log`,
  + topic tags); link related notes with `[[wikilinks]]`. **Never delete/overwrite**
  existing notes; confine all writes to your harness's memory subfolder.

---

## Agent pipeline — RAIL (how we work)

Non-trivial changes flow through **RAIL** (*Rule-governed Agentic Iteration Loop*).
Full concept reference: [`docs/rail-pipeline.md`](docs/rail-pipeline.md).
Principles: [`docs/principles.md`](docs/principles.md).

The RAIL roles (both harnesses implement the same roles):

0. **Product Owner** *(features only)* — gate start with **Definition of Ready**
   (user story, testable acceptance criteria, vertical slice, size); gate end with
   **acceptance** (criteria met). Skip for pure bugfixes/chores/refactors.
1. **Code Planner** — present a brief plan (goal, files, approach, **tests to write
   first**, docs, risks) before editing. Skip only for trivial edits.
2. **Development SME / Architect** — validate design against USAi conventions,
   then implement TDD-style: Red → Green → Refactor. Security is woven in.
3. **Tester** — add/update tests (zero-dep stack: stdlib `unittest` + `node --test`).
   Coverage is gated.
4. **Security** — run `./scripts/security-scan.sh` (gitleaks + bandit + pip-audit).
5. **Reviewer (QA)** — run the full check suite and fix failures before declaring done.

**Cross-cutting principles** (see `docs/principles.md`): **DevSecOps** — security
shifted left and machine-enforced; **IaC** — environment is declarative and
reproducible (`Dockerfile`/`docker-compose.yml`/`Makefile`); **Observability** —
log via `add_log`, never log secrets.

**How each harness runs the RAIL QA gate:**
- **Continue:** run **`/check`** (VS Code) or `./scripts/cli-check.sh` (CLI).
  Checks live in `.continue/checks/`.
- **Cline:** run **`/review`** workflow. See `.clinerules/workflows/review.md`.

---

## Security (non-negotiable)

- **Never commit or echo secrets.** API keys live only in `.env` (git-ignored).
- `/config` must return **only non-secret fields** plus `has_*` boolean feature
  flags. The proxy injects the API key server-side — secrets never reach the browser.
- **Reject path traversal** and confine writes to the intended folder for any
  filesystem endpoint (`/memory/*`, `/sessions`, `/chunk-cache`).
- **SSRF guard:** the proxy / Context7 only reach **http(s)** upstreams
  (`is_safe_upstream_url` in `server.py`).
- **Run the deterministic scan** for non-trivial changes:
  `./scripts/security-scan.sh` (or `make scan`) — gitleaks + bandit + pip-audit;
  don't weaken/disable a scanner to pass.

---

## Coding conventions

- **Minimal, audited *runtime* surface:** frontend is plain HTML/CSS/JS (no
  framework/build/runtime deps); backend is Python **stdlib + `python-dotenv` only**.
  Dev/CI tooling that ships nothing into the app is allowed/encouraged (coverage,
  bandit, pip-audit, gitleaks, Docker, make) — see `docs/principles.md` §1.
- **Comments explain _why_,** not just _what_ — match the existing descriptive style.
- **CSS changes:** bump `styles.css?v=N` in `index.html` to bust the cache.
- **Tool gating:** new tools go in `TOOL_REGISTRY` (`app.js`) and must be gated in
  `getEnabledTools()` on their config + toggle.
- **New endpoints:** add a `_handler` on `EnvConfigHTTPRequestHandler` and register
  it in the `routes` dict of `do_GET`/`do_POST`/`do_DELETE`; validate input size.

---

## Running & validating

```bash
# Start (MUST use the venv so python-dotenv is available)
.venv/bin/python server.py        # then open http://localhost:8000

# Stop / free the port
lsof -ti:8000 | xargs kill
```

Validate changes with the zero-dependency test suite:

```bash
./run-tests.sh                     # syntax gates + JS (node --test) + Python (unittest)
./run-tests.sh --coverage          # the above + coverage gates (server.py ≥ 90%, JS branch ≥ 70%)
```

Or run the pieces individually:

```bash
node --check app.js                                            # JS syntax
python3 -m py_compile server.py                                # Python syntax
node --test $(find tests/js -name '*.test.mjs')                # JS unit tests
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'   # Python unit tests
```

---

## Housekeeping

- Work `backlog.md` items roughly in priority order; check them off when done.
- Record notable changes in `CHANGELOG.md`; update [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for user-facing
  features.

---

*Full project organization (three concerns + shared pieces): [`docs/ORGANIZATION.md`](docs/ORGANIZATION.md).*
*Continue harness reference: [`.continue/rules/CONTINUE.md`](.continue/rules/CONTINUE.md).*
*Cline harness reference: [`.clinerules/rail-pipeline.md`](.clinerules/rail-pipeline.md).*
