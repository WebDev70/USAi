# Spec: Memory-Note Secret Scan False Positives (#72)

**Status:** Done
**Type:** bugfix
**Created:** 2026-09-17
**Completed:** 2026-09-17
**Author:** Cline
**Prior context:** Sprint 16 found check 4/4 matched checklist prose; direct inspection also confirmed `sk-` matches benign `task-…` identifiers.

## 1. Goal & scope

Make the Cline-memory secret scan detect secret-shaped values rather than harmless prose or identifier substrings, so the enforced gate is usable without reducing its scope.

### Out of scope
- Scanning other vault subdirectories.
- Adding runtime dependencies or changing gitleaks, Bandit, or pip-audit.

## 2. User story & acceptance criteria

As a contributor, I want the memory-note secret scan to reject real secret-shaped values without flagging safety-checklist prose, so I can trust a clean security result.

- [x] AC-1: Checklist prose and benign `task-…` identifiers pass check 4/4.
- [x] AC-2: Standalone long `sk-…`, Bearer, `api_key=`, and `password=` values fail check 4/4.
- [x] AC-3: A finding reports only its filename and line number, never its value.
- [x] AC-4: The real Cline memory directory passes unchanged with the vault path exported.

## 3. Affected files

| File | Change |
|------|--------|
| `scripts/security-scan.sh` | Tighten portable secret patterns and redact finding output. |
| `backend/tests/python/test_scripts.py` | Add hermetic regression tests for false positives and true positives. |
| `.clinerules/workflows/housekeep.md` | Delegate duplicate scan guidance to canonical check 4/4. |
| `CHANGELOG.md` | Record #72 fix. |
| `backlog.md` | Track #72 completion. |

## 4. Technical approach

Use Bash 3.2/BSD-grep-compatible extended regexes with token boundaries and minimum value lengths. Keep the `Cline/memories/*.md` scope. Capture `grep -n` output internally and emit only `path:line: [REDACTED]` on failure.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] Secret values are never logged
- [x] CSS / endpoint / tool / path-traversal conventions are N/A

## 4b. Shift-left governance findings

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | Each AC has a hermetic or real-vault assertion. |
| G-2 Scope / value | ✅ Pass | Limited to canonical scan and duplicate workflow guidance. |
| G-3 Dependency coherence | ✅ Pass | No prerequisites. |

## 5. Test plan

| # | Test description | File | Type |
|---|------------------|------|------|
| T-8d | Checklist prose and `task-…` pass | `backend/tests/python/test_scripts.py` | regression |
| T-8e | Four secret-shaped value families fail | `backend/tests/python/test_scripts.py` | regression |
| T-8f | Failure output omits detected value | `backend/tests/python/test_scripts.py` | security |

**TDD order:** tests first (Red), implementation second (Green).

## 6. Docs to update

- [x] `CHANGELOG.md`
- [x] `backlog.md`
- [x] `Cline/scrum/product-backlog.md`
- [x] Cline session memory

## 7. Risks & edge cases

| Risk | Mitigation |
|------|------------|
| Regex is too permissive | Require boundaries and meaningful minimum lengths; test each family. |
| Regex portability drift | Use POSIX ERE supported by macOS BSD grep and Bash 3.2. |
| Secret leakage in diagnostic output | Redact value in all scanner finding output. |

## 8. Review checklist

- [x] Implementation matches §3–5
- [x] `./run-tests.sh --coverage` passes
- [x] `./scripts/security-scan.sh` clean
- [x] Docs and lifecycle records updated
- [x] Memory note written
