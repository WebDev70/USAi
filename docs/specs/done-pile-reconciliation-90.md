# Spec: #90 — Reconcile the Done pile with the code that actually exists

**Status:** Ready
**Type:** chore
**Created:** 2026-09-20
**Author:** Cline / ronaldbblake
**Prior context:** Sprint 19 governance audit (BLOCKING-02) found 5 `[x]` Done items citing 8 identifiers with 0 occurrences in 1,065 historical code blobs. This spec defines the implement-or-strike plan.

---

## 1. Goal & scope

### Goal
To restore trust in the `backlog.md` Done pile by reconciling its claims with the code that actually exists. This involves auditing five specific `[x]` Done items (#10, #11a/#11c, #12, #29, #34), correcting their status and claims, and fixing or removing dependent documentation that describes non-existent features. This is a pure backlog/documentation integrity chore.

### Out of scope
- **Implementing the phantom features.** The default action is **STRIKE**: mark the false claims as `[S] STRUCK` and remove the phantom features from docs. Any item deemed worthy of implementation will be moved back to the open backlog (`[ ]`) with a note, to be prioritized and re-specced separately.
- **Implementing `INNOV-01` (identifier-existence guard).** That is a separate, valuable feature for *preventing* this class of error, but it is not part of the cleanup itself.
- **Auditing the entire Done pile.** The scope is limited to the five items flagged in BLOCKING-02 plus their direct doc dependencies.

---

## 2. User story & acceptance criteria

As a developer, I want the `backlog.md` `[x]` Done items to accurately reflect code that was actually shipped, so that I can trust the project's history, reuse code with confidence, and not be misled by documentation describing features that don't exist.

- [ ] **AC-1:** Each of the five phantom-citing backlog items (#10, #11, #29, #34) and their sub-items are updated with a `[S] STRUCK` or `[✓] Verified` status and a note explaining the finding and correction.
- [ ] **AC-2:** Dependent documentation (`ARCHITECTURE.md`, `USER_GUIDE.md`) is corrected: phantom features (`POST /import-session`, 💭 Thinking block, startup 401 warning) are removed, and drifted claims (e.g., `logs/files?file=`) are fixed to match the code (`?name=`).
- [ ] **AC-3:** The 7 orphan and 16 stale-status specs identified in `ADVISORY-04` are either archived (and git-removed) or their status is corrected to `Done`. The missing `startup-auth-probe.md` spec is marked as such in the backlog.
- [ ] **AC-4:** The oversized `## Completed (archive)` section in `backlog.md` is moved to a separate `docs/archive/backlog-2026-h1.md` file to improve readability, leaving only the last ~2 sprints of Done items in the live file.

---

## 3. Affected files

| File | Change |
|------|--------|
| `backlog.md` | **Primary artifact.** Add `[S] STRUCK` / `[✓] Verified` annotations to #10, #11, #29, #34. Move bulk of archive to a new file. |
| `docs/ARCHITECTURE.md` | Remove `POST /import-session` from §3b endpoint table; correct `GET /logs/files?file=` to `?name=`. |
| `docs/USER_GUIDE.md` | Remove references to the 💭 Thinking block (§Reasoning-effort) and the startup 401 warning (§Troubleshooting). |
| `docs/specs/*.md` | Change `Status: Ready/In Progress` to `Status: Done` for 16 stale specs. |
| `docs/archive/backlog-2026-h1.md` | **New file.** Will contain the archived portion of the `backlog.md` Done pile. |
| `CHANGELOG.md` | Add an entry for #90 under `[Unreleased]` → `Changed` or `Fixed`. |

---

## 4. Technical approach

### Role 2 — Architect sign-off
This is a search-and-replace task guided by the verified findings from the Sprint 19 governance audit.

1.  **Backlog Annotation:** Systematically edit `backlog.md` to prepend a status marker and note to each of the 5 items and their sub-claims. `[S]` for Struck, `[✓]` for Verified.
2.  **Doc Correction:** Edit `ARCHITECTURE.md` and `USER_GUIDE.md` to remove the sections describing phantom features. This is pure text removal/correction.
3.  **Spec Archival:** Write a script or a single multi-file `sed` command to change `Status: Ready` and `Status: In Progress` to `Status: Done` in the 16 identified stale spec files. The 7 orphan specs will be `git rm`'d.
4.  **Backlog Splitting:** Manually cut and paste the lower ~900 lines of the `## Completed (archive)` section from `backlog.md` into the new `docs/archive/backlog-2026-h1.md` file, leaving a link in its place.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A) -> N/A
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A) -> N/A
- [x] `/config` exposes no secrets (or N/A) -> N/A
- [x] Path traversal rejected on filesystem access (or N/A) -> 
---

## 4b. Shift-left governance findings (Step 2b output)

> Filled by Cline during `/spec`. Advisory — does not block Status: Ready.

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All ACs are binary and observable by checking file contents. |
| G-2 Scope / value | ✅ Pass | Scope is tightly bound to the BLOCKING-02 audit findings. |
| G-3 Dependency coherence | ✅ Pass | No prerequisite backlog items. This item unblocks #91. |
| G-4 Grep-based security specs | ✅ Pass | N/A: no grep/regex scanner in scope. |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | After edits, re-run the phantom-identifier grep from the audit to confirm they are all gone from doc claims. | (shell command) | verification |
| T-2 | Run `./scripts/doc-consistency-check.sh` to ensure no new drift was introduced. | (shell command) | integration |
| T-3 | Manually verify the links in the newly split `backlog.md` and `backlog-2026-h1.md` are not broken. | (manual) | verification |

**TDD order:** N/A for this chore. The "tests" are post-facto verification steps.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — add entry under `[Unreleased]` for #90.
- [x] `docs/USER_GUIDE.md` — **is being edited.**
- [x] `backlog.md` — **is being edited.**
- [ ] `AGENTS.md` / `CONTINUE.md` — no conventions change.

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Over-aggressive striking removes a claim that was real but hard to find. | The audit used an exhaustive blob scan with positive controls, making this unlikely. Each change will be part of a single, reviewable commit. |
| Introducing broken links when splitting `backlog.md`. | Manual verification (T-3) and a full `doc-consistency-check.sh` run (T-2). |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-N all verified
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

> *Leave empty if no amendments were needed.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
