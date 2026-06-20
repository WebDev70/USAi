---
alwaysApply: true
---

# Role: TDD Workflow (Test-Driven Development — enforced default)

USAi Chat follows **Test-Driven Development**. For any non-trivial change to
testable logic in `app.js` or `server.py`, you **write the test(s) first**, watch
them fail, then write the minimum code to pass, then refactor. This rule is the
inner loop of **RAIL** (the Rule-governed Agentic Iteration Loop) — it sits on top
of the Full Test Suite role (`testing-standards.md`) and the QA checks
(`.continue/checks/`). Full strategy: `docs/testing-and-agents-strategy.md`.

## The Red → Green → Refactor loop (do this every time)

1. **RED — write a failing test first.**
   - Add the test case(s) in `tests/js/*.test.mjs` (JS) or `tests/python/test_*.py`
     (Python) that describe the desired behavior / bug.
   - Run the suite and **show the failure** (paste the failing assertion). A test
     that passes before you write the code proves nothing — it must fail first for
     the right reason.
2. **GREEN — write the minimum code to pass.**
   - Implement the smallest change that makes the new test(s) pass without breaking
     existing ones. Expose new JS helpers via the Node-only `module.exports` guard
     at the end of `app.js`; keep Python helpers module-level and importable.
3. **REFACTOR — clean up under green.**
   - Improve names/structure/comments with the tests still passing. Re-run the full
     suite after refactoring.

State which phase you're in as you go (e.g. "RED: added 2 failing cases", "GREEN:
implemented X, suite passes").

## When TDD applies

- **Always** for: new pure functions, new/changed `server.py` handlers and helpers,
  bug fixes (write the regression test first — it must fail, then fix).
- **Relaxed** for: pure copy/markup/CSS tweaks, doc/config edits, and DOM-only
  wiring that calls already-tested helpers (verify via syntax gates + manual/in
  browser). Even then, prefer extracting any real logic into a tested pure helper.

## What "test everything" means here (layers)

| Layer | How it's covered |
|-------|------------------|
| **Pure functions** (JS + Python) | `node --test` / `unittest` unit tests — the bulk of coverage. |
| **HTTP endpoints** (`server.py`) | **Integration tests** that boot the real `ThreadingHTTPServer` on an ephemeral port and hit routes with stdlib `urllib` (`tests/python/test_server_http.py`). Covers routing, `/config` redaction, `/memory/*`, `/sessions`, `/chunk-cache`, input-size limits, and traversal guards. |
| **Browser DOM wiring** | Syntax gate (`node --check`) + manual/in-browser testing. We do **not** add a headless-browser/jsdom dependency; keep DOM handlers thin and push logic into tested pure helpers. |

## Coverage is measured and gated (dev-only tooling, no runtime deps)

- **Python:** `coverage.py` (installed only in `.venv`, never in
  `requirements.txt`). Threshold: **`server.py` ≥ 90%** lines.
- **JS:** Node's **built-in** `--experimental-test-coverage` (needs Node ≥ 22 —
  the project's dev Node is pinned to 22+/24). Threshold: **tested `app.js` helpers
  ≥ 85%** (the file as a whole will read lower because browser-only DOM code isn't
  unit-tested — that's expected; judge coverage of the *exported* helpers).
- Run locally with **`./run-tests.sh --coverage`**; CI runs it on every push/PR.
- Ratchet thresholds **up** over time; never lower them to make a change pass —
  add tests instead.

## Definition of done (before requesting review / shipping)

1. New/changed logic has tests that were written **first** and failed before the
   code existed.
2. `./run-tests.sh` is green (syntax gates + JS + Python).
3. `./run-tests.sh --coverage` meets thresholds (or you added tests until it did).
4. `/check` passes (test-coverage, security, code-quality, docs-in-sync, and
   ui-ux-review for frontend changes).
5. Docs updated in the same turn (`keep-docs-in-sync`).
