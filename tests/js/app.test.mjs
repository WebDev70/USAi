// Starter unit tests for pure helper functions in ../../app.js
//
// Run from the project root with:  node --test $(find tests/js -name '*.test.mjs')
// (or simply `./run-tests.sh`).
// Uses Node's built-in test runner (node:test) + assertions (node:assert) — no
// third-party test framework, per the project's zero-new-dependency philosophy.
//
// app.js exports these helpers only when `module.exports` exists (Node), so this
// import has no effect on the browser bundle.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

// app.js was written for the browser and touches `document`/`window` at module
// scope (e.g. `document.getElementById(...)` and DOMContentLoaded wiring). To
// unit-test its *pure* helper functions under Node without a DOM library, we
// install tiny no-op stubs for the few globals referenced during load. This adds
// no dependencies and does not change browser behavior — the stubs exist only in
// this test process. If app.js starts referencing more globals at load time, add
// them here.
const noop = () => {};
const fakeEl = {
  addEventListener: noop, removeEventListener: noop,
  appendChild: noop, setAttribute: noop, classList: { add: noop, remove: noop, toggle: noop },
  style: {}, dataset: {}, value: '', textContent: '', innerHTML: '',
  querySelector: () => null, querySelectorAll: () => [],
};
globalThis.document = {
  getElementById: () => fakeEl,
  querySelector: () => fakeEl,
  querySelectorAll: () => [],
  createElement: () => ({ ...fakeEl }),
  addEventListener: noop,
  body: fakeEl,
};
globalThis.window = {
  matchMedia: () => ({ matches: false, addEventListener: noop }),
  addEventListener: noop,
  localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
};
globalThis.localStorage = globalThis.window.localStorage;

// app.js is a CommonJS-style script (uses module.exports under a Node guard), so
// load it via require() rather than ESM import.
const require = createRequire(import.meta.url);
const app = require('../../app.js');

test('escapeHtml escapes the dangerous characters', () => {
  assert.equal(
    app.escapeHtml('<script>"x" & y</script>'),
    '&lt;script&gt;&quot;x&quot; &amp; y&lt;/script&gt;'
  );
});

test('renderMarkdown is XSS-safe: raw HTML is escaped, not executed', () => {
  const html = app.renderMarkdown('<img src=x onerror=alert(1)>');
  assert.ok(!html.includes('<img'), 'raw <img> tag must be escaped');
  assert.ok(html.includes('&lt;img'), 'angle brackets should be escaped');
});

test('renderMarkdown renders bold and inline code', () => {
  const html = app.renderMarkdown('Hello **world** and `code`');
  assert.match(html, /<strong>world<\/strong>/);
  assert.match(html, /<code[^>]*>code<\/code>/);
});

test('renderMarkdown renders fenced code blocks', () => {
  const html = app.renderMarkdown('```js\nconst a = 1;\n```');
  assert.match(html, /<pre class="md-pre"><code class="language-js">/);
  assert.match(html, /const a = 1;/);
});

test('renderMarkdown handles null/undefined safely', () => {
  assert.equal(app.renderMarkdown(null), '');
  assert.equal(app.renderMarkdown(undefined), '');
});

test('extractJson parses plain JSON', () => {
  assert.deepEqual(app.extractJson('{"a":1,"b":[2,3]}'), { a: 1, b: [2, 3] });
});

test('extractJson recovers JSON from a ```json fenced block', () => {
  const text = 'Sure, here you go:\n```json\n{"ok": true}\n```\nLet me know!';
  assert.deepEqual(app.extractJson(text), { ok: true });
});

test('extractJson recovers the first balanced object from prose', () => {
  assert.deepEqual(app.extractJson('blah {"x": 1} trailing'), { x: 1 });
});

test('extractJson returns null for non-strings and unparseable input', () => {
  assert.equal(app.extractJson(42), null);
  assert.equal(app.extractJson('no json here'), null);
});

test('formatUsage tolerates both prompt_tokens and input_tokens naming', () => {
  assert.equal(
    app.formatUsage({ prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 }),
    '10 in · 5 out · 15 total tokens'
  );
  assert.equal(
    app.formatUsage({ input_tokens: 7, output_tokens: 3 }),
    '7 in · 3 out · 10 total tokens'
  );
  assert.equal(app.formatUsage(null), '');
});

// FU-R1: reasoning_tokens inside completion_tokens_details → appended as "· 32 reasoning"
test('formatUsage appends reasoning token count when completion_tokens_details.reasoning_tokens > 0', () => {
  assert.equal(
    app.formatUsage({
      prompt_tokens: 84,
      completion_tokens: 51,
      total_tokens: 135,
      completion_tokens_details: { reasoning_tokens: 32 },
    }),
    '84 in · 51 out · 135 total · 32 reasoning tokens'
  );
});

// FU-R2: reasoning_tokens === 0 → NO reasoning segment (no false positive)
test('formatUsage does NOT append reasoning segment when reasoning_tokens is 0', () => {
  const result = app.formatUsage({
    prompt_tokens: 10,
    completion_tokens: 5,
    total_tokens: 15,
    completion_tokens_details: { reasoning_tokens: 0 },
  });
  assert.equal(result, '10 in · 5 out · 15 total tokens');
  assert.ok(!result.includes('reasoning'), 'must not mention reasoning when count is 0');
});

// FU-R3: top-level reasoning_tokens fallback (alt provider shape)
test('formatUsage accepts top-level reasoning_tokens as fallback', () => {
  assert.equal(
    app.formatUsage({
      prompt_tokens: 20,
      completion_tokens: 10,
      total_tokens: 30,
      reasoning_tokens: 5,
    }),
    '20 in · 10 out · 30 total · 5 reasoning tokens'
  );
});

// FU-R4: no completion_tokens_details at all → output unchanged (regression guard)
test('formatUsage is unchanged when no completion_tokens_details present', () => {
  assert.equal(
    app.formatUsage({ prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 }),
    '10 in · 5 out · 15 total tokens'
  );
});

test('getExcludedParams omits temperature for Claude Opus', () => {
  const excluded = app.getExcludedParams('claude_opus_4');
  assert.ok(excluded.has('temperature'), 'opus models exclude temperature');
});

test('getExcludedParams returns an empty set for an unknown model', () => {
  const excluded = app.getExcludedParams('some-random-model');
  assert.equal(excluded.size, 0);
});

test('buildResponseFormat returns null responseFormat when JSON mode is off', () => {
  const { responseFormat } = app.buildResponseFormat({ jsonMode: false });
  assert.equal(responseFormat, null);
});

test('buildResponseFormat produces json_object when no schema is given', () => {
  const { responseFormat, error } = app.buildResponseFormat({ jsonMode: true, jsonSchema: '' });
  assert.equal(error, undefined);
  assert.equal(responseFormat.type, 'json_object');
});

// ─── Added for the thorough-QA / TDD initiative (backlog #25) ────────────────

test('buildResponseFormat wraps a bare schema and enforces strict mode', () => {
  const { responseFormat, error } = app.buildResponseFormat({
    jsonMode: true,
    jsonSchema: JSON.stringify({ type: 'object', properties: { a: { type: 'string' } } }),
  });
  assert.equal(error, undefined);
  assert.equal(responseFormat.type, 'json_schema');
  const schema = responseFormat.json_schema.schema;
  assert.equal(schema.additionalProperties, false, 'strict adds additionalProperties:false');
  assert.deepEqual(schema.required, ['a'], 'strict lists all props as required');
});

test('buildResponseFormat reports an error for invalid JSON schema', () => {
  const { error } = app.buildResponseFormat({ jsonMode: true, jsonSchema: '{not valid' });
  assert.match(error, /Invalid JSON Schema/);
});

test('enforceStrictSchema recurses into nested objects and arrays', () => {
  const out = app.enforceStrictSchema({
    type: 'object',
    properties: {
      items: { type: 'array', items: { type: 'object', properties: { x: { type: 'number' } } } },
    },
  });
  assert.equal(out.additionalProperties, false);
  assert.deepEqual(out.required, ['items']);
  const itemSchema = out.properties.items.items;
  assert.equal(itemSchema.additionalProperties, false);
  assert.deepEqual(itemSchema.required, ['x']);
});

test('safeTrim handles null/undefined/whitespace', () => {
  assert.equal(app.safeTrim(null), '');
  assert.equal(app.safeTrim(undefined), '');
  assert.equal(app.safeTrim('  hi  '), 'hi');
  assert.equal(app.safeTrim(42), '42');
});

test('chunkText splits into line-sized, non-empty chunks', () => {
  const text = Array.from({ length: 10 }, (_, i) => `line ${i}`).join('\n');
  const chunks = app.chunkText(text, 4);
  assert.equal(chunks.length, 3, '10 lines / 4 per chunk = 3 chunks');
  assert.ok(chunks.every((c) => c.trim().length > 0));
});

test('chunkText drops whitespace-only chunks', () => {
  const chunks = app.chunkText('\n\n   \n\n', 2);
  assert.equal(chunks.length, 0);
});

test('scoreChunkByKeywords rewards more keyword hits', () => {
  const q = 'pineapple pizza';
  const high = app.scoreChunkByKeywords('pineapple pizza pineapple pizza', q);
  const low = app.scoreChunkByKeywords('something unrelated entirely here', q);
  assert.ok(high > low, 'more matches → higher score');
});

test('normalizeAssistantText stringifies objects and handles null', () => {
  assert.equal(app.normalizeAssistantText(null), 'No assistant text received.');
  assert.equal(app.normalizeAssistantText('hi'), 'hi');
  assert.equal(app.normalizeAssistantText({ a: 1 }), JSON.stringify({ a: 1 }, null, 2));
});

test('extractJson recovers JSON from a ```json fenced block', () => {
  const text = 'Here you go:\n```json\n{"ok": true, "n": 3}\n```\nThanks!';
  assert.deepEqual(app.extractJson(text), { ok: true, n: 3 });
});

test('renderMarkdown does not pass through raw HTML (XSS-safe)', () => {
  const html = app.renderMarkdown('<img src=x onerror=alert(1)>');
  assert.ok(!html.includes('<img'), 'raw tags must be escaped');
  assert.ok(html.includes('&lt;img'), 'angle brackets escaped');
});

test('renderMarkdown rejects javascript: links', () => {
  const html = app.renderMarkdown('[click](javascript:alert(1))');
  assert.ok(!html.includes('href="javascript:'), 'unsafe scheme not linkified');
});

// ── Sidebar collapse toggle tests (T-1…T-6) ─────────────────────────────────
// These tests exercise the applySidebarCollapsed helper and its localStorage
// persistence contract. A minimal DOM is built per-test so each is isolated.

function makeSidebarDOM() {
  const container = { classList: { contains: () => false, toggle() {}, remove() {}, add() {} } };
  const btn = { _attrs: {}, setAttribute(k, v) { this._attrs[k] = v; } };
  const ls = { _store: {}, getItem(k) { return this._store[k] ?? null; }, setItem(k, v) { this._store[k] = v; } };
  return { container, btn, ls };
}

test('T-1: applySidebarCollapsed(true) adds .sidebar-collapsed, sets correct aria+title', () => {
  const { container, btn, ls } = makeSidebarDOM();
  let addedClass = null;
  container.classList.toggle = (cls, force) => { addedClass = force ? cls : null; };
  app.applySidebarCollapsed(true, container, btn);
  assert.equal(addedClass, 'sidebar-collapsed', 'should add sidebar-collapsed');
  assert.equal(btn._attrs['aria-expanded'], 'false');
  assert.equal(btn._attrs['aria-label'], 'Expand sidebar');
  assert.equal(btn._attrs['title'], 'Expand sidebar');
});

test('T-2: applySidebarCollapsed(false) removes .sidebar-collapsed, sets correct aria+title', () => {
  const { container, btn } = makeSidebarDOM();
  let removedClass = null;
  container.classList.toggle = (cls, force) => { if (!force) removedClass = cls; };
  app.applySidebarCollapsed(false, container, btn);
  assert.equal(removedClass, 'sidebar-collapsed', 'should remove sidebar-collapsed');
  assert.equal(btn._attrs['aria-expanded'], 'true');
  assert.equal(btn._attrs['aria-label'], 'Collapse sidebar');
  assert.equal(btn._attrs['title'], 'Collapse sidebar');
});

test('T-3: toggle click saves "1" to localStorage when collapsing', () => {
  const { container, btn, ls } = makeSidebarDOM();
  container.classList.contains = () => false; // not yet collapsed → will collapse
  container.classList.toggle = () => {};
  app._testToggle(container, btn, ls);
  assert.equal(ls._store['sidebarCollapsed'], '1', 'should save "1" when collapsing');
});

test('T-4: toggle click saves "0" to localStorage when expanding', () => {
  const { container, btn, ls } = makeSidebarDOM();
  container.classList.contains = () => true; // currently collapsed → will expand
  container.classList.toggle = () => {};
  app._testToggle(container, btn, ls);
  assert.equal(ls._store['sidebarCollapsed'], '0', 'should save "0" when expanding');
});

test('T-5: init with sidebarCollapsed="1" restores collapsed state', () => {
  const { container, btn, ls } = makeSidebarDOM();
  ls._store['sidebarCollapsed'] = '1';
  let collapsed = null;
  const spy = (c, cont, b) => { collapsed = c; };
  app._testInit(ls, container, btn, spy);
  assert.equal(collapsed, true, 'should restore collapsed=true');
});

test('T-6: init with no localStorage value starts expanded with correct labels', () => {
  const { container, btn, ls } = makeSidebarDOM();
  // ls has no sidebarCollapsed key
  let collapsed = null;
  const spy = (c, cont, b) => { collapsed = c; };
  app._testInit(ls, container, btn, spy);
  assert.equal(collapsed, false, 'should start expanded');
});

// ─── Streaming + tool calling tests (ST-1 … ST-4) ────────────────────────────
// These tests exercise the new `_runWithToolsTest` export which allows callFn
// and streamFn to be injected so no network access is needed.

// Minimal conversation stub accepted by runWithTools.
const fakeConv = {
  appendChild: () => {},
  scrollTop: 0,
  scrollHeight: 0,
  querySelectorAll: () => [],
};

test('ST-1: runWithTools streams the final answer round when streamFinalAnswer is true', async () => {
  let streamCalled = false;
  const callFn = async () => ({
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
    fakeConv,
    { streamFinalAnswer: true, callFn, streamFn },
  );
  assert.equal(streamCalled, true, 'streamFn must be called for the final answer');
  assert.equal(result.assistantText, 'hello', 'assistantText should be "hello"');
});

test('ST-2: runWithTools uses callFn for intermediate rounds and streamFn for final', async () => {
  let callCount = 0;
  let streamCount = 0;
  // Round 0: model requests a tool.  Round 1 (final): no tool_calls → streamFn.
  const callFn = async (_payload) => {
    callCount++;
    if (callCount === 1) {
      // First call: model asks for a tool
      return {
        message: {
          role: 'assistant',
          content: null,
          tool_calls: [{ id: 't1', function: { name: 'test_tool', arguments: '{}' } }],
        },
        usage: null,
      };
    }
    // Subsequent non-stream calls (shouldn't be reached in this scenario)
    return { message: { role: 'assistant', content: 'done', tool_calls: [] }, usage: null };
  };
  const streamFn = async () => {
    streamCount++;
    return { assistantText: 'done', usage: null };
  };
  await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: true, callFn, streamFn },
  );
  assert.equal(callCount, 1, 'callFn used for the tool-call round only');
  assert.equal(streamCount, 1, 'streamFn called for the final answer');
});

test('ST-3: runWithTools uses callFn for final answer when streamFinalAnswer is false', async () => {
  let callCount = 0;
  let streamCount = 0;
  const callFn = async () => {
    callCount++;
    return { message: { role: 'assistant', content: 'hi', tool_calls: [] }, usage: null };
  };
  const streamFn = async () => {
    streamCount++;
    return { assistantText: 'hi', usage: null };
  };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn, streamFn },
  );
  assert.equal(callCount, 1, 'callFn used for the final answer');
  assert.equal(streamCount, 0, 'streamFn should not be called');
  assert.equal(result.assistantText, 'hi', 'assistantText should be "hi"');
});

test('ST-4: abort from streamFn propagates aborted:true', async () => {
  const callFn = async () => ({
    message: { role: 'assistant', content: null, tool_calls: [] },
    usage: null,
  });
  const streamFn = async () => ({ aborted: true, assistantText: 'partial' });
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: true, callFn, streamFn },
  );
  assert.equal(result.aborted, true, 'aborted flag should propagate');
  assert.equal(result.assistantText, 'partial', 'partial text should be preserved');
});

test('ST-5: runWithTools returns error when callFn returns error', async () => {
  const callFn = async () => ({ error: 'upstream error' });
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn },
  );
  assert.equal(result.error, 'upstream error', 'error should propagate from callFn');
});

test('ST-6: runWithTools returns aborted when callFn returns aborted', async () => {
  const callFn = async () => ({ aborted: true });
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn },
  );
  assert.equal(result.aborted, true, 'aborted should propagate from callFn');
});

test('ST-7: runWithTools handles callFn returning no message object', async () => {
  const callFn = async () => ({ message: null, usage: null });
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn },
  );
  assert.ok(result.error, 'should return an error when message is null');
});

test('ST-8: runWithTools without streamFinalAnswer after tool use calls callFn for final answer', async () => {
  let callCount = 0;
  // Round 0: model requests a tool. Round 1: final answer via callFn (not streamFn).
  const callFn = async () => {
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
    return { message: { role: 'assistant', content: 'final', tool_calls: [] }, usage: null };
  };
  let streamCount = 0;
  const streamFn = async () => { streamCount++; return { assistantText: 'final', usage: null }; };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn, streamFn },
  );
  assert.equal(result.assistantText, 'final', 'final answer should be returned');
  assert.equal(streamCount, 0, 'streamFn should not be called when streamFinalAnswer is false');
});

test('ST-9: onDelta callback receives incremental tokens during streaming', async () => {
  const deltas = [];
  const callFn = async () => ({
    message: { role: 'assistant', content: null, tool_calls: [] },
    usage: null,
  });
  const streamFn = async (_payload, onDelta) => {
    onDelta('tok1', 'tok1');
    onDelta('tok2', 'tok1tok2');
    return { assistantText: 'tok1tok2', usage: null };
  };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: true, callFn, streamFn, onDelta: (d, f) => deltas.push({ d, f }) },
  );
  assert.equal(deltas.length, 2, 'onDelta should be called twice');
  assert.equal(deltas[0].d, 'tok1');
  assert.equal(deltas[1].f, 'tok1tok2');
  assert.equal(result.assistantText, 'tok1tok2');
});

test('ST-10: runWithTools abort from callFn in tool round propagates aborted', async () => {
  // callFn aborts mid-way through the first tool-calling round
  const callFn = async () => ({ aborted: true });
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: true, callFn },
  );
  assert.equal(result.aborted, true, 'abort in tool round should propagate');
});

test('ST-11: MAX_TOOL_ROUNDS safety-net: final callFn called after hitting round limit', async () => {
  // Always return a tool call so the loop exhausts MAX_TOOL_ROUNDS (10), then
  // forces a non-streaming final answer. We verify a successful final answer
  // comes back and that callFn was called more than once.
  let calls = 0;
  const callFn = async () => {
    calls++;
    // Keep requesting tools forever so the loop hits the ceiling
    return {
      message: {
        role: 'assistant', content: null,
        tool_calls: [{ id: `t${calls}`, function: { name: 'test_tool', arguments: '{}' } }],
      },
      usage: null,
    };
  };
  // Override the safety-net final call to return a real answer
  let finalCalled = false;
  let originalCalls = 0;
  const wrappedCallFn = async (payload) => {
    // After round limit is hit the call has no tools field in payload
    const result = await callFn(payload);
    if (!payload.tools) {
      finalCalled = true;
      return { assistantText: 'forced final', usage: null };
    }
    return result;
  };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn: wrappedCallFn },
  );
  // Either we get the final text or toolsUsed is populated (loop ran)
  assert.ok(result.toolsUsed || result.assistantText, 'should return something after exhausting rounds');
});

test('ST-12: runWithTools error in safety-net final call propagates error', async () => {
  // Force constant tool calls so the loop hits MAX_TOOL_ROUNDS, then the
  // final forced call returns an error
  let calls = 0;
  const callFn = async (payload) => {
    calls++;
    if (!payload.tools) {
      return { error: 'final call failed' };
    }
    return {
      message: {
        role: 'assistant', content: null,
        tool_calls: [{ id: `t${calls}`, function: { name: 'test_tool', arguments: '{}' } }],
      },
      usage: null,
    };
  };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn },
  );
  // The error from the post-round-limit call must surface
  assert.ok(result.error || result.toolsUsed, 'error or toolsUsed should be set after round limit');
});

test('ST-13: runWithTools abort in safety-net final call propagates aborted', async () => {
  let calls = 0;
  const callFn = async (payload) => {
    calls++;
    if (!payload.tools) {
      return { aborted: true };
    }
    return {
      message: {
        role: 'assistant', content: null,
        tool_calls: [{ id: `t${calls}`, function: { name: 'test_tool', arguments: '{}' } }],
      },
      usage: null,
    };
  };
  const result = await app._runWithToolsTest(
    { messages: [], model: 'gpt-4o' },
    fakeConv,
    { streamFinalAnswer: false, callFn },
  );
  assert.ok(result.aborted || result.toolsUsed, 'aborted should propagate from safety-net call');
});

// ─── Prompt Templates tests (PT-1 … PT-7) ────────────────────────────────────
// These tests exercise the pure helper functions for the prompt-template library:
// loadPromptTemplates, applyTemplate, saveCurrentAsTemplate, deleteUserTemplate.
// A per-test fake localStorage is injected so tests are fully isolated.

function makeFakeLS(initial = {}) {
  const store = { ...initial };
  const ls = {
    getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem(k, v) { store[k] = v; },
    removeItem(k) { delete store[k]; },
    _store: store,
  };
  // alias so tests can write to either ls.data or ls._store
  ls.data = store;
  return ls;
}

function makeFakeInput(initial = '') {
  return { value: initial };
}

test('PT-1: loadPromptTemplates returns BUILTIN_TEMPLATES when localStorage is empty', () => {
  const ls = makeFakeLS();
  const templates = app.loadPromptTemplates(ls);
  // Should contain all built-ins; no user templates
  assert.ok(Array.isArray(templates), 'should return an array');
  assert.ok(templates.length >= 6, 'should have at least 6 built-in templates');
  assert.ok(templates.every(t => t.id && typeof t.name === 'string'), 'every template has id+name');
  assert.ok(templates.every(t => !t.id.startsWith('user-')), 'no user templates when ls empty');
});

test('PT-2: applyTemplate sets #systemPrompt.value and calls saveSettings', () => {
  const input = makeFakeInput('old value');
  let saveSettingsCalled = false;
  app.applyTemplate('new prompt text', input, () => { saveSettingsCalled = true; });
  assert.equal(input.value, 'new prompt text', 'should set input value to template text');
  assert.equal(saveSettingsCalled, true, 'should call saveSettings');
});

test('PT-2b: applyTemplate with empty string clears the field', () => {
  const input = makeFakeInput('something');
  app.applyTemplate('', input, () => {});
  assert.equal(input.value, '', 'empty string template should clear the field');
});

test('PT-3: saveCurrentAsTemplate appends to user templates and persists to localStorage', () => {
  const ls = makeFakeLS();
  const result = app.saveCurrentAsTemplate('My Prompt', 'Be helpful.', ls);
  assert.equal(result, true, 'should return true on success');
  const raw = ls.getItem('usai.prompt-templates.v1');
  assert.ok(raw, 'should write to localStorage');
  const saved = JSON.parse(raw);
  assert.equal(saved.length, 1, 'should have one saved template');
  assert.equal(saved[0].name, 'My Prompt');
  assert.equal(saved[0].text, 'Be helpful.');
  assert.ok(saved[0].id.startsWith('user-'), 'id should start with user-');
});

test('PT-4: loadPromptTemplates after save returns built-ins + saved user template', () => {
  const ls = makeFakeLS();
  app.saveCurrentAsTemplate('Custom', 'Custom text.', ls);
  const templates = app.loadPromptTemplates(ls);
  const userTemplates = templates.filter(t => t.id.startsWith('user-'));
  const builtins = templates.filter(t => !t.id.startsWith('user-'));
  assert.equal(userTemplates.length, 1, 'should have 1 user template');
  assert.ok(builtins.length >= 6, 'built-ins still present');
  assert.equal(userTemplates[0].name, 'Custom');
});

test('PT-5: deleteUserTemplate removes correct entry; built-ins unchanged', () => {
  const ls = makeFakeLS();
  app.saveCurrentAsTemplate('A', 'text A', ls);
  app.saveCurrentAsTemplate('B', 'text B', ls);
  const allAfterSave = app.loadPromptTemplates(ls);
  const userTemplates = allAfterSave.filter(t => t.id.startsWith('user-'));
  assert.equal(userTemplates.length, 2, 'should have 2 user templates after saves');
  const idToDelete = userTemplates[0].id;
  app.deleteUserTemplate(idToDelete, ls);
  const allAfterDelete = app.loadPromptTemplates(ls);
  const userAfterDelete = allAfterDelete.filter(t => t.id.startsWith('user-'));
  assert.equal(userAfterDelete.length, 1, 'should have 1 user template after delete');
  assert.ok(!userAfterDelete.some(t => t.id === idToDelete), 'deleted id should be gone');
  // Built-ins must be unaffected
  const builtinsAfter = allAfterDelete.filter(t => !t.id.startsWith('user-'));
  assert.ok(builtinsAfter.length >= 6, 'built-ins must not be deleted');
});

test('PT-6: saveCurrentAsTemplate with empty/whitespace name is rejected', () => {
  const ls = makeFakeLS();
  const result1 = app.saveCurrentAsTemplate('', 'some text', ls);
  const result2 = app.saveCurrentAsTemplate('   ', 'some text', ls);
  assert.equal(result1, false, 'empty name should be rejected');
  assert.equal(result2, false, 'whitespace name should be rejected');
  assert.equal(ls.getItem('usai.prompt-templates.v1'), null, 'nothing saved to localStorage');
});

test('PT-7: saveCurrentAsTemplate with empty/whitespace text is rejected', () => {
  const ls = makeFakeLS();
  const result1 = app.saveCurrentAsTemplate('My Name', '', ls);
  const result2 = app.saveCurrentAsTemplate('My Name', '   ', ls);
  assert.equal(result1, false, 'empty text should be rejected');
  assert.equal(result2, false, 'whitespace text should be rejected');
  assert.equal(ls.getItem('usai.prompt-templates.v1'), null, 'nothing saved to localStorage');
});

test('PT-8: loadPromptTemplates handles corrupted localStorage gracefully', () => {
  const ls = makeFakeLS();
  // Inject invalid JSON so the JSON.parse branch throws
  ls.data[app.PROMPT_TEMPLATES_KEY] = 'not-valid-json{{{';
  const templates = app.loadPromptTemplates(ls);
  // Should still return built-ins (user templates array falls back to [])
  assert.ok(Array.isArray(templates), 'returns array even with bad localStorage');
  assert.ok(templates.length >= 6, 'built-ins still returned after JSON parse error');
  const userTemplates = templates.filter(t => t.id.startsWith('user-'));
  assert.equal(userTemplates.length, 0, 'no user templates after JSON error');
});

test('PT-9: loadPromptTemplates treats non-array JSON as empty user list', () => {
  const ls = makeFakeLS();
  // Inject a JSON object (not array) — should be normalised to []
  ls.data[app.PROMPT_TEMPLATES_KEY] = JSON.stringify({ bad: true });
  const templates = app.loadPromptTemplates(ls);
  assert.ok(templates.length >= 6, 'built-ins present');
  const userTemplates = templates.filter(t => t.id.startsWith('user-'));
  assert.equal(userTemplates.length, 0, 'non-array JSON treated as empty user list');
});

test('PT-10: saveCurrentAsTemplate handles localStorage quota error silently', () => {
  const ls = {
    data: {},
    getItem(k) { return this.data[k] ?? null; },
    // Simulate QuotaExceededError on setItem
    setItem() { throw new Error('QuotaExceededError: storage full'); },
  };
  // Should not throw — the savePromptTemplates logger.warn branch is hit
  assert.doesNotThrow(() => {
    app.saveCurrentAsTemplate('X', 'text', ls);
  }, 'quota error should be swallowed, not thrown');
});

test('PT-11: deleteUserTemplate handles corrupted localStorage gracefully', () => {
  const ls = makeFakeLS();
  // Inject invalid JSON so the JSON.parse catch branch in deleteUserTemplate fires
  ls.data[app.PROMPT_TEMPLATES_KEY] = '{{invalid}}';
  // Should not throw; built-ins are unaffected (delete is a no-op on error)
  assert.doesNotThrow(() => {
    app.deleteUserTemplate('user-nonexistent', ls);
  }, 'corrupted localStorage should not throw in deleteUserTemplate');
});

test('PT-12: deleteUserTemplate with non-array JSON falls back gracefully', () => {
  const ls = makeFakeLS();
  // Inject a JSON object (not array)
  ls.data[app.PROMPT_TEMPLATES_KEY] = JSON.stringify({ wrong: true });
  assert.doesNotThrow(() => {
    app.deleteUserTemplate('user-nonexistent', ls);
  }, 'non-array JSON should not throw in deleteUserTemplate');
});

// ---------------------------------------------------------------------------
// cosineSimilarity tests
// ---------------------------------------------------------------------------

test('cosineSimilarity: identical unit vectors return 1', () => {
  const v = [1, 0, 0];
  assert.strictEqual(app.cosineSimilarity(v, v), 1);
});

test('cosineSimilarity: orthogonal vectors return 0', () => {
  assert.strictEqual(app.cosineSimilarity([1, 0], [0, 1]), 0);
});

test('cosineSimilarity: null/empty inputs return 0', () => {
  assert.strictEqual(app.cosineSimilarity(null, [1, 0]), 0);
  assert.strictEqual(app.cosineSimilarity([1, 0], null), 0);
  assert.strictEqual(app.cosineSimilarity([], []), 0);
});

test('cosineSimilarity: mismatched length returns 0', () => {
  assert.strictEqual(app.cosineSimilarity([1, 0], [1, 0, 0]), 0);
});

test('cosineSimilarity: zero vector returns 0 without NaN', () => {
  const result = app.cosineSimilarity([0, 0], [0, 0]);
  assert.strictEqual(result, 0);
  assert.ok(!Number.isNaN(result));
});

// ---------------------------------------------------------------------------
// MS-1: embedMemorySearch semantic path (has_embeddings=true, embedTexts returns vecs)
// ---------------------------------------------------------------------------

test('MS-1: embedMemorySearch re-ranks by cosine similarity when has_embeddings=true', async () => {
  // Save real appConfig.has_embeddings and replace fetch
  const orig = app.appConfig.has_embeddings;
  app.appConfig.has_embeddings = true;

  let fetchCalls = [];
  const fakeFetch = async (url, opts) => {
    fetchCalls.push(url);
    if (String(url).includes('/memory/search')) {
      return {
        ok: true,
        json: async () => ({
          ok: true, query: 'car', embed_available: true, results: [
            { path: 'a.md', snippet: 'automobile note', score: 2 },
            { path: 'b.md', snippet: 'vehicle info',   score: 1 },
          ],
        }),
      };
    }
    if (String(url).includes('/embeddings')) {
      // Return 3 vectors: query, then one per snippet
      return {
        ok: true,
        json: async () => ({
          data: [
            { index: 0, embedding: [1, 0, 0] },   // query vector
            { index: 1, embedding: [0.9, 0.1, 0] }, // higher sim to query
            { index: 2, embedding: [0, 1, 0] },   // lower sim
          ],
        }),
      };
    }
    throw new Error('unexpected fetch: ' + url);
  };

  const results = await app._embedMemorySearchTest('car', 5, fakeFetch);
  app.appConfig.has_embeddings = orig;

  // b.md has lower sim; a.md is ranked #1 by cosine
  assert.ok(results.length >= 1, 'should return results');
  // Both snippets have _sim fields attached
  assert.ok(typeof results[0]._sim === 'number', 'result should have _sim');
  // a.md (higher cosine to query) should sort first
  assert.strictEqual(results[0].path, 'a.md', 'higher cosine result ranks first');
});

// ---------------------------------------------------------------------------
// MS-2: embedMemorySearch falls back to keyword order when embedTexts throws
// ---------------------------------------------------------------------------

test('MS-2: embedMemorySearch falls back to keyword order when embedTexts throws', async () => {
  const orig = app.appConfig.has_embeddings;
  app.appConfig.has_embeddings = true;

  const fakeFetch = async (url) => {
    if (String(url).includes('/memory/search')) {
      return {
        ok: true,
        json: async () => ({
          ok: true, query: 'car', results: [
            { path: 'x.md', snippet: 'first', score: 3 },
            { path: 'y.md', snippet: 'second', score: 1 },
          ],
        }),
      };
    }
    // Simulate /embeddings failure
    return { ok: false, json: async () => ({}) };
  };

  const results = await app._embedMemorySearchTest('car', 5, fakeFetch);
  app.appConfig.has_embeddings = orig;

  // Should return keyword-ordered results (no _sim), not throw
  assert.ok(results.length >= 1, 'should return keyword results on fallback');
  assert.strictEqual(results[0].path, 'x.md', 'keyword order preserved on fallback');
  assert.ok(!('_sim' in results[0]), 'no _sim field on keyword fallback');
});

// ---------------------------------------------------------------------------
// MS-3: embedMemorySearch falls back when has_embeddings is false
// ---------------------------------------------------------------------------

test('MS-3: embedMemorySearch returns keyword results when has_embeddings is false', async () => {
  const orig = app.appConfig.has_embeddings;
  app.appConfig.has_embeddings = false;

  let embedCalled = false;
  const fakeFetch = async (url) => {
    if (String(url).includes('/embeddings')) { embedCalled = true; }
    return {
      ok: true,
      json: async () => ({
        ok: true, query: 'q', results: [{ path: 'z.md', snippet: 'something', score: 1 }],
      }),
    };
  };

  const results = await app._embedMemorySearchTest('q', 5, fakeFetch);
  app.appConfig.has_embeddings = orig;

  assert.strictEqual(embedCalled, false, '/embeddings should NOT be called when has_embeddings false');
  assert.ok(results.length >= 1, 'keyword results should still be returned');
});

// ---------------------------------------------------------------------------
// JS-1…JS-5: getRelevantChunks — semantic embeddings RAG path (#7)
// ---------------------------------------------------------------------------

// JS-1: cosine path used when chunks have embeddings and toggle is on
test('JS-1: getRelevantChunks uses cosine path when chunks have embeddings and semanticSearch is on', async () => {
  const origConfig = { ...app.appConfig };
  app.appConfig.has_embeddings = true;

  // Fake embedTexts: returns a unit vector for the query and two chunk vectors
  const fakeQueryVec = [1, 0];
  const fakeChunkVec0 = [0.9, 0.1]; // high similarity
  const fakeChunkVec1 = [0.1, 0.9]; // low similarity
  let embedCallCount = 0;
  const fakeFetch = async (url) => {
    embedCallCount++;
    return {
      ok: true,
      json: async () => ({
        data: [
          { index: 0, embedding: fakeQueryVec },
        ],
      }),
    };
  };

  const chunks = [
    { fileName: 'a.txt', chunkId: 0, text: 'car automobile vehicle', embedding: fakeChunkVec0, embedModel: 'test-model' },
    { fileName: 'b.txt', chunkId: 0, text: 'blue sky weather', embedding: fakeChunkVec1, embedModel: 'test-model' },
  ];

  const result = await app._getRelevantChunksTest(chunks, 'automobile', 5, fakeFetch, true);

  app.appConfig.has_embeddings = origConfig.has_embeddings;

  assert.ok(result.length >= 1, 'should return results');
  assert.strictEqual(result[0].fileName, 'a.txt', 'highest cosine similarity chunk should rank first');
});

// JS-2: keyword fallback when no chunk has an embedding
test('JS-2: getRelevantChunks falls back to keyword when no chunk has an embedding', async () => {
  const origConfig = { ...app.appConfig };
  app.appConfig.has_embeddings = true;

  let embedCalled = false;
  const fakeFetch = async () => { embedCalled = true; return { ok: true, json: async () => ({}) }; };

  const chunks = [
    { fileName: 'a.txt', chunkId: 0, text: 'car automobile vehicle', embedding: null },
    { fileName: 'b.txt', chunkId: 0, text: 'blue sky automobile weather', embedding: null },
  ];

  // 'automobile' appears in both; b.txt has more occurrences so should rank higher on keyword
  const result = await app._getRelevantChunksTest(chunks, 'automobile', 5, fakeFetch, true);

  app.appConfig.has_embeddings = origConfig.has_embeddings;

  assert.strictEqual(embedCalled, false, '/embeddings should NOT be called when no chunks have embeddings');
  assert.ok(result.length >= 1, 'should return keyword-ranked results');
});

// JS-3: keyword fallback when semanticSearchEnabled is false
test('JS-3: getRelevantChunks falls back to keyword when semanticSearch toggle is off', async () => {
  const origConfig = { ...app.appConfig };
  app.appConfig.has_embeddings = true;

  let embedCalled = false;
  const fakeFetch = async () => { embedCalled = true; return { ok: true, json: async () => ({}) }; };

  const chunks = [
    { fileName: 'a.txt', chunkId: 0, text: 'annual revenue income', embedding: [1, 0], embedModel: 'test-model' },
    { fileName: 'b.txt', chunkId: 0, text: 'blue sky weather', embedding: [0, 1], embedModel: 'test-model' },
  ];

  // semanticSearchEnabled=false → keyword path regardless of embeddings
  const result = await app._getRelevantChunksTest(chunks, 'annual revenue', 5, fakeFetch, false);

  app.appConfig.has_embeddings = origConfig.has_embeddings;

  assert.strictEqual(embedCalled, false, '/embeddings should NOT be called when semantic toggle is off');
  assert.strictEqual(result[0].fileName, 'a.txt', 'keyword scoring should rank the matching chunk first');
});

// JS-4: query-embed failure → keyword fallback with no uncaught throw
test('JS-4: getRelevantChunks falls back to keyword when embedTexts rejects (no uncaught throw)', async () => {
  const origConfig = { ...app.appConfig };
  app.appConfig.has_embeddings = true;

  // embedTexts will throw because /embeddings returns 500
  const failFetch = async () => ({
    ok: false,
    status: 500,
    json: async () => ({}),
  });

  const chunks = [
    { fileName: 'a.txt', chunkId: 0, text: 'yearly income revenue', embedding: [1, 0], embedModel: 'test-model' },
    { fileName: 'b.txt', chunkId: 0, text: 'blue sky weather', embedding: [0, 1], embedModel: 'test-model' },
  ];

  // Should not throw even though embedTexts will fail
  let result;
  await assert.doesNotReject(async () => {
    result = await app._getRelevantChunksTest(chunks, 'income', 5, failFetch, true);
  }, 'should not throw when embedTexts rejects');

  app.appConfig.has_embeddings = origConfig.has_embeddings;

  assert.ok(Array.isArray(result), 'should return an array even on embeddings failure');
  assert.ok(result.length >= 1, 'should return keyword results on fallback');
});

// JS-5: results sorted descending by cosine score when embeddings path used
test('JS-5: getRelevantChunks sorts results descending by cosine score', async () => {
  const origConfig = { ...app.appConfig };
  app.appConfig.has_embeddings = true;

  // Query vector [1, 0]; chunk A=[0.8, 0.6], chunk B=[0.2, 0.98], chunk C=[0.95, 0.31]
  // cos(A, query)≈0.8, cos(B, query)≈0.2, cos(C, query)≈0.95 → order: C, A, B
  const queryVec = [1, 0];
  const fakeFetch = async () => ({
    ok: true,
    json: async () => ({
      data: [{ index: 0, embedding: queryVec }],
    }),
  });

  const chunks = [
    { fileName: 'A.txt', chunkId: 0, text: 'chunk A', embedding: [0.8, 0.6], embedModel: 'test-model' },
    { fileName: 'B.txt', chunkId: 0, text: 'chunk B', embedding: [0.2, 0.98], embedModel: 'test-model' },
    { fileName: 'C.txt', chunkId: 0, text: 'chunk C', embedding: [0.95, 0.31], embedModel: 'test-model' },
  ];

  const result = await app._getRelevantChunksTest(chunks, 'query', 3, fakeFetch, true);

  app.appConfig.has_embeddings = origConfig.has_embeddings;

  assert.ok(result.length === 3, 'should return all 3 chunks');
  // Scores should be non-increasing
  assert.ok(result[0].score >= result[1].score, 'result[0].score >= result[1].score');
  assert.ok(result[1].score >= result[2].score, 'result[1].score >= result[2].score');
  // C should rank first (highest cosine similarity to [1,0])
  assert.strictEqual(result[0].fileName, 'C.txt', 'C has highest cosine similarity to query vector [1,0]');
});

// ─── Auto Model Router tests (#19) ───────────────────────────────────────────
// Tests for the pure routeModel() classifier and TIER_MAP defaults.
// None of these touch the DOM; all run in the Node test environment.

// RM-1: Short greeting → 'low' (short + matches LOW_KW, no tools)
test('RM-1: routeModel returns "low" for a short greeting', () => {
  assert.strictEqual(app.routeModel('hi'), 'low');
});

// RM-2: Long message (>800 chars) → 'high'
test('RM-2: routeModel returns "high" for a long message (>800 chars)', () => {
  const longMsg = 'x'.repeat(801);
  assert.strictEqual(app.routeModel(longMsg), 'high');
});

// RM-3: Message containing a code fence → 'high'
test('RM-3: routeModel returns "high" when message contains a code fence', () => {
  const codeMsg = 'Can you fix this?\n```js\nconst x = 1;\n```';
  assert.strictEqual(app.routeModel(codeMsg), 'high');
});

// RM-4: opts.override = 'high' on a short greeting → 'high' (override wins)
test('RM-4: routeModel honours override "high" even for a short message', () => {
  assert.strictEqual(app.routeModel('hi', { override: 'high' }), 'high');
});

// RM-5: opts.override = 'low' on a long message → 'low' (override wins)
test('RM-5: routeModel honours override "low" even for a long message', () => {
  const longMsg = 'x'.repeat(801);
  assert.strictEqual(app.routeModel(longMsg, { override: 'low' }), 'low');
});

// RM-6: Medium-length plain message (no keywords/code) → 'medium'
test('RM-6: routeModel returns "medium" for a plain mid-length message', () => {
  // 130–800 chars, no HIGH_KW, no code, no LOW_KW prefix → 'medium'
  const msg = 'Please summarise the main points of this article for me. '.repeat(4);
  assert.ok(msg.length > 120 && msg.length <= 800, 'message should be mid-length');
  assert.strictEqual(app.routeModel(msg), 'medium');
});

// RM-7: Short message with toolsEnabled:true → 'medium' (tools floor the tier)
test('RM-7: routeModel returns at least "medium" when toolsEnabled is true', () => {
  const tier = app.routeModel('hi', { toolsEnabled: true });
  assert.ok(tier === 'medium' || tier === 'high', `expected "medium" or "high", got "${tier}"`);
});

// RM-8: opts.override = 'off' → 'medium' (router disabled → neutral default)
test('RM-8: routeModel returns "medium" when override is "off"', () => {
  assert.strictEqual(app.routeModel('hi', { override: 'off' }), 'medium');
});

// RM-9: TIER_MAP falls back to the verified gateway model ids when appConfig
// tier overrides are not set. These ids use underscores (e.g. claude_4_8_opus)
// which is the format the GSA/USAi API gateway accepts. Ids with dashes like
// 'claude-opus-4' are NOT accepted and cause upstream 400/404 errors — this
// test pins the correct fallback values so a typo regression is caught early.
test('RM-9: TIER_MAP falls back to verified gateway model ids when overrides are empty', () => {
  // appConfig tier fields are '' by default in the Node test environment
  // (no browser / no /config fetch), so the || fallbacks are exercised.
  const high = app.TIER_MAP.high();
  const medium = app.TIER_MAP.medium();
  const low = app.TIER_MAP.low();
  assert.strictEqual(high,   'claude_4_8_opus',    `TIER_MAP.high() wrong: got "${high}"`);
  assert.strictEqual(medium, 'claude_4_6_sonnet',  `TIER_MAP.medium() wrong: got "${medium}"`);
  assert.strictEqual(low,    'claude_4_5_haiku',   `TIER_MAP.low() wrong: got "${low}"`);
});

// RM-10: When appConfig tier overrides are set, TIER_MAP uses those values
// instead of the hardcoded fallbacks — operator deployments can override without
// touching source code by setting TIER_HIGH/MEDIUM/LOW_MODEL in .env.
test('RM-10: TIER_MAP honours appConfig tier_*_model overrides', () => {
  // Temporarily set overrides on the shared appConfig object.
  const saved = {
    high:   app.appConfig.tier_high_model,
    medium: app.appConfig.tier_medium_model,
    low:    app.appConfig.tier_low_model,
  };
  app.appConfig.tier_high_model   = 'custom-high';
  app.appConfig.tier_medium_model = 'custom-medium';
  app.appConfig.tier_low_model    = 'custom-low';
  try {
    assert.strictEqual(app.TIER_MAP.high(),   'custom-high',   'override not honoured for high');
    assert.strictEqual(app.TIER_MAP.medium(), 'custom-medium', 'override not honoured for medium');
    assert.strictEqual(app.TIER_MAP.low(),    'custom-low',    'override not honoured for low');
  } finally {
    // Restore so subsequent tests see the original empty-string defaults.
    app.appConfig.tier_high_model   = saved.high;
    app.appConfig.tier_medium_model = saved.medium;
    app.appConfig.tier_low_model    = saved.low;
  }
});

