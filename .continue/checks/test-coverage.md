---
name: Test Coverage
description: New or changed logic in app.js / server.py ships with corresponding tests following project conventions
---

Review this change for **test coverage** under the project's **TDD** workflow
(`.continue/rules/tdd-workflow.md`) and zero-dependency test stack
(`docs/rail-pipeline.md`).

Pass the check only if all of these hold:

- **Tests-first / Red→Green.** New or modified logic ships with tests, and bug
  fixes include a **regression test** that would fail without the fix. (Ideally the
  test was written before the implementation per TDD.)
- New or modified **pure/testable functions** in `app.js` have corresponding cases
  in `tests/js/*.test.mjs`, and any importable helper is added to the Node-only
  `module.exports` block at the end of `app.js`.
- New or modified **logic in `server.py`** has corresponding cases. Prefer **HTTP
  integration tests** (`tests/python/test_server_http.py` /
  `test_server_branches.py` / `test_server_proxy.py`) for handler/routing changes,
  and unit tests for pure helpers (`get_memory_dir`, `_slugify`,
  `_resolve_memory_file`, `add_log`, `load_config`, `_get_config` redaction).
- Tests follow the existing conventions: `node:test`/`node:assert` for JS,
  `unittest.TestCase` for Python; file naming `*.test.mjs` / `test_*.py`.
- **Coverage gates pass:** `./run-tests.sh --coverage` keeps `server.py` ≥ 90% and
  the JS branch gate ≥ its threshold. Coverage tooling must remain **dev-only**
  (`coverage.py` in the venv, Node's built-in coverage) — never a runtime dep.
- `./run-tests.sh` still passes (no broken or silently skipped tests).

Flag as **failing** if new behavior is added with no tests, a fix has no regression
test, tests don't follow the conventions above, coverage drops below the gate, or a
new test framework/dependency (pytest, jest, vitest, etc.) was introduced.

If the change is a pure doc/config edit with no code-behavior change, pass.
