---
name: UI/UX Design Review
description: Frontend changes stay accessible, responsive, token-driven, dependency-free, and UX-sound
---

Review this change for **UX & UI quality and accessibility**, but only when it
touches `index.html` or `styles.css` (see `docs/rail-pipeline.md`). If the
change doesn't touch the frontend, pass.

Flag as **failing** if any of the following are true:

---

## UX quality failures

- **User goal absent:** an interactive element or new control was added with no
  stated user need — the spec, comment, or PR description cannot answer *"which user
  task does this enable?"*
- **Flow undescribed for multi-step interactions:** a new dialog, settings sequence,
  or multi-step workflow was added with no sentence-level user flow (e.g. "user
  clicks X → Y appears → user confirms → Z"). The flow does not need to be a
  wireframe, but it must exist somewhere (spec §4, code comment, or PR description).
- **Wrong IA placement:** a new control was placed in a settings or UI section that
  does not match its conceptual function (e.g. a file-retrieval toggle placed in
  MCP & Plugins, or an appearance option buried in a data section) — and no
  cross-check was made against `docs/USER_GUIDE.md` section headings.

---

## UI quality failures

- **New dependency / build step / framework** was introduced for the frontend
  (Tailwind, React, shadcn, icon packages, a CSS bundler, etc.). The frontend must
  stay plain HTML + vanilla CSS.
- **CSS cache not busted:** `styles.css` changed but `styles.css?v=N` in
  `index.html` was not bumped.
- **Hardcoded design values** that bypass the token system: raw hex colors,
  ad-hoc radii/shadows, or magic spacing where a `--color-*` / `--radius-*` /
  `--shadow-*` custom property exists (or should). Colors must work in **both**
  light and dark themes.
- **Accessibility regressions:**
  - An interactive control without a visible keyboard focus state (outline removed
    with no `:focus-visible` replacement).
  - An icon-only button/control without an accessible name (`aria-label` / visible
    label).
  - Non-semantic markup where semantic exists (e.g. a clickable `<div>` instead of
    `<button>`), or heading order broken.
  - Plausibly insufficient contrast (body text < ~4.5:1, large/UI < ~3:1) in either
    theme.
  - New non-essential animation that doesn't respect
    `@media (prefers-reduced-motion: reduce)`.
- **Responsiveness broken:** the change is likely to break the ≤768px / ≤640px
  layouts, the collapsible sidebar drawer, the composer toolbar, or cause obvious
  layout shift.

---

When non-trivial design choices were made, the change should reference the guidance
it followed (e.g. **USWDS** via Context7, or a specific ARIA/WCAG pattern). Note its
absence as a soft warning, not an automatic failure.

If none of the above issues are present, pass the check.
