# Spec: RAIL Pipeline Improvements

**Status:** Done
**Created:** 2026-06-23
**Author:** Cline / user
**Prior context:** None found in Obsidian vault memories on this topic. RAIL pipeline is current, active, and well-documented per backlog items #17, #25, #26, #30, and #34.

---

## 1. Goal & scope

### Goal
RAIL is well-designed but relies too heavily on agent self-attestation — the agent
can mark every review checkbox ✅ without those checks being machine-verifiable.
We will close the most important trust-vs-verification gaps by adding machine-
enforced scripts and tightening existing gates across five phases. Each phase is
independently shippable and tested. No app code or runtime behavior is changed —
this is entirely tooling/harness hardening.

### Out of scope
- Rewriting or restructuring the RAIL concept itself.
- Any change to `server.py`, `app.js`, `index.html`, or `styles.css`.
- Adding new runtime dependencies.
- Implementing all five phases at once — each phase ships as its own RAIL loop.

---

## 2. User story & acceptance criteria

As a developer using the RAIL pipeline, I want automated scripts to verify
that the spec↔build contract, coverage, documentation, and security claims are
actually true — not just self-asserted by the agent — so that quality gates
cannot be silently skipped.

### Phase 1 — Verification gaps (A: spec↔build diff, TDD red-receipt, memory-note existence)

- [x] AC-1-a: `scripts/spec-check.sh <spec-file>` exits non-zero when a file listed
  in the spec's §3 table is absent from `git diff --name-only HEAD` (flagging
  a missed file), and also when a file appears in the diff that is NOT in §3
  (flagging scope creep). On a clean match it exits 0 and prints a summary.
- [x] AC-1-b: `scripts/spec-check.sh` exits non-zero when a `tests/` row listed in
  spec §5 has no corresponding new or modified test file in the diff.
- [x] AC-1-c: `/review` workflow references `scripts/spec-check.sh` in its §6a
  spec-compliance check, replacing the manual table-read with the script output.
- [x] AC-1-d: `/loop` done-criteria list includes "memory note exists in
  `Cline/memories/`" as a machine-checkable line (script or filesystem assertion).
- [x] AC-1-e: `/build` Role 3a instructs Cline to paste the failing-test output
  ("Red receipt") into the session memory note before proceeding to Green.

### Phase 2 — Coverage depth (B: Python branch coverage, threshold ratchet guard)

- [x] AC-2-a: `run-tests.sh --coverage` measures Python branch coverage
  (`coverage run --branch`) in addition to line coverage.
- [x] AC-2-b: A Python branch coverage threshold (≥ 80%) is added to `.coveragerc`
  and enforced by `run-tests.sh --coverage` (exits non-zero if below threshold).
- [x] AC-2-c: A committed `.coverage-thresholds` file records the current high-water
  marks (Python line %, Python branch %, JS branch %); `scripts/ratchet-check.sh`
  exits non-zero if any threshold in the file is *decreased* vs. the committed value;
  called automatically by `run-tests.sh --coverage`.
- [x] AC-2-d: Existing tests still pass; no test is weakened or deleted.

### Phase 3 — Drift / parity (C: canonical convention list, doc-consistency check, harness-parity check)

- [x] AC-3-a: The USAi convention table (no new deps / `_handler` / path traversal /
  CSS bump / SSRF / secrets) appears in **exactly one place** as the canonical
  source (`docs/rail-pipeline.md` §3); all other occurrences in `AGENTS.md`,
  `.clinerules/rail-pipeline.md`, `docs/tooling/cline.md`, and the individual
  workflows are replaced with a short reference link.
- [x] AC-3-b: `scripts/doc-consistency-check.sh` exits non-zero when it detects a
  convention entry (e.g. "styles.css?v=N" or "is_safe_upstream_url") appearing
  verbatim in more than one location outside the canonical source file.
- [x] AC-3-c: A harness-parity table is added to `docs/rail-pipeline.md` listing
  each of the 10 `.continue/checks/*.md` check names and which Cline `/review`
  gate step enforces it; the table is the single reference for parity status.

### Phase 4 — Ergonomics (D: change-type classifier, escalation memory note, proposal sink)

- [x] AC-4-a: The `/spec` workflow Step 1 includes a mandatory change-type question
  ("feature | bugfix | chore | docs | css") and the spec template's §1 records the
  type; the type determines which RAIL roles and gates apply (documented in `/spec`
  and `/build`).
- [x] AC-4-b: `/loop` escalation (after 5 failed iterations) writes an interim
  memory note to `Cline/memories/` capturing the current gap list and iteration
  history — not just on success.
- [x] AC-4-c: `/self-improve` proposals (new check/rule/test/backlog suggestions)
  are written as tagged Obsidian notes AND as new `backlog.md` entries, not left
  as inline chat suggestions.

### Phase 5 — Security depth (E: hash-pinned deps, memory-note secret scan)

- [x] AC-5-a: `requirements.txt` pins `python-dotenv` with a hash
  (`--hash=sha256:...`); the `iac-review` check and `.env.example` drift guard
  include the hash-pin verification step.
- [x] AC-5-b: `scripts/security-scan.sh` includes a regex pass over
  `<vault>/Cline/memories/` for common secret patterns (`sk-`, `Bearer `,
  `api_key`, `password`) and exits non-zero if any match is found.
- [x] AC-5-c: The `/loop` and `/review` memory-note step reminds Cline to redact
  any API key or token before writing; this instruction is added to the memory-note
  template in `loop.md`.

---

## 3. Affected files

| File | Change |
|------|--------|
| `scripts/spec-check.sh` | **New** — spec §3/§5 vs. git-diff validator |
| `scripts/doc-consistency-check.sh` | **New** — convention-duplication detector |
| `.coverage-thresholds` | **New** — committed high-water mark file for ratchet guard |
| `run-tests.sh` | Add `--branch` flag to Python coverage run; enforce branch threshold |
| `.coveragerc` | Add `branch = True`; add `[coverage:report]` branch threshold |
| `scripts/cli-check.sh` | Reference `spec-check.sh` and `doc-consistency-check.sh` |
| `scripts/security-scan.sh` | Add memory-note secret scan (Phase 5) |
| `.clinerules/workflows/spec.md` | Add change-type classifier question (Phase 4) |
| `.clinerules/workflows/build.md` | Add Red-receipt instruction to Role 3a (Phase 1) |
| `.clinerules/workflows/review.md` | Replace §6a manual table with `spec-check.sh` output (Phase 1) |
| `.clinerules/workflows/loop.md` | Add memory-note-exists check to done criteria; add escalation note (Phase 1, 4) |
| `.clinerules/workflows/self-improve.md` | Wire proposals to `backlog.md` + Obsidian (Phase 4) |
| `docs/rail-pipeline.md` | Canonical convention table (Phase 3); harness-parity table (Phase 3) |
| `AGENTS.md` | Replace duplicate convention table with link to canonical source |
| `.clinerules/rail-pipeline.md` | Replace duplicate convention table with link to canonical source |
| `docs/tooling/cline.md` | Replace duplicate convention list with link |
| `requirements.txt` | Hash-pin `python-dotenv` (Phase 5) |
| `tests/python/test_server.py` | Tests for new scripts (invoked via subprocess) |
| `CHANGELOG.md` | Add entry under `[Unreleased]` |
| `backlog.md` | Add / update item #35 |

---

## 4. Technical approach

### Role 2 — Architect sign-off

**Phase 1 — Verification gaps:**

`scripts/spec-check.sh <spec-file>` — pure bash script, no deps:
1. Parse spec §3 file table: extract lines matching `` `path` `` pattern.
2. Run `git diff --name-only HEAD` (or `git diff --cached --name-only` for staged).
3. Compute set-diff: files in §3 not in diff → "missing file" warning; files in
   diff (excluding `docs/` and `CHANGELOG.md`) not in §3 → "scope creep" warning.
4. Parse spec §5 test plan: extract `tests/` path entries; confirm at least one
   matching file is in the diff set. Missing test files → error.
5. Exit 0 only if no errors (warnings are printed but do not block).

`/review` §6a updated: run `./scripts/spec-check.sh <spec>` before the manual
table, show its output, treat its non-zero exit as a GAP.

Memory-note existence check: at the end of `/loop` done-criteria, assert
`ls <OBSIDIAN_VAULT_PATH>/Cline/memories/ | grep $(date +%Y-%m-%d)` returns at
least one file. If not, the "Memory note written" checkbox is left unchecked and
emitted as a GAP.

**Phase 2 — Coverage depth:**

`run-tests.sh --coverage` change: replace `coverage run --source=server` with
`coverage run --branch --source=server`. Add a second `coverage report` pass that
checks branch coverage (using `--fail-under` on the branch % column).

`.coverage-thresholds` format:
```
python_line=90
python_branch=80
js_branch=70
```
CI job reads this file and fails if any value is lower than the committed value.
A small bash comparison loop in `run-tests.sh` or a dedicated check script.

**Phase 3 — Drift/parity:**

`scripts/doc-consistency-check.sh`: for each of 5–6 key convention phrases
(e.g. `` `styles.css?v=N` ``, `is_safe_upstream_url`, `TOOL_REGISTRY`), uses
`grep -r` to count occurrences outside `docs/rail-pipeline.md` (the canonical
source). If any phrase appears in more than one *other* file verbatim, exits
non-zero with a list of offenders.

Harness-parity table in `docs/rail-pipeline.md`: Markdown table with columns
`Check file | Cline /review step`. One row per check. This is documentation,
not a script; updated manually when checks are added.

**Phase 4 — Ergonomics:**

`/spec` Step 1 gains question 0 (before the five existing questions):
> "What type of change is this? (feature | bugfix | chore | docs | css)"

The answer is recorded in the spec as a **Type:** field after **Status:**. The
type propagates to `/build` and `/review` to enable role-skipping for chore/css.

`/loop` escalation block gains a `write_escalation_memory_note()` call:
writes `Cline/memories/YYYY-MM-DD-HHMMSS-<feature>-escalation.md` with the
current gap list and iteration summary.

`/self-improve` proposals: the "Propose improvements" section is updated to
explicitly require (a) adding each proposal as a `backlog.md` entry with `[ ]`
status, and (b) writing a tagged Obsidian note in `Cline/memories/`.

**Phase 5 — Security depth:**

`requirements.txt` hash-pin: use `pip download python-dotenv` to get the wheel,
run `pip hash` to generate the sha256, add `--hash=sha256:<hash>` annotation.

`scripts/security-scan.sh` memory-note scan: add a block near the end that runs
`grep -r -l "sk-\|Bearer \|api_key\s*=\|password\s*=" <vault>/Cline/memories/`
and exits non-zero if any file matches. Skipped if `OBSIDIAN_VAULT_PATH` is not set.

`/loop` memory-note template: add a "Secrets removed" reminder line and a `[ ]`
checkbox before the memory note is written.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A) — N/A (scripts only)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A) — N/A
- [x] `/config` exposes no secrets (or N/A) — N/A
- [x] Path traversal rejected on filesystem access (or N/A) — N/A (scripts, not endpoints)
- [x] CSS bump applied (or N/A) — N/A (no CSS changes)

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | `spec-check.sh` exits 0 when diff matches §3 and §5 exactly | `tests/python/test_scripts.py` (subprocess) | unit |
| T-2 | `spec-check.sh` exits non-zero when a §3 file is absent from diff | `tests/python/test_scripts.py` | unit |
| T-3 | `spec-check.sh` exits non-zero when a diff file is absent from §3 (scope creep) | `tests/python/test_scripts.py` | unit |
| T-4 | `spec-check.sh` exits non-zero when a §5 test row has no matching changed file | `tests/python/test_scripts.py` | unit |
| T-5 | `run-tests.sh --coverage` fails when Python branch coverage is below threshold | `tests/python/test_coverage_gate.py` | unit |
| T-6 | `doc-consistency-check.sh` exits non-zero when a convention phrase appears in >1 non-canonical file | `tests/python/test_scripts.py` | unit |
| T-7 | `doc-consistency-check.sh` exits 0 when all convention phrases appear only in the canonical source | `tests/python/test_scripts.py` | unit |
| T-8 | `security-scan.sh` exits non-zero when a memory note contains a `sk-` pattern | `tests/python/test_scripts.py` | unit |
| T-9 | `.coverage-thresholds` ratchet check exits non-zero when a threshold value decreases | `tests/python/test_scripts.py` | unit |
| T-10 | Python branch coverage is actually ≥ 80% on current `server.py` (gate verification) | `tests/python/test_server.py` (coverage run) | integration |

**TDD order:** write these tests first (Red) → implement each script (Green) →
refactor and confirm all tests stay green.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — no user-facing changes (tooling only)
- [ ] `README.md` — update "Running tests" if `run-tests.sh` flags change
- [ ] `backlog.md` — mark #35 phases done as each ships; this spec linked from #35
- [ ] `AGENTS.md` / `CONTINUE.md` — update convention table reference to canonical source (Phase 3)
- [ ] `docs/rail-pipeline.md` — canonical convention table + harness-parity table (Phase 3)

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| `spec-check.sh` false positive on refactors where many files change | Warnings (not errors) for scope-creep; only §3 absence is a hard exit-1 |
| `spec-check.sh` parsing fails on non-standard §3 table format | Script validates that it found ≥1 row; emits a parse-error warning if the §3 table is absent |
| Python branch coverage threshold fails on existing test suite | Phase 2 starts by measuring current branch % before setting the gate; threshold set to actual current % to avoid a day-1 failure |
| De-duplicating convention text (Phase 3) breaks links in editors | All removed sections replaced with explicit file-relative links, not bare references |
| `security-scan.sh` memory-note scan is slow on large vaults | `grep -r` with targeted pattern; `--include="*.md"` and scoped to `Cline/memories/` only |
| Hash-pinning `python-dotenv` breaks `pip install` in some pip versions | Test against the same pip version used in CI; document the `--require-hashes` behavior |
| Phase 4 change-type classifier adds friction for trivial changes | Type question is the *first* question (quick), and "chore" / "css" fast-paths skip most steps |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 90% line, ≥ 80% branch; JS branch ≥ 70%)
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §6 (CHANGELOG, backlog #35 all phases, spec Status→Done)
- [x] Acceptance criteria AC-1-a through AC-5-c all verified
- [x] Memory note written to `Cline/memories/`
