# Spec: Raw API Response Capture (Non-Streaming, v1)

**Status:** In Progress
**Created:** 2026-06-27
**Author:** Cline / user

---

## 1. Goal & scope

Capture and persist the **full raw upstream API response envelope** returned by
every **non-streaming** `/api/*` proxy call — including `id`, `model`, `usage`,
`finish_reason`, `choices`, HTTP status code, and the complete JSON payload —
so developers and operators can debug, audit token usage, and inspect exactly
what the upstream returned.

**In scope (v1):**
- Non-streaming responses only (streamed SSE capture → backlog item #48).
- New on-disk rotating store: `.raw_responses/` (one JSON file per response).
- New `GET /raw-responses` (list) and `GET /raw-responses?id=` (read one).
- New `DELETE /raw-responses` (clear all) and `DELETE /raw-responses?id=` (delete one).
- Opt-in via `CAPTURE_RAW_RESPONSES=true` in `.env` (off by default).
- Rotating cap via `RAW_RESPONSES_MAX` (default 200).
- `/config` gains `has_raw_capture` boolean only — never secrets.

**Out of scope (v1):**
- Streaming SSE capture (→ backlog #48).
- Browser/UI panel to browse captures.
- Request body capture (we only capture the *response*).
- Redacting response body content (response payloads stored verbatim — only the
  `Authorization` request header is never stored).

---

## 2. User story & acceptance criteria

As a developer/operator I want every full raw upstream JSON response captured
to disk so I can debug, audit token usage, and inspect exact upstream behaviour.

- [x] **AC-1** Non-streaming `/api/*` proxy response body written to
  `.raw_responses/<timestamp>_<short-id>.json` when `CAPTURE_RAW_RESPONSES=true`.
- [x] **AC-2** Each stored record contains: `timestamp`, `method`, `path`,
  `status` (int), `streamed: false`, `model` (from request body), `raw` (full JSON).
- [x] **AC-3** The `Authorization` header / API key is **never** in any stored record.
- [x] **AC-4** When `CAPTURE_RAW_RESPONSES` is absent/falsy — no files written,
  proxy behaviour byte-for-byte identical to today.
- [x] **AC-5** Rotation: oldest file deleted when count reaches `RAW_RESPONSES_MAX` (default 200).
- [x] **AC-6** `GET /raw-responses` returns array of `{id, timestamp, method, path, status, model}` (no `raw`).
- [x] **AC-7** `GET /raw-responses?id=` returns full record with `raw`. 404 if not found.
- [x] **AC-8** `DELETE /raw-responses?id=` deletes one; `DELETE /raw-responses` clears all.
- [x] **AC-9** `?id=` path traversal rejected via `Path(id).name` + `relative_to` guard.
- [x] **AC-10** `/config` includes `has_raw_capture` boolean only.
- [x] **AC-11** Capture failure never breaks proxy response (all capture in try/except).
- [x] **AC-12** Both env vars documented in `.env.example`.
- [x] **AC-13** `.raw_responses/` added to `.gitignore`.
- [x] **AC-14** `test_env_example_sync` covers the two new env keys.

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | `RAW_RESPONSES_DIR`; `load_config()` for 2 new keys; `_capture_raw_response()` helper; hook in `_proxy_api` non-streaming + HTTPError paths; `_get_raw_responses` + `_delete_raw_responses` handlers; routes registered; `has_raw_capture` in `/config`. |
| `.env.example` | New section: `CAPTURE_RAW_RESPONSES=false` + `RAW_RESPONSES_MAX=200`. |
| `.gitignore` | Add `.raw_responses/`. |
| `tests/python/test_server_http.py` | RC-1…RC-4 (capture-on, list/read/delete, config bool). |
| `tests/python/test_server_branches.py` | RC-5…RC-8 (capture-off, rotation, path-traversal, no auth leak). |
| `docs/ARCHITECTURE.md` | `.raw_responses/` data-store row; 2 endpoint rows. |
| `CHANGELOG.md` | Entry under `[Unreleased]`. |
| `docs/USER_GUIDE.md` | Short note on enabling capture + file location. |
| `backlog.md` | This item `[~]`→`[x]`; new #48 streaming capture added. |

---

## 4. Technical approach

### 4a. Module-level constants (server.py, after SESSIONS_DIR)
```python
RAW_RESPONSES_DIR = PROJECT_ROOT / '.raw_responses'
RAW_RESPONSES_DIR.mkdir(exist_ok=True)
```

### 4b. load_config() additions
```python
'capture_raw_responses': os.getenv('CAPTURE_RAW_RESPONSES', '').lower() in ('1', 'true', 'yes'),
'raw_responses_max': int(os.getenv('RAW_RESPONSES_MAX', '200') or '200'),
```

### 4c. _capture_raw_response(meta, raw_bytes) helper
- Generates filename: `{iso_ts_safe}_{secrets.token_hex(4)}.json`
- Rotation: glob `*.json`, sort by mtime, unlink oldest while `len >= cap`
- Parses `raw_bytes` as JSON (falls back to utf-8 string on error)
- Stores: `{id, timestamp, method, path, status, streamed:false, model, raw}`
- Logs via `add_log('info', 'capture', ...)` — never logs payload or auth

### 4d. Hook in _proxy_api (non-streaming path only)
After `response_body = resp.read()` / `response_status = resp.status`, before
`self.send_response(...)`:
```python
if CONFIG.get('capture_raw_responses'):
    try:
        req_model = json.loads(request_body).get('model') if request_body else None
    except Exception:
        req_model = None
    try:
        _capture_raw_response({
            'timestamp': datetime.now().isoformat(), 'method': method,
            'path': self.path, 'status': response_status, 'model': req_model,
        }, response_body)
    except Exception as cap_err:
        add_log('warn', 'capture', f'Capture failed (non-fatal): {cap_err}')
```
Same pattern applied inside the `except HTTPError` branch for error responses.

### 4e. _get_raw_responses / _delete_raw_responses
Follow identical pattern to `_get_sessions` / `_delete_sessions`:
- `?id=` → `Path(id).name` + `relative_to(RAW_RESPONSES_DIR)` guard → 400 on escape
- List: returns metadata array (no `raw` field) sorted newest-first
- Read: full record or 404
- Delete one: unlink if exists; delete all: glob + unlink

### 4f. Routes
- `do_GET`: `'/raw-responses': self._get_raw_responses`
- `do_DELETE`: `'/raw-responses': self._delete_raw_responses`

### 4g. /config safe fields
```python
'has_raw_capture': bool(config.get('capture_raw_responses')),
```

---

## 5. Test plan

| ID | File | Description |
|----|------|-------------|
| RC-1 | test_server_http.py | Capture-on: POST non-streaming through loopback stub → one `.json` file; `status`/`path`/`model` correct; no auth value in file |
| RC-2 | test_server_http.py | `GET /raw-responses` list (no `raw`); `GET ?id=` full record; `DELETE ?id=` removes file |
| RC-3 | test_server_http.py | `DELETE /raw-responses` clears all files |
| RC-4 | test_server_http.py | `/config` returns `has_raw_capture: true` when enabled |
| RC-5 | test_server_branches.py | Capture-off (default): proxy succeeds, zero files written |
| RC-6 | test_server_branches.py | Rotation: `RAW_RESPONSES_MAX=3`, 4th capture deletes oldest; count stays ≤ 3 |
| RC-7 | test_server_branches.py | `GET /raw-responses?id=../../etc/passwd` → 400 |
| RC-8 | test_server_branches.py | No stored file contains the API key string |

---

## 6. Docs to update

- [x] `CHANGELOG.md`
- [x] `docs/USER_GUIDE.md` (enable capture + location)
- [x] `docs/ARCHITECTURE.md` (data store + endpoints)
- [x] `.env.example`
- [x] `.gitignore`
- [x] `backlog.md` (this item done; #48 streaming added)

---

## 7. Risks / edge cases

| Risk | Mitigation |
|------|-----------|
| Capture failure breaks proxy | All capture wrapped in `try/except`; warn log, continue |
| Disk growth | Rotation cap (default 200); inherits 10 MB proxy ceiling |
| Path traversal on `?id=` | `Path(id).name` + `relative_to` guard (same as `_get_sessions`) |
| Concurrent writes | Unique filenames via iso-ts + `secrets.token_hex(4)` |
| Auth key stored | Only response body + request metadata; `Authorization` header never stored |

---

## 8. Review checklist

- [ ] Implementation matches spec sections 3–5
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (section 6)
- [ ] Memory note written

---

## Spec changelog

| Date | Change |
|------|--------|
| 2026-06-27 | Initial — non-streaming v1; streaming deferred to backlog #48 |
