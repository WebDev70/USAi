# Spec: Coverage Threshold Ratchet

**Status:** Done
**Created:** 2026-09-19
**Author:** Cline
**Type:** chore / test tooling

## 1. Goal & scope

Raise the committed coverage high-water marks to the reproducible coverage verified
after backlog item #76(a), and make future unclaimed coverage headroom visible without
making the reminder itself a build failure.

In scope: `.coverage-thresholds`, the ratchet script, its Python regression tests,
and lifecycle documentation. Out of scope: adding application tests solely to increase
coverage, changing coverage measurement, or adding dependencies.

## 2. User story & acceptance criteria

As a maintainer, I want coverage floors close to verified coverage and excess headroom
reported automatically so regressions cannot hide inside a stale threshold.

- [x] `.coverage-thresholds` records `python_line=90`, `python_branch=90`, and `js_branch=75`.
- [x] `scripts/ratchet-check.sh` prints a per-metric advisory when live coverage is at least 5 percentage points above its threshold.
- [x] An advisory does not change a successful exit status; coverage below threshold still fails.
- [x] `./run-tests.sh --coverage` passes with current verified coverage.
- [x] Required quality, security, and documentation gates pass.

## 3. Affected files

- `.coverage-thresholds` — raise Python-branch and JS-branch floors.
- `run-tests.sh` — align the directly enforced branch floors with the ratchet values.
- `.github/workflows/tests.yml` — align CI's directly enforced branch floors.
- `scripts/ratchet-check.sh` — add non-failing excessive-headroom advisory.
- `backend/tests/python/test_scripts.py` — pin committed values and advisory behavior.
- `docs/specs/coverage-ratchet.md` — implementation contract and review evidence.
- `backlog.md` — transition #74 through its lifecycle.
- `CHANGELOG.md` — record the tooling change.
- `Cline/scrum/product-backlog.md` — mirror #74 status (Obsidian vault).

## 4. Technical approach

Keep the existing Bash 3.2-compatible implementation. After a metric passes its floor,
calculate `live - threshold` with `awk`; at headroom `>= 5`, print an `ADVISORY` naming
the metric, headroom, and ratcheting action. Do not increment the existing error count.
The existing below-threshold path remains unchanged and authoritative.

No runtime dependencies, application endpoints, SSRF surfaces, paths, or CSS are affected.

## 5. Test plan

| Test | File | Description |
|------|------|-------------|
| Threshold consistency | `backend/tests/python/test_scripts.py` | Assert the committed file, local runner, and CI use the approved floors. |
| Excess-headroom advisory | `backend/tests/python/test_scripts.py` | At exactly 5 points, output names the metric and recommends ratcheting while exiting 0. |
| Below-advisory boundary | `backend/tests/python/test_scripts.py` | At 4.99 points, no advisory is printed and exit remains 0. |
| Existing failure tests | `backend/tests/python/test_scripts.py` | Confirm below-threshold metrics still exit non-zero. |

## 6. Docs to update

- [x] `CHANGELOG.md`
- [x] `docs/USER_GUIDE.md` not applicable (developer tooling only)
- [x] `README.md` not applicable (no setup/config change)
- [x] `backlog.md` (marked done after all gates passed)

## 7. Risks / edge cases

- The boundary is inclusive: exactly 5.00 points must advise.
- Decimal coverage values must compare correctly under the existing `awk` approach.
- The advisory must never mask or soften a below-threshold failure.
- Thresholds must not exceed the clean-checkout measurements: 90% Python lines,
  92.31% Python branches, and 75.19% JS branches.

## 8. Review checklist (filled by Reviewer role)

- [x] Implementation matches spec sections 3–5
- [x] `./scripts/quality-gate.sh` passes (exit 0)
- [x] `./run-tests.sh --coverage` passes (exit 0; 435 Python tests; 90% aggregate Python lines; `server.py` branch 92.31%; JS branch 75.19%)
- [x] `./scripts/security-scan.sh` passes (exit 0; gitleaks unavailable and explicitly skipped)
- [x] `./scripts/doc-consistency-check.sh` passes (exit 0)
- [x] Docs and backlog lifecycle updated
- [x] Memory note written