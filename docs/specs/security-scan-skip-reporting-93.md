# Spec: Stop security-scan.sh skips from reporting "passed"

**Status:** Done
**Type:** bugfix
**Created:** 2026-09-20
**Author:** Cline (RAIL Role 0 skipped — bugfix; Role 1 Code Planner)
**Backlog:** #93 — 📋 ADVISORY — stop security-scan skips reading as passes *(XS)*

> **Prior-context recall:** Searched `Cline/memories/`, `Continue Extension/memories/`, `USAi/memories/`. MCP server timed out; used direct filesystem access. Found Sprint 19 governance ADVISORY-05/06 (3rd sighting). Root cause confirmed: `SKIP_*` env vars and the vault self-skip do not prevent exit 0 or the "passed" message. Prevention-rule recall: Entry 010 (redaction), Entry 011 (execute-controls).

## 1. Goal & scope

**Goal:** Modify `scripts/security-scan.sh` so that its exit code and summary message accurately reflect when scanners have been skipped. A scan with skipped components must not report "all scanners passed" or exit with a simple success code that could be misinterpreted as a complete, clean run. Contributors and reviewers must be able to distinguish a complete, clean scan from a partial one.

**In scope**
- `scripts/security-scan.sh`: The core logic for tracking skipped scanners and adjusting exit code and summary messages.
- `backend/tests/python/test_scripts.py`: A new regression test class for `security-scan.sh` to assert the correct behavior for all skip combinations.
- `.github/workflows/tests.yml`: Adjust the CI invocation which currently uses `SKIP_GITLEAKS=1` with `--strict`.
- `CHANGELOG.md`: Entry for the fix.
- `backlog.md` & `Cline/scrum/product-backlog.md`: Update item status.

**Out of scope**
- No new scanners or dependencies.
- No changes to the secrets themselves or the patterns gitleaks uses.
- No changes to the UI or runtime application behavior.
- No changes to the separate, dedicated gitleaks GitHub Action.


## 2. User story & acceptance criteria

> As a **developer or reviewer**, I want `security-scan.sh` to **fail unambiguously** when run in `--strict` mode with any scanner skipped, and to report a **clear "partial run" status** in lenient mode, so that I am never misled into thinking a partial scan was a complete and successful one.

- [ ] **AC-1 (Strict Mode):** If `--strict` is passed, the script MUST exit with a non-zero status code if any of the four scanner blocks (gitleaks, bandit, pip-audit, vault-secrets) are skipped, either due to a `SKIP_*` environment variable or a missing tool/path.
- [ ] **AC-2 (Lenient Mode - Summary):** In default (lenient) mode, if any scanner block is skipped, the final summary message MUST NOT contain the word "passed". It should clearly state that the run was partial (e.g., "Scan incomplete: 3/4 scanners run, 0 findings.").
- [ ] **AC-3 (Lenient Mode - Exit Code):** In default (lenient) mode, if any scanner block is skipped but no findings are reported by the scanners that did run, the script MUST exit with status `0`.
- [ ] **AC-4 (Full Success):** The summary message "All scanners passed" and exit code `0` are produced ONLY when all four scanner blocks run, and none report any findings.
- [ ] **AC-5 (CI Workflow):** The `tests.yml` CI workflow invocation of `security-scan.sh` is updated to handle the new skip logic correctly without failing the build unnecessarily (e.g., by removing `--strict` if `SKIP_GITLEAKS` is set).
- [ ] **AC-6 (Hermetic Redaction Test):** A new test in `test_scripts.py` MUST plant a fake secret, run the vault-secrets scan block, and assert that the script exits non-zero AND the fake secret does NOT appear in stdout or stderr, preserving the G-4 redaction guarantee.

## 3. Architectural approach

The script will introduce a new state variable, `SKIPPED_COUNT`, initialized to 0. Each of the four main scan blocks will be instrumented:
1.  **Gitleaks:** The existing `SKIP_GITLEAKS` check will increment `SKIPPED_COUNT`. The check for the `gitleaks` binary will also increment it.
2.  **Bandit:** A new `SKIP_BANDIT` check will be added. The check for the `bandit` binary will increment `SKIPPED_COUNT`.
3.  **pip-audit:** A new `SKIP_PIP_AUDIT` check will be added. The check for the `pip-audit` binary will increment `SKIPPED_COUNT`.
4.  **Vault secrets:** The existing check for `OBSIDIAN_VAULT_PATH` will increment `SKIPPED_COUNT`.

The final reporting logic will be modified:
- An aggregate `FINAL_RC` will hold the highest exit code from the scanners that ran.
- If `SKIPPED_COUNT > 0`:
    - If `--strict` is present, `FINAL_RC` will be set to `1` (or a specific error code).
    - The summary message will be updated to reflect a partial run.
- If `SKIPPED_COUNT == 0` and `FINAL_RC == 0`, the success message is printed.

## 4. Test plan

| Test | File | Description |
|------|------|-------------|
| SS-1 | `backend/tests/python/test_scripts.py` | No skips, no findings -> exit 0, "All scanners passed". |
| SS-2 | `backend/tests/python/test_scripts.py` | `SKIP_GITLEAKS=1`, no other findings -> lenient exit 0, "Scan incomplete"; strict exit > 0. |
| SS-3 | `backend/tests/python/test_scripts.py` | `SKIP_BANDIT=1`, no other findings -> lenient exit 0, "Scan incomplete"; strict exit > 0. |
| SS-4 | `backend/tests/python/test_scripts.py` | `SKIP_PIP_AUDIT=1`, no other findings -> lenient exit 0, "Scan incomplete"; strict exit > 0. |
| SS-5 | `backend/tests/python/test_scripts.py` | No `OBSIDIAN_VAULT_PATH`, no other findings -> lenient exit 0, "Scan incomplete"; strict exit > 0. |
| SS-6 | `backend/tests/python/test_scripts.py` | Multiple skips -> lenient exit 0, "Scan incomplete"; strict exit > 0. |
| SS-7 | `backend/tests/python/test_scripts.py` | One finding, one skip -> lenient exit > 0; strict exit > 0. |
| SS-8 | `backend/tests/python/test_scripts.py` | **Hermetic Redaction Test (AC-6):** Planted vault secret is detected (non-zero exit) but not printed. |

## 5. Docs to update
- [ ] CHANGELOG.md
- [ ] backlog.md
- [ ] Cline/scrum/product-backlog.md

## 6. Risks / edge cases
- **CI disruption:** The change to `--strict` behavior is a breaking change for the CI pipeline. The spec explicitly calls out modifying the workflow file to account for this.
- **Error code semantics:** Using a simple `1` for strict-mode failures is sufficient. No need for complex, distinct error codes for each skipped scanner.

## 7. Review checklist (filled by `/review`)
- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §5
- [x] Acceptance criteria AC-1…AC-6 all verified
- [x] Memory note written to `Cline/memories/`
