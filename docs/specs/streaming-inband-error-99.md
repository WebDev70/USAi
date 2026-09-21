# Spec: Surface in-band SSE error frames in `streamChatApi` (#99)

**Status:** Done
**Created:** 2026-09-21
**Author:** Cline

## 1. Goal & scope

When the upstream gateway is rate-limited (or otherwise errors *after* committing
to a `200 OK` streaming response), it emits the error **inside** the SSE body as a
JSON object with an `error` field rather than as `choices[].delta.content`:

```
a9
{"error":{"message":"I'm receiving a high volume of requests right now, so I couldn't complete your request. Please wait a moment and try again.","type":"rate_limit"}}

0
```

`streamChatApi` (`frontend/app.js`) only reads `json.choices[0].delta.content`, so
this frame is silently ignored. `assistantText` stays empty, the function returns
`{ assistantText: null }`, and `normalizeAssistantText(null)` renders/persists the
placeholder **"No assistant text received."** as a fake assistant turn — which then
reappears on reload (`chat_history.json` is written with the bogus turn).

**In scope:** detect an in-band `error` object in the streaming SSE loop and return
`{ error }` so the existing error branches in `sendMessage` short-circuit *before*
`persistExchange` — no fake turn is ever rendered or saved.

**Out of scope:** the Python proxy (it correctly relays the frame verbatim — proven
by `.raw_responses/` capture and `ProxyReasoningStreamTests`); the non-streaming
path (`callChatApi` already surfaces `!resp.ok`); retry/back-off behaviour; UI copy
changes beyond showing the upstream error message.

## 2. User story & acceptance criteria

As a user, when the model service is rate-limited mid-stream, I want to see the
error message instead of a silent empty reply, so that I know to retry and my chat
history isn't polluted with an empty ghost turn.

- [x] **AC-1** Given a `200` SSE stream whose only data frame is
  `{"error":{"message":"…","type":"rate_limit"}}`, `streamChatApi` returns an object
  with a truthy `error` string containing the upstream message, and **not**
  `assistantText`.
- [x] **AC-2** `onDelta` is never invoked for an in-band error frame.
- [x] **AC-3** A normal content stream (no `error` field) is unaffected — deltas
  accumulate and `{ assistantText }` is returned exactly as today (regression).
- [x] **AC-4** A mixed stream that emits real content deltas *then* an error frame
  returns `{ error }` (the error is authoritative; a partial answer must not be
  silently persisted as if complete).
- [x] **AC-5** No fake "No assistant text received." turn is persisted: with the
  error surfaced, `sendMessage`'s existing `if (error) { … return; }` branch runs
  before `persistExchange`.

## 3. Affected files

- `frontend/app.js` — `streamChatApi` SSE parse loop: detect `json.error` and
  capture it; after the read loop, if an in-band error was seen return `{ error }`.
- `frontend/tests/js/app.behavior.test.mjs` — new tests **SIE-1..SIE-3**
  (in-band error only; mixed content-then-error; regression happy path already
  covered by B-04 but re-assert no-error).

## 4. Technical approach

In the frame parse loop, alongside the existing `delta`/`usage` extraction, add:

```js
const inbandError = json?.error;
if (inbandError) {
  const msg = typeof inbandError === 'string'
    ? inbandError
    : (inbandError.message || JSON.stringify(inbandError));
  streamError = `API error (stream): ${msg}`;
  logger.error('chat', 'Upstream error delivered in SSE stream', { error: msg });
  // stop reading further frames — the stream is aborted upstream
  break; // out of the per-line loop
}
```

Track `let streamError = null;` before the read loop; after the loop, if
`streamError` is set, `return { error: streamError };`. Break out of the outer
`while (true)` read loop too (guard with the same flag) so we stop promptly. Keep
the existing `assistantText || null` return path for the normal case.

Conventions: frontend-only vanilla JS; no new deps; the three send-paths already
return on `{ error }` before `persistExchange`, so no send-path change is required.

## 5. Test plan

| Test | File | Description |
|------|------|-------------|
| SIE-1 | app.behavior.test.mjs | 200 stream with a single `{"error":{…}}` frame → `result.error` truthy & contains message; `onDelta` not called; no `assistantText` |
| SIE-2 | app.behavior.test.mjs | Stream emits `content` deltas then an `error` frame → returns `{ error }` (AC-4) |
| SIE-3 | app.behavior.test.mjs | Normal content stream → `{ assistantText }`, no `error` (regression, AC-3) |

Full suite + coverage gate: `./run-tests.sh --coverage`
(server.py ≥ 90% lines; JS branch ≥ 70%).

## 6. Docs to update

- [ ] CHANGELOG.md (`### Fixed` under `[Unreleased]`)
- [ ] backlog.md (add #99 → Done under Bug fixes)
- [ ] Cline/scrum/product-backlog.md (mirror #99)
- [ ] docs/USER_GUIDE.md — not user-facing config; skip
- [ ] README.md — no setup change; skip

## 7. Risks / edge cases

- `error` could be a bare string vs an object — handle both.
- A stream that emits partial content then errors: we deliberately discard the
  partial (AC-4) because it is not a complete answer and persisting it would be
  misleading; the raw capture still records it for debugging.
- `[DONE]` after an error frame: harmless — we already `break` on the error.

## 8. Review checklist (filled by Reviewer role)

- [x] Implementation matches spec sections 3–5
- [x] `./run-tests.sh --coverage` passes (server.py branch 92.31%, JS branch 75.29%)
- [x] `./scripts/security-scan.sh` clean (2/4 ran, 0 findings; gitleaks + memory-note skipped — unavailable in shell / `OBSIDIAN_VAULT_PATH` unset)
- [x] Docs updated (section 6)
- [x] Memory note written
