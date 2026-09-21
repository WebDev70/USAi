// TR-1..TR-6 — truncationNote() regression tests
//
// A "cut off mid-thought" reply happens when the upstream model stops because it
// hit its output-token ceiling (OpenAI-compatible `finish_reason: "length"`).
// The client never truncates the assistant text itself — `truncationNote` is a
// pure predicate that decides whether to *surface* a visible warning note on the
// turn. These tests lock its contract: only "length" produces a note; every
// other finish_reason (including null/undefined) produces the empty string, so
// normal turns are unchanged and nothing is ever stripped from the reply.
//
// Zero-dependency: Node's built-in test runner + assert, per project philosophy.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

// app.js touches document/window at module scope; install the same tiny no-op
// stubs used by the other suites so the module loads under Node without a DOM.
const noop = () => {};
const fakeEl = {
  addEventListener: noop, removeEventListener: noop,
  appendChild: noop, setAttribute: noop, removeAttribute: noop,
  classList: { add: noop, remove: noop, toggle: noop },
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
globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({}), text: async () => '' });

const require = createRequire(import.meta.url);
const app = require('../../../frontend/app.js');

test('TR-1: finish_reason "length" produces a visible truncation note', () => {
  const note = app.truncationNote('length');
  assert.ok(note, 'a non-empty note is returned for "length"');
  assert.match(note, /truncat/i, 'note explains the response was truncated');
  assert.match(note, /Max tokens/i, 'note points the user at the Max tokens control');
});

test('TR-2: finish_reason "stop" (normal completion) produces no note', () => {
  assert.equal(app.truncationNote('stop'), '');
});

test('TR-3: finish_reason "tool_calls" produces no note', () => {
  assert.equal(app.truncationNote('tool_calls'), '');
});

test('TR-4: null / undefined finish_reason produces no note', () => {
  assert.equal(app.truncationNote(null), '');
  assert.equal(app.truncationNote(undefined), '');
});

test('TR-5: unknown finish_reason produces no note', () => {
  assert.equal(app.truncationNote('content_filter'), '');
});

test('TR-6: purity — repeated calls are stable and side-effect free', () => {
  assert.equal(app.truncationNote('length'), app.truncationNote('length'));
  assert.equal(app.truncationNote('stop'), app.truncationNote('stop'));
});
