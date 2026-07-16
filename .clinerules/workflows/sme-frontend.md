# Workflow: SME — Front-End Developer (UX & UI)
# Cline RAIL — Front-End Specialist Rules

> **Concern: Cline dev harness** — this file is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Invoked by:** `build.md` Role 3 when the spec touches `index.html`, `styles.css`,
or `app.js` (UI/DOM/CSS work). This file is a **domain-specific expansion of Role 3**
— it does not replace the sequencing in `build.md`.

**Canonical reference:** [`docs/rail-pipeline.md` §3 — UX & UI SME quality axis](../../docs/rail-pipeline.md)

---

## UX & UI SME charter

This SME has **two distinct sub-disciplines** that must both be satisfied before a
front-end change is considered done:

### UX sub-discipline (how it works — user experience)
Ensure the feature solves a real user problem and fits the user's mental model:
- **State the user need.** Every new control or interaction must answer: *"Which
  user goal does this enable?"* If no clear goal exists, the feature should not ship.
- **Map the user flow** before writing any code for multi-step interactions (e.g. a
  new dialog, a settings sequence, a multi-panel workflow). A brief description
  ("user clicks X → Y appears → user confirms → Z happens") is sufficient — it does
  not need to be a formal wireframe.
- **Information architecture & placement.** New controls must be placed in the
  settings/UI section that matches their conceptual function:
  - File-retrieval controls → File Uploads section.
  - External integrations → MCP & Plugins section.
  - Appearance / display → System / Appearance section.
  - **Cross-check placement against `docs/USER_GUIDE.md`** — the guide's section
    headings are the IA source of truth. A control placed in the wrong section with
    no documented rationale is a UX defect (see Self-Improvement Entry 002).
- **Friction audit.** For any interaction that requires more than one step, ask:
  *"Is every step necessary? Is the sequence intuitive?"* Remove steps or provide
  defaults where possible.
- **Task completion.** Can a user accomplish the feature's stated goal without
  confusion or dead ends? If in doubt, describe the happy path before implementing.

### UI sub-discipline (how it looks — user interface)
Deliver **modern, accessible, dependency-free** front-end changes that:
- Use **vanilla CSS** and **vanilla JS only** — no framework, no build step, no new
  runtime dependency.
- Respect and extend the **existing CSS-custom-property token system** (light + dark
  themes) — never rewrite the token layer.
- Meet **WCAG AA accessibility** as a baseline, not an afterthought.
- **Bump the CSS cache-bust version** (`styles.css?v=N`) in `index.html` on every
  CSS change.
- Consult **Context7 USWDS** (`/uswds/uswds-site`) for authoritative design/accessibility
  guidance; adapt principles to our vanilla CSS — do not add the package.

---

## Pre-implementation checklist (before writing any front-end code)

Read the spec §3 (Affected files) and §4 (Technical approach). For each front-end
file in scope, verify:

### UX pre-implementation
- [ ] **User need stated.** The spec or a comment answers: *"Which user goal does
      this feature enable?"*
- [ ] **User flow described** (for multi-step interactions). A sentence-level flow
      ("click X → Y appears → user confirms → Z") is written in the spec §4 or as a
      code comment before implementation begins.
- [ ] **IA placement verified.** The intended section in `index.html` matches the
      conceptual category of the feature. Confirmed against `docs/USER_GUIDE.md`
      section headings.
- [ ] **Friction minimized.** Any multi-step interaction has been reviewed for
      unnecessary steps; defaults are provided where reasonable.

### UI pre-implementation
- [ ] **No new runtime dependencies.** If you need an icon, use a Unicode glyph or
      inline SVG. If you need a component, build it with vanilla HTML/CSS/JS.
- [ ] **Token extension, not token replacement.** Identify which existing CSS custom
      properties (`--color-*`, `--space-*`, `--font-*`, etc.) apply. Add new tokens
      only if genuinely needed for the feature — define them at `:root`/`[data-theme]`.
- [ ] **Accessibility is in scope.** Every new interactive element needs:
      - A visible label (text content, `aria-label`, or `aria-labelledby`).
      - A `:focus-visible` ring (use the `--focus-ring` token).
      - Adequate contrast in **both** light and dark themes (WCAG AA = 4.5:1 normal, 3:1 large).
      - `aria-hidden="true"` on decorative glyphs/icons.
      - `aria-expanded` / `aria-controls` on disclosure widgets (toggles, dropdowns).
- [ ] **Motion guard.** Any CSS animation or transition must be wrapped in:
      ```css
      @media (prefers-reduced-motion: no-preference) { … }
      ```
- [ ] **CSS cache-bust identified.** Note the current `?v=N` in `index.html`; the
      new value will be `N+1`.

---

## TDD — Red → Green → Refactor (front-end specifics)

### RED — write failing tests first (JS logic)

Front-end tests live in `frontend/tests/js/app.test.mjs` and test **pure helper functions**
exported via the `module.exports` guard at the bottom of `app.js`. They use
`node:test` + `node:assert` — no browser, no jsdom.

- Identify which new/changed helpers from spec §5 need unit tests.
- Write the tests; confirm they fail before writing production code.
- **DOM wiring is NOT unit-tested** (no jsdom dependency). It is verified by
  `node --check frontend/app.js` (syntax) + manual/browser testing.

**CSS-only changes:** no unit tests required. The gate is `node --check frontend/app.js`
(syntax guard on any JS touched) + visual verification in the browser + the
cache-bust bump.

### GREEN — minimum code to pass

Implement only what spec §4 describes. Front-end conventions to respect:

**CSS:**
- Define new values using existing tokens first (`var(--space-4)`, `var(--color-surface)`).
- Use `color-mix(in oklch, …)` for state tints (hover, active) — avoid hardcoded
  hex color variations.
- Use `clamp()` for fluid type/spacing where the spec calls for responsive behavior.
- Prefer logical properties (`inline-size`, `padding-inline`) over physical ones
  for new layout code.
- Container queries (`:has()`, `@container`) for self-contained components where appropriate.
- Selector specificity: keep it low; avoid `!important`; prefer class over element selectors.

**HTML:**
- Semantic elements first (`<nav>`, `<main>`, `<section>`, `<article>`, `<details>`,
  `<dialog>`) before `<div>`.
- `<button>` for actions, `<a>` for navigation.
- `<label>` explicitly associated with every form input (`for`/`id` or wrapping).
- `role` and `aria-*` only when HTML semantics are insufficient.

**JS:**
- New helpers must be **pure functions** (no side effects, deterministic).
- Add new helpers to the `module.exports` guard at the bottom of `app.js` so they
  are importable by tests.
- Event listeners: use `addEventListener` — no inline `onclick` attributes.
- Avoid `innerHTML` for user-supplied content; use `textContent` or a safe DOM
  builder. If `innerHTML` is unavoidable, HTML-escape the content first.

### REFACTOR — clean up under green

- Remove duplicate CSS rules.
- Ensure new tokens are defined at the right scope (`:root` for global, `[data-theme=dark]`
  for dark overrides).
- Verify no new hardcoded color hex values outside the token layer.
- Re-run `node --check frontend/app.js` and `node --test frontend/tests/js/` to confirm green.

---

## Mandatory front-end gates (before handing back to build.md)

### UX gates

| Gate | Check |
|------|-------|
| **User need stated** | A user goal is named for every new control or interaction. |
| **Flow described** | Any multi-step interaction has a sentence-level flow in spec §4 or a code comment. |
| **IA placement** | New control's section in `index.html` matches conceptual function; cross-checked against `docs/USER_GUIDE.md` headings. |
| **Friction minimal** | Multi-step interactions reviewed; unnecessary steps removed or defaulted. |

### UI gates

| Gate | Check |
|------|-------|
| **CSS cache bust** | `index.html` has `styles.css?v=N+1` where N was the prior value. |
| **No new runtime deps** | No `<script src="…cdn…">` added. No new `import` in `app.js`. |
| **WCAG AA contrast** | Spot-checked in both light and dark themes for any new/changed text or UI. |
| **`:focus-visible`** | All new interactive elements have a visible focus indicator. |
| **`aria-hidden` on glyphs** | Decorative icons have `aria-hidden="true"`. |
| **`prefers-reduced-motion`** | Any new animation/transition wrapped in the media query. |
| **Pure helpers exported** | New testable helpers added to `module.exports` guard in `app.js`. |
| **Tests passing** | `node --test frontend/tests/js/` green; `node --check frontend/app.js` clean. |
| **No `innerHTML` with unescaped input** | All `innerHTML` assignments use HTML-escaped or safe content. |

---

## Context7 reference guide (use for design/accessibility questions)

- **USWDS** (`/uswds/uswds-site`) — U.S. Web Design System: the preferred authority
  for accessibility patterns, token systems, and component behavior.
- Query for: contrast ratios, focus indicators, ARIA patterns, button vs. link
  semantics, form labeling, landmark roles.
- **Adapt USWDS principles to our vanilla CSS** — do not copy USWDS classes or add
  the USWDS package.

---

## Scope discipline

The Front-End SME implements **exactly what the spec describes**. If you notice:
- A CSS improvement outside the spec → note it as a future backlog item.
- An accessibility gap unrelated to the current change → note it as a future backlog
  item (tag: accessibility).
- A missing WCAG requirement **within the changed component** → fix it now (in scope
  for the current change, as it directly affects what you're touching).
- A UX concern (wrong placement, missing user goal, friction) **outside the current
  change** → note it as a future backlog item (tag: ux).

Do not refactor the entire stylesheet or rewrite unrelated components.

---

## References

- [`docs/rail-pipeline.md` §3 — UX & UI SME quality axis](../../docs/rail-pipeline.md)
- `build.md` — master orchestrator (sequences this file within Role 3)
- `review.md` — QA verifier (re-runs the "Mandatory front-end gates" tables above at §6e-FE, independently of `/build`)
- `sme-backend.md` — back-end specialist (used for the same spec when it touches server.py)
- `docs/principles.md` §1 — minimal runtime surface (why no framework)
