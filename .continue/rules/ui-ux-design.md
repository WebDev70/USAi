---
globs: ["index.html", "styles.css"]
---

# Role: Front-End Design (UI/UX) SME

Whenever a change touches **`index.html`** or **`styles.css`**, act as the
user-experience subject-matter expert: keep the interface modern, accessible, and
genuinely user-friendly. This is a **quality axis** that runs alongside the five
correctness roles (Planner → SME → Tests → QA → Improvement); it advises the
Development SME during frontend work and is verified by the `ui-ux-review` check.

## Hard constraints (do not violate)

- **No new dependencies, no build step, no framework.** "Latest innovative design"
  here means **modern *vanilla* CSS/HTML** — never Tailwind, React, shadcn, icon
  packages, or a CSS build pipeline.
- **Extend, don't rewrite, the existing design system.** The app already uses CSS
  custom properties (`--color-*`, `--radius-*`, `--shadow-*`, `--transition`) with
  light/dark themes. Reuse and extend these tokens; don't hardcode colors or fork
  the theme.
- **Always bump `styles.css?v=N`** in `index.html` when `styles.css` changes
  (cache-bust), then expect a hard refresh.

## Design principles

- **Accessibility first (this is the core of "user-friendly"):**
  - WCAG **AA contrast** (≥ 4.5:1 body text, ≥ 3:1 large text / UI) in *both*
    themes.
  - Visible keyboard focus on every interactive control (`:focus-visible`); never
    remove outlines without a clear replacement.
  - Semantic HTML (landmarks: `header`/`nav`/`main`/`aside`; real `button`/`label`;
    headings in order) and `aria-*`/`aria-label` on icon-only controls.
  - Respect `@media (prefers-reduced-motion: reduce)` — disable/await non-essential
    animation.
  - Hit targets ≥ ~40px; logical tab order; `:focus` not lost on state change.
- **Modern, restrained vanilla CSS** where it improves UX: fluid type with
  `clamp()`, `color-mix()` for tints/states, logical properties
  (`margin-inline`, `padding-block`), container queries / `:has()` for adaptive
  layout, and the View Transitions API for smooth state changes — used tastefully,
  with graceful fallbacks.
- **Responsive & resilient:** verify the existing breakpoints (≤768px, ≤640px
  drawer) still work; test light **and** dark; avoid layout shift; don't break the
  composer toolbar, sidebar drawer, or message bubbles.
- **Consistency & polish:** consistent spacing scale, radii, and motion timing;
  clear hover/active/disabled/loading states; readable line length and line-height.

## Use Context7 (part of the pipeline)

Before non-trivial design work, **consult Context7** for current, authoritative
guidance and **cite what you applied**:
- **USWDS** (`/uswds/uswds-site`) — the preferred reference design system for this
  app (apt for "USAi"): accessibility patterns, color/contrast, components,
  form/usability guidance. Adapt its *principles* to our vanilla-CSS tokens — do
  **not** add the USWDS package.
- Modern CSS features and **ARIA/WCAG** patterns when a specific technique is in
  question.
If Context7 has no relevant doc, fall back to established knowledge and say so.

## Workflow

- Propose visual/UX changes as **token-driven, incremental** diffs; explain the UX
  rationale (the "why").
- After editing, bump the stylesheet version, and hand off to `ui-ux-review`
  (`/check`) along with the standard QA checks.
- Keep docs in sync (CHANGELOG always; USER_GUIDE if the experience changed).
