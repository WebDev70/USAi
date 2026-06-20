# USAi Chat

A lightweight browser-based chat interface for connecting to USAi-compatible model APIs.

## Project overview

This repository contains:
- `index.html` — static chat UI for sending prompts and receiving model responses
- `styles.css` — styling for the chat interface
- `app.js` — browser logic for model selection, request handling, and UI updates

- `server.py` — a simple backend server to proxy API requests and serve the UI
- `requirements.txt` — Python dependencies for the backend server


## How it works

The application consists of a static frontend (`index.html`, `app.js`, `styles.css`) and a simple Python backend (`server.py`).

The backend server has two primary roles:
1.  **Serve Static Files**: It serves the main HTML, CSS, and JavaScript files to the browser.
2.  **API Proxy**: It securely proxies API requests from the frontend to the configured `BASE_URL`. This avoids exposing the API key in the browser and bypasses potential CORS issues.



## Configuration via `.env`

Store your API settings in `.env` so the frontend does not require manual editing of `index.html`.
Create or update `.env` in the project root with values like:

```env
API_KEY=YOUR_API_KEY_HERE
BASE_URL=https://api.prod.gsai.mcaas.fcs.gsa.gov/
DEFAULT_MODEL=claude_3_haiku
DEFAULT_SYSTEM_PROMPT=
```

This file is ignored by git and is loaded by the local config server.

## context7 integration

You can configure context7 as a secondary context provider by adding the following to `.env`:

```env
CONTEXT7_API_KEY=YOUR_CONTEXT7_API_KEY
CONTEXT7_BASE_URL=https://api.context7.com
CONTEXT7_PATH=/v1/context
CONTEXT7_METHOD=GET
```

When configured, the frontend will call `/context7` on the backend and merge the returned context into the chat prompt.

## Obsidian long-term memory ("second brain")

The app can use an [Obsidian](https://obsidian.md/) vault as persistent long-term
memory, so the assistant can save and recall facts, preferences, and decisions
across conversations. Enable it by adding the following to `.env`:

```env
OBSIDIAN_VAULT_PATH=/absolute/path/to/your/Obsidian Vault
OBSIDIAN_MEMORY_SUBDIR=USAi
```

When configured, `/config` reports `has_obsidian: true`, the **Obsidian Memory**
and **Auto-recall memories** toggles light up, and a **💾 Remember** button appears
on each message. The app saves notes as tagged Markdown in
`<vault>/<OBSIDIAN_MEMORY_SUBDIR>/memories/` and **only ever reads/writes inside
that folder** — your other notes are never touched. See `USER_GUIDE.md` for usage.

### Two memory destinations (by writer)

This project is developed in **VS Code with the Continue extension**, and Continue
*also* uses the same Obsidian vault as its long-term memory. To keep the two
streams separate, notes are written to **different subfolders depending on who is
writing**:

| Writer | Saves to | Controlled by |
|--------|----------|---------------|
| **USAi Chat app** (this web app — 💾 button + in-app tools) | `USAi/memories/` | `.env` → `OBSIDIAN_MEMORY_SUBDIR=USAi` |
| **Continue extension** (dev/agent sessions in VS Code) | `Continue Extension/memories/` | `AGENTS.md` directive + the `obsidian-mcp` server |

The two never collide: the app's destination comes from `.env`, while Continue's
comes from the rules in `AGENTS.md`. See `AGENTS.md` for the full agent memory
directive.

## Running the frontend

1. **Install dependencies** (use a virtual environment so `python-dotenv` is
   available to the server):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Start the server** from the project root. **Use the venv's Python** so
   `python-dotenv` loads (otherwise you'll get `ModuleNotFoundError: No module
   named 'dotenv'`):

```bash
.venv/bin/python server.py        # or: activate the venv, then `python3 server.py`
```

To stop the server / free the port:

```bash
lsof -ti:8000 | xargs kill
```

3. **Open in Browser**

Navigate to `http://localhost:8000` in your web browser (hard-refresh with
Cmd/Ctrl+Shift+R after frontend changes).

## Running tests

The project follows **Test-Driven Development** and ships a **zero-runtime-dependency**
test suite — `node --test` (built into Node 18+) for `app.js` pure functions and the
Python standard-library `unittest` for `server.py` (both **unit** tests and **HTTP
integration** tests that boot the real server). Run everything with the helper
script:

```bash
./run-tests.sh             # syntax gates + JS tests + Python tests
./run-tests.sh --coverage  # also measure coverage and enforce gates
```

The `--coverage` mode enforces thresholds (**`server.py` ≥ 90%**, **JS branch ≥ 70%**
of the exported helpers) using **dev-only** tooling — `coverage.py` (installed in
the venv: `.venv/bin/pip install coverage`) and Node ≥ 22's built-in coverage. This
tooling is never added to `requirements.txt` and never ships in the app.

Or run the pieces individually:

```bash
node --check app.js && python3 -m py_compile server.py        # syntax gates
node --test $(find tests/js -name '*.test.mjs')               # JS unit tests
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'  # Python tests
```

Tests live in `tests/js/*.test.mjs` and `tests/python/test_*.py` (the Python HTTP
integration suites are `test_server_http.py`, `test_server_branches.py`, and
`test_server_proxy.py`). See
[`docs/testing-and-agents-strategy.md`](docs/testing-and-agents-strategy.md) for the
full TDD strategy and **RAIL** (*Rule-governed Agentic Iteration Loop*) — the
five-role agent pipeline (Code Planner → Development SME → Full Test Suite → QA
Review → Continuous Improvement) used for changes.

These same checks (including the coverage gates) also run automatically in **CI** on
every push / pull request via GitHub Actions (`.github/workflows/tests.yml`).

## Usage

Your **API key and Base URL come from `.env`**, so in most cases you can start
chatting right away — the key is injected server-side by the proxy and never sent
to the browser.

1. Pick a **model** (and optional **reasoning effort**) from the composer toolbar
   at the bottom.
2. Optionally set a **system prompt** in *Prompt & Parameters*.
3. Type a message and send it (**Enter** / **Ctrl+Enter**; **Shift+Enter** for a
   new line).

## Security notes

- Do not commit your API key or `.env` file to the repository.
- The local Python server acts as a proxy, so your `API_KEY` is not directly exposed to the browser. It is sent from the server to the target API endpoint.
- This setup is intended for local development. If you deploy this frontend publicly, ensure the server is properly secured and hardened.

## Recommended improvements

- The project now includes a basic backend proxy, which is a good first step. This could be further enhanced with more robust error handling and security features.
- The backend could be expanded to include user authentication, persistent storage, and other features.
- Implement stronger frontend validation and better response error handling.
- ~~Add automated tests for the Python server and the UI logic.~~ Started — see
  **Running tests** above and `docs/testing-and-agents-strategy.md` (backlog #17).
- Add documentation for environment variables and deployment.

## Notes

The repository contains a static frontend and a Python backend. Node.js is **not
required to run the app**, but it is used (Node 18+) for the optional `node --test`
JS unit tests.


