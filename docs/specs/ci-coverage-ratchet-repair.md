# Spec: CI Coverage Ratchet Repair

**Status:** In Progress
**Created:** 2026-09-19
**Author:** Cline/user

## 1. Goal & scope
Make GitHub Actions enforce the same coverage, frontend-test dependency, and
production-security contracts that pass locally. No coverage or security floor is
lowered, and no runtime dependency is added.

## 2. Acceptance criteria
- [ ] JavaScript CI installs the committed dev dependency set reproducibly.
- [ ] Python CI measures `backend` and finds `backend/server.py` in coverage JSON.
- [ ] CI and local security checks share recursive production-only Bandit scope.
- [ ] Untrusted DOCX XML declarations are rejected before stdlib parsing.
- [ ] All deterministic local gates and the replacement Actions run pass.

## 3. Affected files
- `.github/workflows/tests.yml` — align CI commands with local contracts.
- `scripts/security-scan.sh` — recursively scan production Python, excluding tests.
- `backend/file_parser.py` — reject unsafe XML declarations before parsing.
- `backend/tests/python/test_file_parser.py` — XML security regression test.
- `backend/tests/python/test_scripts.py` — canonical Bandit scope contract test.
- `.gitignore`, `package-lock.json` — commit reproducible dev dependency resolution.
- `CHANGELOG.md` — record the repair.

## 4. Technical approach
Use `npm ci`, explicit coverage `--source=backend`, and the shared strict security
script. Keep the dedicated gitleaks Action, then skip only that duplicate phase when
the shared script runs. Reject DTD/entity declarations before the narrowly suppressed
ElementTree call; no parser dependency is introduced.

## 5. Test plan
- Run the focused XML and security-script regression tests red, then green.
- Reproduce the corrected npm, coverage, and security commands locally.
- Run quality gate, full coverage suite, security scan, and doc consistency check.
- Push and verify all GitHub Actions jobs.

## 6. Docs to update
- [x] `CHANGELOG.md`
- [x] This bugfix spec
- [ ] Mark this spec Done after replacement Actions verification.

## 7. Risks / edge cases
- `npm ci` requires the lockfile to be tracked.
- Security findings in production code must be fixed, never hidden by excluding the
  whole backend or reducing Bandit's severity threshold.

## 8. Review checklist
- [ ] Implementation matches sections 3–5
- [ ] `./run-tests.sh --coverage` passes
- [ ] `./scripts/security-scan.sh` clean
- [ ] All four deterministic gates pass
- [ ] Replacement Actions run passes
- [ ] Memory note written