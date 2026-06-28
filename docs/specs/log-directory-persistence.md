# Spec: Log Directory & Timestamped File Persistence (#49)

**Status:** Done
**Created:** 2026-06-27
**Author:** Cline

---

## 1. Goal & scope

Create a `logs/` directory in the project root and wire `server.py`'s `add_log()`
function to **optionally persist log entries to timestamped JSONL files** on disk.
Currently all server logs are in-memory only — they are lost on restart and flushed
by `/logs/clear`. This feature makes the log record durable and organised by date/time.

**In scope:**
- `logs/` directory with `.gitkeep` + `README.md` convention doc.
- New `PERSIST_LOGS` and `LOG_FILE_MAX` config keys (off by default).
- `_persist_log(entry)` helper in `server.py` — appends to a per-session JSONL file.
- Rotation: oldest session files pruned beyond `LOG_FILE_MAX`.
- `persist_logs` boolean added to `/config` response (non-secret).
- Unit tests (4 new tests) in `tests/python/test_server.py`.
- Docs: `.env.example`, `CHANGELOG.md`, `docs/USER_GUIDE.md`, `docs/ARCHITECTURE.md`,
  `.gitignore`, `backlog.md`.

**Out of scope:** Log viewer UI; log shipping / remote sinks; changing in-memory
`server_logs` behaviour or the `/logs` HTTP API.

---

## 2. User story & acceptance criteria

As a developer running USAi Chat, I want the server to write logs to dated files in a
`logs/` directory so that I can inspect what happened after a crash or restart.

- [ ] AC-1: `logs/` directory exists and is tracked (via `.gitkeep` + `README.md`).
- [ ] AC-2: With `PERSIST_LOGS=false` (default) nothing is written to `logs/`.
- [ ] AC-3: With `PERSIST_LOGS=true`, every `add_log` call appends a JSON line to
         `logs/YYYY-MM-DD-HHMMSS-server.jsonl` (session-start timestamp).
- [ ] AC-4: The JSONL entry matches the in-memory entry shape:
         `{timestamp, level, component, message, details}`.
- [ ] AC-5: A write failure (e.g. unwritable dir) is swallowed — `add_log` never raises.
- [ ] AC-6: When `*.jsonl` files exceed `LOG_FILE_MAX`, oldest (by mtime) are deleted.
- [ ] AC-7: `GET /config` returns `persist_logs: true|false` (boolean, non-secret).
- [ ] AC-8: `logs/*.jsonl` are git-ignored; `logs/.gitkeep` and `logs/README.md` tracked.

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | Add `LOGS_DIR`, `_LOG_SESSION_STAMP`, `_persist_log()`, wire into `add_log()`, add config keys, add `persist_logs` to `/config` |
| `.env.example` | Add `PERSIST_LOGS=false` and `LOG_FILE_MAX=20` |
| `.gitignore` | Add `logs/*.log`, `logs/*.jsonl` |
| `logs/.gitkeep` | New empty tracker file |
| `logs/README.md` | New convention doc |
| `docs/ARCHITECTURE.md` | §3d table + §3e text |
| `docs/USER_GUIDE.md` | §10 Troubleshooting |
| `CHANGELOG.md` | [Unreleased] entry |
| `backlog.md` | Mark #49 done |
| `tests/python/test_server.py` | 4 new tests (PL-1…PL-4) |

---

## 4. Technical approach

**Module-level (server.py, alongside existing dir setup):**
```python
LOGS_DIR = PROJECT_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
_LOG_SESSION_STAMP = datetime.now().strftime('%Y-%m-%d-%H%M%S')
```

**load_config() additions:**
```python
'persist_logs': os.getenv('PERSIST_LOGS', '').lower() in ('1', 'true', 'yes'),
'log_file_max': max(1, int(os.getenv('LOG_FILE_MAX', '20') or '20')),
```

**`_persist_log(entry)` — called from `add_log()` after in-memory append:**
- No-op when `CONFIG['persist_logs']` is false.
- Opens `logs/<stamp>-server.jsonl` in append mode; writes `json.dumps(entry) + '\n'`.
- Before write: prune oldest `*.jsonl` files (excluding current) beyond `log_file_max`.
- Wraps everything in `try/except Exception: pass` (same pattern as `_capture_raw_response`).

**`_get_config()` addition:**
```python
'persist_logs': bool(CONFIG.get('persist_logs')),
```

---

## 5. Test plan

Tests added to `AddLogTests` class in `tests/python/test_server.py`.

| ID | Description | Expected |
|----|-------------|---------|
| PL-1 | `_persist_log` writes valid JSON line when enabled | File created, line is valid JSON with correct fields |
| PL-2 | `_persist_log` is no-op when disabled | No file created |
| PL-3 | Write failure (bad path) is swallowed | No exception from `add_log` |
| PL-4 | Rotation: oldest file pruned when at cap | File count ≤ `LOG_FILE_MAX` |

---

## 6. Docs to update

- [ ] `CHANGELOG.md`
- [ ] `docs/USER_GUIDE.md` §10 Troubleshooting
- [ ] `docs/ARCHITECTURE.md` §3d + §3e
- [ ] `.env.example`
- [ ] `backlog.md` (item #49)

---

## 7. Risks / edge cases

- Concurrent writes safe: Python GIL + append mode is safe for single-process threads.
- Disk full / unwritable: covered by `try/except`.
- `LOG_FILE_MAX=1`: clamped to `max(1, ...)`.
- Same-second restart: would append to same file — acceptable.

---

## 8. Review checklist

- [ ] Implementation matches spec sections 3–5
- [ ] `./run-tests.sh --coverage` passes
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (section 6)
- [ ] Memory note written
