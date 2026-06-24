---
name: Dependency & Supply-Chain Review
description: Runtime surface stays minimal/audited; deps pinned; dev-only tooling never leaks into runtime
---

Review this change for **supply-chain / dependency hygiene** (DevSecOps), per
`docs/principles.md` §1–2 and `AGENTS.md`.

The governing principle is **minimal, audited *runtime* surface** — dev/CI tooling
that ships nothing into the running app is allowed and encouraged.

Flag as **failing** if any of these are true:

- **New runtime dependency.** `requirements.txt` gained anything beyond
  `python-dotenv`, OR `app.js`/`index.html`/`styles.css` started depending on a
  framework, CDN script, icon pack, or build tool. (The litmus test: is it
  *imported by / shipped with* the running app? If yes, it's runtime and is
  forbidden by default.)
- **Dev tooling leaked into runtime.** A dev/CI-only tool (`coverage`, `bandit`,
  `pip-audit`, `gitleaks`, Docker, etc.) was added to `requirements.txt`, imported
  by `server.py`/`app.js`, or otherwise made a thing the app needs to *run*.
- **Unpinned/loosened dependency.** A change widened a version constraint or
  removed pinning in a way that reduces reproducibility, without justification.
- **Vendored/minified blob.** A pre-built or minified third-party file was added to
  the repo (an opaque blob defeats auditability).
- **Bypassing the scanners.** The change disables/neuters `scripts/security-scan.sh`,
  the CI `security` job, or removes a scanner without an explicit, reviewed reason.

Soft warning (not an automatic fail): a new `.env` variable or external service was
introduced without a note about its trust/security implications.

If the runtime surface is unchanged (or only dev/CI tooling was added) and deps stay
pinned and auditable, pass the check.
