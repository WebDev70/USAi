# Spec: Reasoning Proxy Integration Test (#11d)

**Status:** Ready
**Type:** chore
**Created:** 2026-06-26
**Author:** Cline / user
**Prior context:** Part of the #11 "Reasoning / Thinking Display" feature cluster. #11a–#11c and #11e are done. This is the sole remaining open sub-item: a Python integration test confirming the proxy relays `reasoning` / `reasoning_content` SSE fields verbatim.

---

## 1. Goal & scope

### Goal
The existing proxy (`_proxy_api` in `server.py`) relays SSE bytes verbatim — it does
not inspect or modify field names. Backlog item **#11d** calls for a Python integration
test that proves this contract holds specifically for the reasoning fields used by
reasoning-capable models (OpenAI o-series, Claude extended thinking, etc.).

The test uses the same fake-upstream pattern already established in
`test_server_proxy.py`: a stdlib `ThreadingHTTPServer` emits canned SSE chunks that
include `delta.reasoning` and `delta.reasoning_content` fields, and the test asserts
those fields arrive in the relayed stream unchanged.

### Out of scope
- No change to `server.py` — the proxy already relays correctly; this spec is
  test-only.
- No JS test changes — JS-side reasoning display tests (RD-1…RD-12) are already done.
- Non-streaming (batch) path verification — the same relay logic applies; one
  streaming test is the primary gap.

---

## 2. User story & acceptance criteria

As a developer maintaining the USAi proxy I want a regression test that confirms
the proxy does not strip or mangle reasoning fields so that future refactors of the
streaming relay cannot silently break reasoning-capable model support.

- [ ] **AC-1:** A fake upstream emitting SSE chunks with `delta.reasoning` →
  the relayed stream (received by the test client) contains those exact
  `delta.reasoning` values intact.
- [ ] **AC-2:** A fake upstream emitting SSE chunks with `delta.reasoning_content`
  (alternate field name used by some providers) → the relayed stream contains
  those `delta.reasoning_content` values intact.
- [ ] **AC-3:** A fake upstream that also includes `delta.content` alongside
  `delta.reasoning` → both fields are present in the relayed stream, confirming
  co-presence is preserved.
- [ ] **AC-4:** The test is self-contained (no network, no third-party deps —
  stdlib only) and follows the class/setup/teardown pattern of
  `ProxyStreamingTests` in `test_server_proxy.py`.

---

## 3. Affected files

| File | Change |
|------|--------|
| `tests/python/test_server_proxy.py` | New test class `ProxyReasoningStreamTests` + new fake upstream handler `_ReasoningStreamUpstreamHandler` |
| `docs/specs/reasoning-proxy-integration-test.md` | This file |
| `backlog.md` | Mark `#11d` done |
| `CHANGELOG.md` | Add entry under `[Unreleased]` |
| `server.py` | No change |
| `app.js` | No change |
| `index.html` | No change |
| `styles.css` | No change |

---

## 4. Technical approach

### Role 2 — Architect sign-off

#### New fake upstream handler: `_ReasoningStreamUpstreamHandler`
- Extends `BaseHTTPRequestHandler`, silences logs.
- `do_POST`: drains the request body, then writes a sequence of SSE lines over
  `text/event-stream`, using HTTP/1.0-style connection-close framing (matching the
  existing `_StreamUpstreamHandler` pattern).
- Emits **three SSE data frames**:

  ```
  data: {"id":"1","choices":[{"delta":{"reasoning":"Think step 1"}}]}

  data: {"id":"2","choices":[{"delta":{"reasoning_content":"Think step 2","content":"Answer"}}]}

  data: {"id":"3","choices":[{"delta":{"content":" more"}}]}

  data: [DONE]
  ```

  This covers AC-1 (reasoning field), AC-2 (reasoning_content field), and AC-3
  (co-presence of content + reasoning_content).

#### New test class: `ProxyReasoningStreamTests`
- Pattern: identical lifecycle to `ProxyStreamingTests` — `setUpClass` starts the
  fake upstream and a USAi `ThreadingHTTPServer`; `tearDownClass` shuts both down
  and restores `server.CONFIG`.
- `CONFIG` patch: same minimal keys as other streaming tests
  (`api_key`, `base_url`, `_test_allow_loopback: True`).
- Test method uses a raw socket (matching `ProxyStreamingTests.test_streaming_response_is_relayed`)
  to read all bytes until `[DONE]` is received.
- Assertions:
  - Response status line `HTTP/1.1 200` present.
  - `Content-Type: text/event-stream` header present.
  - Raw body contains `"reasoning":"Think step 1"` (AC-1).
  - Raw body contains `"reasoning_content":"Think step 2"` (AC-2).
  - Raw body contains `"content":"Answer"` alongside the reasoning_content chunk (AC-3).
  - Raw body contains `[DONE]` sentinel (relay completeness).

#### Why raw socket (not `_request`)?
`_request` uses `urllib.request.urlopen`, which may buffer chunked transfer-encoded
streaming responses and is unreliable for SSE. All existing streaming tests use a
raw socket for this reason.

**Conventions applied:**
- [x] No new runtime dependency added — stdlib only
- [x] New endpoint follows `_handler` + `routes` pattern — N/A (test-only)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern — N/A
- [x] `/config` exposes no secrets — N/A
- [x] Path traversal rejected on filesystem access — N/A
- [x] CSS bump applied — N/A (no CSS change)

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-11d-1 | Proxy relays `delta.reasoning` field verbatim in SSE stream | `tests/python/test_server_proxy.py` | integration |
| T-11d-2 | Proxy relays `delta.reasoning_content` field verbatim in SSE stream | `tests/python/test_server_proxy.py` | integration |
| T-11d-3 | `delta.content` is also present when upstream co-emits it alongside `delta.reasoning_content` | `tests/python/test_server_proxy.py` | integration |
| T-11d-4 | `[DONE]` sentinel is relayed (stream completeness) | `tests/python/test_server_proxy.py` | integration |

All four assertions live inside a single test method
`test_reasoning_fields_relayed_verbatim` within `ProxyReasoningStreamTests`.

**TDD order:** Add `_ReasoningStreamUpstreamHandler` + `ProxyReasoningStreamTests`
with assertions → run (Red — class exists but assertions may fail if handler not
wired) → wire handler → run (Green) → refactor if needed.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `backlog.md` — mark `#11d` done
- [ ] `docs/USER_GUIDE.md` — no user-facing change
- [ ] `README.md` — no setup/config change
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention change

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| SSE chunks arrive split across TCP `recv()` boundaries | Accumulate `seen` buffer across all `recv()` calls before asserting (matches existing pattern in `ProxyStreamingTests`) |
| `[DONE]` not received within timeout | Use 10s socket timeout; fail with a clear message if `[DONE]` missing |
| `time.sleep` needed between chunks to avoid race | Add a 20ms sleep between upstream writes (matching `_StreamUpstreamHandler`) |
| Test isolation — `server.CONFIG` mutated by class | `setUpClass` saves `dict(server.CONFIG)` → `tearDownClass` restores it (established pattern) |
| Coverage gate regression | New test adds lines to `test_server_proxy.py`, not `server.py`; no coverage gate risk |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-4 all verified
- [ ] Memory note written to `Cline/memories/`
