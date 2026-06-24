# Spec: Architecture & Engineering Document

**Status:** Ready
**Created:** 2026-06-23
**Author:** Cline / user
**Prior context:** Prior sessions covered three-concern org map (#30 doc-split done 2026-06-23) and engineering principles. No prior spec for a dedicated architecture document found.

---

## 1. Goal & scope

### Goal
Create `docs/ARCHITECTURE.md` — a concise, overview-level architecture and engineering
reference for the USAi Chat **application** (concern #1 only). It gives any developer
or agent a single place to understand how the system is built: component responsibilities,
request flow, data persistence, security architecture, and the tool/streaming model.
A companion deep-detail note is written to the Obsidian vault for richer reference
without bloating the repo doc.

### Out of scope
- The Continue or Cline dev harnesses (those are covered by `docs/ORGANIZATION.md` and
  `docs/tooling/`).
- Per-feature design decisions (those live in `docs/specs/`).
- Engineering process / RAIL pipeline (that lives in `docs/rail-pipeline.md`).
- End-user how-to content (that lives in `docs/USER_GUIDE.md`).

---

## 2. User story & acceptance criteria

As a developer (or agent) onboarding to USAi Chat, I want a single architecture
reference so that I can understand the system's design without reading every source file.

- [x] AC-1: `docs/ARCHITECTURE.md` exists, renders cleanly in GitHub Markdown, and
  is ≤ ~500 lines (concise overview).
- [x] AC-2: The doc includes a Mermaid request-flow diagram showing browser →
  `server.py` → upstream API.
- [x] AC-3: The doc covers: system overview, component map, backend routing pattern,
  frontend tool/streaming model, data persistence, and security architecture.
- [x] AC-4: `docs/ORGANIZATION.md` file table and "Where to put new things" table
  updated to reference `docs/ARCHITECTURE.md`.
- [x] AC-5: `CHANGELOG.md` updated under `[Unreleased]`.
- [x] AC-6: A deep architecture note written to
  `Cline/memories/YYYY-MM-DD-HHMMSS-architecture-deep-dive.md` in the Obsidian vault.

---

## 3. Affected files

| File | Change |
|------|--------|
| `docs/ARCHITECTURE.md` | **New** — concise overview architecture doc |
| `docs/ORGANIZATION.md` | Add `ARCHITECTURE.md` row to file table; add "Where to put it" entry |
| `CHANGELOG.md` | Add entry under `[Unreleased]` |
| `docs/specs/architecture-doc.md` | This file (new spec) |
| Obsidian `Cline/memories/` | New deep-dive note |

---

## 4. Technical approach

### Role 2 — Architect sign-off
This is a documentation chore — no runtime code changes.

**Conventions applied:**
- [x] No new runtime dependency added — documentation only
- [ ] New endpoint follows `_handler` + `routes` pattern (N/A)
- [ ] New tool follows `TOOL_REGISTRY` + gate pattern (N/A)
- [x] `/config` exposes no secrets (N/A — no code change)
- [ ] Path traversal rejected on filesystem access (N/A)
- [ ] CSS bump applied (N/A — no CSS change)

---

## 5. Test plan (Role 4 — Tester)

No automated tests required for a documentation-only change.
Manual verification: confirm `docs/ARCHITECTURE.md` renders in GitHub/VS Code,
Mermaid diagrams parse, and all internal links resolve.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — not user-facing; N/A
- [ ] `README.md` — optionally add a link to ARCHITECTURE.md in the docs section
- [x] `docs/ORGANIZATION.md` — add ARCHITECTURE.md to file table
- [ ] `backlog.md` — no backlog item (this is a chore initiated by user request)

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Doc goes stale as codebase evolves | Sec 4 of ARCHITECTURE.md links directly to source files; RAIL pipeline `docs-in-sync` check covers it |
| Mermaid not rendered in all viewers | Add a text fallback description next to each diagram |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-6 all verified
- [ ] Memory note written to `Cline/memories/`
