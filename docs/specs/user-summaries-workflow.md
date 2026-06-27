# Spec: User Summaries Workflow Convention

**Status:** Ready
**Type:** docs
**Created:** 2026-06-26
**Author:** Cline / user
**Prior context:** `Cline/User Summaries/2026-06-24-RAIL-Pipeline-User-Summary.md` established the pattern during a `/self-improve` session; backlog item #40 was created to formalize it.

---

## 1. Goal & scope

### Goal
Formalize the `Cline/User Summaries/` Obsidian folder as a first-class RAIL workflow output. When `/self-improve` surfaces a structural explanation or when `/spec` produces a concept that benefits from a plain-English companion, Cline should automatically offer — and if confirmed, write — a **User Summary note** alongside the technical spec or memory note. This makes key project concepts accessible to non-technical stakeholders and improves onboarding.

### Out of scope
- Retroactively writing User Summaries for all past specs (backlog item if desired).
- Any changes to `server.py`, `app.js`, `index.html`, or `styles.css`.
- Adding automated tests (docs-only change).

---

## 2. User story & acceptance criteria

As a developer using RAIL, I want Cline to automatically offer a plain-English User Summary when completing a `/spec` or `/self-improve` session, so that key project concepts are accessible to non-technical readers and the `Cline/User Summaries/` folder grows organically alongside the technical record.

- [ ] AC-1: `.clinerules/workflows/self-improve.md` has a dedicated "User Summary" section that instructs Cline to offer a User Summary after any `/self-improve` session that produces a structural explanation or process improvement, and to write it to `Cline/User Summaries/YYYY-MM-DD-<topic>-user-summary.md` if the user confirms (or automatically if unattended).
- [ ] AC-2: `.clinerules/workflows/spec.md` has a "User Summary (optional)" step in the Step 4 handoff section that instructs Cline to offer a User Summary for any `feature` or `docs` type spec where a plain-English companion would add clear onboarding value.
- [ ] AC-3: Both workflows reference the same `Cline/User Summaries/` path and note-naming convention (`YYYY-MM-DD-<topic>-user-summary.md` with YAML frontmatter: `title`, `created`, `tags: [usai-chat, user-summary, <topic-tags>]`, `source: cline`).
- [ ] AC-4: `backlog.md` item #40 is marked `[x]` Done with the date and one-line outcome.
- [ ] AC-5: A `Cline/memories/` session note records this task completion.

---

## 3. Affected files

| File | Change |
|------|--------|
| `.clinerules/workflows/self-improve.md` | Add "User Summary" section after "Proposing improvements" |
| `.clinerules/workflows/spec.md` | Add "User Summary (optional)" step to Step 4 handoff |
| `backlog.md` | Mark item #40 `[x]` Done |
| `docs/specs/user-summaries-workflow.md` | This spec (new) |
| `Cline/memories/` | Session note (at task end) |
| `Cline/scrum/product-backlog.md` | Fix #40 status (was incorrectly marked Done 2026-06-24; confirm correct outcome date) |

No app code, tests, `index.html`, or `styles.css` changes.

---

## 4. Technical approach

### Role 2 — Architect sign-off

This is a pure documentation/workflow change. No runtime code is involved. The two workflow files (`.clinerules/workflows/self-improve.md` and `.clinerules/workflows/spec.md`) are plain Markdown read by Cline at workflow invocation time.

**`self-improve.md` change:** Add a new `## User Summary` section after the existing `## Proposing improvements after /self-improve` section. The section should:
- Explain when to write a User Summary (when the session produced a plain-English explanation of a process, concept, or workflow that has standalone value for non-technical readers).
- Give the file naming convention and YAML frontmatter template.
- Reference the `Cline/User Summaries/` path.
- Note: offer the summary and write it automatically if the workflow is unattended, or after a user confirmation prompt if interactive.

**`spec.md` change:** Add a `### User Summary (optional)` subsection inside **Step 4 — Handoff**. The step should:
- Trigger for `feature` or `docs` type specs where the spec introduces a new concept or workflow.
- Offer to write `Cline/User Summaries/YYYY-MM-DD-<topic>-user-summary.md`.
- Be explicitly optional (not a gate — missing it does not block the handoff).

**Conventions applied:**
- [x] No new runtime dependency added — docs/workflow only
- [x] New endpoint follows `_handler` + `routes` pattern (N/A)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (N/A)
- [x] `/config` exposes no secrets (N/A)
- [x] Path traversal rejected on filesystem access (N/A)
- [x] CSS bump applied (N/A — no CSS changed)

---

## 5. Test plan (Role 4 — Tester)

This is a `docs` type change — no code is modified, so no automated tests are added or required. The quality gate is human review of the two modified workflow files against the acceptance criteria.

Manual verification:
- Read `.clinerules/workflows/self-improve.md` and confirm the User Summary section is present, correctly placed, and matches the naming convention in AC-3.
- Read `.clinerules/workflows/spec.md` Step 4 and confirm the User Summary optional step is present and non-blocking.
- Confirm `backlog.md` #40 is `[x]` with date and outcome.

---

## 6. Docs to update

- [ ] `backlog.md` — mark #40 `[x]` Done (2026-06-26)
- [ ] `Cline/scrum/product-backlog.md` — fix #40 entry (was prematurely marked done)
- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `Cline/memories/` — session memory note at task end

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| User Summary step becomes a gate that blocks the handoff | Spec explicitly marks it "optional" — missing it does not block `/loop` or `/review` |
| Notes accumulate in `Cline/User Summaries/` without any index | Convention uses consistent frontmatter tags (`user-summary`) so Obsidian search/dataview finds them; add a note in the convention about using `[[wikilinks]]` to link related summaries |
| Naming collision with session memory notes | Different folder (`User Summaries/` vs `memories/`) and different suffix (`-user-summary.md` vs date-only slug); no collision risk |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (N/A — docs-only change; run syntax check instead: `python3 -m py_compile server.py && node --check app.js`)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-5 all verified
- [ ] Memory note written to `Cline/memories/`
