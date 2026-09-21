# Spec: UX & UI SME Quality Axis

**Status:** Done
**Type:** docs
**Created:** 2026-07-15
**Author:** Cline / user
**Prior context:** Existing "Front-End Design (UI/UX)" quality axis found in `docs/rail-pipeline.md §3`, `.continue/rules/ui-ux-design.md`, `.continue/checks/ui-ux-review.md`, and `.clinerules/workflows/sme-frontend.md`. Self-improvement Entry 002 (UI control placement / doc-HTML drift) directly motivates the UX sub-discipline.

---

## 1. Goal & scope

### Goal
Elevate the existing "Front-End Design (UI/UX)" quality axis into an explicit **two-discipline UX & UI SME** with clearly separated responsibilities. Today's axis is heavily weighted toward UI (tokens, accessibility, CSS conventions) and thin on UX (user-need framing, user-flow mapping, information architecture, friction audits). This change adds a formal UX sub-discipline alongside the existing UI material so that every frontend change is evaluated on *both* how it works and how it looks.

This is a **process/documentation change only** — no app code (`server.py`, `app.js`, `index.html`, `styles.css`) is modified. All changes are confined to the Cline harness workflows, the shared RAIL pipeline doc, and the Continue harness rule/check files.

### Out of scope
- Any modification to `server.py`, `app.js`, `index.html`, or `styles.css`.
- Promoting the axis to a new numbered sequential RAIL role (it remains a quality axis advising Roles 2–3).
- Adding new automated tooling (linters, accessibility scanners) — the gate stays documentation-driven and manual-review-oriented.
- Redesigning or refactoring the USAi Chat UI itself.

---

## 2. User story & acceptance criteria

As a **Cline RAIL developer** working on a frontend change, I want a clear UX & UI SME with distinct UX and UI sub-disciplines so that I evaluate *how the feature works for the user* (UX) as well as *how it looks and is coded* (UI) — and don't ship a control that is visually correct but conceptually misplaced.

- [ ] **AC-1:** `.clinerules/workflows/sme-frontend.md` contains a distinct **UX sub-discipline** section (including user-need framing, user-flow/journey mapping, information architecture & placement, and a friction audit gate) alongside a clearly labeled **UI sub-discipline** section with the existing UI content.
- [ ] **AC-2:** `docs/rail-pipeline.md` §3 defines the "Quality axis — Front-End Design" as **UX & UI SME** with explicit UX (how it works) and UI (how it looks) breakdown.
- [ ] **AC-3:** `.continue/rules/ui-ux-design.md` reflects the UX/UI split with at least the UX sub-discipline principles present.
- [ ] **AC-4:** `.continue/checks/ui-ux-review.md` includes at least one new UX-oriented failing criterion (e.g., a new multi-step interaction with no described user journey/flow, or a control added in the wrong information-architecture section with no stated user goal).
- [ ] **AC-5:** All existing hard constraints (no framework, vanilla CSS/JS only, CSS `?v=N` bump, extend-don't-replace tokens, WCAG AA) remain intact and present in all edited files.
- [ ] **AC-6:** `backlog.md` shows this item as `[~]` In Progress with a spec link, and `CHANGELOG.md` has an `[Unreleased]` entry.

---

## 3. Affected files

| File | Change |
|------|--------|
| `.clinerules/workflows/sme-frontend.md` | Add UX sub-discipline charter, UX pre-implementation checklist, and UX gate items; relabel existing content as UI sub-discipline. |
| `docs/rail-pipeline.md` | Rewrite §3 "Quality axis — Front-End Design (UI/UX)" as "UX & UI SME" with two-discipline breakdown. |
| `.continue/rules/ui-ux-design.md` | Mirror UX/UI split: add UX sub-discipline principles block alongside existing UI content. |
| `.continue/checks/ui-ux-review.md` | Add UX-oriented failing criteria alongside existing UI/accessibility criteria. |
| `docs/tooling/cline.md` | Minor: update the sme-frontend.md reference in the workflow table if needed (or note it is unaffected). |
| `CHANGELOG.md` | Add `[Unreleased]` entry. |
| `backlog.md` | Add item #59, set `[~]` In Progress + spec link. |
| `Cline/scrum/product-backlog.md` | Mirror: move item to In-Progress table. |
| `docs/specs/ux-ui-sme-role.md` | This spec file. |

---

## 4. Technical approach

### Role 2 — Architect sign-off

This is a pure documentation/process change. The implementation amounts to structured text additions and reorganizations across four harness files.

**File-by-file approach:**

**`.clinerules/workflows/sme-frontend.md`** (primary change):
- Rename "Front-End SME charter" → split into two sub-sections:
  - **UX sub-discipline charter** (new): user-need framing, user-flow & journey mapping, wireframe-level thinking before styling, information architecture & placement-in-context (directly from Entry 002 prevention rule), friction/task-completion audit.
  - **UI sub-discipline charter** (existing content, relabeled): vanilla CSS, token system, WCAG AA, USWDS/Context7, motion guard, CSS cache-bust.
- Expand "Pre-implementation checklist" into two sub-checklists: UX pre-impl + UI pre-impl (existing items move to UI).
- Expand "Mandatory front-end gates" table with new UX rows: user-need stated, flow described (if multi-step), control placement cross-checked vs docs.

**`docs/rail-pipeline.md`** §3 "Quality axis — Front-End Design (UI/UX)":
- Rename block header to "Quality axis — UX & UI SME".
- Add the two-discipline definition immediately after the header.
- Keep the constraint list (vanilla CSS, no framework) under UI sub-discipline.
- Add UX principles (user-need framing, flow mapping, IA) as a new bullet block.

**`.continue/rules/ui-ux-design.md`**:
- Split into two labeled sub-discipline blocks (UX + UI) to match Cline parity.
- UX block: user-need framing, flow/journey mapping, IA & placement, friction audit.
- UI block: existing content, unchanged.

**`.continue/checks/ui-ux-review.md`**:
- Add a new "UX quality" failing-criteria block:
  - Multi-step interaction added with no described user journey or flow.
  - A new control placed in a settings/UI section that doesn't match its conceptual function (wrong IA placement, no cross-check against docs).
  - User goal absent: interactive element added with no stated user need or task it enables.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A) — N/A (docs only)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A) — N/A
- [x] `/config` exposes no secrets (or N/A) — N/A
- [x] Path traversal rejected on filesystem access (or N/A) — N/A
- [x] CSS bump applied (or N/A) — N/A (no `styles.css` change)

---

## 4b. Shift-left governance findings (Step 2b output)

> Filled by Cline during `/spec`. Advisory — does not block Status: Ready.

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All ACs are binary and observable (file contents verifiable by `read_file` or `grep`). |
| G-2 Scope / value | ✅ Pass | No scope creep identified; every change maps to the stated goal of formalizing the two-discipline UX/UI axis. |
| G-3 Dependency coherence | ✅ Pass | No prerequisite backlog items; builds only on the already-present UX/UI axis material. |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

> **Type: docs/process spec.** No new testable code is introduced. The test plan is
> documentation-consistency verification, not automated unit/integration tests.

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | `sme-frontend.md` contains both "UX sub-discipline" and "UI sub-discipline" section headers. | `.clinerules/workflows/sme-frontend.md` | manual / grep |
| T-2 | `docs/rail-pipeline.md` contains "UX & UI SME" quality-axis heading. | `docs/rail-pipeline.md` | manual / grep |
| T-3 | `.continue/rules/ui-ux-design.md` contains UX sub-discipline block. | `.continue/rules/ui-ux-design.md` | manual / grep |
| T-4 | `.continue/checks/ui-ux-review.md` contains at least one UX-oriented failing criterion. | `.continue/checks/ui-ux-review.md` | manual / grep |
| T-5 | All hard constraints (no framework, vanilla CSS/JS, `?v=N` bump, WCAG AA) still present across all edited files. | all edited files | manual review |
| T-6 | `CHANGELOG.md` has `[Unreleased]` entry referencing this change. | `CHANGELOG.md` | manual / grep |
| T-7 | `backlog.md` item #59 has `[~]` status + spec link. | `backlog.md` | manual / grep |

**TDD order:** Because this is docs-only, test verification is done post-implementation via grep/review rather than Red→Green TDD. Automated test gates (`./run-tests.sh --coverage`) are expected to remain green (no code touched).

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — not required (no user-facing app change)
- [ ] `README.md` — not required (no setup/config change)
- [ ] `backlog.md` — add item #59, mark `[~]` In Progress
- [ ] `AGENTS.md` / `CONTINUE.md` — not required (conventions unchanged; the UX/UI axis already references the same conventions)

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Harness parity drift: Cline and Continue files diverge in their UX discipline definitions. | Implement both harnesses in the same turn; include cross-harness T-3/T-4 in the verification step. |
| Scope creep: author starts improving the actual UI/CSS while editing these docs. | Spec §1 "Out of scope" explicitly excludes app-code changes; any observed improvement should be noted as a new backlog item. |
| Entry 002 prevention rule not encoded in the UX gates. | Explicitly include "control placement cross-checked against docs" as a UX gate item in both `sme-frontend.md` and `ui-ux-review.md`. |
| Existing AI check (`cn review`) parses `.continue/checks/ui-ux-review.md` and new UX criteria trigger false positives on backend-only changes. | The check's first line already scopes it to `index.html`/`styles.css` changes only — preserve this scope guard. |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-6 all verified
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

> *Optional — populated only when a spec amendment is made during `/build`
> (see build.md §3d). Leave empty if no amendments were needed.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
