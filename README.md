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
BASE_URL=https://your-openai-compatible-endpoint/
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

To enable **semantic (embeddings-based) memory re-ranking**, also add:

```env
EMBED_MODEL=text-embedding-3-small   # any OpenAI-compatible embedding model
EMBED_INPUT_TYPE=search_document     # optional; Cohere-style hint
```

When `EMBED_MODEL` is set, `/config` reports `has_embeddings: true` and memory
search results are automatically re-ranked by cosine similarity. Falls back to
keyword ranking silently when not set.

When configured, `/config` reports `has_obsidian: true`, the **Obsidian Memory**
and **Auto-recall memories** toggles light up, and a **💾 Remember** button appears
on each message. The app saves notes as tagged Markdown in
`<vault>/<OBSIDIAN_MEMORY_SUBDIR>/memories/` and **only ever reads/writes inside
that folder** — your other notes are never touched. See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for usage.

### Three separate memory destinations (by writer)

This project is developed with two VS Code AI extensions (Continue and Cline), and
all three writers share the vault but use **separate subfolders** so notes never
collide:

| Writer | Saves to | Controlled by |
|--------|----------|---------------|
| **USAi Chat app** (this web app — 💾 button + in-app tools) | `USAi/memories/` | `.env → OBSIDIAN_MEMORY_SUBDIR=USAi` |
| **Continue extension** (VS Code dev sessions) | `Continue Extension/memories/` | `AGENTS.md` memory directive |
| **Cline extension** (VS Code dev sessions) | `Cline/memories/` | `.clinerules/rail-pipeline.md` |

See `AGENTS.md` for the shared agent memory directive, and `docs/ORGANIZATION.md`
for the full three-concern map (app / Continue / Cline).

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

### Or run it with Docker (declarative, reproducible — Infrastructure as Code)

The app ships a `Dockerfile` + `docker-compose.yml` so you don't have to manage a
venv. Put your config in `.env` (see above) and run:

```bash
docker compose up --build      # or: make docker-up
# stop:  docker compose down    # or: make docker-down
```

Secrets stay in the git-ignored `.env` (injected via `env_file`) and are never
baked into the image; the container runs as a non-root user and binds `0.0.0.0`
inside the container (`HOST`/`PORT` are read by `server.py`). A `Makefile` provides
one-word entry points used both locally and in CI:

```bash
make help        # list targets
make run         # start locally (venv Python)
make test        # zero-dep test suite
make coverage    # tests + coverage gates
make scan        # DevSecOps security scan (gitleaks + bandit + pip-audit)
make check       # full QA gate: coverage + security scan
```

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
`test_server_proxy.py`). See [`docs/rail-pipeline.md`](docs/rail-pipeline.md)
for the full TDD strategy. Engineering principles are in [`docs/principles.md`](docs/principles.md).

> **Note on AI development tooling:** This project is built with two VS Code agent
> harnesses (Continue and Cline), each implementing the same **RAIL** pipeline.
> They are separate from the app itself. See [`docs/ORGANIZATION.md`](docs/ORGANIZATION.md)
> for the three-concern map (app / Continue / Cline).

These same checks (including the coverage gates) also run automatically in **CI** on
every push / pull request via GitHub Actions (`.github/workflows/tests.yml`).

## Git hooks (optional)

Install the pre-commit hook locally with:

```bash
make hooks
```

This symlinks `.git/hooks/pre-commit` → `scripts/pre-commit.sh`, which runs:
1. **Python syntax** (`py_compile`) on every staged `.py` file.
2. **JS syntax** (`node --check`) on every staged `.js` file.
3. **Secret scan** (`gitleaks detect --staged`) — skipped gracefully when
   gitleaks is not installed, or when `SKIP_GITLEAKS=1` is set.

Running `make hooks` twice is idempotent. The hook fires before every local
commit; CI has independent gates so the hook is optional (not mandatory).

> **Tip:** if gitleaks is not installed locally you can set `SKIP_GITLEAKS=1`
> in your shell profile to suppress the missing-binary warning without affecting
> the syntax gates.



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
- The `/config` endpoint returns **only non-secret** fields plus `has_*` feature
  flags — secrets never reach the browser.
- **`GET /health`** returns server status, uptime, version, and `has_*` feature
  flags — safe for use in container liveness probes; exposes no secrets.
- **SSRF guard:** the proxy and Context7 only reach **http(s)** upstreams.
- **Deterministic security gates** (DevSecOps, dev/CI-only — ship nothing in the
  app): `./scripts/security-scan.sh` (or `make scan`) runs **gitleaks** (secrets),
  **bandit** (SAST), and **pip-audit** (dependency CVEs); they also run in CI.
- The server binds `127.0.0.1` by default (localhost only); `0.0.0.0` is used only
  inside the Docker container via `HOST`. This setup is intended for local
  development — secure and harden it before any public deployment.

See [`docs/principles.md`](docs/principles.md) for the engineering principles
(minimal runtime surface, DevSecOps, Infrastructure as Code, Agile) behind these.

## Recommended improvements

- The backend could be expanded to include user authentication and persistent
  storage.
- Implement stronger frontend validation and better response error handling.
- Add embeddings-based memory/RAG search (backlog).

## Notes

The repository contains a static frontend and a Python backend. Node.js is **not
required to run the app**, but it is used (Node 18+) for the optional `node --test`
JS unit tests.


