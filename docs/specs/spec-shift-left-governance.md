# Spec: Shift-left governance — SBA/SA-lite checks in /spec

**Status:** Done
**Type:** chore
**Created:** 2026-06-27
**Author:** Cline
**Prior context:** Question raised about whether `/spec` should incorporate `govern.md` checks or keep them only at sprint close.

---

## 1. Goal & scope

### Goal
Add a lightweight, per-requirement governance pre-check (Step 2b) to `/spec` so
that the three most common requirement-level failures are caught before implementation
begins, without burdening the workflow with the full four-role Governance Board audit.

### Out of scope
- Moving SE, SPMS, or any macro/cross-sprint governance rubric into `/spec`.
- Making any governance check blocking (all findings remain advisory).
- Any change to app code (`server.py`, `app.js`), tests, or CSS.
- Moving the full `/govern` cadence — it stays sprint-close / on-demand.

---

## 2. User story & acceptance criteria

As a developer running `/spec`, I want a lightweight requirement-quality gate
so that scope creep, vague ACs, and undeclared dependencies are surfaced at
authoring time rather than discovered during the sprint-close Governance Board audit.

- [x] AC-1: `/spec` includes a Step 2b with three named checks (G-1, G-2, G-3).
- [x] AC-2: The spec template includes a §4b table for recording shift-left findings.
- [x] AC-3: All Step 2b findings are explicitly advisory (non-blocking).
- [x] AC-4: `govern.md` cadence note references the shift-left split.
- [x] AC-5: `docs/governance.md` "Relationship to RAIL" section documents the two-level model.

---

## 3. Affected files

| File | Change |
|------|--------|
| `.clinerules/workflows/spec.md` | Added Step 2b (G-1/G-2/G-3 checks) + §4b in spec template |
| `.clinerules/workflows/govern.md` | Added shift-left note to cadence paragraph |
| `docs/governance.md` | Expanded "Relationship to RAIL" with shift-left table + two-level model |
| `backlog.md` | Added item #46 as `[x]` Done |
| `CHANGELOG.md` | Added `[Unreleased]` entry |
| `docs/specs/spec-shift-left-governance.md` | This file |

---

## 4. Technical approach

### Role 2 — Architect sign-off
Pure process/documentation change. No app code, endpoints, tools, runtime deps,
CSS, or test infrastructure affected.

**Conventions applied:**
- [x] No new runtime dependency added
- [ ] New endpoint follows `_handler` + `routes` pattern (N/A)
- [ ] New tool follows `TOOL_REGISTRY` + gate pattern (N/A)
- [ ] `/config` exposes no secrets (N/A)
- [ ] Path traversal rejected on filesystem access (N/A)
- [ ] CSS bump applied (N/A)

---

## 4b. Shift-left governance findings (Step 2b output)

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All ACs are binary and observable (doc/file existence checks) |
| G-2 Scope / value | ✅ Pass | Scope is precisely bounded — workflow files + one doc section only |
| G-3 Dependency coherence | ✅ Pass | No open backlog prerequisites |

---

## 5. Test plan

No automated tests — pure process documentation. AC verification is by inspection
of the changed workflow files.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — N/A (developer process, not user-facing)
- [ ] `README.md` — N/A (no setup/config changes)
- [x] `backlog.md` — item #46 marked done

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Step 2b adds friction for simple chores/bugfixes | Checks are silent and self-resolving for trivial cases; no user interruption unless a flag requires rewording |
| Perceived duplication with `/govern` | Explicit cadence note in `govern.md` and the two-level table in `docs/governance.md` make the separation clear |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` N/A (no code change)
- [x] `./scripts/security-scan.sh` N/A (no code change)
- [x] Docs updated per §6
- [x] Acceptance criteria AC-1…AC-5 all verified
- [x] Memory note written to `Cline/memories/`
