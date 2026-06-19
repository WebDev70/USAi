---
name: Security Review
description: No secrets leak, /config stays redacted, and all filesystem access rejects path traversal
---

Review this change for **security issues** specific to USAi Chat.

Flag as **failing** if any of these are true:

- **Secrets leak.** Hardcoded API keys/tokens/passwords in any committed file
  (source, config, `.continue/**`), or a secret value added to `.env.example`/docs.
  (Real secrets belong only in the git-ignored `.env`.)
- **`/config` exposes secrets.** `_get_config` in `server.py` returns anything
  beyond non-secret fields + `has_*` boolean flags (it must never return `api_key`
  or `context7_api_key`), or `app.js` stores/sends a secret it shouldn't.
- **Path traversal.** Any filesystem endpoint (`/memory/*`, `/sessions`,
  `/chunk-cache`) builds a path from user input without confining it to the
  intended folder and rejecting `..` / absolute-path escapes. (See
  `get_memory_dir`'s `relative_to` guard as the reference pattern.)
- **Missing input limits.** A new endpoint reads a request body without a size
  limit, or trusts client-supplied filenames without sanitizing them
  (cf. `_slugify`).
- **Unsafe HTML.** New rendering of model/user content injects raw HTML instead of
  escaping first (cf. `renderMarkdown`, which escapes then whitelists) — i.e. an
  XSS risk.
- **Binding/exposure.** The server is changed to bind beyond `127.0.0.1`, or a new
  proxy path forwards the API key to the browser.

If none of these are present, pass the check.
