# Spec: Document SME — Workflow, Build Dispatch & Review Gate

**Status:** Done
**Created:** 2026-06-26
**Author:** Cline
**Type:** docs

## 1. Goal & scope

Add a dedicated **Document Steward SME** workflow to the Cline RAIL harness.
The Document SME is the authoritative owner of all project documentation and the
Obsidian Cline second-brain vault, enforcing three quality pillars on every change:
**completeness**, **accuracy**, and **truthfulness**.

Today, documentation quality is enforced only implicitly through the "Docs in sync"
non-negotiable in `rail-pipeline.md` and partial checks in `doc-consistency-check.sh`.
No single owner exists for docs, and the Obsidian memory vault has no formal gate.
This spec closes that gap — a first-class SME workflow with its own checklist,
mandatory gates table, and matching review section.

**In scope:**
- Create `.clinerules/workflows/sme-docs.md` (new file, Document SME workflow)
- Wire the Document SME into the `/build` SME dispatch table (`build.md`)
- Add a `§6e-DOCS` QA re-verification gate to `/review` (`review.md`)
- Update `CHANGELOG.md`

**Out of scope:**
- Phase 2 (5th Governance role SDKS) — deferred
- Changes to `server.py`, `app.js`, `index.html`, `styles.css` (no app code)
- New unit tests (docs-type change — Tester gate + security scan skipped per `build.md` Type table)
- Continue harness files (`.continue/`) — Cline harness only

---

## 2. User story & acceptance criteria

*As a Cline dev-harness operator, I want a dedicated Document SME that is automatically
dispatched by `/build` and re-verified by `/review` whenever a change touches documentation
or memory, so that every shipped change leaves docs complete, accurate, and truthful —
and the Obsidian second brain is a reliable knowledge source.*

- [ ] **AC-1** — `.clinerules/workflows/sme-docs.md` exists and follows the same structure
  as `sme-frontend.md` / `sme-backend.md` (header block → charter → pre-checklist →
  process → mandatory gates → scope discipline → references).
- [ ] **AC-2** — `build.md` SME dispatch table has a row for "docs / specs / memory"
  pointing to `sme-docs.md`, replacing the current "Neither (docs / chore)" generalist
  row for doc changes.
- [ ] **AC-3** — `review.md` has a `§6e-DOCS` gate section sourced from `sme-docs.md`,
  parallel to the existing `§6e-FE` and `§6e-BE` gate sections.
- [ ] **AC-4** — `./scripts/doc-consistency-check.sh` exits 0 after all changes.
- [ ] **AC-5** — `./scripts/spec-check.sh docs/specs/document-sme.md` exits 0 after
  all changes (all §3 files present, no unexpected additions).

---

## 3. Affected files

- `.clinerules/workflows/sme-docs.md` — **CREATE** (Document SME workflow)
- `.clinerules/workflows/build.md` — **EDIT** (SME dispatch table + §3d pointer)
- `.clinerules/workflows/review.md` — **EDIT** (add §6e-DOCS gate section)
- `CHANGELOG.md` — **EDIT** (log the addition)

---

## 4. Technical approach

### 4a. `sme-docs.md` — structure (mirrors sme-backend.md exactly)

```
# Workflow: SME — Document Steward
# Cline RAIL — Documentation Specialist Rules

> Concern callout + invoked-by line + canonical reference

---
## Document Steward charter
## Pre-implementation checklist
## Process — Completeness → Accuracy → Truthfulness
## Mandatory documentation gates (table)
## Memory / Obsidian conventions
## Scope discipline
## References
```

**Charter:** Deliver documentation and Obsidian memory that is complete, accurate,
and truthful. Three pillars:
1. **Completeness** — every substantive change reflected in the right doc
   (CHANGELOG always; USER_GUIDE if user-facing; README if setup/config; backlog
   item ticked; spec §6 boxes ticked; session memory note written).
2. **Accuracy** — docs match real code/behavior (endpoint catalog, config flags,
   paths, CLI commands, CSS `?v=N` bump all current; no stale claims).
3. **Truthfulness** — nothing aspirational or invented; every documented feature
   actually exists and was verified; "out of scope" sections honored.

**Three-concern discipline:** writes memory only to `Cline/` subfolders
(`Cline/memories/`, `Cline/scrum/`), never `USAi/memories/` or
`Continue Extension/memories/`.

**Mandatory gates table** keys:
- `doc-consistency-check.sh` exits 0
- `spec-check.sh <spec-path>` exits 0 (for spec-driven changes)
- CHANGELOG updated under `[Unreleased]`
- Memory note written for the session
- No API keys / `sk-` values / secrets in any doc or memory note
- Three-concern boundary respected (no writes to other harness memory)

### 4b. `build.md` SME dispatch table edit

Replace the current last row:

> `| Neither (docs / chore / css-only) | Use the generalist path inline (no specialist file needed) |`

With two rows:

> `| Docs / specs / memory (`.md` files, `docs/`, `CHANGELOG`, `backlog`, Obsidian vault) | **[`sme-docs.md`]** — completeness/accuracy/truthfulness pillars, doc gates |`
> `| Chore / refactor (code only, no doc content changes) | Use the generalist path inline (no specialist file needed) |`

Also add a one-line pointer in §3d (Docs in sync): "For doc-heavy changes, the full
Document Steward checklist lives in `sme-docs.md`."

### 4c. `review.md` §6e-DOCS gate

Insert after `§6e-BE` (before `§6g`), following the identical header pattern:

```
### 6e-DOCS. Documentation QA gates *(skip if spec does not touch any .md / docs / memory)*

> Source of truth: [`sme-docs.md`] — "Mandatory documentation gates".
> `/review` independently re-verifies these; do not assume `/build` caught them all.

| Gate | Check | Result |
|------|-------|--------|
| doc-consistency-check.sh | exits 0 | ✅ / N/A / ❌ |
| spec-check.sh (for spec-driven changes) | exits 0 | ✅ / N/A / ❌ |
| CHANGELOG updated | entry under [Unreleased] | ✅ / N/A / ❌ |
| Memory note written | Cline/memories/ note exists for session | ✅ / N/A / ❌ |
| No secrets in docs/notes | no sk-, Bearer, api_key= patterns | ✅ / N/A / ❌ |
| Three-concern boundary | no writes to USAi/ or Continue Extension/ memory | ✅ / N/A / ❌ |
```

---

## 5. Test plan

| Test | File / command | Description |
|------|---------------|-------------|
| Doc consistency | `./scripts/doc-consistency-check.sh` | All cross-references and doc structure checks pass |
| Spec file check | `./scripts/spec-check.sh docs/specs/document-sme.md` | §3 files present; no unexpected scope creep |

No unit tests are required — this is a `docs`-type change. Per `build.md` Type table,
the Tester gate (Role 4) and security scan (Role 5) are skipped.

---

## 6. Docs to update

- [x] `docs/specs/document-sme.md` — this spec (created by /spec step)
- [ ] `CHANGELOG.md` — log addition of Document SME workflow (under `[Unreleased]`)
- [ ] `backlog.md` — check off any related backlog item if applicable

---

## 7. Risks / edge cases

- **Three-concern boundary:** `sme-docs.md` must be explicit that it is Cline-harness
  only and must NOT instruct writing to `USAi/memories/` or `Continue Extension/memories/`.
- **Scope creep temptation:** the Document SME charter is broad (all docs). The scope
  discipline section must explicitly prohibit silently fixing unrelated doc issues —
  note them as backlog items instead.
- **`/review` section numbering:** `review.md` currently has a gap (`§6e` is FE/BE, then
  `§6f` dev-deps, `§6g` conventions). Inserting `§6e-DOCS` between `§6e-BE` and `§6f`
  must not renumber or break existing gate references.

---

## 8. Review checklist (filled by Reviewer role)

- [x] `sme-docs.md` exists and matches the structure in §4a
- [x] `build.md` dispatch table updated per §4b
- [x] `review.md` `§6e-DOCS` gate added per §4c
- [x] `./scripts/doc-consistency-check.sh` exits 0 — ✅ PASS
- [x] `./scripts/spec-check.sh docs/specs/document-sme.md` exits 0 — ✅ PASS (§3 uses list format, exempt from pipe-table parser; scope-creep warnings are pre-existing commits, not part of this change)
- [x] `CHANGELOG.md` updated — entry under `[Unreleased]`
- [x] Memory note written to `Cline/memories/` — `2026-06-26-165200-document-sme-added.md`
- [x] No secrets in any new/edited file — verified
