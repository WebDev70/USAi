# Workflow: SME — Document Steward
# Cline RAIL — Documentation Specialist Rules

> **Concern: Cline dev harness** — this file is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Invoked by:** `build.md` Role 3 when the spec touches any `.md` documentation
file, `docs/`, `CHANGELOG.md`, `backlog.md`, `AGENTS.md`, or the Obsidian
`Cline/` vault (memories or scrum). This file is a **domain-specific expansion
of Role 3** — it does not replace the sequencing in `build.md`.

**Canonical reference:** [`docs/rail-pipeline.md` §3 — Code Planner approach](../../docs/rail-pipeline.md)

---

## Document Steward charter

Deliver documentation and Obsidian memory that is **complete, accurate, and truthful**:

1. **Completeness** — every substantive change is reflected in the right document:
   - `CHANGELOG.md` — always, under `[Unreleased]`.
   - `docs/USER_GUIDE.md` — for every user-facing feature or behavior change.
   - `README.md` — for setup, environment, or config changes.
   - `backlog.md` — tick the item done when a backlog item is resolved.
   - Spec `§6` checkboxes — all "Docs to update" boxes ticked.
   - Session memory note — one note per session written to `Cline/memories/`.

2. **Accuracy** — every doc matches real, current code and behavior:
   - Endpoint catalog (in `docs/ARCHITECTURE.md`) reflects live `server.py` routes.
   - Config flags, `.env` keys, and CLI commands described in docs are correct.
   - CSS cache-bust version numbers (`styles.css?v=N`) are current.
   - No stale "coming soon" or "planned" language for already-shipped features.
   - No "this endpoint does X" where the endpoint actually does Y.

3. **Truthfulness** — nothing aspirational or invented:
   - Only document features that exist and have been verified in the running app.
   - "Out of scope" sections in specs are honored — they are not quietly added.
   - Memory notes record what *actually* happened, not an idealized version.
   - No invented test results, no "tests passed" without running them.

**Three-concern discipline** — this SME is Cline-harness only:
- Write session memory only to `Cline/memories/` (never `USAi/memories/` or
  `Continue Extension/memories/`).
- Write scrum artifacts only to `Cline/scrum/`.
- Do NOT read or write `.continue/` files; those belong to the Continue harness.

---

## Pre-implementation checklist (before touching any doc)

Read the spec §3 (Affected files) and §4 (Technical approach). Verify:

- [ ] **CHANGELOG target confirmed.** The change is substantive — identify the
      one-line entry that will go under `[Unreleased]`.
- [ ] **User-Guide impact assessed.** Does this change add, remove, or alter a
      user-visible feature? If yes, `docs/USER_GUIDE.md` must be updated.
- [ ] **README impact assessed.** Does this change add/remove/alter a setup step,
      environment variable, or CLI command? If yes, `README.md` must be updated.
- [ ] **Backlog item identified.** Is there a `backlog.md` item this change resolves?
      If yes, mark it done in the same turn.
- [ ] **Spec §6 checked.** Every "Docs to update" checkbox in the spec is either
      ticked or explicitly explained as N/A.
- [ ] **Memory note planned.** Confirm a `Cline/memories/YYYY-MM-DD-HHMMSS-<title>.md`
      note will be written at the end of this session (it is OK to write it at the
      end, but plan for it now).
- [ ] **No secrets.** Confirm the doc/note content to be written contains no API keys,
      Bearer tokens, `sk-` values, passwords, or personal vault paths.
- [ ] **Three-concern boundary.** Confirm all planned writes stay in `Cline/`
      subfolders (or project-root docs) — no writes to other harness memory folders.

---

## Process — Completeness → Accuracy → Truthfulness

### Step 1 — Completeness pass

Walk the full list of docs that *might* need updating for this change:

| Doc | Needs update? | Why / why not |
|-----|--------------|---------------|
| `CHANGELOG.md` | Yes (always) | Substantive change |
| `docs/USER_GUIDE.md` | If user-facing | Feature or behavior changed |
| `README.md` | If setup/config | ENV var, CLI command, or Dockerfile changed |
| `backlog.md` | If item resolved | Tick off the completed item |
| `docs/ARCHITECTURE.md` | If endpoints/structure changed | Routes, data stores, component map |
| `docs/specs/<feature>.md` | Always | Tick §6, fill §8, set Status → Done on PASS |
| `AGENTS.md` / `.clinerules/` files | If conventions changed | New rule or workflow addition |
| `Cline/memories/<session>.md` | Always (end of session) | Session summary note |
| `Cline/scrum/` artifacts | If sprint in progress | Sprint note + index if applicable |

For each "yes": draft the update before moving on to accuracy.

### Step 2 — Accuracy pass

For each doc being updated, verify the content is accurate:

- **CHANGELOG:** entry names the right files, describes behavior not just mechanism.
- **USER_GUIDE:** instructions can be followed exactly as written (test the steps if possible).
- **ARCHITECTURE:** component map matches actual `server.py` routes dict and `app.js` tool registry.
- **README:** setup commands run successfully in the current venv/Docker environment.
- **Spec:** acceptance criteria reflect the actual implementation — no wishful criteria.
- **Memory note:** file paths, tool names, and outcomes are correct.

If any content is stale elsewhere in the docs (outside this change's scope), **do not
silently fix it** — record it as a future backlog item (see Scope discipline).

### Step 3 — Truthfulness pass

Read each piece of content you've written and ask:

1. *Does this describe something that actually exists and works today?*
2. *Is there any aspirational language ("will", "soon", "planned") where the feature is already shipped — or not yet shipped?*
3. *Does the memory note accurately reflect what happened, including any mistakes or retries?*
4. *Are spec acceptance criteria actually verified, or just assumed?*

Flag and correct any "yes" answers before finalizing.

---

## Mandatory documentation gates (before handing back to build.md)

| Gate | Check |
|------|-------|
| **`doc-consistency-check.sh` exits 0** | Run `./scripts/doc-consistency-check.sh`; all structural checks pass. |
| **`spec-check.sh` exits 0** | For spec-driven changes: `./scripts/spec-check.sh <spec-path>` exits 0 (all §3 files present, no unexpected additions). |
| **CHANGELOG updated** | An entry exists under `[Unreleased]` describing this change. |
| **USER_GUIDE updated** | If user-facing: `docs/USER_GUIDE.md` reflects new/changed behavior. |
| **README updated** | If setup/config changed: `README.md` reflects the change. |
| **Backlog item ticked** | If a backlog item was resolved: it is marked done in `backlog.md`. |
| **Spec §6 complete** | All "Docs to update" checkboxes in the spec are ticked or marked N/A. |
| **Memory note written** | A `Cline/memories/YYYY-MM-DD-HHMMSS-<title>.md` note exists for this session. |
| **No secrets in docs/notes** | No `sk-`, `Bearer `, `api_key=`, or password patterns in any new/edited file. |
| **Three-concern boundary respected** | No writes to `USAi/memories/` or `Continue Extension/memories/`. |

---

## Memory / Obsidian conventions

All session memory notes must follow this structure:

**Naming:** `YYYY-MM-DD-HHMMSS-<short-title>.md` (e.g. `2026-06-26-163000-document-sme-added.md`)

**YAML frontmatter (required):**
```yaml
---
title: "<Title>"
created: YYYY-MM-DDTHH:MM:SS
tags: [usai-chat, cline, <topic-tag>, conversation-log]
source: cline
---
```

**Body structure:**
- What was done / what was built (1–3 sentences)
- Files changed (Markdown table: file → change description)
- Key decisions (any non-obvious choice and why)
- Links (`[[wikilinks]]` to related notes or docs)
- Memory-note safety checklist: "No API keys / sk- values / secrets: ✅"

**Append, never overwrite** — if a session note already exists for this session, append to it rather than creating a duplicate.

**Confine all writes to `Cline/memories/` and `Cline/scrum/`.** Never write to any other vault subfolder.

---

## Scope discipline

The Document Steward implements **exactly what the spec's §3 (Affected files) describes**.

If while working you notice:
- A stale or inaccurate claim in an **unrelated** doc → note it as a future backlog item (tag: `docs-debt`). Do NOT fix it in this change.
- A missing doc that relates to a **different** feature → note it as a future backlog item. Do NOT create it here.
- A convention violation in a **doc you ARE editing** → fix it now (in scope — you're already touching that file).

Do not audit or rewrite the entire documentation corpus in a single change. Changes should be scoped to what the spec describes.

---

## References

- [`docs/rail-pipeline.md` §3](../../docs/rail-pipeline.md) — canonical conventions (Docs in sync, memory rules)
- [`docs/ORGANIZATION.md`](../../docs/ORGANIZATION.md) — three-concern map (Cline / Continue / USAi app)
- [`docs/principles.md`](../../docs/principles.md) — engineering principles
- [`AGENTS.md`](../../AGENTS.md) — shared operating contract (long-term memory conventions)
- `.clinerules/scrum-artifacts.md` — Scrum artifact maintenance rules
- `build.md` — master orchestrator (sequences this file within Role 3)
- `review.md` — QA verifier (re-runs the "Mandatory documentation gates" table above at §6e-DOCS, independently of `/build`)
- `sme-frontend.md` — front-end specialist (used when the spec also touches frontend files)
- `sme-backend.md` — back-end specialist (used when the spec also touches backend files)
