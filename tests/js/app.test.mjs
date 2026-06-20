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
