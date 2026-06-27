# Spec: Obsidian-MCP Bridge (Backlog #16 Phase 2)

**Status:** Done
**Type:** feature
**Created:** 2026-06-25
**Author:** Cline / user
**Prior context:** Phase 1 (direct filesystem I/O, `/memory/*` endpoints, `search_memory`/`save_memory` tools) fully complete. Obsidian-mcp timeout issue (#23, #24) resolved in Cline by using globally-installed `node` binary directly. `obsidian-mcp` is already running as PID 12548 in Cline's MCP context. See `implementation_plan.md` for full architecture detail.

---

## 1. Goal & scope

### Goal
Add an optional `obsidian-mcp` Node.js subprocess bridge to `server.py` so the USAi Chat app can invoke rich Obsidian operations — `rename_tag`, `move_note`, `list_available_vaults`, and the generic `mcp_tool` passthrough — without any new Python runtime dependencies. The bridge is gated on a new `OBSIDIAN_MCP_PATH` env var; when that var is absent the app behaves exactly as it does today.

### Out of scope
- Embeddings-based memory search (depends on #7, separate sub-task).
- Persistent MCP process / connection pooling (per-request subprocess is safe and simple).
- UI changes to `index.html`/`styles.css` (tools surface through existing tool-calling UI).
- Any change to the four existing `/memory/*` Phase 1 endpoints.

---

## 2. User story & acceptance criteria

As a user of USAi Chat with an Obsidian vault configured, I want the model to be able to rename tags, move notes, and list all available vaults in my Obsidian vault via the tool-calling interface, so that I can manage my second brain without leaving the chat.

- [ ] AC-1: When `OBSIDIAN_MCP_PATH` is set to a valid path and `OBSIDIAN_VAULT_PATH` is configured, `GET /config` returns `"has_mcp_bridge": true`.
- [ ] AC-2: When `OBSIDIAN_MCP_PATH` is unset, `GET /config` returns `"has_mcp_bridge": false` and all `/mcp/*` endpoints return 400.
- [ ] AC-3: `POST /mcp/rename-tag` with valid `{"oldTag": "foo", "newTag": "bar"}` relays the call to `obsidian-mcp` and returns `{"ok": true, "result": "..."}`.
- [ ] AC-4: `POST /mcp/move-note` with valid `{"source": "note.md", "destination": "folder/note.md"}` relays the call and returns `{"ok": true, "result": "..."}`.
- [ ] AC-5: `GET /mcp/vaults` returns the list of available vaults from `obsidian-mcp`.
- [ ] AC-6: `POST /mcp/tool` rejects tool names not in the allowlist with 400.
- [ ] AC-7: `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%); all 13 new tests green.
- [ ] AC-8: `./scripts/security-scan.sh` clean — no new secrets, no path traversal, subprocess uses only admin-configured env var paths.
- [ ] AC-9: Three new tools (`obsidian_rename_tag`, `obsidian_move_note`, `obsidian_list_vaults`) appear in the model's tool list when `has_mcp_bridge` is true and the Obsidian Memory toggle is on.

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | Add `call_obsidian_mcp()`, `_mcp_enabled()`, 4 handler methods, 2 new routes, 2 new CONFIG keys, `has_mcp_bridge` in `/config` |
| `app.js` | Add `callMcpTool()` helper, 3 `TOOL_REGISTRY` entries, update `getEnabledTools()` gate |
| `index.html` | None |
| `styles.css` | None |
| `.env.example` | Add `OBSIDIAN_MCP_PATH` and `OBSIDIAN_NODE_PATH` with comments |
| `tests/python/test_server_mcp.py` | New — 13 TDD tests |
| `docs/specs/obsidian-mcp-bridge.md` | This spec |
| `docs/USER_GUIDE.md` | Add Phase 2 MCP bridge section |
| `CHANGELOG.md` | Add `[Unreleased]` entry |
| `backlog.md` | Mark Phase 2 done under item #16 |

---

## 4. Technical approach

### Role 2 — Architect sign-off

**`call_obsidian_mcp(tool_name, arguments, timeout=10)`** — module-level function in `server.py`. Reads `CONFIG['obsidian_mcp_path']` and `CONFIG['obsidian_node_path']`. If `mcp_path` is empty or the file does not exist, returns `(None, "MCP bridge not configured")`. Otherwise spawns:

```python
subprocess.run(
    [node_path, mcp_path, vault_path],
    input=json.dumps(rpc_request).encode(),
    capture_output=True,
    timeout=timeout,
)
```

Parses the first valid JSON line from stdout. Handles `TimeoutExpired`, `FileNotFoundError`, and JSON parse errors gracefully — all return `(None, error_string)` without raising.

The `vault_path` argument is taken from `CONFIG['obsidian_vault_path']` (admin-configured), NOT from any user-supplied input.

**`_mcp_enabled()`** — module-level function. Returns `True` iff `CONFIG['obsidian_mcp_path']` is non-empty, the file exists, and `get_memory_dir()` is not None.

**Allowlist for `/mcp/tool`:**
```python
MCP_TOOL_ALLOWLIST = {
    "create_note", "edit_note", "read_note", "search_vault",
    "add_tags", "remove_tags", "rename_tag", "move_note",
    "list_available_vaults", "create_directory", "delete_note",
}
```

**`_get_config()` change:** one new key `'has_mcp_bridge': _mcp_enabled()` added to `safe_config`. No secrets exposed.

**`app.js` additions:**
- `callMcpTool(toolName, args)` — `async` helper that `fetch`es `POST /mcp/tool` and returns result text or throws.
- Three `TOOL_REGISTRY` entries that call `POST /mcp/rename-tag`, `POST /mcp/move-note`, `GET /mcp/vaults`.
- Gate in `getEnabledTools()`:
  ```js
  const MCP_TOOLS = ['obsidian_rename_tag', 'obsidian_move_note', 'obsidian_list_vaults'];
  if (MCP_TOOLS.includes(name) && (!appConfig.has_mcp_bridge || !memoryEnabled)) continue;
  ```

**Conventions applied:**
- [x] No new runtime dependency added (uses `subprocess`, `json`, already imported)
- [x] New endpoints follow `_handler` + `routes` pattern
- [x] New tools follow `TOOL_REGISTRY` + `getEnabledTools()` gate pattern
- [x] `/config` exposes only `has_mcp_bridge` boolean — no paths, no binary names
- [x] Path traversal N/A for MCP bridge (no user-supplied filesystem paths in subprocess args)
- [x] CSS bump N/A (no CSS change)
- [x] SSRF N/A (no HTTP requests; subprocess only)

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | `call_obsidian_mcp` with mocked subprocess returning valid JSON-RPC result → returns `(text, None)` | `tests/python/test_server_mcp.py` | unit |
| T-2 | `call_obsidian_mcp` with mocked `TimeoutExpired` → returns `(None, error_str)` | `tests/python/test_server_mcp.py` | unit |
| T-3 | `call_obsidian_mcp` when `mcp_path` points at non-existent file → returns `(None, error_str)` | `tests/python/test_server_mcp.py` | unit |
| T-4 | `call_obsidian_mcp` when process returns JSON-RPC error object → returns `(None, error_str)` | `tests/python/test_server_mcp.py` | unit |
| T-5 | `_mcp_enabled()` returns False when `obsidian_mcp_path` is empty | `tests/python/test_server_mcp.py` | unit |
| T-6 | `_mcp_enabled()` returns True when both path exists and vault is configured | `tests/python/test_server_mcp.py` | unit |
| T-7 | `POST /mcp/tool` without bridge configured → 400 | `tests/python/test_server_mcp.py` | integration |
| T-8 | `POST /mcp/tool` with tool name not in allowlist → 400 | `tests/python/test_server_mcp.py` | integration |
| T-9 | `POST /mcp/rename-tag` missing `oldTag` or `newTag` → 400 | `tests/python/test_server_mcp.py` | integration |
| T-10 | `POST /mcp/move-note` missing `source` or `destination` → 400 | `tests/python/test_server_mcp.py` | integration |
| T-11 | `GET /mcp/vaults` without bridge configured → 400 | `tests/python/test_server_mcp.py` | integration |
| T-12 | `GET /config` includes `has_mcp_bridge` key | `tests/python/test_server_mcp.py` | integration |
| T-13 | `POST /mcp/tool` with body > 5MB → 413 | `tests/python/test_server_mcp.py` | integration |

**TDD order:** write all tests first (Red) → implement production code (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — add "Obsidian MCP Bridge" section explaining the two new env vars and available tools
- [ ] `backlog.md` — mark Phase 2 done under item #16
- [ ] `.env.example` — add `OBSIDIAN_MCP_PATH` and `OBSIDIAN_NODE_PATH`

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| MCP process startup time (~200–400ms) adds latency per tool call | Acceptable for interactive tool use; document in USER_GUIDE. Persistent process is a future optimisation. |
| `obsidian-mcp` stdout may contain startup banners before the JSON line | Parse only the first line that is valid JSON; skip non-JSON lines |
| obsidian-mcp may output multi-line JSON or multiple JSON objects | Read all stdout, split by newline, find the line that parses as the JSON-RPC response |
| User has Node via nvm but `node` is not on PATH at server startup | `OBSIDIAN_NODE_PATH` env var allows explicit absolute path (same fix as #23/#24) |
| obsidian-mcp version mismatch | Document in USER_GUIDE that `OBSIDIAN_MCP_PATH` must be updated after `npm i -g obsidian-mcp` upgrades |
| `delete_note` in allowlist could destroy vault content | Tool is in allowlist but the model should only call it when user explicitly asks; acceptable for now |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
      Actual: server.py line 90.6% ✅, branch 88% ✅; JS branch 72.49% ✅
- [x] `./scripts/security-scan.sh` clean (bandit -ll no medium+ issues; nosec B603 B607 justified)
- [x] Docs updated per §6 (CHANGELOG, USER_GUIDE, backlog, .env.example)
- [x] Acceptance criteria AC-1…AC-9 all verified (17 tests T-1…T-17)
- [x] Memory note written to `Cline/memories/2026-06-26-231000-obsidian-mcp-bridge-done.md`
