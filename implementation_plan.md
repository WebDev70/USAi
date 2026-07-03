# Implementation Plan: RAIL Pipeline Gap Closure — All Five Dimensions

[Overview]
Close every identified gap in the RAIL pipeline across Agile/Scrum, DevSecOps, IaC, TDD, and CI/CD.

This plan addresses the full-breadth gap analysis of the USAi Chat RAIL pipeline conducted on 2026-07-02. The RAIL pipeline is mature (11 hardening phases shipped, Governance Board in place, CI exists) but has concrete gaps in five areas that leave some quality/security assertions as honor-system or local-only rather than machine-enforced in CI.

**Scope:** Dev/CI tooling only — no changes to runtime `requirements.txt` or shipped `app.js`/`server.py` beyond new Python stdlib test assertions. Every new gate has a local `make` target so CI ≡ Makefile parity is maintained. The implementation is organised into five phases; each phase is independently shippable.

**Phases:**
- Phase 1 (CI/CD): Ratchet gate in CI, Dependabot, CodeQL, Docker build job, pre-commit parity job, branch-protection doc.
- Phase 2 (DevSecOps): `.gitleaks.toml` pin, Trivy image scan job, SBOM generation, `security-scan.sh` SSRF/secrets-baseline extension, new `tests/python/test_security_posture.py`.
- Phase 3 (IaC): `tests/python/test_iac.py` (non-root, HEALTHCHECK, compose parse, Makefile↔CI parity), `make ratchet` / `make sbom` / `make mutation` targets.
- Phase 4 (TDD): `scripts/tdd-red-check.sh` (machine-proof Red receipt artifact), mutation gate promoted to scheduled CI job with survivor-budget threshold.
- Phase 5 (Agile/Scrum): `scripts/scrum-metrics.py` (velocity+WIP burndown report), `sprint-10.md` retroactive creation, sprint-open-at-start discipline in `.clinerules`, DoR story-point rubric.

**Hard constraints honored throughout:**
- No new runtime dependencies (stdlib Python + `python-dotenv` only in shipped app).
- Dev/CI tooling (coverage, bandit, pip-audit, gitleaks, Trivy, syft, CodeQL) ships nothing into the app.
- All gates have `make` entry points.
- Comments explain *why*.
- CHANGELOG updated, docs in sync, backlog updated in same turn.

---

[Types]
No new application data types; new CI/test configuration structures, a scrum metrics report schema, and a gitleaks TOML configuration.

**Scrum Metrics Report (output of `scripts/scrum-metrics.py`):**
```
{
  "sprint": "NN",
  "velocity": int,           # items completed this sprint
  "cumulative_velocity": int, # total items completed all sprints
  "backlog_open": int,        # items with [ ]
  "backlog_in_progress": int, # items with [~]
  "backlog_done": int,        # items with [x]
  "wip_count": int,           # current [~] items (WIP limit check)
  "wip_limit": int,           # configurable, default 3
  "wip_ok": bool,
  "burndown": [               # per-sprint cumulative completion counts
    {"sprint": "NN", "done": int}
  ]
}
```

**`.gitleaks.toml` config structure:** Standard TOML gitleaks config with `[[rules]]` overrides for known false-positive patterns in USAi (e.g. test fixture keys), `[allowlist]` regexes.

**`test_iac.py` assertion targets:**
```python
# Assertions verified by these test IDs:
# IaC-1: Dockerfile contains "USER" instruction (non-root)
# IaC-2: Dockerfile contains "HEALTHCHECK" instruction
# IaC-3: docker-compose.yml parses as valid YAML
# IaC-4: Makefile 'check' target contains same commands as CI tests.yml jobs
# IaC-5: Makefile 'scan' target references security-scan.sh
# IaC-6: .env.example keys == load_config() expected keys (existing, reconfirm)
```

---

[Files]
New and modified files across CI config, scripts, tests, and documentation.

**NEW FILES:**
- `.github/workflows/codeql.yml` — GitHub CodeQL analysis (JS + Python), triggers on push/PR/schedule.
- `.github/workflows/sbom.yml` — SBOM generation via `anchore/sbom-action`, uploads as workflow artifact.
- `.github/dependabot.yml` — Automated dependency update PRs for pip + github-actions ecosystems.
- `.gitleaks.toml` — Deterministic gitleaks ruleset with USAi-specific allowlist; replaces implicit default.
- `docs/ci-cd.md` — CI/CD contract doc: describes all jobs, required branch-protection settings, local equivalents.
- `docs/specs/rail-gap-closure.md` — Spec document for this implementation (Status: In Progress).
- `scripts/tdd-red-check.sh` — Verifies a TDD Red receipt artifact exists for the current change (git-diff based).
- `scripts/scrum-metrics.py` — Parses `backlog.md` + sprint-index.md → emits velocity/WIP/burndown JSON + Markdown report.
- `tests/python/test_iac.py` — Deterministic IaC assertions (non-root, HEALTHCHECK, compose YAML, Makefile↔CI parity).
- `tests/python/test_security_posture.py` — SSRF allowlist, `/config` redaction invariant, and path-traversal pattern assertions (stdlib only).
- `"/Users/ronaldbblake/Documents/Obsidian Vault/Cline/scrum/sprints/sprint-10.md"` — Retroactive sprint-10 note (ADVISORY-02 fix).

**MODIFIED FILES:**
- `.github/workflows/tests.yml` — Add `ratchet` job (bash 4+ image, runs `scripts/ratchet-check.sh`), `docker-build` job, `pre-commit-parity` job. Add `needs:` dependency chain so `ratchet` only runs after python gate passes.
- `scripts/security-scan.sh` — Add SSRF allowlist assertion block (step 5/5) and secrets-baseline re-scan of `Cline/memories/` (already partially present; extend). Add Trivy call when `trivy` binary is available (local); CI Trivy runs in separate job.
- `Makefile` — Add `make ratchet`, `make sbom`, `make mutation`, `make scrum-metrics`, `make iac-test` targets. Update `make check` to include `make iac-test`.
- `docs/rail-pipeline.md` — §4 CI section: describe all new jobs, remove "pre-commit is future backlog #28" note (now done), add CodeQL/SBOM/Trivy references.
- `docs/governance.md` — SE rubric (§3): add mutation kill-rate + Trivy scan as SE-4 checks. SPMS rubric (§4): add scrum-metrics report as SPMS-2 check.
- `docs/principles.md` — §2 DevSecOps: add Trivy/SBOM to the deterministic gates list.
- `.clinerules/scrum-artifacts.md` — Add "On sprint start" step 0: create sprint note BEFORE first `/build` commit; reference `scrum-metrics.py` for velocity calculation.
- `.clinerules/workflows/spec.md` — Add step to open sprint note at sprint start (INNOV-01 fix).
- `"/Users/ronaldbblake/Documents/Obsidian Vault/Cline/scrum/definition-of-ready.md"` — Add story-point estimation rubric (S=0.5d, M=1-2d, L=3-5d) + WIP limit check (≤3 concurrent `[~]` items before pulling new item).
- `backlog.md` — Add new backlog items for each shipped phase, mark this spec as [~] In Progress.
- `CHANGELOG.md` — Entry under `[Unreleased]` for each phase as it ships.

---

[Functions]
New scripts and Python functions; no changes to shipped `server.py` or `app.js`.

**NEW FUNCTIONS/SCRIPTS:**

`scripts/tdd-red-check.sh`:
```bash
tdd_red_check()   # Main: checks git diff for test file added/modified BEFORE implementation;
                  # emits a TDD-Red-Receipt artifact to /tmp/usai-tdd-red-receipt-<feature>
                  # Returns 0 if receipt found, 1 if not (advisory in CI, blocking in /build)
```

`scripts/scrum-metrics.py`:
```python
parse_backlog(path: str) -> dict         # Parses backlog.md, counts [ ] / [~] / [x] items per section
parse_sprint_index(path: str) -> list    # Parses sprint-index.md velocity column
compute_burndown(sprints: list) -> list  # Cumulative completion per sprint
check_wip_limit(in_progress: int, limit: int) -> bool
emit_report(metrics: dict, output_path: str) -> None   # Writes JSON + Markdown report
main()   # Entry point: reads OBSIDIAN_VAULT_PATH from env or default
```

`tests/python/test_iac.py`:
```python
class TestDockerfileIaC(unittest.TestCase):
    test_non_root()      # IaC-1: USER instruction present
    test_healthcheck()   # IaC-2: HEALTHCHECK instruction present

class TestComposeIaC(unittest.TestCase):
    test_compose_parses() # IaC-3: docker-compose.yml valid YAML

class TestMakefileCI_Parity(unittest.TestCase):
    test_check_target_has_runtests()  # IaC-4: 'make check' references run-tests.sh
    test_scan_target_has_security_sh() # IaC-5: 'make scan' references security-scan.sh
    test_ci_jobs_match_makefile()     # IaC-6: tests.yml job steps reference same commands
```

`tests/python/test_security_posture.py`:
```python
class TestSSRFGuard(unittest.TestCase):
    test_safe_urls_pass()           # SP-1: known safe HTTPS upstreams pass is_safe_upstream_url
    test_localhost_blocked()        # SP-2: 127.0.0.1 / localhost blocked
    test_private_ranges_blocked()   # SP-3: RFC-1918 ranges blocked (10.x, 192.168.x, 172.16-31.x)
    test_file_scheme_blocked()      # SP-4: file:// scheme blocked
    test_metadata_endpoint_blocked()# SP-5: 169.254.169.254 AWS metadata endpoint blocked

class TestConfigRedaction(unittest.TestCase):
    test_api_key_not_in_config()    # SP-6: /config response must not contain API key value
    test_has_flags_present()        # SP-7: has_* boolean flags present in /config

class TestPathTraversalGuard(unittest.TestCase):
    test_dotdot_rejected()          # SP-8: ../.. sequences rejected by get_memory_dir
    test_null_byte_rejected()       # SP-9: null bytes rejected
    test_absolute_path_rejected()   # SP-10: absolute paths rejected for memory filenames
```

**MODIFIED FUNCTIONS:**

`scripts/security-scan.sh` — `run_security_scan()`:
- Add step 5: SSRF self-test (`grep is_safe_upstream_url server.py` confirms guard present)
- Add step 6 (conditional): `trivy fs . --exit-code 1 --severity HIGH,CRITICAL` when `command -v trivy` succeeds locally

`Makefile` — new targets:
- `ratchet:` → `./scripts/ratchet-check.sh`
- `sbom:` → `(syft . -o spdx-json > sbom.spdx.json 2>/dev/null || echo "sbom: syft not installed locally — runs in CI")`
- `mutation:` → `./scripts/mutation-audit.sh`
- `scrum-metrics:` → `.venv/bin/python scripts/scrum-metrics.py`
- `iac-test:` → `.venv/bin/python -m unittest tests/python/test_iac.py tests/python/test_security_posture.py -v`

---

[Classes]
No new classes in the shipped application; all new test files use `unittest.TestCase` subclasses.

**NEW TEST CLASSES:**
- `TestDockerfileIaC(unittest.TestCase)` — in `tests/python/test_iac.py`
- `TestComposeIaC(unittest.TestCase)` — in `tests/python/test_iac.py`
- `TestMakefileCI_Parity(unittest.TestCase)` — in `tests/python/test_iac.py`
- `TestSSRFGuard(unittest.TestCase)` — in `tests/python/test_security_posture.py`
  - Note: imports `is_safe_upstream_url` from `server` via the existing `sys.path` + `importlib` pattern used in other test files.
- `TestConfigRedaction(unittest.TestCase)` — in `tests/python/test_security_posture.py`
  - Boots a test server instance (same pattern as `test_server_http.py`).
- `TestPathTraversalGuard(unittest.TestCase)` — in `tests/python/test_security_posture.py`
  - Imports `get_memory_dir` from `server`.

**MODIFIED CLASSES:** None — existing test classes in `test_server.py`, `test_server_http.py` etc. are not touched unless a regression is introduced.

---

[Dependencies]
No new runtime dependencies; new CI-only tooling added to GitHub Actions workflows only.

**CI/GitHub Actions NEW tooling (dev/CI only — never shipped):**
- `github/codeql-action@v3` — GitHub-native CodeQL; no install step; free for public repos.
- `anchore/sbom-action@v0` — SBOM generation as a workflow step; artifact upload only.
- `aquasecurity/trivy-action@master` — Trivy filesystem + image CVE scan in CI.
- `dependabot` (`.github/dependabot.yml`) — GitHub-native; no package install.

**Local tooling (optional, for `make sbom` locally):**
- `syft` — can be installed locally via `brew install syft` or the install script; not required; `make sbom` gracefully skips if absent.
- `trivy` — can be installed locally; `security-scan.sh` Trivy step is conditional on `command -v trivy`.

**Existing dev deps already in place (no changes needed):**
- `coverage`, `bandit`, `pip-audit`, `gitleaks`, `node --test` — all already wired.

**`requirements-dev.txt`** — no changes; Trivy/syft/CodeQL are CI-job level tooling, not pip packages.

---

[Testing]
New test files enforce IaC and security posture deterministically; new CI jobs gate ratchet, Docker build, and pre-commit in automation.

**New test files (run by `./run-tests.sh` and CI):**
- `tests/python/test_iac.py` — 6 tests (IaC-1 through IaC-6). Run by: `make iac-test`, `make check`, CI `python` job (matrix 3.9+3.11).
- `tests/python/test_security_posture.py` — 10 tests (SP-1 through SP-10). Run by: `make iac-test`, `make check`, CI `python` job.

**`run-tests.sh` update:** Add `test_iac.py` and `test_security_posture.py` to the `unittest discover` call so they are included in the full suite automatically.

**New CI jobs (`.github/workflows/tests.yml` additions):**
- `ratchet` job: `runs-on: ubuntu-latest`, installs `bash 5` via `apt`, runs `./scripts/ratchet-check.sh`. `needs: [python]` so it only runs after the coverage gate passes.
- `docker-build` job: `runs-on: ubuntu-latest`, runs `docker build -t usai-test .` + `docker compose config` + (optional) `docker run --rm usai-test python -c "import server"` smoke test.
- `pre-commit-parity` job: `runs-on: ubuntu-latest`, installs python-dotenv, runs `./scripts/pre-commit.sh` to confirm the hook script works in CI.

**New CI workflows:**
- `.github/workflows/codeql.yml` — CodeQL for JS + Python. Scheduled weekly + on push/PR. Uses `github/codeql-action/init`, `autobuild`, `analyze`. Non-blocking-by-default (advisory) unless a HIGH/CRITICAL finding is detected.
- `.github/workflows/sbom.yml` — SBOM. Runs on push to main only. Artifact upload. Not blocking.

**Scrum metrics validation:**
- `scripts/scrum-metrics.py` includes a `--selftest` flag that parses a fixture backlog (inline string) and asserts correct velocity/WIP counts — runnable in CI via `make scrum-metrics -- --selftest`.

**Mutation testing promotion:**
- `.github/workflows/mutation.yml` (new) — scheduled weekly (`cron: '0 3 * * 1'`), runs `./scripts/mutation-audit.sh`, posts kill-rate to workflow summary. Non-blocking unless kill rate < 50% (configurable threshold).

---

[Implementation Order]
Phases are sequenced to keep every gate green at each merge; each phase is independently reviewable.

**Phase 1 — CI/CD Foundation (S, ~1 sprint)**
1. Add `.github/dependabot.yml` (pip + github-actions; XS, zero-risk).
2. Add `docker-build` CI job to `tests.yml` (validates Dockerfile + compose config).
3. Add `ratchet` CI job to `tests.yml` (closes `#39` intentional skip; needs bash 5 image).
4. Add `pre-commit-parity` CI job to `tests.yml`.
5. Add `.gitleaks.toml` config file (pins gitleaks ruleset, adds USAi allowlist).
6. Write `docs/ci-cd.md` (branch-protection contract, job descriptions, local equivalents).
7. Update `docs/rail-pipeline.md` §4, remove backlog #28 "future" note, add Dependabot/CodeQL references.

**Phase 2 — DevSecOps Hardening (M)**
8. Write `tests/python/test_security_posture.py` (TDD: write tests first, confirm red, then adjust server.py imports as needed).
9. Add `test_security_posture.py` to `run-tests.sh` discover path.
10. Extend `scripts/security-scan.sh` with SSRF guard assertion (step 5) and conditional Trivy (step 6).
11. Add `.github/workflows/codeql.yml`.
12. Add `.github/workflows/sbom.yml`.
13. Add `make sbom` target to Makefile.
14. Update `docs/principles.md` §2 with Trivy/SBOM.
15. Update `docs/governance.md` SE rubric to reference new gates.

**Phase 3 — IaC Test Coverage (S)**
16. Write `tests/python/test_iac.py` (TDD: Red first, confirm Dockerfile/compose assertions fail or pass as expected).
17. Add `make iac-test` and `make ratchet` to Makefile.
18. Add IaC tests to `run-tests.sh`.
19. Update `docker-compose.yml` or `Dockerfile` if non-root / HEALTHCHECK assertions fail (fix the code, not the test).

**Phase 4 — TDD Enforcement (S)**
20. Write `scripts/tdd-red-check.sh` (machine-proof Red receipt).
21. Add reference to `tdd-red-check.sh` in `.clinerules/workflows/build.md` Role 3 / TDD Red section.
22. Add `.github/workflows/mutation.yml` (weekly scheduled, non-blocking, kill-rate report).
23. Add `make mutation` target to Makefile (already references `mutation-audit.sh`).
24. Update `docs/rail-pipeline.md` to describe mutation as "scheduled CI gate" not "optional cadence".

**Phase 5 — Agile/Scrum Discipline (S)**
25. Create `"/Users/ronaldbblake/Documents/Obsidian Vault/Cline/scrum/sprints/sprint-10.md"` retroactively (ADVISORY-02 fix).
26. Write `scripts/scrum-metrics.py` with `--selftest` mode.
27. Add `make scrum-metrics` to Makefile.
28. Update `.clinerules/scrum-artifacts.md` — add "open sprint note at sprint start" as Step 0 in "On sprint start".
29. Update `.clinerules/workflows/spec.md` — add sprint-note-open reminder (INNOV-01 fix).
30. Update `"/Users/ronaldbblake/Documents/Obsidian Vault/Cline/scrum/definition-of-ready.md"` — add size/estimation rubric + WIP limit gate.
31. Update `docs/governance.md` SPMS rubric to reference scrum-metrics report.

**Phase 6 — Documentation & Backlog Close-out (XS)**
32. Add all new backlog items to `backlog.md`, mark spec [~] → [x] Done.
33. Write Cline memory note.
34. Update `CHANGELOG.md [Unreleased]`.

---

## Plan Navigation Commands

```bash
# Read Overview section
sed -n '/\[Overview\]/,/\[Types\]/p' implementation_plan.md | cat

# Read Types section
sed -n '/\[Types\]/,/\[Files\]/p' implementation_plan.md | cat

# Read Files section
sed -n '/\[Files\]/,/\[Functions\]/p' implementation_plan.md | cat

# Read Functions section
sed -n '/\[Functions\]/,/\[Classes\]/p' implementation_plan.md | cat

# Read Classes section
sed -n '/\[Classes\]/,/\[Dependencies\]/p' implementation_plan.md | cat

# Read Dependencies section
sed -n '/\[Dependencies\]/,/\[Testing\]/p' implementation_plan.md | cat

# Read Testing section
sed -n '/\[Testing\]/,/\[Implementation Order\]/p' implementation_plan.md | cat

# Read Implementation Order section
sed -n '/\[Implementation Order\]/,$p' implementation_plan.md | cat
```
