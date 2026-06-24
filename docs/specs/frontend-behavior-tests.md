# Spec: Frontend Behavior Tests (jsdom dev-only layer)

**Status:** Ready  
**Created:** 2026-06-24  
**Author:** Cline  
**Type:** feature (test infrastructure only — no app-code changes)

---

## 1. Goal & scope

Add a **dev-only jsdom layer** to the test suite so the orchestration logic in
`app.js` — `sendMessage`, `streamChatApi`, `callChatApi`, `runWithTools`,
`loadChatHistory`, `archiveCurrentSession`, `appendMessage`, `saveMemory`,
`saveSettings/restoreSettings`, and the error-display path — can be exercised by
`node --test` without requiring a real browser.

This closes the largest single gap identified in
`docs/specs/qa-testing-review.md` (P1): today, the 16 user-facing UI flows are
completely untested. A regression in any of them silently passes all CI gates.

**Explicitly out of scope:**
- Changing any production app code (`app.js`, `server.py`, `index.html`,
  `styles.css`).
- End-to-end Puppeteer/Playwright tests (separate decision; this spec is for
  unit-level DOM behavior tests only).
- Adding runtime dependencies to the app.

---

## 2. User story & acceptance criteria

> As a developer, I want `node --test` to exercise the key user-flow functions in
> `app.js` using a lightweight jsdom DOM stub, so that UI-flow regressions are caught
> by CI before they reach production.

- [ ] **AC-1:** A `tests/js/app.behavior.test.mjs` file exists and is picked up by
  the existing `node --test $(find tests/js -name '*.test.mjs')` command in
  `run-tests.sh` — no changes to test runner config.
- [ ] **AC-2:** `jsdom` is listed as a **dev-only** dependency in a new
  `package.json` (or `package-dev.json`) — **not** in `requirements.txt`, not
  imported by `app.js`, and never shipped in the running app.
- [ ] **AC-3:** Tests pass for all behaviours listed in §4.
- [ ] **AC-4:** The `run-tests.sh` test step installs jsdom if not already present
  (`npm install --save-dev jsdom` in a dev context, or a `Makefile` `dev-setup`
  target). The step is gated so it doesn't fail if `node_modules` is absent — it
  gracefully skips the behavior tests with a clear warning in that case.
- [ ] **AC-5:** CI installs jsdom before running the test step; existing JS/Python
  jobs continue to pass unchanged.
- [ ] **AC-6:** The JS branch coverage gate (70% of exported helpers) is unchanged.
  The behavior tests may push coverage higher but must not lower it.
- [ ] **AC-7:** `./scripts/security-scan.sh` passes cleanly — jsdom is a dev dep
  only, pip-audit/bandit are unaffected.

---

## 3. Affected files

| File | Change |
|------|--------|
| `tests/js/app.behavior.test.mjs` | **New** — jsdom-based behavior tests |
| `package.json` | **New** — `{"devDependencies": {"jsdom": "^25"}}` |
| `run-tests.sh` | **Modify** — add optional behavior-test step (jsdom-guarded) |
| `.github/workflows/tests.yml` | **Modify** — `npm ci` + run behavior tests in JS job |
| `docs/specs/frontend-behavior-tests.md` | This file |
| `CHANGELOG.md` | **Update** — record the new test layer |
| `backlog.md` | **Update** — check off the frontend-tests item |

**Not changing:** `app.js`, `server.py`, `index.html`, `styles.css`, `requirements.txt`.

---

## 4. Technical approach

### 4a. Why jsdom?

jsdom provides a complete DOM + `window` + `localStorage` environment in Node.
It is the standard approach used by testing frameworks (Jest, Vitest) to test
browser code without a browser. The project already stubs `document`/`window`/
`localStorage` at the top of `app.test.mjs` for the sidebar tests — the pattern
is proven; jsdom just makes it richer.

`jsdom` is **dev/CI only** under the existing `RUNTIME vs DEV/CI` litmus test in
`docs/principles.md §1` — it ships nothing into the running app.

### 4b. Test file structure

```js
// tests/js/app.behavior.test.mjs
//
// Behavior tests for the orchestration layer of app.js (sendMessage,
// streamChatApi, callChatApi, runWithTools, appendMessage, etc.)
//
// Requires jsdom (dev-only):  npm install --save-dev jsdom
// Run with: node --test tests/js/app.behavior.test.mjs
//   (or via run-tests.sh which discovers all *.test.mjs files)

import { test, describe, beforeEach, mock } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

// Bootstrap a minimal DOM that satisfies app.js globals
function makeDom() {
  const dom = new JSDOM('<!DOCTYPE html>...<minimal-html>...', {
    url: 'http://localhost:8000',
    pretendToBeVisual: true,
  });
  // Expose globals app.js expects
  global.window    = dom.window;
  global.document  = dom.window.document;
  global.localStorage = dom.window.localStorage;
  global.fetch     = stubFetch;       // see §4d
  global.performance = dom.window.performance;
  return dom;
}
```

### 4c. Stubs required

| Global / API | Stub approach |
|-------------|--------------|
| `fetch` | `node:test` `mock.fn()` — returns canned response objects per test |
| `localStorage` | jsdom's built-in `localStorage` (no stub needed) |
| `document` / DOM | jsdom (complete) |
| `performance.now()` | jsdom's `performance` (works in Node context) |
| `AbortController` | Node built-in (already available in Node 18+) |
| `ReadableStream` / SSE | `node:stream` `Readable` adapted to `Response.body` |

### 4d. `fetch` stub pattern

```js
function stubFetch(responses) {
  // responses: Map<url-pattern, {status, body, stream?}>
  return async (url, opts) => {
    const match = [...responses.entries()]
      .find(([pattern]) => url.includes(pattern));
    if (!match) throw new Error(`No fetch stub for: ${url}`);
    const [, { status = 200, body = '{}', stream = false }] = match;
    if (stream) {
      // Returns a ReadableStream of SSE chunks for streamChatApi tests
      const { Readable } = await import('node:stream');
      const r = new Readable({ read() {} });
      // Push SSE frames after a tick so the consumer can attach
      setImmediate(() => { /* push chunks... */ r.push(null); });
      return { ok: status < 400, status, body: r };
    }
    return { ok: status < 400, status,
             json: async () => JSON.parse(body),
             text: async () => body };
  };
}
```

### 4e. Import strategy

`app.js` uses `module.exports` only under the Node guard. The behavior tests need
to invoke DOM-aware functions that are **not** exported. Two options:

1. **Option A (preferred — no app changes):** Load `app.js` via `import()` *after*
   setting `global.document` etc. (jsdom globals in place). Functions declared with
   `function` keyword are hoisted onto the module scope — call them by monkey-
   patching onto `global` before load, or use `vm.runInContext` with the jsdom window.
2. **Option B:** Add more exports to the `module.exports` guard in `app.js`. This is
   safe (browser ignores the block) but couples the spec to the internal API.

Recommendation: **Option A** for functions that work purely with stubbed globals;
**Option B** only for functions that are trivially extractable (e.g., `appendMessage`
is already well-isolated).

---

## 5. Test plan

| ID | Function under test | Scenario | Assertion |
|----|--------------------|---------|----|
| B-01 | `callChatApi` | Happy path — fetch returns 200 JSON | Returns `{assistantText, usage}` |
| B-02 | `callChatApi` | fetch returns 4xx | Returns `{error}` with status in message |
| B-03 | `callChatApi` | fetch throws (network error) | Returns `{error}` |
| B-04 | `streamChatApi` | Receives 3 SSE `data:` lines + `[DONE]` | `onDelta` called 3 times; returns full `{assistantText}` |
| B-05 | `streamChatApi` | Stream returns HTTP 429 before body | Returns `{error}` with status 429 |
| B-06 | `streamChatApi` | AbortController fires mid-stream | Stops calling `onDelta`; returns `{assistantText: partial}` |
| B-07 | `runWithTools` | One tool call round-trip (non-streaming) | Calls tool handler, sends result back, returns final text |
| B-08 | `runWithTools` | Tool not in registry | Returns `{error}` or safe fallback |
| B-09 | `appendMessage` | Role "assistant" + markdown text | DOM contains a `.message-bubble` with rendered HTML |
| B-10 | `appendMessage` | Role "user" | DOM contains `.message-group.user` |
| B-11 | `appendMessage` | XSS payload in `text` | Output HTML does not contain `<script>` |
| B-12 | `saveSettings` + `restoreSettings` | Round-trip model + temperature | After restore, `document` fields reflect saved values |
| B-13 | `saveMemory` | fetch returns saved memory | Returns `{ok: true, path}` |
| B-14 | `saveMemory` | fetch returns 400 | Returns `{error}` |
| B-15 | `archiveCurrentSession` | Non-empty `chatDisplayHistory` | `POST /sessions` called with correct payload |
| B-16 | `archiveCurrentSession` | Empty history | `fetch` NOT called |
| B-17 | `loadChatHistory` | Server returns `{turns: [...]}` | Conversation history array populated; DOM shows turns |
| B-18 | `loadChatHistory` | Server returns `{turns: []}` | No error; DOM empty |
| B-19 | Error display path | `sendMessage` with network error | Error bubble with human-readable message appears in DOM |

---

## 6. Docs to update

- [x] `docs/specs/frontend-behavior-tests.md` (this file)
- [ ] `CHANGELOG.md`
- [ ] `backlog.md` (mark item done / reference this spec)
- [ ] `docs/rail-pipeline.md` — add `jsdom` to the dev tooling table
- [ ] `README.md` — add `npm install` (dev-setup step) to Getting Started

---

## 7. Risks / edge cases

| Risk | Mitigation |
|------|-----------|
| jsdom is a significant package (~8 MB node_modules) | Kept strictly dev-only; never in `requirements.txt`; `npm install` only in dev/CI context |
| jsdom globals may not satisfy all app.js expectations (e.g., `MutationObserver`, `crypto.randomUUID`) | Stub only what the tested functions need; skip (`.skip`) tests for functions that need untested globals and add a TODO |
| Adding `package.json` changes how Node discovers files | Use `"private": true`, no `"main"`, `"type": "module"` — compatible with `node --test` |
| `app.js` loaded globally pollutes cross-test state | Reset DOM + `global.fetch` in `beforeEach`; use `JSDOM` fresh per describe block |
| CI speed regression | jsdom install is fast (~1s); behavior tests should stay < 2s total; no external I/O |
| `app.js` uses `DOMContentLoaded` event to wire things up | Dispatch the event manually in test setup after globals are in place |

---

## 8. Review checklist (filled by Reviewer role)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh` (without `--coverage`) passes — jsdom behavior tests included
- [ ] `./run-tests.sh --coverage` passes — coverage gates unchanged or improved
- [ ] `./scripts/security-scan.sh` clean
- [ ] No app code changed (`app.js`, `server.py`, `index.html`, `styles.css` diffs = empty)
- [ ] Docs updated (§6 checklist)
- [ ] Memory note written

---

## Appendix: minimal `package.json`

```json
{
  "private": true,
  "description": "Dev-only tooling for USAi Chat (not shipped in the app).",
  "type": "module",
  "devDependencies": {
    "jsdom": "^25.0.0"
  },
  "scripts": {
    "test": "node --test $(find tests/js -name '*.test.mjs')",
    "test:behavior": "node --test tests/js/app.behavior.test.mjs"
  }
}
```

## Appendix: `run-tests.sh` addition (behavior-test step)

```bash
echo "── JS behavior tests (jsdom, dev-only) ───────────────────"
if [ -d "node_modules/jsdom" ]; then
  node --test tests/js/app.behavior.test.mjs
else
  echo "  ⚠ jsdom not installed — skipping behavior tests."
  echo "    Run: npm install  (or: make dev-setup)"
fi
```

## Appendix: `.github/workflows/tests.yml` addition

```yaml
      - name: Install JS dev dependencies (jsdom for behavior tests)
        run: npm ci   # reads package.json; installs jsdom
      - name: Run JS behavior tests (jsdom DOM stubs)
        run: node --test tests/js/app.behavior.test.mjs
```
