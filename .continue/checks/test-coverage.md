---
name: Test Coverage
description: New or changed logic in app.js / server.py ships with corresponding tests following project conventions
---

Review this change for **test coverage**, using the project's zero-dependency test
stack (`docs/testing-and-agents-strategy.md`).

Pass the check only if all of these hold:

- New or modified **pure/testable functions** in `app.js` have corresponding cases
  in `tests/js/*.test.mjs`, and any importable helper is added to the Node-only
  `module.exports` block at the end of `app.js`.
- New or modified **logic in `server.py`** (especially `get_memory_dir`,
  `_get_config` redaction, `/memory/*` handling, `_slugify`, routing/input limits)
  has corresponding cases in `tests/python/test_*.py`.
- Tests follow the existing conventions: `node:test`/`node:assert` for JS,
  `unittest.TestCase` for Python; file naming `*.test.mjs` / `test_*.py`.
- Bug fixes include a **regression test** that would fail without the fix.
- `./run-tests.sh` would still pass (no obviously broken or skipped tests).

Flag as **failing** if new behavior is added with no tests, tests don't follow the
conventions above, or a new test framework/dependency (pytest, jest, vitest, etc.)
was introduced.

If the change is a pure doc/config edit with no code-behavior change, pass.
