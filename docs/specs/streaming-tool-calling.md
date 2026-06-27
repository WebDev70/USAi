# Spec: Streaming + Tool Calling Together (#9)

**Status:** In Progress
**Created:** 2026-06-25
**Updated:** 2026-06-26
**Author:** Cline

---

## 1. Goal & scope

Allow the model to **stream its final text reply** even when tool calling is
enabled.  Today `runWithTools` forces non-streaming for every round; after this
change only the intermediate tool-request rounds stay non-streaming — the final
round (where the model produces its answer with no more tool calls) switches to
`streamChatApi` so the user sees tokens arriving in real time.

**In scope:**
- Modify `runWithTools` to accept an options object `{ streamFinalAnswer, callFn, streamFn, onDelta }`
  so the final-answer round can stream.
- Update the tool-calling path in `sendMessage` (3a) to create the bubble
  *before* calling `runWithTools`, pass an `onDelta` callback for live rendering,
  and handle the streamed result.
- Remove the `streamToggle.disabled = toolsEnabled` override from the
  `toolsToggle` change listener so the stream toggle works with tools on.
- Also update the `jsonModeToggle` listener which computes
  `streamToggle.disabled = enabled || toolsEnabled` — that should no longer
  gate on `toolsEnabled`.
- Add a `_runWithToolsTest` export so unit tests can inject `callFn` / `streamFn`.
- Write 4 new JS unit tests (ST-1 through ST-4).

**Out of scope:**
- Accumulating `delta.tool_calls` fragments from a *tool-request* round
  (i.e. streaming the tool-call JSON itself) — that is the harder "parallel
  streaming tool calls" feature; defer.
- Reasoning / thinking streaming (#11 — already done).
- Any `server.py` changes.

---

## 2. User story & acceptance criteria

*As a USAi user, I want tool-assisted responses to stream just like normal
responses, so I see the answer appearing word-by-word instead of waiting for
the whole reply.*

- [ ] When tools are enabled AND `streamEnabled` is true, the final answer
  round inside `runWithTools` uses `streamChatApi` (or the injected `streamFn`),
  not `callChatApi`.
- [ ] Intermediate rounds (where the model requests tool calls) remain
  non-streaming (`callChatApi`) so we can inspect `tool_calls`.
- [ ] The stream-toggle is **no longer disabled** when tools are on; it
  controls whether the final answer is streamed.
- [ ] If `streamEnabled` is false (user unchecked stream), `runWithTools`
  falls back to `callChatApi` for the final round (original behaviour).
- [ ] `streamChatApi` receives an `onDelta` callback that updates the
  `bubble` in real time (same as the non-tool streaming path — 3b).
- [ ] Abort / cancel works correctly mid-stream on the tool path.
- [ ] 4 new JS unit tests all pass: ST-1 (final round streamed), ST-2
  (intermediate rounds not streamed), ST-3 (stream off → callFn used for final
  round), ST-4 (streaming abort propagates).
- [ ] All existing JS tests still pass (≥ 24 total after adding 4 new ones).
- [ ] server.py coverage still ≥ 90 %; JS branch ≥ 70 %.
- [ ] Security scan clean.
- [ ] `CHANGELOG.md` updated; `backlog.md` item #9 checked off.

---

## 3. Affected files

- `app.js` — `runWithTools`, `toolsToggle` event handler, `jsonModeToggle`
  event handler, tool path in `sendMessage` (3a), `module.exports`
- `tests/js/app.test.mjs` — 4 new ST-* tests
- `CHANGELOG.md` — new entry
- `backlog.md` — item #9 checked off
- `docs/USER_GUIDE.md` — minor note in streaming section

---

## 4. Technical approach

### 4.1 `runWithTools` signature change

Add an options third parameter (default values shown). Also rename the internal
`callChatApi` references to `callFn` when using the injected version so tests
don't need network access:

```js
// Options: streamFinalAnswer (bool), callFn (for non-streaming rounds, default=callChatApi),
//          streamFn (for final answer, default=streamChatApi), onDelta (callback for streaming)
async function runWithTools(basePayload, conversation, {
  streamFinalAnswer = false,
  callFn = callChatApi,
  streamFn = streamChatApi,
  onDelta = null,
} = {})
```

**Why `streamFinalAnswer = false` default?** Keeps the function's existing
contract intact if called without options (the MAX_TOOL_ROUNDS safety path and
any future callers stay non-streaming by default).

### 4.2 Final-answer call inside `runWithTools`

Replace the `!toolCalls.length` early-return branch (line 1959–1962):

```js
if (!toolCalls.length) {
  // No tools requested — this is the final answer.
  if (streamFinalAnswer && streamFn) {
    const finalPayload = { ...basePayload, messages };
    // streamFn returns { assistantText, usage } or { aborted, assistantText } or { error }
    const streamResult = await streamFn(finalPayload, onDelta);
    return { ...streamResult, toolsUsed };
  }
  return { assistantText: message?.content || null, usage: lastUsage, toolsUsed };
}
```

The MAX_TOOL_ROUNDS fallback at the bottom stays non-streaming (safety net).

### 4.3 Tool path in `sendMessage` (3a) — bubble-first pattern

The current code creates the bubble **after** `runWithTools` returns. For
streaming we need the bubble **before** so `onDelta` can write into it.
Restructure the tool path to mirror the streaming path (3b):

```js
if (toolsEnabled) {
  // 3a. Tool-calling path — stream the final answer if streamEnabled
  // Create the assistant bubble now so onDelta can update it in real time.
  const { group, bubble, noteEl } = appendMessage(conversation, '', 'assistant', contextNote);
  if (streamEnabled) bubble.classList.add('streaming');

  const { assistantText, usage, toolsUsed, error, aborted } = await runWithTools(
    payload, conversation,
    {
      streamFinalAnswer: streamEnabled,
      onDelta: streamEnabled ? (_delta, full) => {
        renderBubbleText(bubble, full, false, false);
        conversation.scrollTop = conversation.scrollHeight;
      } : null,
    }
  );

  bubble.classList.remove('streaming');
  responseLog.textContent = '';

  if (aborted) {
    if (!assistantText) { group.remove(); responseLog.textContent = 'Request cancelled.'; return; }
    // partial streamed text — keep it (same as 3b abort handling)
  }
  if (error) { group.remove(); responseLog.textContent = error; return; }

  const finalText = normalizeAssistantText(assistantText);
  renderBubbleText(bubble, finalText, true); // final Markdown render
  const usageText = formatUsage(usage);
  const uniqueTools = toolsUsed && toolsUsed.length ? [...new Set(toolsUsed)] : [];
  const toolNote = uniqueTools.length ? `Tools: ${uniqueTools.join(', ')}` : '';
  const contextNoteForAssistant = (uniqueTools.length && contextNote === 'No external context')
    ? '' : contextNote;
  setMessageNote(group, noteEl, [contextNoteForAssistant, toolNote, usageText]);
  addMessageActions(group, 'assistant', userDisplayIndex + 1);
  conversation.scrollTop = conversation.scrollHeight;
  await persistExchange(inputs.content, finalText, contextNote, usageText,
    userApiContent, attachedImages, [contextNoteForAssistant, toolNote]);
  ...
}
```

### 4.4 Stream-toggle gating

In the `toolsToggle` change listener (line 2443–2450), **remove**:
```js
if (streamToggle) streamToggle.disabled = toolsEnabled;
```

In the `jsonModeToggle` change listener (line 2452–2462), change:
```js
if (streamToggle) streamToggle.disabled = enabled || toolsEnabled;
```
to:
```js
if (streamToggle) streamToggle.disabled = enabled; // JSON mode disables stream; tools no longer do
```

### 4.5 `_runWithToolsTest` export

Export a testable wrapper that forwards options into `runWithTools`:

```js
_runWithToolsTest: async (basePayload, msgs, opts) =>
  runWithTools(basePayload,
    { appendChild: () => {}, scrollTop: 0, scrollHeight: 0 },
    opts),
```

Add to the `module.exports` block.

---

## 5. Test plan

| Test ID | File | Description |
|---------|------|-------------|
| ST-1 | `tests/js/app.test.mjs` | Final round uses `streamFn` when `streamFinalAnswer: true` |
| ST-2 | `tests/js/app.test.mjs` | Intermediate tool-call rounds use `callFn` (non-stream) |
| ST-3 | `tests/js/app.test.mjs` | `streamFinalAnswer: false` → `callFn` used for final round |
| ST-4 | `tests/js/app.test.mjs` | Abort from `streamFn` propagates `{ aborted: true }` |

**ST-1 — final round streamed:**
```js
test('ST-1: runWithTools streams the final answer round', async () => {
  let streamCalled = false;
  const callFn  = async () => ({
    message: { role: 'assistant', content: 'hello', tool_calls: [] },
    usage: { total_tokens: 5 },
  });
  const streamFn = async (_payload, onDelta) => {
    streamCalled = true;
    if (onDelta) onDelta('hello', 'hello');
    return { assistantText: 'hello', usage: { total_tokens: 5 } };
  };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    [],
    { streamFinalAnswer: true, callFn, streamFn },
  );
  assert.equal(streamCalled, true, 'streamFn must be called');
  assert.equal(result.assistantText, 'hello');
});
```

**ST-2 — intermediate rounds use callFn:**
```js
test('ST-2: runWithTools uses callFn for intermediate (tool-call) rounds', async () => {
  let callCount = 0, streamCount = 0;
  // Round 0: model requests a tool; Round 1: model gives final answer
  const callFn = async (_payload) => {
    callCount++;
    if (callCount === 1) {
      return {
        message: {
          role: 'assistant', content: null,
          tool_calls: [{ id: 't1', function: { name: 'test_tool', arguments: '{}' } }],
        },
        usage: null,
      };
    }
    return { message: { role: 'assistant', content: 'done', tool_calls: [] }, usage: null };
  };
  const streamFn = async () => { streamCount++; return { assistantText: 'done', usage: null }; };
  await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    [],
    { streamFinalAnswer: true, callFn, streamFn },
  );
  assert.equal(callCount, 2, 'both rounds should use callFn (tool round + final)');
  assert.equal(streamCount, 1, 'streamFn called for the final answer');
});
```

**ST-3 — stream off → callFn for final:**
```js
test('ST-3: runWithTools uses callFn for final answer when streamFinalAnswer is false', async () => {
  let callCount = 0, streamCount = 0;
  const callFn = async () => {
    callCount++;
    return { message: { role: 'assistant', content: 'hi', tool_calls: [] }, usage: null };
  };
  const streamFn = async () => { streamCount++; return { assistantText: 'hi', usage: null }; };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    [],
    { streamFinalAnswer: false, callFn, streamFn },
  );
  assert.equal(callCount, 1, 'callFn used for final answer');
  assert.equal(streamCount, 0, 'streamFn should not be called');
  assert.equal(result.assistantText, 'hi');
});
```

**ST-4 — abort propagates:**
```js
test('ST-4: abort from streamFn propagates aborted:true', async () => {
  const callFn = async () => ({
    message: { role: 'assistant', content: null, tool_calls: [] }, usage: null,
  });
  const streamFn = async () => ({ aborted: true, assistantText: 'partial' });
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    [],
    { streamFinalAnswer: true, callFn, streamFn },
  );
  assert.equal(result.aborted, true, 'aborted should propagate');
  assert.equal(result.assistantText, 'partial', 'partial text should be preserved');
});
```

> **Note on ST-2:** The `callFn` for round 1 (final answer, no tool_calls) should
> return via the `callFn` path when `streamFinalAnswer: true` since that round *has*
> no tool calls and we stream it via `streamFn`. Revise test logic accordingly
> during Red phase if needed.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — "Streaming + tool calling: final answer now streamed"
- [ ] `docs/USER_GUIDE.md` — note that the stream toggle works with tools enabled
- [ ] `backlog.md` — check off item #9

---

## 7. Risks / edge cases

| Risk | Mitigation |
|------|-----------|
| Model returns both text AND `tool_calls` in the same response | Existing code skips to tool-call branch; no change needed |
| Abort mid-stream on tool path | `aborted: true` + partial `assistantText` returned; send-handler handles this like 3b |
| `streamChatApi` adds `stream: true` to payload, but the tool-round payload still has `tool_choice: 'auto'` | Final-answer payload (`{ ...basePayload, messages }`) does NOT include `tools`/`tool_choice` — safe |
| Test isolation: default `streamFn = streamChatApi` requires network | Tests inject their own `callFn`/`streamFn` via `_runWithToolsTest` |
| MAX_TOOL_ROUNDS fallback left non-streamed | Acceptable — safety net path |
| Existing bubble rendered twice (line 2291 `appendMessage`) | Restructured 3a creates bubble before call; old `appendMessage` call removed |
| `restoreSettings()` restores `streamToggle.disabled` state | `restoreSettings` does not set `.disabled`; only the change listeners do — removing the toggle guard is safe |

---

## 8. Definition of Ready

- [x] User story written
- [x] Acceptance criteria are testable and observable
- [x] Vertical slice (no backend changes; one feature, one file changed significantly)
- [x] Size estimate: **M**
- [x] Affected files identified
- [x] Test plan with 4 ST-* tests outlined
- [x] Risks identified and mitigated
- [x] Spec reviewed against current code (2026-06-26 audit)

---

## 9. Review checklist (filled by Reviewer role)

- [ ] Implementation matches spec sections 3–5
- [ ] `./run-tests.sh --coverage` passes (≥ 24 JS tests, server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (section 6)
- [ ] Memory note written
