# Spec: RAIL Hardening Phase 2

**Status:** Done
**Type:** chore
**Created:** 2026-06-27
**Author:** Cline
**Prior context:** Deep-planning session identified 8 improvement opportunities. #35 (5-phase hardening) done 2026-06-24. #46 (shift-left governance) done 2026-06-27.

---

## 1. Goal & scope

### Goal
Close the remaining RAIL process gaps identified 2026-06-27. Seven independent
phases ordered by value/effort. Phase 1 is a live bug fix; subsequent phases add
recall receipts, spec-amendment protocol, review coverage of §4b, clean-state
escalation guarantee, ratchet self-advancement, and mutation-test cadence.

### Out of scope
- Changes to `server.py`, `app.js`, `index.html`, `styles.css`, or test files.
- Making `scripts/smoke-check.sh` a mandatory gate (Phase 2 is optional/advisory).
- Restructuring existing RAIL roles beyond the targeted additions.


---

## 2. User story & acceptance criteria

*As a developer using RAIL, I want the workflow files to be internally consistent,
the self-improvement loop to have a visible recall checkpoint, spec deviations to be
handled by protocol, coverage to be self-advancing, and mutation testing to have a
cadence — so the pipeline matures without requiring manual prompting.*

### Phase 1 — Fix §6e cross-reference bug in `review.md` *(XS — live bug)*
- [ ] AC-1.1: `review.md` §6e names subsection labels that match the labels used
  in `sme-backend.md`, `sme-frontend.md`, and `sme-docs.md`.
- [ ] AC-1.2: `./scripts/doc-consistency-check.sh` exits 0 after the change.

### Phase 2 — Prevention-rule recall receipt in `/build` and `/spec` *(S)*
- [ ] AC-2.1: `/build` pre-flight includes a step to read `self-improvement-log.md`
  and declare which entries are relevant (or "Prevention-rule recall: none apply").
- [ ] AC-2.2: `/spec` Step 0 includes the same recall-receipt requirement.
- [ ] AC-2.3: The receipt format is defined in both files (one line per relevant entry).

### Phase 3 — Spec amendment mini-protocol in `/build` *(S)*
- [ ] AC-3.1: `/build` Role 3 has a "Spec amendment" block: when implementation
  reveals the spec is wrong → pause → propose one-line changelog → confirm → continue.
- [ ] AC-3.2: The spec template in `spec.md` gains an optional `## Spec changelog`
  section (empty by default; populated only for in-flight amendments).

### Phase 4 — §4b shift-left findings verified by `/review` *(S)*
- [ ] AC-4.1: `/review` §6 includes a §6f gate confirming spec §4b is filled
  (G-1/G-2/G-3 each have a result row).
- [ ] AC-4.2: Any ⚠️ finding in §4b is addressed or deferred to a named backlog
  item; missing deferral is emitted as an advisory GAP (non-blocking).

### Phase 5 — Clean-state guarantee on `/loop` escalation *(S)*
- [ ] AC-5.1: `/loop` escalation block has a "Clean-state guarantee" section with
  two options: (a) `git stash` / branch the WIP, or (b) revert to last green commit.
- [ ] AC-5.2: The escalation memory note template gains a `## Working-tree state`
  section recording which option was chosen and the stash/commit reference.

### Phase 6 — Coverage ratchet self-advancement rule *(S)*
- [ ] AC-6.1: `/loop` Continuous Improvement section includes: when measured
  coverage exceeds any `.coverage-thresholds` gate by ≥ 5 points, propose bumping
  that threshold in the post-loop retro.
- [ ] AC-6.2: `govern.md` SE-4 references this rule so the Board can verify it
  is being applied across sprints.

### Phase 7 — Wire mutation testing into `/govern` and `/loop` *(S)*
- [ ] AC-7.1: `govern.md` SE-2 references `scripts/mutation-audit.sh` as a
  periodic check for `server.py`-heavy changes.
- [ ] AC-7.2: `/loop` Continuous Improvement section mentions mutation audit as an
  optional deep-quality pass for builds that significantly touch `server.py`.

---

## 3. Affected files

| File | Change |
|------|--------|
| `.clinerules/workflows/review.md` | Ph1: fix §6e labels; Ph4: add §6f |
| `.clinerules/workflows/sme-backend.md` | Ph1: align §6e-BE label |
| `.clinerules/workflows/sme-frontend.md` | Ph1: align §6e-FE label |
| `.clinerules/workflows/sme-docs.md` | Ph1: align §6e-DOCS label |
| `.clinerules/workflows/build.md` | Ph2: recall receipt; Ph3: spec amendment block |
| `.clinerules/workflows/spec.md` | Ph2: recall receipt in Step 0; Ph3: `## Spec changelog` in template |
| `.clinerules/workflows/loop.md` | Ph5: clean-state guarantee; Ph6: ratchet rule; Ph7: mutation mention |
| `.clinerules/workflows/govern.md` | Ph6: SE-4 ratchet ref; Ph7: SE-2 mutation ref |
| `docs/specs/rail-hardening-phase2.md` | This spec |
| `backlog.md` | Item #47 `[~]` now → `[x]` at loop close |
| `CHANGELOG.md` | Entry under `[Unreleased]` at loop close |

---

## 4. Technical approach

### Role 2 — Architect sign-off
All changes are workflow `.md` files only. No app code, endpoints, tools, runtime
deps, CSS, or tests affected.

**Conventions applied:**
- [x] No new runtime dependency added
- [ ] New endpoint (N/A)
- [ ] New tool (N/A)
- [ ] `/config` secrets (N/A)
- [ ] Path traversal (N/A)
- [ ] CSS bump (N/A)

### Implementation order
Phases 1–7 in order. Phase 1 is a live bug fix — highest priority. Each phase is
a self-contained edit block. All four SME files must be updated atomically in Ph1.

---

## 4b. Shift-left governance findings

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All ACs are binary: label matches / section present / rule stated |
| G-2 Scope / value | ✅ Pass | Targeted workflow gaps only; no scope creep |
| G-3 Dependency coherence | ✅ Pass | Depends only on #35 (done) and #46 (done) |

---

## 5. Test plan

| # | Test | File | Type |
|---|------|------|------|
| T-1 | `./scripts/doc-consistency-check.sh` exits 0 | `scripts/doc-consistency-check.sh` | script gate |

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — entry under `[Unreleased]`
- [ ] `backlog.md` — mark #47 done
- [ ] `Cline/scrum/product-backlog.md` — move #47 to completed
- [ ] `docs/USER_GUIDE.md` — N/A

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Ph1 label fix must touch 4 files consistently | Update all atomically in one turn |
| Recall receipt adds per-task friction | "None apply" is a valid one-word answer |
| Ratchet rule creates noise on every loop | Fires only at ≥ 5pt gap; proposal only, never auto-edit |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3 file list exactly
- [ ] `./scripts/doc-consistency-check.sh` exits 0
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] AC-1.1 … AC-7.2 all verified
- [ ] Memory note written to `Cline/memories/`

