# Spec: RAIL QA Hardening (Process-First)

**Status:** Done
**Type:** chore/tooling
**Created:** 2026-06-24
**Author:** Cline / user
**Prior context:** Phases 1–5 of `docs/specs/rail-improvements.md` fully implemented (Status: Done, 2026-06-23). This spec closes five remaining gaps: dev-dep drift, flaky timing test, missing pre-commit gate, no mutation-testing visibility, and workflow self-attestation on convention/deps gates.

---

## 1. Goal & scope

### Goal

Eliminate the last five trust-vs-verification gaps in the RAIL pipeline by adding
machine-enforced tooling and hardening a flaky test — without touching any app
code (`server.py`, `app.js`, `index.html`, `styles.css`) or adding runtime deps.

### Out of scope

- jsdom / frontend behavior tests (deferred — separate spec)
- Any change to `server.py`, `app.js`, `index.html`, or `styles.css`
- Adding new *runtime* Python dependencies to `requirements.txt`
- Automatic mutation-test CI gate (mutation audit is opt-in/non-blocking only)
- Rewriting the RAIL concept or restructuring existing workflows beyond the targeted tightening

---

## 2. User story & acceptance criteria

As a developer (and as the Cline agent), I want the RAIL pipeline to machine-enforce
dev-tool version pins, pre-commit feedback, and assertion-quality visibility so that
the remaining self-attestation checkboxes are either eliminated or backed by a real
script output.

- [ ] **AC-1-a:** `requirements-dev.txt` exists, contains hash-pinned versions of
  `coverage`, `bandit`, `pip-audit`, and `mutmut`; `make setup` installs from it;
  CI installs from it (not bare `pip install`).
- [ ] **AC-1-b:** `scripts/dev-deps-check.sh` exits 1 when an installed tool version
  differs from the pin in `requirements-dev.txt`; exits 0 when all match; exits 2 on
  usage error or missing pin file.
- [ ] **AC-2:** `tests/python/test_dev_deps.py` covers all four `dev-deps-check.sh`
  exit-code paths (match, mismatch, missing package in file, missing file).
- [ ] **AC-3-a:** `scripts/pre-commit.sh` runs syntax gate + gitleaks staged scan +
  changed-file tests; exits 1 on any failure; exits 0 when clean.
- [ ] **AC-3-b:** `make hooks` installs `scripts/pre-commit.sh` as `.git/hooks/pre-commit`.
- [ ] **AC-3-c:** `scripts/pre-commit.sh` skips the secret scan gracefully (with a
  warning, not an error) when gitleaks is absent.
- [ ] **AC-4:** `scripts/mutation-audit.sh` runs mutmut on `server.py` and prints a
  kill-rate summary; always exits 0; is invokable via `make mutation`.
- [ ] **AC-5:** `test_first_chunk_arrives_before_last` in `test_server_proxy.py`
  uses event-ordering (chunk-sequence assertion) instead of wall-clock timing and
  passes deterministically in CI.
- [ ] **AC-6-a:** `scripts/cli-check.sh` calls `dev-deps-check.sh` as a named gate
  (after the security scan gate); non-zero exit is treated as a gate failure.
- [ ] **AC-6-b:** `.clinerules/workflows/review.md` has a `§6f. Dev-deps gate` section
  that references `./scripts/dev-deps-check.sh` and treats non-zero as a GAP.
- [ ] **AC-6-c:** `.clinerules/workflows/loop.md` done-criteria list includes
  `dev-deps-check.sh` passes.
- [ ] **AC-7:** `./run-tests.sh --coverage` passes all existing gates (server.py ≥ 90%
  line, ≥ 80% branch; JS helpers ≥ 70% branch) after all changes.
- [ ] **AC-8:** `./scripts/security-scan.sh` is clean after all changes.

---

## 3. Affected files

| File | Change |
|------|--------|
| `requirements-dev.txt` | **New** — hash-pinned dev/CI tool versions |
| `scripts/dev-deps-check.sh` | **New** — installed-vs-pinned version checker |
| `scripts/pre-commit.sh` | **New** — fast pre-commit gate (syntax + secrets + changed tests) |
| `scripts/mutation-audit.sh` | **New** — opt-in mutmut wrapper (always exits 0) |
| `docs/specs/rail-qa-hardening.md` | **New** — this spec |
| `tests/python/test_dev_deps.py` | **New** — 4 subprocess tests for `dev-deps-check.sh` |
| `tests/python/test_scripts.py` | **Modify** — add `TestPreCommit` class (3 new tests) |
| `tests/python/test_server_proxy.py` | **Modify** — harden `test_first_chunk_arrives_before_last` |
| `Makefile` | **Modify** — add `dev-setup`, `hooks`, `mutation`, `precommit` targets; update `setup` |
| `scripts/cli-check.sh` | **Modify** — add `dev-deps-check.sh` gate block |
| `scripts/security-scan.sh` | **Modify** — add version-pin echo step; update gate count headers (4/4→4/5 + new 5/5) |
| `.github/workflows/tests.yml` | **Modify** — install from `requirements-dev.txt`; add `dev-deps-check` step |
| `.clinerules/workflows/review.md` | **Modify** — add §6f dev-deps gate; tighten §6c docs gate |
| `.clinerules/workflows/loop.md` | **Modify** — add `dev-deps-check.sh` to done-criteria; add pre-commit to quick-reference |
| `docs/rail-pipeline.md` | **Modify** — add "Dev tooling version pins" row to canonical tooling table |
| `CHANGELOG.md` | **Update** — add entry under `[Unreleased]` |
| `backlog.md` | **Update** — check off #28; add #40 (mutation audit) |

**Not changing:** `server.py`, `app.js`, `index.html`, `styles.css`, `requirements.txt`.

---

## 4. Technical approach

### Role 2 — Architect sign-off

**Dev-dep pinning (`requirements-dev.txt` + `dev-deps-check.sh`):**

`requirements-dev.txt` mirrors the format of `requirements.txt`:
```
# Dev/CI-only — NEVER imported by the app. Regenerate hashes with:
#   pip download <pkg>==<ver> --no-deps && pip hash <wheel>
coverage==7.6.1 \
    --hash=sha256:<generated-hash>
bandit==1.7.10 \
    --hash=sha256:<generated-hash>
pip-audit==2.7.3 \
    --hash=sha256:<generated-hash>
mutmut==2.5.1 \
    --hash=sha256:<generated-hash>
```

`dev-deps-check.sh` logic:
1. Parse `requirements-dev.txt` with `grep -E '^<pkg>=='` to extract pinned version.
2. Run `$PY -m pip show <pkg>` and extract `Version:` line.
3. Compare; emit ✓ or ✕; count failures.
4. Exit 1 if any mismatch; exit 2 on usage error or missing pin file.

**Pre-commit gate (`scripts/pre-commit.sh`):**

Three sequential checks:
1. `node --check app.js && $PY -m py_compile server.py` — syntax (< 1 s)
2. `gitleaks detect --no-banner --staged` — staged-only secret scan; skipped with
   `SKIP_GITLEAKS=1` or when gitleaks absent
3. Detect staged `.py` / `.mjs` files; run the specific test file if found;
   fall back to `./run-tests.sh` (without coverage) if detection fails

Hook installation: `make hooks` copies/symlinks `scripts/pre-commit.sh` to
`.git/hooks/pre-commit` and sets it executable.

**Mutation audit (`scripts/mutation-audit.sh`):**

Wrapper around `mutmut run --paths-to-mutate server.py`:
- Checks for mutmut; emits hint and exits 0 if absent.
- Runs mutmut; extracts `killed/survived/timeout` from `mutmut results`.
- Prints kill-rate summary (`kill_rate = killed / (killed + survived) * 100`).
- Always exits 0 — this is informational, not a hard gate.

**Timing-test hardening:**

`test_first_chunk_arrives_before_last` currently measures `time.time()` for first
and last chunk and asserts `first_time < last_time + EPSILON`. Replacement:

The fake upstream in `_FakeUpstreamHandler` sends chunks with embedded sequence
numbers: `b"data: CHUNK-1\n\n"`, `b"data: CHUNK-2\n\n"` etc. The test reads the
raw socket buffer and asserts that `CHUNK-1` appears at a byte offset strictly less
than `CHUNK-2`. This is a pure ordering assertion — no wall-clock involved. A
`select`-based non-blocking read with 200 ms timeout replaces the existing
`time.sleep` + blocking read pattern.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A) — N/A (scripts only)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A) — N/A
- [x] `/config` exposes no secrets (or N/A) — N/A
- [x] Path traversal rejected on filesystem access (or N/A) — N/A (scripts only)
- [x] CSS bump applied (or N/A) — N/A (no CSS changes)

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | `dev-deps-check.sh` exits 0 when all installed versions match pin file | `tests/python/test_dev_deps.py` | unit (subprocess) |
| T-2 | `dev-deps-check.sh` exits 1 when an installed version mismatches pin | `tests/python/test_dev_deps.py` | unit (subprocess) |
| T-3 | `dev-deps-check.sh` exits 2 when a package is absent from pin file | `tests/python/test_dev_deps.py` | unit (subprocess) |
| T-4 | `dev-deps-check.sh` exits 2 when `requirements-dev.txt` is missing | `tests/python/test_dev_deps.py` | unit (subprocess) |
| T-5 | `pre-commit.sh` exits 0 on clean staged Python + JS files | `tests/python/test_scripts.py` | unit (subprocess) |
| T-6 | `pre-commit.sh` exits 1 when staged Python file has syntax error | `tests/python/test_scripts.py` | unit (subprocess) |
| T-7 | `pre-commit.sh` exits 0 when `SKIP_GITLEAKS=1` (graceful secret-scan skip) | `tests/python/test_scripts.py` | unit (subprocess) |
| T-8 | `test_first_chunk_arrives_before_last` passes deterministically (no timing) | `tests/python/test_server_proxy.py` | integration |

**TDD order:** write T-1 through T-7 first (Red) → implement scripts (Green) →
refactor. T-8 is the hardened version of an existing test (replace, not add).

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — no user-facing changes (tooling only)
- [ ] `README.md` — add `make dev-setup` + `make hooks` to Getting Started dev-setup section
- [ ] `backlog.md` — check off #28 (pre-commit hook); add #40 (mutation audit visibility)
- [ ] `docs/rail-pipeline.md` — add dev-tooling version pins row to canonical tooling table
- [ ] `.clinerules/workflows/review.md` — add §6f dev-deps gate
- [ ] `.clinerules/workflows/loop.md` — update done-criteria + quick-reference

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Hash-pinning dev tools breaks `pip install -r requirements-dev.txt` on some pip versions | Use `pip install --require-hashes` explicitly in docs; CI uses a current pip — test with `pip>=22` |
| `dev-deps-check.sh` version parse breaks on multi-line `pip show` output | Use `grep '^Version:'` — this field is always a single line in pip's output format |
| Pre-commit hook blocks commit on slow machines (test discovery too broad) | Scope changed-file detection to staged files only; add 30 s timeout with `timeout 30` wrapper |
| `mutmut` fails on Python syntax patterns it doesn't recognise | `mutation-audit.sh` always exits 0; a mutmut parse error just means 0 mutations were attempted |
| Hardened timing test is still flaky if kernel scheduling reorders delivery | The new assertion is purely on byte offset in a single read buffer — not time-dependent |
| `pre-commit.sh` staged-file detection fails in a non-git context (e.g. tests) | Tests set `GIT_DIR` to a temp repo; `pre-commit.sh` falls back to full-suite if `git diff --cached` fails |
| `requirements-dev.txt` `--hash` format requires all deps in the file to be hashed (pip restriction) | Hash all four entries — `coverage`, `bandit`, `pip-audit`, `mutmut` — consistently |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90% line, ≥ 80% branch; JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] `./scripts/dev-deps-check.sh` exits 0 (all dev tools at pinned versions)
- [ ] Docs updated per §6 (CHANGELOG, backlog, README dev-setup, rail-pipeline.md table, workflow files)
- [ ] Acceptance criteria AC-1-a through AC-8 all verified
- [ ] Memory note written to `Cline/memories/`
