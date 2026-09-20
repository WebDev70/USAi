// project-context-isolation.test.mjs — regression tests for backlog #94.
//
// Spec: docs/specs/project-context-isolation.md  (AC-1 .. AC-5)
//
// The BLOCKING leak: a chat inside project P retrieved a document belonging to a
// DIFFERENT project because getRelevantChunks() merged [...fileChunks,
// ...projectChunks] with no projectId scoping, and the project-switch entry
// points never cleared stale per-chat state. These tests reconstruct the exact
// observed scenario and assert the leak is closed.
//
// Zero-dependency: Node's built-in test runner + assert, same load strategy as
// app.test.mjs (require() the CommonJS-guarded module.exports block).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

// Minimal DOM/global stubs so app.js can be required under Node (mirrors
// app.test.mjs). Only the globals touched at module load / by the helpers under
// test are stubbed.
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
};
globalThis.localStorage = {
  _s: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; },
};
globalThis.performance = globalThis.performance || { now: () => 0 };

const require = createRequire(import.meta.url);
const app = require('../../../frontend/app.js');

// Chunks belonging to the CURRENTLY OPEN project (2f6d37 in the incident).
const OPEN_PROJECT = 'project_open_2f6d37';
const openProjectChunks = [
  { fileName: 'FSSOnline as is state.txt', chunkId: 0, text: 'FSSOnline current state details differ overview', embedding: null, projectId: OPEN_PROJECT },
  { fileName: 'FAS Cloud Services Overview.txt', chunkId: 0, text: 'FAS cloud services overview differ documents', embedding: null, projectId: OPEN_PROJECT },
];
// A chunk from a DIFFERENT project (30a89f) that leaked in the incident.
const FOREIGN_PROJECT = 'project_foreign_30a89f';
const foreignChunk = { fileName: 'eOffer Data Dictionary.xlsx', chunkId: 0, text: 'eOffer data dictionary SOLICITATIONS ADDL_INFO differ documents', embedding: null, projectId: FOREIGN_PROJECT };

// ── AC-1 / AC-4: retrieval must drop chunks whose projectId != active ─────────
test('PCI-1: getRelevantChunks excludes chunks from a different project (leak closed)', async () => {
  const chunks = [...openProjectChunks, foreignChunk];
  // activeProjectId is passed via the new scoped test hook.
  const result = await app._getRelevantChunksScopedTest(chunks, 'how do the documents differ', 5, OPEN_PROJECT);
  const names = result.map(c => c.fileName);
  assert.ok(!names.includes('eOffer Data Dictionary.xlsx'),
    'foreign-project chunk must NOT appear in retrieval for the open project');
  assert.ok(names.length >= 1, 'own-project chunks should still be retrievable');
});

// ── AC-4: a chunk with no projectId (genuine per-chat upload) is allowed ──────
test('PCI-2: unscoped per-chat chunks (no projectId) are retained', async () => {
  const perChat = { fileName: 'scratch.txt', chunkId: 0, text: 'per chat upload differ documents note', embedding: null };
  const chunks = [...openProjectChunks, perChat, foreignChunk];
  const result = await app._getRelevantChunksScopedTest(chunks, 'documents differ', 5, OPEN_PROJECT);
  const names = result.map(c => c.fileName);
  assert.ok(names.includes('scratch.txt'), 'per-chat chunk (no projectId) must be retained');
  assert.ok(!names.includes('eOffer Data Dictionary.xlsx'), 'foreign chunk still excluded');
});

// ── AC-2: isolation is keyed on projectId, immune to duplicate display names ──
test('PCI-3: two same-named projects with different ids do not cross-contaminate', async () => {
  // Both projects are named "EmbeddingNegTest"; only ids differ.
  const chunks = [...openProjectChunks, foreignChunk];
  const result = await app._getRelevantChunksScopedTest(chunks, 'differ', 5, OPEN_PROJECT);
  assert.ok(result.every(c => c.projectId === OPEN_PROJECT || c.projectId == null),
    'only active-project or unscoped chunks may survive, regardless of name');
});

// ── AC-3: resetChatContextState clears every per-chat + project array ─────────
test('PCI-4: resetChatContextState empties fileChunks, uploadedFiles, projectChunks', () => {
  app.fileChunks.push({ fileName: 'x.txt', chunkId: 0, text: 'x' });
  app.uploadedFiles.push('x.txt');
  app.projectChunks.push({ ...foreignChunk });
  app._resetChatContextState();
  assert.strictEqual(app.fileChunks.length, 0, 'fileChunks cleared');
  assert.strictEqual(app.uploadedFiles.length, 0, 'uploadedFiles cleared');
  assert.strictEqual(app.projectChunks.length, 0, 'projectChunks cleared');
});

// ── AC-5: full incident reconstruction ───────────────────────────────────────
test('PCI-5: incident reconstruction — eOffer never leaks into the 2f6d37 differ-chat', async () => {
  // 1. User was in the foreign project with eOffer as a per-chat upload.
  app._resetChatContextState();
  app.fileChunks.push({ ...foreignChunk, projectId: undefined }); // per-chat upload had no projectId
  app.uploadedFiles.push('eOffer Data Dictionary.xlsx');
  // 2. User switches to the open project — switch MUST clear stale per-chat state.
  app._resetChatContextState();
  // 3. Open project's shared chunks load (tagged with the open projectId).
  for (const c of openProjectChunks) app.projectChunks.push({ ...c });
  // 4. Ask "how do the documents differ" scoped to the open project.
  const result = await app._getRelevantChunksScopedTest(
    [...app.fileChunks, ...app.projectChunks], 'how do the documents in this project differ', 5, OPEN_PROJECT);
  const names = result.map(c => c.fileName);
  assert.ok(!names.includes('eOffer Data Dictionary.xlsx'),
    'REGRESSION: eOffer must never appear in the open project chat');
});

