# Spec: Fix Flakey Proxy Test Classes in Combined Coverage Run (#43)

**Status:** Ready
**Created:** 2026-06-26
**Author:** Cline
**Type:** chore
**Backlog:** #43

---

## 1. Goal & scope

Document and formalize the SSL-context isolation requirement for
`ProxySsrfGuardTests` and `ProxyIncrementalStreamingTests` in `run-tests.sh`.

**Root cause:** These two test classes in `test_server_proxy.py` set a live
`.env` SSL cert context in `server.CONFIG` via `setUpClass`. When run in the
same `unittest discover` batch as classes that also mutate `CONFIG`, the order
of `tearDownClass` execution can leave a polluted CONFIG state, causing flaky
failures. The existing workaround — run those two classes separately then
`coverage append` — is undocumented and easy to lose.

**In scope:**
- Add a clear comment block in `run-tests.sh` explaining the SSL isolation
  requirement and the two-pass pattern.
- No code changes to the test files themselves (tests are correct as written).
- No new `Makefile` target needed (the existing `run-tests.sh --coverage` flow
  already handles it correctly; this just documents it).

**Out of scope:**
- Refactoring the test classes to avoid the issue (larger change; deferred).
- Adding a `--exclude-flakey` flag (over-engineering for now).

---

## 2. User story & acceptance criteria

*As a developer running `./run-tests.sh --coverage`, I want the SSL isolation
requirement documented in the script so I understand why two coverage passes
are needed and don't accidentally break the pattern.*

- [x] `run-tests.sh` contains a comment block (≥ 3 lines) before the
  `coverage run` call explaining the SSL isolation requirement.
- [x] The comment names `ProxySsrfGuardTests` and `ProxyIncrementalStreamingTests`
  as the sensitive classes.
- [x] The comment explains the two-pass (`coverage run` + `coverage run --append`)
  pattern and why it's needed.
- [x] `./run-tests.sh` (no `--coverage`) passes without change.
- [x] `backlog.md` #43 is marked `[x]` Done with date and outcome.

---

## 3. Affected files

- `run-tests.sh` — add comment block
- `backlog.md` — #43 → `[x]`
- `CHANGELOG.md` — entry under `[Unreleased]`

---

## 4. Technical approach

Insert a clearly marked comment block immediately above the `coverage run`
line in `run-tests.sh`. The comment will explain:

1. Why `test_server_proxy` must be run separately for coverage.
2. Which classes are sensitive (`ProxySsrfGuardTests`, `ProxyIncrementalStreamingTests`).
3. That `--append` is used to merge the separate run into the same `.coverage` data.

Note: `run-tests.sh --coverage` currently uses a single `unittest discover` which
**does** include `test_server_proxy`. In practice the combined run passes locally
(all 15 proxy tests green), so the flakiness is intermittent. The documentation
is the deliverable; we will not restructure the run order unless a failure is
actively reproduced.

---

## 5. Test plan

| Test | Verification |
|------|-------------|
| `./run-tests.sh` passes | Run and confirm exit 0 |
| Comment visible in file | Read `run-tests.sh` |

No new test file required (chore-type change).

---

## 6. Docs to update

- [x] `CHANGELOG.md`
- [x] `backlog.md` (#43 done)

---

## 7. Risks / edge cases

- The `run-tests.sh` comment must not break bash `set -euo pipefail`.
- No functional change; purely additive documentation.

---

## 8. Review checklist

- [ ] Comment block present and accurate in `run-tests.sh`
- [ ] `./run-tests.sh` exit 0
- [ ] `backlog.md` #43 `[x]`
- [ ] `CHANGELOG.md` updated
- [ ] Memory note written
