# Spec: Log File Viewer in Debug Panel (#50)

**Status:** In Progress
**Created:** 2026-06-27
**Author:** Cline

---

## 1. Goal & scope

Add a **"Log Files" tab** to the existing in-app Debug Logs panel that lets users
browse and read the persisted `logs/*.jsonl` session files without leaving the browser
or touching the terminal.

**In scope:**
- `GET /logs/files` endpoint (list + read) in `server.py`.
- "Log Files" / "Live" tab toggle inside the existing `#debugPanel` in `index.html`.
- `Logger.getLogFiles()` + `Logger.readLogFile(name)` + `renderFilesTab()` in `app.js`.
- CSS for tab strip + file-list row in `styles.css`; `?v=25` bump in `index.html`.
- 4 new Python tests (LV-1…LV-4) in `tests/python/test_server_branches.py`.
- `CHANGELOG.md`, `docs/USER_GUIDE.md` §10, `backlog.md` #50.

**Out of scope:** delete/export of log files from UI; log streaming; search within files.

---

## 2. User story & acceptance criteria

As a developer, I want to open the Debug Logs panel and switch to a "Log Files" tab to
see a list of persisted session log files and click one to read its entries, without
using the terminal.

- [ ] AC-1: Debug panel shows two tabs: "Live" (existing) and "Log Files".
- [ ] AC-2: "Log Files" tab calls `GET /logs/files` and renders a list (name, size,
         date) when `PERSIST_LOGS=true` and files exist.
- [ ] AC-3: Clicking a file row loads and renders its entries using the same
         log-entry styling as the live panel.
- [ ] AC-4: When `PERSIST_LOGS=false` or no files exist, a friendly message is shown.
- [ ] AC-5: `GET /logs/files` (list) returns `{enabled, files:[{name,size,modified}]}`.
- [ ] AC-6: `GET /logs/files?name=<file>` returns `{entries:[...]}` (array of log objects).
- [ ] AC-7: Path-traversal is rejected: names containing `/`, `\`, or starting with `.`
         return 400.
- [ ] AC-8: When `PERSIST_LOGS=false`, list returns `{enabled:false, files:[]}` (200).

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | `_get_log_files()` handler; register `/logs/files` in `do_GET` routes |
| `app.js` | `Logger.getLogFiles()`, `Logger.readLogFile(name)`, `renderFilesTab()`, tab-switch wiring |
| `index.html` | Tab buttons + `#debugFiles` div inside `#debugPanel`; `?v=25` |
| `styles.css` | `.debug-tab`, `.debug-tab.active`, `.log-file-row` |
| `tests/python/test_server_branches.py` | 4 new tests LV-1…LV-4 |
| `CHANGELOG.md` | [Unreleased] entry |
| `docs/USER_GUIDE.md` | §10 Troubleshooting — update log viewer section |
| `backlog.md` | #50 done |

---

## 4. Technical approach

### `server.py` — `_get_log_files()`

```python
def _get_log_files(self):
    """GET /logs/files          → list session log files (newest first).
    GET /logs/files?name=<f>  → read one file as array of log entries.

    Path-traversal guard: name must contain no / \\ or leading dot.
    Returns {enabled, files} on list (200 even when disabled — enabled:false).
    Returns 404 when named file not found; 400 on traversal attempt.
    """
```

Response shapes:
- **List:** `{"enabled": true|false, "files": [{"name": "...", "size": N, "modified": "ISO"}]}`
- **Read:** `{"name": "...", "entries": [<log objects>]}`

Register in `do_GET`:
```python
'/logs/files': self._get_log_files,
```

### `app.js` additions to `Logger`

```js
async getLogFiles()         // GET /logs/files → {enabled, files}
async readLogFile(name)     // GET /logs/files?name=<name> → {entries}
async renderFilesTab()      // fetch list → render; on row click → fetch + render entries
```

Tab switching: two `.debug-tab` buttons (`data-tab="live"` / `data-tab="files"`);
toggling visibility of `#debugLogs` vs `#debugFiles`.

### `index.html` changes

Inside `#debugPanel > .debug-header`, add a tab strip before the controls:
```html
<div class="debug-tabs">
  <button class="debug-tab active" data-tab="live">Live</button>
  <button class="debug-tab" data-tab="files">Log Files</button>
</div>
```
Add below `#debugLogs`:
```html
<div class="debug-files" id="debugFiles" style="display:none;"></div>
```
Bump `styles.css?v=24` → `styles.css?v=25`.

### `styles.css` additions

```css
.debug-tabs { display:flex; gap:4px; margin-bottom:8px; }
.debug-tab { ... }
.debug-tab.active { ... }
.log-file-row { ... cursor:pointer; }
.log-file-row:hover { ... }
```

---

## 5. Test plan

Tests in `tests/python/test_server_branches.py`.

| ID | Description | Expected |
|----|-------------|---------|
| LV-1 | `GET /logs/files` when enabled + files present | 200, `enabled:true`, list with name/size/modified |
| LV-2 | `GET /logs/files` when disabled | 200, `enabled:false`, empty list |
| LV-3 | `GET /logs/files?name=<file>` reads entries | 200, `entries` array with correct fields |
| LV-4 | Path-traversal name rejected | 400 |

---

## 6. Docs to update
- [ ] `CHANGELOG.md`
- [ ] `docs/USER_GUIDE.md` §10
- [ ] `backlog.md` #50

---

## 7. Risks / edge cases
- Large log files: `readLogFile` reads whole file; capped to last 500 lines server-side.
- Malformed JSONL lines: skip silently (return what can be parsed).
- `PERSIST_LOGS` not enabled: UI shows "Log file persistence is not enabled" message.

---

## 8. Review checklist
- [ ] Implementation matches spec §3–§5
- [ ] `./run-tests.sh` passes
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated
- [ ] Memory note written
