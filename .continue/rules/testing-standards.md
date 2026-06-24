---
alwaysApply: true
---

# Role: Full Test Suite (Step 3 of RAIL — the Rule-governed Agentic Iteration Loop)

Write and maintain tests for every non-trivial change, using the project's
**zero-dependency** test stack. New/changed logic should ship with tests in the same
turn as the code. Full strategy: `docs/rail-pipeline.md`.

## Stack (no new dependencies)

| Layer | Tool | Command |
|-------|------|---------|
| Python (`server.py`) | `unittest` (stdlib) | `.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'` |
| JS (`app.js`) | `node --test` (Node 18+) | `node --test "tests/js/**/*.test.mjs"` |
| Syntax gates | `node --check`, `py_compile` | `node --check app.js && python3 -m py_compile server.py` |

The easiest way to run everything is the repo's `./run-tests.sh` (syntax gates +
both suites).

Do **not** introduce pytest / jest / vitest or any other test framework — it would
violate the project's no-build, stdlib-only philosophy.

## Layout & naming

```
tests/
├── python/test_*.py      # unittest.TestCase classes
└── js/*.test.mjs         # node:test + node:assert (ESM)
```

## What to test (priorities)

1. **Pure functions** — deterministic, no I/O. Highest value, lowest friction.
   - JS: `renderMarkdown`, `extractJson`, `formatUsage`, `getExcludedParams` /
     `MODEL_PARAM_EXCLUSIONS`, `buildResponseFormat`.
   - Python: `get_memory_dir` (path-traversal guard), config redaction helpers.
2. **Security behavior** — `_get_config` returns no secrets; `/memory/*` confines
   writes to the memory folder and sanitizes filenames; input-size limits.
3. **Edge cases** — empty/missing input, malformed JSON, naming variants, boundary
   values.

## Rules of thumb

- **Deterministic & fast** — no live network/API calls; stub or monkeypatch. The
  whole suite should run in seconds.
- **Test behavior, not implementation details** — avoid brittle DOM/markup
  assertions; assert on outputs/return values.
- To make a function testable, prefer a **small, behavior-preserving refactor**
  (e.g. extract a pure helper; guard `module.exports` in `app.js` so Node can import
  it without affecting the browser) over leaving it untested.
- When you fix a bug, add a **regression test** that fails before the fix.

## After writing tests

Run the full command set above; all tests + syntax gates must pass before handing
off to QA Review (`/check`).
