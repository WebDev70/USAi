// #95 — Max tokens clarify-the-cap regression tests (MT-1..MT-5)
//
// Guards the payload-assembly behavior contract that the #95 UX-copy change must
// NOT regress: leaving Max tokens blank omits the parameter; a positive value is
// sent as-is; and models that exclude `max_tokens` never receive it. The decision
// predicate is exported from app.js as `shouldSendMaxTokens` so these tests
// exercise the real code path used inside sendMessage(), not a copy.
//
// Zero-dependency: Node's built-in test runner + assert, per project philosophy.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

// app.js touches document/window at module scope; install the same tiny no-op
// stubs used by app.test.mjs so the module loads under Node without a DOM.
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

const EMPTY = new Set();

test('MT-1: blank (NaN) Max tokens omits the parameter', () => {
  // parseInt('', 10) === NaN — the exact value getChatInputs() produces for a blank field.
  assert.equal(app.shouldSendMaxTokens(EMPTY, Number.parseInt('', 10)), false);
  assert.equal(app.shouldSendMaxTokens(EMPTY, NaN), false);
});

test('MT-2: zero (and negative) Max tokens omits the parameter', () => {
  assert.equal(app.shouldSendMaxTokens(EMPTY, 0), false, '0 must omit');
  assert.equal(app.shouldSendMaxTokens(EMPTY, -5), false, 'negative must omit');
});

test('MT-3: a positive Max tokens is sent when the model allows it', () => {
  assert.equal(app.shouldSendMaxTokens(EMPTY, 4096), true);
  assert.equal(app.shouldSendMaxTokens(EMPTY, 1), true, 'minimum positive included');
});

test('MT-4: excluded model never receives max_tokens even with a positive value', () => {
  const excluded = new Set(['max_tokens']);
  assert.equal(app.shouldSendMaxTokens(excluded, 4096), false);
});

test('MT-5: exclusion source (getExcludedParams) is untouched — still returns a Set', () => {
  const s = app.getExcludedParams('gpt-5');
  assert.ok(s instanceof Set, 'getExcludedParams must return a Set');
  // gpt-5 excludes temperature (existing behavior); max_tokens is NOT excluded by
  // name here — the omission for reasoning models is handled elsewhere and is not
  // part of this predicate's contract.
  assert.equal(s.has('temperature'), true, 'existing gpt-5 temperature exclusion preserved');
});
