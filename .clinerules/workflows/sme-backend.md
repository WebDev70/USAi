# Workflow: SME — Back-End Developer
# Cline RAIL — Back-End Specialist Rules

> **Concern: Cline dev harness** — this file is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Invoked by:** `build.md` Role 3 when the spec touches `server.py`, endpoints, or
proxy behavior. This file is a **domain-specific expansion of Role 3** — it does not
replace the sequencing in `build.md`.

**Canonical reference:** [`docs/rail-pipeline.md` §3 — Code Planner approach](../../docs/rail-pipeline.md)

---

## Back-End SME charter

Deliver **secure, minimal-surface, stdlib-only** back-end changes that:
- Use **Python stdlib + `python-dotenv` only** at runtime — no new runtime packages.
- Apply all security guards consistently: SSRF guard, path-traversal rejection, `/config`
  redaction, and `add_log` for all server logging.
- Follow the established **endpoint pattern** (`_handler` method + `routes` dict).
- Keep the environment **declarative and drift-free** (`HOST`/`PORT` via
  `resolve_bind_address`; new config keys added to `.env.example` and the sync test).
- Write **testable pure helpers** — keep functions small, pure, and importable by
  `tests/python/test_server.py`.

---

## Pre-implementation checklist (before writing any back-end code)

Read the spec §3 (Affected files) and §4 (Technical approach). Verify:

- [ ] **No new runtime dependencies.** Any new functionality must use Python stdlib.
      If a runtime dep is genuinely necessary (e.g., a new binary format), stop and
      raise it with the user — do not add it silently.
- [ ] **Endpoint pattern identified.** New endpoints follow:
      - A `_handler_<name>` method on the server class.
      - Registered in the `routes` dict.
      - Input-size validation at the top of the handler.
      - Path parameter validated and sanitized before any FS access.
- [ ] **SSRF surface identified.** Any handler that makes an outbound HTTP/HTTPS
      call must pass the URL through `is_safe_upstream_url()` first.
- [ ] **FS surface identified.** Any handler that reads or writes files must:
      - Use `get_memory_dir()` or an equivalent path-resolver that rejects `..` traversal.
      - Confine writes to the intended directory (vault, sessions, cache).
- [ ] **`/config` check.** If the change touches `load_config()` or adds new
      config fields: verify `/config` still returns only non-secret fields +
      `has_*` boolean flags. Secrets must never reach the browser.
- [ ] **IaC check.** New `.env` config keys must be:
      - Added to `.env.example` (with a safe placeholder value, never a real key).
      - Covered by `tests/python/test_env_example_sync.py` (which checks that
        `load_config()` reads every key in `.env.example`).
- [ ] **`add_log` check.** All server-side logging must use `add_log()` — never
      `print()` or `logging.*` directly. Logged messages must never contain
      secrets, API keys, or vault content.

---

## TDD — Red → Green → Refactor (back-end specifics)

### RED — write failing tests first

Back-end tests live in:
- `tests/python/test_server.py` — unit tests for pure helpers (no network, no FS)
- `tests/python/test_server_http.py` — HTTP integration tests (boot real server on ephemeral port)
- `tests/python/test_server_branches.py` — branch/error-path integration tests
- `tests/python/test_server_proxy.py` — proxy + `/context7` tests (fake stdlib upstream)

Write tests from spec §5 before touching `server.py`. Run:

```bash
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'
```

Confirm each new test fails for the right reason before writing production code.

**Red receipt (TDD evidence):** paste the failing-test output into the session
memory note before writing any production code (required by `/review` §6a).

### GREEN — minimum code to pass

Implement only what spec §4 describes. Back-end conventions to respect:

**Endpoint pattern:**
```python
def _handler_my_endpoint(self, path, qs, body, send):
    # 1. Validate input size
    # 2. Parse and sanitize parameters (reject path traversal, validate URL scheme)
    # 3. Execute logic (pure helper call preferred)
    # 4. Send response
    pass

routes = {
    ...
    '/my-endpoint': self._handler_my_endpoint,
}
```

**SSRF guard** — mandatory for ANY outbound call:
```python
if not is_safe_upstream_url(url):
    send(400, {"error": "Invalid upstream URL"})
    return
```

**Path-traversal guard** — mandatory for ANY FS endpoint:
```python
safe_path = get_memory_dir(...)  # or equivalent validated path
# Never construct paths from user input with os.path.join alone
```

**`/config` redaction** — if adding new config fields, pattern is:
```python
# SAFE — non-secret value
"my_setting": config.get("MY_SETTING", "default"),
# SAFE — secret as boolean flag only
"has_my_key": bool(config.get("MY_SECRET_KEY", "")),
# NEVER — direct secret exposure
# "my_secret_key": config.get("MY_SECRET_KEY"),  ← FORBIDDEN
```

**Pure helpers** — keep business logic in small pure functions at module scope:
```python
def _my_pure_helper(arg1, arg2):
    """Why this helper exists — what problem it solves."""
    ...
```
These are importable by unit tests without booting the server.

**`add_log` for all logging:**
```python
add_log(f"Action completed: {safe_summary}")  # OK
# Never: print(f"Key={api_key}")  ← FORBIDDEN
```

### REFACTOR — clean up under green

- Extract any duplicated logic into a named pure helper.
- Ensure all error paths return a consistent `{"error": "…"}` JSON body.
- Verify `try/except` blocks are specific (not bare `except Exception`).
- Add `# why` comments explaining non-obvious decisions.
- Re-run `python3 -m py_compile server.py` and the full test suite.

---

## Mandatory back-end gates (before handing back to build.md)

| Gate | Check |
|------|-------|
| **No new runtime deps** | `requirements.txt` unchanged (or new dep is justified, pinned, hash-verified). |
| **SSRF guard on all new outbound calls** | Every new `urlopen`/HTTP call uses `is_safe_upstream_url()`. |
| **Path-traversal guard on all new FS paths** | Every new FS endpoint uses `get_memory_dir()` or equivalent validation. |
| **`/config` still safe** | No new secret fields returned by `/config`. |
| **`.env.example` in sync** | New config keys added to `.env.example` + sync test updated/passing. |
| **`add_log` used for all logging** | No new `print()` or `logging.*` calls. |
| **No secrets in logs** | `add_log` messages contain no keys, tokens, or vault content. |
| **Endpoint registered in `routes`** | New endpoint handler registered in the `routes` dict. |
| **Tests passing** | `.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'` green. |
| **Coverage gate** | `./run-tests.sh --coverage` passes `server.py` ≥ 90% line, ≥ 80% branch. |
| **Security scan clean** | `./scripts/security-scan.sh` exits 0. |

---

## Integration test conventions

HTTP integration tests follow this pattern (from `test_server_http.py`):

```python
class TestMyEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Boot server on ephemeral port — see existing test files for the pattern
        ...

    def test_happy_path(self):
        # Exercise the endpoint, assert on response status + body
        ...

    def test_traversal_rejected(self):
        # Confirm path traversal returns 400/403/404
        ...

    def test_invalid_input(self):
        # Malformed body → 400
        ...
```

Always use a **temp directory** for FS tests — never touch the real vault or
runtime session files.

---

## Scope discipline

The Back-End SME implements **exactly what the spec describes**. If you notice:
- A refactoring opportunity outside the spec → note it as a future backlog item.
- A missing security guard on an **unrelated** existing endpoint → note it as a
  future backlog item (tag: security). Do NOT fix it in this build.
- A missing security guard **on the endpoint you're adding/changing** → fix it now
  (in scope — it directly affects what you're touching).

Do not refactor the entire `server.py` or add unrelated endpoints.

---

## References

- [`docs/rail-pipeline.md` §3](../../docs/rail-pipeline.md) — canonical conventions (SSRF, path-traversal, endpoint pattern, `/config` rule)
- [`docs/principles.md` §1–2](../../docs/principles.md) — minimal runtime surface + DevSecOps
- `build.md` — master orchestrator (sequences this file within Role 3)
- `review.md` — QA verifier (re-runs the "Mandatory back-end gates" table above at §6e-BE, independently of `/build`)
- `sme-frontend.md` — front-end specialist (used when the same spec touches frontend files)
- `tests/python/` — test conventions and patterns to follow
