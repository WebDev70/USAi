# USAi Chat — Project Guide (CONTINUE.md)

This guide helps developers (and Continue) understand and work with the USAi Chat
codebase. Continue automatically loads this file into context for this project.

---

## ⭐ Agent Directive: Use Obsidian as Long-Term Memory (Second Brain)

> **The authoritative memory rules live in [`AGENTS.md`](../../AGENTS.md).**
> Always treat the user's Obsidian vault as persistent long-term memory: **recall**
> relevant prior context at the start of a task, and **record** decisions/summaries
> as you work.

**Quick reference (see `AGENTS.md` for the full rules):**
- **Vault:** `/Users/ronaldbblake/Documents/Obsidian Vault`.
- **Where to write depends on the writer:**
  - The **Continue extension (VS Code)** saves to **`Continue Extension/memories/`**.
  - The **USAi Chat web app** (💾 Remember button + in-app tools) saves to
    **`USAi/memories/`** on its own via the backend (`OBSIDIAN_MEMORY_SUBDIR=USAi`).
- **Access (Continue):** **prefer direct filesystem I/O** (your file tools on
  `<vault>/Continue Extension/memories/`) — it never times out and needs no Node
  process. The `obsidian-mcp` tools are optional/secondary (they intermittently
  time out with `-32001`). See `AGENTS.md` for the full priority order.
- One note per session (`YYYY-MM-DD-HHMMSS-title.md`), YAML frontmatter, consistent
  tags, never delete/overwrite.

---

## 1. Project Overview

**USAi Chat** is a lightweight, browser-based chat interface for talking to
USAi-compatible (OpenAI-style) model APIs. It is deliberately dependency-light: a
**static vanilla-JS frontend** served by a **small Python standard-library backend**
that proxies API calls and provides local persistence.

**Key technologies**
- **Frontend:** plain HTML, CSS, and JavaScript (no framework, no build step).
- **Backend:** Python 3 using `http.server` (`ThreadingHTTPServer`). Only one
  third-party dependency: `python-dotenv`.
- **External services:** an OpenAI-compatible chat API (via `BASE_URL`), optional
  **Context7** documentation provider, and an optional **Obsidian vault** used as
  long-term memory.

**High-level architecture**

```
Browser (index.html + app.js + styles.css)
        │   fetch()
        ▼
server.py  ── /api/*        → proxies to BASE_URL (injects API key)
           ── /context7     → proxies to Context7
           ── /memory/*     → reads/writes the Obsidian vault
           ── /config       → non-secret config + feature flags
           ── /sessions, /chat-history, /chunk-cache, /logs → local JSON storage
```

The backend has two core jobs: **serve the static UI** and **act as a secure proxy**
so secrets (API keys) never reach the browser and CORS is avoided.

---

## 2. Getting Started

### Prerequisites
- **Python 3** (developed/tested on 3.9).
- A virtual environment is recommended (the repo includes a `.venv/`).
- An OpenAI-compatible API key + base URL (for chatting).

### Installation
```bash
# from the project root
python3 -m venv .venv          # if you don't already have one
source .venv/bin/activate
pip install -r requirements.txt # installs python-dotenv
```

### Configuration
Create a `.env` file in the project root (it is git-ignored):
```env
API_KEY=YOUR_API_KEY
BASE_URL=https://your-openai-compatible-endpoint/
DEFAULT_MODEL=claude_3_haiku
DEFAULT_SYSTEM_PROMPT=

# Optional — Context7 documentation provider
CONTEXT7_API_KEY=...
CONTEXT7_BASE_URL=https://context7.com
CONTEXT7_PATH=/api/v2/libs/search
CONTEXT7_METHOD=GET

# Optional — Obsidian "second brain" long-term memory
OBSIDIAN_VAULT_PATH=/absolute/path/to/your/Obsidian Vault
OBSIDIAN_MEMORY_SUBDIR=USAi
```

### Run
```bash
# IMPORTANT: use the venv's Python so python-dotenv is available
.venv/bin/python server.py      # or: activate the venv, then `python3 server.py`
```
Then open **http://localhost:8000** and hard-refresh (Cmd/Ctrl+Shift+R) after
frontend changes.

To stop the server / free the port:
```bash
lsof -ti:8000 | xargs kill
```

### Running tests
The project uses a **zero-runtime-dependency, TDD-first** test stack — `node --test`
(built into Node 18+) for `app.js` pure functions and stdlib `unittest` for
`server.py` (unit **and** HTTP integration tests). We write the failing test first
(Red → Green → Refactor; see [`.continue/rules/tdd-workflow.md`](tdd-workflow.md)).
Run everything with the helper script:
```bash
./run-tests.sh             # syntax gates + JS tests + Python tests
./run-tests.sh --coverage  # adds coverage gates (server.py ≥ 90%, JS branch ≥ 70%)
```
Coverage tooling is **dev-only** (`coverage.py` in the venv; Node ≥ 22 built-in JS
coverage) — it is never added to `requirements.txt` or shipped in the app.
Or individually:
```bash
node --check app.js && python3 -m py_compile server.py        # syntax gates
node --test $(find tests/js -name '*.test.mjs')               # JS unit tests
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'  # Python tests
```
Tests live in `tests/js/*.test.mjs` and `tests/python/test_*.py` (with HTTP
integration suites `test_server_http.py`, `test_server_branches.py`,
`test_server_proxy.py`). See
[`docs/testing-and-agents-strategy.md`](../../docs/testing-and-agents-strategy.md)
for the full strategy and **RAIL** (*Rule-governed Agentic Iteration Loop*) — the
five-role agent pipeline (Planner → SME → Tests → QA `/check` → Continuous
Improvement).

---

## 3. Project Structure

| Path | Role |
|------|------|
| `index.html` | Static chat UI markup. Sidebar settings, composer toolbar (model + reasoning + attach + send), debug panel. |
| `app.js` | All frontend logic: config load, model selection, streaming, tool calling, file/image uploads, history/sessions, settings persistence, Obsidian memory UI. |
| `styles.css` | All styling. **Cache-busted** via `?v=N` query in `index.html` — bump on CSS changes. |
| `server.py` | Python backend: static file serving + proxy + local JSON storage + `/memory/*`. |
| `requirements.txt` | Python dependencies (`python-dotenv`). |
| `.env` | Secrets & config (git-ignored). **Never commit.** |
| `chat_history.json` | The current/active conversation. |
| `.chat_sessions/` | Archived chat sessions (one JSON per session). |
| `.chunk_cache/` | Cached chunked text uploads for RAG. |
| `.continue/` | Continue config: `rules/` (this file), `agents/`, `mcpServers/`. |
| `.github/copilot-instructions.md` | Copilot guidance. |
| `README.md` | Setup/overview. |
| `USER_GUIDE.md` | End-user feature documentation. |
| `CHANGELOG.md` | Detailed change log (kept current as features land). |
| `backlog.md` | Prioritized roadmap; items checked off when done. |

---

## 4. Development Workflow

### Coding standards / conventions
- **No build step, no framework.** Keep the frontend as dependency-free vanilla JS.
- **Backend uses only the Python standard library + `python-dotenv`.** Avoid adding
  heavy dependencies without good reason.
- **Comments explain *why*,** not just *what* — match the existing descriptive style.
- **Security first:** secrets stay server-side. `/config` returns only non-secret
  fields plus `has_*` boolean feature flags; the proxy injects the API key.
- **Path safety:** any endpoint that touches the filesystem must reject path
  traversal and confine writes to the intended folder (see `/memory/*`, sessions,
  chunk-cache).
- **CSS changes:** bump the `styles.css?v=N` version in `index.html` to bust cache.

### Testing approach
Zero-dependency unit tests (`node --test` for JS, stdlib `unittest` for Python) via
`./run-tests.sh`, plus syntax gates and in-browser testing. Watch the **Debug Logs**
panel and the server terminal for errors. Non-trivial changes follow **RAIL** — the
five-role agent pipeline (see `docs/testing-and-agents-strategy.md`).

### Build & deployment
No build. Deployment = run `server.py` somewhere it can read `.env`. Intended for
**local development**; harden before any public exposure. — **Needs verification.**

### Contribution guidelines
- Work through `backlog.md` items roughly in priority order; mark them done.
- Record notable changes in `CHANGELOG.md` and update `USER_GUIDE.md` for
  user-facing features.

### Keep docs in sync (enforced rule)
An always-on Continue rule, [`keep-docs-in-sync.md`](keep-docs-in-sync.md), requires
that documentation be updated **in the same turn** as the change that affects it —
docs are part of "done." Roughly:

| Change | Update |
|--------|--------|
| Almost any notable code/behavior change | `CHANGELOG.md` (`## [Unreleased]`) |
| User-facing feature (toggle/button/setting/workflow) | `USER_GUIDE.md` |
| Setup, `.env` vars, run commands, architecture | `README.md` |
| Completing/starting roadmap items | `backlog.md` (`[x]` / `[~]`) |
| Structure, concepts, conventions, troubleshooting | this file (`CONTINUE.md`) |
| Agent rules, security, conventions, memory directive | `AGENTS.md` |

Avoid duplicating content across docs — link between them instead.

---

## 5. Key Concepts

- **Proxy pattern:** `server.py` proxies `/api/*` to `BASE_URL`, injecting the API
  key and relaying SSE streams chunk-by-chunk (so secrets never hit the browser).
- **Feature flags via `/config`:** the frontend learns what's configured through
  booleans `has_api_key`, `has_context7`, `has_obsidian` — never the secrets.
- **Tool calling (`TOOL_REGISTRY`):** built-in tools the model can invoke —
  `calculator`, `search_uploaded_files`, `fetch_context7`, and the Obsidian
  `search_memory` / `save_memory`. `getEnabledTools()` gates each tool on its
  config + toggle; `runWithTools()` loops model → tool calls → results.
- **Per-model parameter exclusion:** `MODEL_PARAM_EXCLUSIONS` / `getExcludedParams()`
  omit params a model rejects (e.g. `temperature` for Claude Opus / OpenAI o-series).
- **RAG over uploads:** text files are chunked (`.chunk_cache/`) and the most
  relevant chunks are injected as context (`prepareContextMessages`).
- **Obsidian "second brain":** long-term memory stored as tagged Markdown in
  `<vault>/<subdir>/memories/`. Three usage paths: memory tools, opt-in auto-recall,
  and a manual **💾 Remember** button.
- **Settings persistence:** UI state saved to `localStorage` under
  `usai.settings.v1` and restored on load.

---

## 6. Common Tasks

**Add a new built-in tool**
1. Add an entry to `TOOL_REGISTRY` in `app.js` with a `definition` and async `run`.
2. Gate it in `getEnabledTools()` if it depends on config/a toggle.
3. (If it needs server access) add an endpoint in `server.py` and route it in
   `do_GET`/`do_POST`.

**Add a new server endpoint**
1. Write a `_handler` method on `EnvConfigHTTPRequestHandler`.
2. Register its path in the `routes` dict inside `do_GET`/`do_POST`/`do_DELETE`.
3. Validate input size and reject path traversal for any filesystem access.

**Change styling**
1. Edit `styles.css`. 2. Bump `styles.css?v=N` in `index.html`. 3. Hard-refresh.

**Expose a new config value**
1. Read it in `load_config()` (`server.py`). 2. If non-secret, add to the
   `safe_config` dict in `_get_config` (or add a `has_*` flag if it's a secret).
   3. Consume it in `app.js` via `appConfig`.

**Restart the server cleanly**
```bash
lsof -ti:8000 | xargs kill
.venv/bin/python server.py
```

---

## 7. Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `ModuleNotFoundError: No module named 'dotenv'` | Server started with the wrong Python. Use the venv: `.venv/bin/python server.py`. |
| `OSError: [Errno 48] Address already in use` | A server is already on port 8000. Free it: `lsof -ti:8000 \| xargs kill`. |
| `API error: 400` when sending | Provider rejected the request — wrong model id, an unsupported param, or max tokens too high. Check the **Debug Logs** entry. |
| Obsidian Memory toggles greyed out / no 💾 button | No vault configured. Set `OBSIDIAN_VAULT_PATH` in `.env` and restart (`/config` should show `has_obsidian: true`). |
| Model used Context7 unexpectedly | Uncheck **Context7** in MCP & Plugins; tools are gated on the toggle. |
| CSS changes not showing | Bump `styles.css?v=N` and hard-refresh. |
| `404 GET /favicon.ico` | Harmless — the app has no tab icon. |
| Obsidian MCP `Request timed out` / JSON-RPC error `-32001` in Continue | **Two causes.** (1) **Orphaned duplicate `obsidian-mcp` processes** contending for the vault stdio pipe (Continue spawns a new one on each reload/reset without killing the old). (2) **A single, lone process can ALSO wedge its stdio pipe over time/idle** (observed 2026-06-19: one clean process, no duplicates, yet reads+writes all `-32001`) — so "exactly one process" is necessary but not sufficient. Ritual: `./scripts/kill-stale-obsidian-mcp.sh` → **fully quit VS Code (Cmd+Q)** → reopen → confirm **exactly ONE** process with `ps aux \| grep obsidian-mcp`; if a single process still times out, **reload the MCP server / VS Code window again**. **Most reliable: don't depend on the MCP for memory — use direct filesystem reads/writes to the vault** (Obsidian auto-indexes them); the app's own memory (`/memory/*`) already works this way and never wedges. The server is pinned to **Node 20 LTS** in `.continue/mcpServers/new-mcp-server.yaml` (switching Node means reinstalling obsidian-mcp for that version + updating both `command` and `args[0]`). To prove the binary is healthy independent of Continue, pipe a JSON-RPC `initialize` into it directly — if that succeeds but Continue times out, the fault is the long-lived Continue↔child stdio session, not obsidian-mcp. |
| Obsidian MCP `-32601 Method not found` at load | **Harmless/cosmetic.** Continue probes for "resource templates"; `obsidian-mcp` exposes tools, not that optional capability. Not the cause of timeouts. |

**Debugging tips:** open the **Debug Logs** panel (top-right) for frontend +
proxied errors, and watch the `server.py` terminal output (every request and memory
save is logged).

---

## 8. References

- `README.md` — setup & overview
- `USER_GUIDE.md` — end-user feature documentation
- `CHANGELOG.md` — detailed change history
- `backlog.md` — roadmap / planned work
- Context7 MCP: https://mcp.context7.com/mcp
- `obsidian-mcp` (optional Phase 2 bridge): https://github.com/stevenstavrakis/obsidian-mcp
- OpenAI Chat Completions API (the request/response shape this app targets)

---

*Tip: you can add more focused `rules.md` files in subdirectories for
component-specific guidance; Continue will load them in context for that area.*
