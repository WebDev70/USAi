// Starter unit tests for pure helper functions in ../../app.js
//
// Run from the project root with:  node --test tests/js
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
