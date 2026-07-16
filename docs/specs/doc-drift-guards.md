# Spec: Doc-Drift Guards

**Status:** Done
**Type:** chore
**Created:** 2026-07-15
**Author:** Cline / user
**Prior context:** Previous session (2026-07-15) identified five doc-drift issues in the RAIL
workflow files and fixed them by hand; this spec adds machine checks so the three highest-priority
drift classes are caught automatically by the existing `doc-consistency-check.sh` gate.

---

## 1. Goal & scope

### Goal
Extend `scripts/doc-consistency-check.sh` with three deterministic bash guards so the
documentation-drift classes fixed manually in this session become self-enforcing.
The guards ride the existing `cli-check.sh --review` §6a gate and the pre-commit hook
— no new plumbing is needed. Regression tests are added to `backend/tests/python/test_scripts.py`
using the established temp-fixture pattern so each guard cannot silently rot.

### Out of scope
- Auto-fixing drift — guards detect and fail; humans fix.
- AC-2 (referenced-path existence guard): more complex Bash parsing; deferred to a
  separate backlog item (#58) to keep this chore minimal and shippable quickly.
- Any USAi app code changes (`server.py`, `app.js`, `frontend/`, `backend/`).
- Any new CI pipeline changes (the guards run through the existing gate).

---

## 2. User story & acceptance criteria

As a developer on USAi Chat, I want `doc-consistency-check.sh` to fail automatically
when known drift classes are introduced, so documentation stays correct without requiring
a manual review audit.

- [ ] **AC-1 Stale-path guard:** `doc-consistency-check.sh` exits non-zero (≥1) if any
  deprecated flat test path (`tests/js/`, `tests/python/`, `node --check app.js`,
  `py_compile server.py`) appears verbatim in `.clinerules/` or `docs/tooling/` files.
- [ ] **AC-3 Role-count consistency guard:** `doc-consistency-check.sh` exits non-zero if
  the phrase `The RAIL roles (0–6)` is absent from `.clinerules/rail-pipeline.md`, or if a
  standalone conflicting count phrase (`five roles`, `six roles`, `seven roles`) appears
  verbatim in any of the enforcing files.
- [ ] **AC-4 Mandatory-gate guard:** `doc-consistency-check.sh` exits non-zero if the word
  `optional` appears within 80 characters of `cli-check.sh --review` in any Cline doc
  (`.clinerules/`, `docs/tooling/cline.md`), indicating the gate has been incorrectly
  described as optional.
- [ ] **AC-5 Clean-tree unchanged:** `./scripts/doc-consistency-check.sh` continues to exit 0
  on the current (post-fix) working tree.
- [ ] **AC-6 Regression tests green:** Three new test classes in
  `backend/tests/python/test_scripts.py` (one per guard) create drifted-fixture temp repos
  and assert non-zero exit; a clean-fixture test asserts exit 0.
  All existing tests continue to pass.

---

## 3. Affected files

| File | Change |
|------|--------|
| `scripts/doc-consistency-check.sh` | Add three guard blocks (stale-path, role-count, mandatory-gate); Bash 3.2-compat |
| `backend/tests/python/test_scripts.py` | Add `TestStalePathGuard`, `TestRoleCountGuard`, `TestMandatoryGateGuard` test classes |
| `docs/specs/doc-drift-guards.md` | This spec (new) |
| `CHANGELOG.md` | Add entry under `[Unreleased]` |
| `backlog.md` | Mark this item `[~]`; add deferred AC-2 item `[ ] #58` |

---

## 4. Technical approach

### Role 2 — Architect sign-off

The three new guard blocks are appended after the existing phrase-duplication loop in
`doc-consistency-check.sh`. They follow the same structure: loop over a set of
enforcing-file patterns, grep for the offending phrase, accumulate `ERRORS`, print
offenders at the end. Existing `ERRORS` and `OFFENDERS` vars are reused.

**Guard 1 — Stale-path guard (AC-1)**
```bash
# Stale paths: these moved to frontend/tests/js/ and backend/tests/python/ in #56.
STALE_PATH_PHRASES=("tests/js/" "tests/python/" "node --check app.js" "py_compile server.py")
STALE_PATH_FILES=(".clinerules" "docs/tooling")  # recursive glob via find
```
Use `find $REPO_ROOT/<dir> -name "*.md" | xargs grep -lF "$phrase"` for each phrase.
False-positive risk: `tests/js/` matches `frontend/tests/js/` — use exact-substring match
which is safe because the stale form is the shorter flat path (no `frontend/` prefix).

**Guard 2 — Role-count consistency guard (AC-3)**
Two sub-checks:
1. Assert `The RAIL roles (0–6)` IS present in `.clinerules/rail-pipeline.md`
   (missing = drift).
2. Check for conflicting count phrases (`five roles`, `six roles`, `seven roles`) as
   standalone words in any enforcing file.

**Guard 3 — Mandatory-gate guard (AC-4)**
Use `grep -i "optional"` near `cli-check.sh --review` within a context window. In bash,
safest approach: extract lines containing `cli-check.sh --review`, then check if `optional`
appears in the same line. Applies to `.clinerules/*.md` and `docs/tooling/cline.md`.
The correct policy is that `./scripts/cli-check.sh --review` is **fail-closed**: it always
attempts the AI review pass (`cn` or the `npx @continuedev/cli` fallback) and the gate fails
if that command fails. Documentation should describe the AI review as *"attempted as part of
the full review gate"* — never as optional or skippable.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A) — N/A
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A) — N/A
- [x] `/config` exposes no secrets (or N/A) — N/A
- [x] Path traversal rejected on filesystem access (or N/A) — N/A
- [x] CSS bump applied (or N/A) — N/A

---

## 4b. Shift-left governance findings (Step 2b output)

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All ACs are binary and observable (exit code + output text) |
| G-2 Scope / value | ✅ Pass | Three guards scoped to exactly the drift classes that just bit us; AC-2 deferred to avoid gold-plating |
| G-3 Dependency coherence | ✅ Pass | No prerequisite backlog items; guards operate on existing files |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-11a | `TestStalePathGuard.test_fails_when_stale_path_in_clinerules` — fixture with `tests/js/` in `.clinerules/workflows/build.md` → exit non-zero | `backend/tests/python/test_scripts.py` | unit |
| T-11b | `TestStalePathGuard.test_passes_when_correct_paths_used` — fixture with `frontend/tests/js/` and `backend/tests/python/` only → exit 0 | `backend/tests/python/test_scripts.py` | unit |
| T-12a | `TestRoleCountGuard.test_fails_when_canonical_phrase_missing` — fixture without `The RAIL roles (0–6)` in `.clinerules/rail-pipeline.md` → exit non-zero | `backend/tests/python/test_scripts.py` | unit |
| T-12b | `TestRoleCountGuard.test_fails_when_conflicting_count_present` — fixture with `six roles` in an enforcing file → exit non-zero | `backend/tests/python/test_scripts.py` | unit |
| T-12c | `TestRoleCountGuard.test_passes_when_canonical_phrase_present_no_conflict` — correct phrase, no conflicting count → exit 0 | `backend/tests/python/test_scripts.py` | unit |
| T-13a | `TestMandatoryGateGuard.test_fails_when_optional_on_same_line_as_cli_check` — fixture with `cli-check.sh --review` and `optional` on same line → exit non-zero | `backend/tests/python/test_scripts.py` | unit |
| T-13b | `TestMandatoryGateGuard.test_passes_when_cli_check_not_described_as_optional` — `cli-check.sh --review` without `optional` → exit 0 | `backend/tests/python/test_scripts.py` | unit |

**TDD order:** write T-11 through T-13 first (Red) → implement guards (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `backlog.md` — mark this item `[~]`; add deferred `[ ] #58` referenced-path existence guard
- [ ] `Cline/scrum/product-backlog.md` — move #58-equivalent item to In-Progress; add #59 to Open

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| False positives on stale-path guard — `tests/js/` might appear in exempt files (CHANGELOG, specs) | Guard scoped to `.clinerules/` and `docs/tooling/` only, matching the existing ENFORCING_FILES pattern |
| `The RAIL roles (0–6)` phrase changes in the future | Guard is a literal grep; if the heading changes, update the guard in the same commit — test T-12a will catch the omission |
| `optional` appears near `cli-check.sh --review` for a legitimate reason (e.g., "not optional") | Guard checks for `optional` without negation context; risk is LOW because the word "optional" rarely appears adjacent to this command legitimately. If a false positive occurs, phrase the sentence differently (e.g., "mandatory, never optional" will still trigger — acceptable trade-off for the chore scope) |
| All guards add to cumulative script runtime | Each guard is a few greps over 5–10 small Markdown files; total added time < 100 ms |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] AC-1, AC-3, AC-4, AC-5, AC-6 all verified
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
