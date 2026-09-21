/**
 * index-html-structure.test.mjs — structural guards for the real frontend/index.html.
 *
 * Why this file exists (regression guard):
 *   A malformed `</div>` in index.html once left the Project Settings modal
 *   (`#projectSettingsModal`) NESTED *inside* the Create Project modal
 *   (`#createProjectModal`). Because the parent overlay carried `hidden` +
 *   `display:none`, the child settings overlay collapsed to a 0×0 box even after
 *   `_showProjectSettingsModal` removed its own `hidden` attribute — the gear
 *   button "did nothing" from the user's point of view. The unit/behavior tests
 *   never caught it because they boot from a hand-written MINIMAL_HTML skeleton,
 *   not the shipped index.html. This suite parses the *real* index.html with jsdom
 *   and asserts the structural invariants that keep the modals independently
 *   toggleable.
 *
 * Zero new deps: jsdom is already a dev dependency (see app.behavior.test.mjs).
 * Run: node --test frontend/tests/js/index-html-structure.test.mjs
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { JSDOM } from 'jsdom';

const here = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(here, '..', '..');
const INDEX_HTML = readFileSync(path.resolve(frontendRoot, 'index.html'), 'utf8');

function docFromIndex() {
  return new JSDOM(INDEX_HTML).window.document;
}

// Overlay containers that must each be a standalone, independently-toggleable
// dialog. If any two of these become ancestor/descendant of one another, the
// inner one inherits the outer's hidden/display state and silently breaks.
const MODAL_OVERLAY_IDS = ['createProjectModal', 'projectSettingsModal'];

describe('index.html — modal overlay structure', () => {
  test('both modal overlays exist and start hidden', () => {
    const doc = docFromIndex();
    for (const id of MODAL_OVERLAY_IDS) {
      const el = doc.getElementById(id);
      assert.ok(el, `#${id} must exist in index.html`);
      assert.ok(
        el.classList.contains('modal-overlay'),
        `#${id} must carry the .modal-overlay class`,
      );
      assert.equal(
        el.hasAttribute('hidden'), true,
        `#${id} must start with the hidden attribute`,
      );
    }
  });

  test('no modal overlay is nested inside another modal overlay', () => {
    // This is the exact invariant the stray </div> violated.
    const doc = docFromIndex();
    for (const outerId of MODAL_OVERLAY_IDS) {
      const outer = doc.getElementById(outerId);
      for (const innerId of MODAL_OVERLAY_IDS) {
        if (innerId === outerId) continue;
        const inner = doc.getElementById(innerId);
        assert.equal(
          outer.contains(inner), false,
          `#${innerId} must NOT be nested inside #${outerId} — a nested overlay ` +
          `inherits the parent's hidden/display state and cannot be shown on its own`,
        );
      }
    }
  });

  test('every modal overlay is a direct child of the app container', () => {
    // Keeping overlays as siblings under .app-container guarantees each one
    // toggles solely on its own hidden attribute.
    const doc = docFromIndex();
    for (const id of MODAL_OVERLAY_IDS) {
      const el = doc.getElementById(id);
      const parent = el.parentElement;
      assert.ok(parent, `#${id} must have a parent element`);
      assert.ok(
        parent.classList.contains('app-container'),
        `#${id} must be a direct child of .app-container (found parent ` +
        `<${parent.tagName.toLowerCase()} id="${parent.id}" class="${parent.className}">)`,
      );
    }
  });

  test('#projectSettingsModal exposes the elements _showProjectSettingsModal queries', () => {
    // Guards against a future edit that moves the settings form out of its
    // overlay (which would make querySelector inside the handler return null).
    const doc = docFromIndex();
    const modal = doc.getElementById('projectSettingsModal');
    const requiredIds = [
      'settingsProjectName',
      'settingsProjectMemoryMode',
      'settingsProjectInstructions',
      'projectSettingsSaveBtn',
      'projectSettingsCancelBtn',
      'settingsProjectFileUploadInput',
      'settingsProjectFilesList',
    ];
    for (const id of requiredIds) {
      assert.ok(
        modal.querySelector(`#${id}`),
        `#${id} must live inside #projectSettingsModal`,
      );
    }
  });
});
