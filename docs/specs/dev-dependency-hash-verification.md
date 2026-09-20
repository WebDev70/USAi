# Spec: Dev Dependency Hash Verification

**Status:** Done
**Type:** bugfix
**Created:** 2026-09-19
**Author:** Cline / user
**Prior context:** Sprint 19 governance BLOCKING-01 found the `mutmut==2.5.1` digest was fabricated and the existing checker validated versions only.

---

## 1. Goal & scope

### Goal
Repair the invalid `mutmut` artifact pin and turn the decorative hashes in
`requirements-dev.txt` into an executed supply-chain control. Restore the Make entry
points already promised by scripts/specs so failure remediation is actionable.

### Out of scope
- Fully locking and hashing every transitive dependency of the dev tools.
- Changing dev-tool versions or making mutation testing a hard quality gate.
- Addressing security-scan strictness (#93).

---

## 2. User story & acceptance criteria

As a maintainer, I want dev-tool artifact hashes verified by pip so that a fabricated or
tampered digest fails the same gate that claims to validate the dependency manifest.

- [x] **AC-1:** `mutmut==2.5.1` is pinned to PyPI's only published artifact digest, `sha256:d8fea2538805277f6290922e88881ad045002fc284d5a53c2b3915298b77f79d`.
- [x] **AC-2:** `dev-deps-check.sh` invokes pip hash enforcement for all declared top-level artifacts and exits nonzero when any digest is corrupt.
- [x] **AC-3:** Hash verification uses `--no-deps`, avoiding an implicit transitive-lockfile expansion while still verifying every declared artifact.
- [x] **AC-4:** Hash-verification tests are hermetic: a local artifact with its real digest passes and the same artifact with a corrupt digest fails, without network access.
- [x] **AC-5:** `make dev-setup` exists and installs the hash-verified top-level manifest before resolving the dev tools' transitive dependencies.
- [x] **AC-6:** `make mutation` exists and invokes `scripts/mutation-audit.sh` with the project venv Python.
- [x] **AC-7:** Existing version/missing-pin exit behavior remains covered and passing.

---

## 3. Affected files

| File | Change |
|------|--------|
| `requirements-dev.txt` | Replace the invalid `mutmut` digest and document top-level-only hash scope. |
| `scripts/dev-deps-check.sh` | Add pip download/hash verification with isolated temporary output and cleanup. |
| `Makefile` | Add `dev-setup` and `mutation`; make `setup` delegate to hash-enforcing dev setup. |
| `backend/tests/python/test_dev_deps.py` | Add hermetic valid/corrupt hash tests and Make-target assertions. |
| `CHANGELOG.md` | Record #89 under `[Unreleased]`. |
| `backlog.md` | Track #89 through In Progress to Done and add approved #90–#93. |
| `Cline/scrum/product-backlog.md` | Mirror approved and In-Progress statuses. |

---

## 4. Technical approach

### Role 2 — Architect sign-off
Add a dedicated hash phase before installed-version comparison. It calls the selected
Python as `-m pip download --no-deps --require-hashes -r "$REQ_DEV" -d <tempdir>`;
`mktemp -d` plus a trap prevents residue. `--no-deps` is deliberate: the file is a
hash-pinned top-level manifest, not a complete transitive lockfile. Tests point pip at a
local `--find-links` directory with `--no-index` through a script environment override.

`dev-setup` first runs the same hash-enforced top-level download/install contract, then
allows pip to resolve transitive dev-only dependencies. `mutation` passes `.venv/bin/python`
to the existing informational wrapper.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (N/A)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (N/A)
- [x] `/config` exposes no secrets (N/A)
- [x] Path traversal rejected on filesystem access (N/A; caller-provided test paths only)
- [x] CSS bump applied (N/A)

---

## 4b. Shift-left governance findings (Step 2b output)

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | Every criterion is a command result, exact digest, target existence, or regression test. |
| G-2 Scope / value | ✅ Pass | Full transitive lock generation is explicitly excluded; restoring `mutation` resolves directly related contract drift. |
| G-3 Dependency coherence | ✅ Pass | No prerequisite backlog items; #90–#93 remain independent. |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-6 | Local artifact with correct sha256 makes hash gate pass | `backend/tests/python/test_dev_deps.py` | subprocess/integration |
| T-7 | Same local artifact with corrupt sha256 makes checker exit 1 | `backend/tests/python/test_dev_deps.py` | regression |
| T-8 | `dev-setup` and `mutation` targets exist with required commands | `backend/tests/python/test_dev_deps.py` | unit/text contract |
| T-1–T-5 | Existing version and configuration contracts stay green | `backend/tests/python/test_dev_deps.py` | regression |

**TDD order:** write T-6–T-8 first and capture Red → implement minimum changes → refactor under green.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — add #89 under `[Unreleased]`
- [x] `README.md` — N/A; `make help` is the setup-command surface and will expose the target
- [x] `docs/USER_GUIDE.md` — N/A; developer tooling only
- [x] `backlog.md` — #89 Done after gates; #90–#93 remain open
- [x] Scrum mirror — #89 Completed after gates; #90–#93 open

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Network-dependent tests are flaky | Use a local dummy artifact, `--no-index`, and `--find-links`. |
| pip skips hash checks for already installed tools | Use `pip download`, which fetches/verifies declared artifacts independently of installed state. |
| Full `--require-hashes` install rejects unhashed transitive dependencies | Deliberately use `--no-deps`; full transitive locking remains out of scope. |
| Temporary downloads pollute the repo | Allocate an OS temp directory and remove it with an EXIT trap. |
| sdist metadata/build isolation adds unnecessary work | Hash gate downloads artifacts; empirically completes in seconds with cache. |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes
- [x] `./scripts/security-scan.sh` clean
- [x] `./scripts/quality-gate.sh` and `./scripts/doc-consistency-check.sh` pass
- [x] Acceptance criteria AC-1…AC-7 verified
- [x] Memory note written to `Cline/memories/`

## Spec changelog

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
| 2026-09-20 | §4 approach, §5 tests | Replaced the custom `PIP_HASH_CHECK_OPTIONS` word-split array with pip's native `PIP_NO_INDEX`/`PIP_FIND_LINKS`; T-1 now builds local wheels with real digests. | Expanding an empty indexed array under `set -u` in bash 3.2 raised "unbound variable", breaking `./run-tests.sh --coverage`; env vars are also space-safe. |
