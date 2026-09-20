# Spec: /spec Workflow Hardening — Backlog-ID Guard (#85) + Grep-Redact Standing Requirement (#79)

**Status:** Done
**Type:** chore
**Created:** 2026-09-20
**Author:** Cline / user
**Prior context:** Entry 010 (self-improvement-log) established the grep-redact rule after Sprint 17; Entry 011 flagged audit claims scored without execution. Backlog grooming 2026-09-18 confirmed both items DoR and recommended batching. #79 and #85 both target `.clinerules/workflows/spec.md`.

---

## 1. Goal & scope

### Goal
Two hardening edits to the `/spec` workflow doc prevent two categories of silent failure:

1. **#85 — Pre-flight backlog-ID guard.** Each `/spec` run assigns a new backlog ID manually. In Sprint 18, ID `#79` was assigned twice. Fix: embed the max-ID verification command verbatim in Step 3 of `spec.md` so the Code Planner always confirms the next ID before writing the spec, and requires updating the "highest-assigned ID is **N**" header note in `backlog.md` in the same turn.

2. **#79 — Standing grep-redact requirement.** Any spec for a grep/regex-based security check must carry two explicit requirements routinely discovered mid-implementation: (a) the scanner reports `path:line` only — matched value is `[REDACTED]` — and (b) a hermetic test plants a known fake token and asserts it is absent from stdout+stderr. Fix: add a named standing check (G-4) in Step 2b of `spec.md` plus a one-line cross-reference in `docs/rail-pipeline.md` §3.

### Out of scope
- No changes to `scripts/security-scan.sh`, the test suite, or the USAi app.
- No new backlog IDs beyond 96 (the ID assigned to this spec itself).
- Rewrites of the full governance audit or `security-review.md` check definition.
- Auto-enforcement tooling (a future spec can add a shell check; this item is doc-only).

---

## 2. User story & acceptance criteria

As a **Code Planner (Cline) running `/spec`**, I want the workflow doc to enforce both the backlog-ID uniqueness check and the grep-redact rule at spec-writing time, so that duplicate IDs and missing redaction ACs are caught before implementation begins.

- [x] **AC-1 (#85a):** `.clinerules/workflows/spec.md` Step 3 contains the max-ID shell command verbatim and states the new ID **MUST be `max + 1`**.
- [x] **AC-2 (#85b):** The same Step 3 requires updating the `"highest-assigned ID is **N**"` line in `backlog.md` header in the same turn as writing the spec.
- [x] **AC-3 (#85c):** Running the command against the current `backlog.md` returns `93 / 94 / 95` (live verification).
- [x] **AC-4 (#79a):** `.clinerules/workflows/spec.md` Step 2b contains a new "Check G-4 — Grep-based security specs" subsection stating that any spec whose scope includes a grep/regex scanner must carry: (a) an AC asserting findings report `path:line` only — matched value is `[REDACTED]`; and (b) a mandatory hermetic test that plants a fake token, runs the scanner, and asserts exit non-zero **and** the token string absent from stdout+stderr.
- [x] **AC-5 (#79b):** `docs/rail-pipeline.md` §3 `security-review` bullet appends a one-line cross-reference: `"grep/regex scanners: see .clinerules/workflows/spec.md Step 2b Check G-4."`.
- [x] **AC-6:** `./scripts/doc-consistency-check.sh` exits 0 after both edits.

---

## 3. Affected files

| File | Change |
|------|--------|
| `.clinerules/workflows/spec.md` | Add AC-1/AC-2 pre-flight ID block to Step 3; add Check G-4 to Step 2b; add G-4 row to §4b template |
| `docs/rail-pipeline.md` | Append one-line cross-ref to `security-review` bullet |
| `.clinerules/workflows/review.md` | Add G-4 row + conditional note to the §6g shift-left findings gate table (see Spec changelog) |
| `docs/specs/spec-workflow-hardening-79-85.md` | This spec file |
| `CHANGELOG.md` | Add `### Changed` entry under `[Unreleased]` |
| `backlog.md` | Flip #79 and #85 `[ ]` → `[~]`; update "highest-assigned ID is **96**" header line |

No production code, no test files, no CSS changes.

---

## 4. Technical approach

### Role 2 — Architect sign-off

Both changes are **documentation-only edits** to workflow/guide files.

**`spec.md` Step 3 — ID guard (#85):**
Insert a clearly labelled "Pre-flight: Backlog ID" callout block immediately before "Write `docs/specs/…`" containing: (1) the verbatim `grep | grep | sort | tail -3` command, (2) the rule "new ID = `max + 1`", (3) the requirement to update the header note in `backlog.md` in the same turn.

**`spec.md` Step 2b — Check G-4 (#79):**
Append a fourth check after G-3. Conditional: only applies when scope includes a grep/regex scanner. Zero overhead for unrelated specs. The §4b governance table template gains a `G-4` row.

**`rail-pipeline.md` security-review (#79):**
Append one parenthetical sentence to the `security-review` QA check bullet.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern — N/A
- [x] New tool follows `TOOL_REGISTRY` + gate pattern — N/A
- [x] `/config` exposes no secrets — N/A
- [x] Path traversal rejected on filesystem access — N/A
- [x] CSS bump applied — N/A (no CSS change)

---

## 4b. Shift-left governance findings (Step 2b output)

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All ACs are binary: command output, file-content grep, or script exit code |
| G-2 Scope / value | ✅ Pass | Each edit maps 1:1 to a groomed, DoR-confirmed backlog item; no gold-plating |
| G-3 Dependency coherence | ✅ Pass | No prerequisite backlog items; both #79 and #85 are standalone doc edits |
| G-4 Grep-based security specs | N/A | No grep/regex scanner in scope |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

Verification steps (doc-only change — no new automated test file needed):

| # | Verification | Command | Expected |
|---|-------------|---------|----------|
| T-1 | ID guard block present in `spec.md` | `grep -c 'grep -oE.*backlog.md' .clinerules/workflows/spec.md` | ≥ 1 |
| T-2 | Command returns current max IDs | `grep -oE '^- \[.\] +\*\*[0-9]+\.' backlog.md \| grep -oE '[0-9]+' \| sort -n \| tail -3` | `93 / 94 / 95` |
| T-3 | Check G-4 block present with key terms | `grep -c 'G-4\|REDACTED\|hermetic' .clinerules/workflows/spec.md` | ≥ 3 |
| T-4 | Cross-ref present in `rail-pipeline.md` | `grep -c 'Check G-4' docs/rail-pipeline.md` | ≥ 1 |
| T-5 | Doc consistency gate | `./scripts/doc-consistency-check.sh` | exit 0 |
| T-6 | Full test suite | `./run-tests.sh` | exit 0 |

**TDD order:** confirm T-1/T-3/T-4 return 0 (Red) before editing → confirm ≥ 1 (Green) after.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — add entry under `[Unreleased]`
- [x] `backlog.md` — flip #79 and #85 `[ ]` → `[~]`; update "highest-assigned ID is **96**"
- [x] `Cline/scrum/product-backlog.md` — move #79 and #85 to In Progress

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| `doc-consistency-check.sh` role-count guard trips on G-4 numbering | G-1..G-4 are spec-workflow checks, not RAIL roles (0–6); guard only counts role-table rows; verify AC-6 |
| Verbatim shell command in `.md` confuses path-existence guard | Command references `backlog.md` which exists; no stale path introduced |
| Future item reuses "G-4" label in governance rubric | Label is scoped inside `/spec` workflow; governance rubric uses different numbering |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly (plus the one recorded §3 amendment)
- [x] `./run-tests.sh --coverage` passes (457 tests; server.py 90% line / 92.31% branch; JS branch 76.2%)
- [x] `./scripts/security-scan.sh` clean (4/4 with `OBSIDIAN_VAULT_PATH` exported)
- [x] `./scripts/doc-consistency-check.sh` exits 0 (AC-6)
- [x] Docs updated per §6
- [x] Acceptance criteria AC-1…AC-6 all verified (T-1..T-6 executed, outputs captured)
- [x] Memory note written to `Cline/memories/`

## Spec changelog

> *Optional — populated only when a spec amendment is made during `/build`
> (see build.md §3d). Leave empty if no amendments were needed.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
| 2026-09-20 | §3 Affected files | Added `.clinerules/workflows/review.md` — G-4 row in §6g gate table | AC-4 adds a 4th row to the §4b template, but `/review` §6g only verified G-1..G-3, so G-4 would never be gated. Clarification completing AC-4's intent, not new scope. |

