# AGENTS.md — Operating Rules for USAi Chat

Concise, agent-facing instructions for working in this repository. For the full
project guide (architecture, structure, troubleshooting, references), see
[`.continue/rules/CONTINUE.md`](.continue/rules/CONTINUE.md).

USAi Chat = a **static vanilla-JS frontend** (`index.html`, `app.js`, `styles.css`)
served by a **small Python stdlib backend** (`server.py`) that proxies an
OpenAI-compatible API and provides local persistence. No build step, no framework.

---

## ⭐ Long-term memory (Obsidian "second brain") — ALWAYS

Treat the user's Obsidian vault as persistent long-term memory. Keep a running
history of conversations and key decisions there so context survives across
sessions.

- **Vault:** `OBSIDIAN_VAULT_PATH` = `/Users/ronaldbblake/Documents/Obsidian Vault`.
- **Where to write — depends on the writer (IMPORTANT):**
  - **You (the Continue extension in VS Code)** → save notes to
    **`Continue Extension/memories/`**.
  - The **USAi Chat web app** (its 💾 Remember button + in-app memory tools) writes
    to `USAi/memories/` on its own via the backend — **don't** write there yourself.
- **Access routes for Continue:** the `obsidian-mcp` server tools (`search-vault`,
  `create-note`, `edit-note`, `read-note`, `add-tags`). Create the
  `Continue Extension/memories/` directory if it doesn't exist.
- **Recall first:** at the start of a task, search the vault (both
  `Continue Extension/memories/` and `USAi/memories/`) for relevant prior context
  before answering.
- **Record continuously:** during/at the end of a task, save important facts,
  decisions, preferences, and a concise session summary to
  `Continue Extension/memories/` — without being asked.
- **Note conventions:** one note per session named `YYYY-MM-DD-HHMMSS-title.md`;
  **append** with `edit-note` rather than spawning duplicates; include YAML
  frontmatter (`title`, `created`, `tags`, `source`); tag consistently
  (`usai-chat`, `conversation-log`, + topic tags); link related notes with
  `[[wikilinks]]`. **Never delete/overwrite** existing notes; confine all writes
  to the memory subfolder.

---

## Agent pipeline (how we work)

Non-trivial changes flow through a five-role pipeline (full detail:
[`docs/testing-and-agents-strategy.md`](docs/testing-and-agents-strategy.md); each
role is an always-on rule in `.continue/rules/`):

1. **Code Planner** — present a brief plan (goal, files, approach, test plan, docs,
   risks) before editing. Skip only for trivial edits.
2. **Development SME** — implement idiomatically (conventions below).
3. **Full Test Suite** — add/update tests for the change (zero-dep stack).
4. **QA Review** — run **`/check`** and fix failures before declaring done. Checks
   live in `.continue/checks/`: test-coverage, security-review, code-quality-review,
   docs-in-sync, and ui-ux-review (frontend changes only).
5. **Continuous Improvement** — brief retro; propose new checks/rules/tests +
   backlog items; record a learning note to `Continue Extension/memories/`.

**Quality axis — Front-End Design (UI/UX):** when a change touches `index.html` or
`styles.css`, the auto-attached `.continue/rules/ui-ux-design.md` rule applies —
keep the UI accessible (WCAG AA, `:focus-visible`, semantic/ARIA, reduced-motion),
responsive, and token-driven using modern **vanilla** CSS (no framework/build/deps).
Consult Context7 (prefer **USWDS** `/uswds/uswds-site`) and cite what you applied;
the `ui-ux-review` check verifies it.

**After making changes, run `/check` and fix any failures before requesting
review.**

## Security (non-negotiable)

- **Never commit or echo secrets.** API keys live only in `.env` (git-ignored).
- `/config` must return **only non-secret fields** plus `has_*` boolean feature
  flags. The proxy injects the API key server-side — secrets never reach the
  browser.
- **Reject path traversal** and confine writes to the intended folder for any
  filesystem endpoint (`/memory/*`, `/sessions`, `/chunk-cache`).

## Coding conventions

- **Frontend:** plain HTML/CSS/JS only — no framework, no build step, no new
  runtime deps.
- **Backend:** Python **standard library + `python-dotenv` only**. Avoid heavy
  dependencies without strong justification.
- **Comments explain _why_,** not just _what_ — match the existing descriptive style.
- **CSS changes:** bump `styles.css?v=N` in `index.html` to bust the cache, then
  hard-refresh.
- **Tool gating:** new tools go in `TOOL_REGISTRY` (`app.js`) and must be gated in
  `getEnabledTools()` on their config + toggle.
- **New endpoints:** add a `_handler` on `EnvConfigHTTPRequestHandler` and register
  it in the `routes` dict of `do_GET`/`do_POST`/`do_DELETE`; validate input size.

## Running & validating

```bash
# Start (MUST use the venv so python-dotenv is available)
.venv/bin/python server.py        # then open http://localhost:8000

# Stop / free the port
lsof -ti:8000 | xargs kill
```

Validate changes with the zero-dependency test suite (see
[`docs/testing-and-agents-strategy.md`](docs/testing-and-agents-strategy.md)):

```bash
./run-tests.sh                     # syntax gates + JS (node --test) + Python (unittest)
```

Or run the pieces individually:

```bash
node --check app.js                                            # JS syntax
python3 -m py_compile server.py                                # Python syntax
node --test $(find tests/js -name '*.test.mjs')                # JS unit tests
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'   # Python unit tests
```

Watch the **Debug Logs** panel (top-right) and the `server.py` terminal for errors.

## Housekeeping

- Work `backlog.md` items roughly in priority order; check them off when done.
- Record notable changes in `CHANGELOG.md`; update `USER_GUIDE.md` for user-facing
  features.

---

*Detailed reference: [`.continue/rules/CONTINUE.md`](.continue/rules/CONTINUE.md).*
