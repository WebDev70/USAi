---
name: Dependency & Supply-Chain Review
description: Runtime surface stays minimal/audited; deps pinned; dev-only tooling never leaks into runtime
---

Review this change for **supply-chain / dependency hygiene** (DevSecOps), per
`docs/principles.md` §1–2 and `AGENTS.md`.

The governing principle is **minimal, audited *runtime* surface** — dev/CI tooling
that ships nothing into the running app is allowed and encouraged.

The **approved runtime allow-list** for `requirements.txt` (see
`docs/principles.md` §1) is exactly:

| Package | Status |
|---------|--------|
| `python-dotenv` | approved — `.env` loading |
| `pypdf` | approved — PDF text extraction (stdlib cannot parse the PDF format) |
| `typing_extensions` | approved — transitive dep of `pypdf`, required because `--require-hashes` mode demands every installed package be pinned + hashed |

Every entry must carry both a `==` version pin and at least one `--hash=sha256:`.

Flag as **failing** if any of these are true:

- **New runtime dependency.** `requirements.txt` gained anything beyond the
  approved allow-list above, OR `app.js`/`index.html`/`styles.css` started
  depending on a framework, CDN script, icon pack, or build tool. (The litmus
  test: is it *imported by / shipped with* the running app? If yes, it's runtime
  and is forbidden by default.)
- **Missing hash pin.** A `requirements.txt` entry lacks a `--hash=sha256:` line,
  or a version bump left a stale hash behind. Any unhashed line silently breaks
  `--require-hashes` for the whole file.
- **A library was reached for where the stdlib suffices.** For example, adding
  `python-docx`/`lxml` back for DOCX parsing: `backend/file_parser.py`
  deliberately reads `.docx` with stdlib `zipfile` + `xml.etree`, because a .docx
  is just a ZIP of XML and `lxml` is a large, platform-specific wheel that makes
  reproducible hash pinning impractical.
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
