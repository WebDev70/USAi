---
name: Code Quality Review
description: Change follows USAi Chat conventions — no new deps, correct patterns, CSS cache-bust, why-comments
---

Review this change against USAi Chat's **coding conventions** (`AGENTS.md`,
`.continue/rules/development-sme.md`, `CONTINUE.md`).

Flag as **failing** if any of these are true:

- **New runtime dependency introduced.** Frontend must stay plain HTML/CSS/JS (no
  framework, no build step); backend must use the Python standard library +
  `python-dotenv` only. (Dev-only test tooling that ships no runtime dep is fine,
  but adding pytest/jest/vitest/etc. is not.)
- **Tool not gated.** A new entry in `TOOL_REGISTRY` (`app.js`) is not gated in
  `getEnabledTools()` on its config + toggle.
- **Endpoint pattern violated.** A new server route is not implemented as a
  `_handler` on `EnvConfigHTTPRequestHandler` and registered in the `routes` dict
  of `do_GET`/`do_POST`/`do_DELETE`.
- **CSS cache not busted.** `styles.css` changed but `styles.css?v=N` in
  `index.html` was not bumped.
- **Hidden global state / untestable code.** New non-trivial logic is buried in a
  way that can't be unit-tested (prefer small, pure, module-level functions; expose
  JS helpers via the Node-only `module.exports` guard).
- **Comments explain only _what_, not _why_,** or the change's style clashes badly
  with the surrounding descriptive style.
- **Settings not persisted.** A new user-facing toggle/setting isn't saved to /
  restored from `localStorage` (`usai.settings.v1`) when that would be expected.

If the change follows the conventions, pass the check.
