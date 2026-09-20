# Spec: Dedicated Project Settings Modal (#82)

**Status:** Done
**Created:** 2026-09-20
**Author:** Cline

## 1. Goal & scope

This item fixes two loose ends from the Project Detail View sprint (#81):
1.  **Refactor the fragile settings modal:** `_showProjectSettingsModal` currently re-uses the create-project modal at runtime, which is fragile. This will be replaced with a dedicated `#projectSettingsModal`.
2.  **Add a delete action:** The project detail view currently has no "Delete project" action. This will be added.

**Out of scope:**
*   Changing the existing project creation flow.
*   Refactoring the `_showProjectRenameModal` function, which also re-uses the create-project modal. This will be left as-is per user direction.

## 2. User story & acceptance criteria

As a user, I want to manage a project's settings and be able to delete a project directly from the detail view, using a clear and dedicated interface.

- [x] **AC-1: Dedicated Settings Modal:** `index.html` contains a new, dedicated `#projectSettingsModal`. The `_showProjectSettingsModal` function in `app.js` is refactored to use this new modal and no longer mutates the create-project modal's title, button text, or submit handler.
- [x] **AC-2: Save and Re-render:** Saving the settings modal sends a `PUT` request to `/projects/<id>` with the updated project details. The project detail view then re-renders to show the new name and instructions without a page reload.
- [x] **AC-3: Delete from Detail View:** The project detail view has a visible "Delete project" button. Clicking this button prompts for confirmation.
- [x] **AC-4: Safe Delete Confirmation:** Confirming the deletion sends a `DELETE` request to `/projects/<id>` and then navigates the user to the empty chat state (not a blank canvas). Cancelling the confirmation leaves the project intact.
- [x] **AC-5: CSS Cache Bust:** Any edits to `styles.css` are accompanied by an incremented version number in `index.html` (e.g., `?v=33`).
- [x] **AC-6: Behavior Tests:** New jsdom behavior tests are added to `frontend/tests/js/app.behavior.test.mjs` to cover the open→edit→save and open→delete→confirm flows. The full test suite passes with `./run-tests.sh --coverage`.

## 3. Affected files

- `frontend/index.html`: Add `#projectSettingsModal` and a delete button to the detail view. Bump CSS version.
- `frontend/app.js`: Refactor `_showProjectSettingsModal`, add delete handler, and wire up the new modal.
- `frontend/styles.css`: Add styles for the new modal and delete button.
- `frontend/tests/js/app.behavior.test.mjs`: Add new behavior tests for the settings and delete flows.
- `CHANGELOG.md`: Record the changes.
- `docs/USER_GUIDE.md`: Update documentation for the new user-facing features.
- `docs/specs/project-detail-view.md`: Mark PD-6 and PD-7 as complete.
- `backlog.md`: Mark item #82 as done.
- `Cline/scrum/product-backlog.md`: Update scrum board.

## 4. Technical approach

1.  **HTML:** In `index.html`, duplicate the structure of `#createProjectModal` to create `#projectSettingsModal`. Add a new "Delete Project" button in the `#projectDetailView` action area. Increment the stylesheet version from `?v=32` to `?v=33`.
2.  **CSS:** In `styles.css`, add a `.modal-btn--danger` style for the delete button.
3.  **JavaScript:**
    - In `app.js`, create a new `_showProjectSettingsModal` function that populates and shows the new modal. The save handler will call `updateProject` and then `showProjectDetail` to refresh the view.
    - Wire up the new Delete button in the detail view to a handler that uses `confirm()`, then calls `deleteProject`, clears `currentProjectId`, and calls `_showChatView()` to return to the empty state.
    - The settings modal will have its own internal Save, Cancel, and Delete handlers, wired up within `_showProjectSettingsModal`.
4.  **Tests:** In `app.behavior.test.mjs`, expand the `MINIMAL_HTML` skeleton to include the new modal and button. Add tests that simulate user interaction: opening the modal, changing values, clicking save, and verifying the `PUT` request and subsequent UI update. Add another test for the delete flow, mocking `confirm` to test both cancel and confirm paths.

## 5. Test plan

| Test ID | File | Description |
|---|---|---|
| PD-JS-7 | app.behavior.test.mjs | Open settings modal, change name, save. Assert `PUT` is called and detail view updates. |
| PD-JS-8 | app.behavior.test.mjs | Click delete button, confirm. Assert `DELETE` is called and view switches to empty chat. |
| PD-JS-9 | app.behavior.test.mjs | Click delete button, cancel. Assert no `DELETE` call is made and UI is unchanged. |

## 6. Docs to update

- [x] `CHANGELOG.md`
- [x] `docs/USER_GUIDE.md`
- [x] `docs/specs/project-detail-view.md`
- [x] `backlog.md`
- [x] `Cline/scrum/product-backlog.md`

## 7. Risks / edge cases

-   The new settings modal must be wired up entirely in `app.js` to avoid a second inline `<script>` block in `index.html`.
-   The jsdom test skeleton must be updated with the new element IDs for the tests to work correctly.

## 8. Review checklist

- [x] Implementation matches spec sections 3–5
- [x] `./run-tests.sh --coverage` passes
- [x] `./scripts/security-scan.sh` clean (2/4 scanners in this env; gitleaks/pip-audit ran clean, memory-note scan skipped — `OBSIDIAN_VAULT_PATH` unset)
- [x] Docs updated (section 6)
- [x] Memory note written
