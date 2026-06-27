# Spec: Pre-commit Git Hook (#28)

**Status:** Done
**Created:** 2026-06-27
**Author:** Cline

## 1. Goal & scope

Wire the existing `scripts/pre-commit.sh` into the project so developers can
install it as a `.git/hooks/pre-commit` hook with a single `make hooks` command.
Document the install step and optional `SKIP_GITLEAKS` escape hatch. Add regression
tests so CI catches any future breakage of the script's exit-code contract.

**Out of scope:**
- Running unit tests inside the hook (syntax gates only — fast and dependency-free).
- Windows `pre-commit.exe` wrapper (macOS/Linux only).
- Adding gitleaks as a hard gate in CI (it is already in `security-scan.sh`).

## 2. User story & acceptance criteria

As a developer, I want `make hooks` to install a git pre-commit hook so that
syntax errors and accidental secrets are caught locally before I push.

- [x] AC-1: `make hooks` symlinks `.git/hooks/pre-commit` → `scripts/pre-commit.sh`
  and marks it executable; running it twice is idempotent.
- [x] AC-2: A staged `.py` file with a syntax error causes the hook to exit 1
  and print an `✕` line.
- [x] AC-3: A staged `.js` file with a syntax error causes the hook to exit 1
  and print an `✕` line.
- [x] AC-4: Clean staged `.py` and `.js` files → hook exits 0.
- [x] AC-5: Non-`.py`/`.js` staged files (e.g. `.md`) are silently ignored → exit 0.
- [x] AC-6: `SKIP_GITLEAKS=1` suppresses the gitleaks step (no error even when
  gitleaks is absent).
- [x] AC-7: `README.md` has a **Git hooks** section documenting `make hooks` and
  the `SKIP_GITLEAKS` escape.
- [x] AC-8: `AGENTS.md` references `make hooks` under developer setup.
- [x] AC-9: `CHANGELOG.md` has a `[Unreleased]` entry for #28.
- [x] AC-10: `backlog.md` item #28 is flipped `[ ]` → `[x]` with Done date.

## 3. Affected files

- `Makefile` — add `hooks` target (+ `.PHONY`)
- `README.md` — add Git hooks section
- `AGENTS.md` — one-line mention under developer setup
- `CHANGELOG.md` — `[Unreleased]` entry
- `backlog.md` — mark #28 done
- `tests/python/test_pre_commit.py` — new regression tests (AC-1 … AC-6)
- `docs/specs/pre-commit-hook.md` — this file

## 4. Technical approach

`scripts/pre-commit.sh` already exists and is well-tested manually. It honours:
- `GIT_WORK_TREE` / `GIT_DIR` env vars (test-harness override).
- `SKIP_GITLEAKS` env var (set in all tests to avoid gitleaks dependency).

The `make hooks` target:
```makefile
hooks: ## Install git hooks (symlinks .git/hooks/pre-commit → scripts/pre-commit.sh)
	@mkdir -p .git/hooks
	@ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✓ pre-commit hook installed (.git/hooks/pre-commit → scripts/pre-commit.sh)"
```

The relative symlink `../../scripts/pre-commit.sh` resolves correctly from inside
`.git/hooks/` regardless of the working directory when the hook fires.

Tests use `subprocess` + `tempfile` + a temporary bare git repo (same pattern as
`test_dev_deps.py`), setting `GIT_DIR`, `GIT_WORK_TREE`, and `SKIP_GITLEAKS=1`.

## 5. Test plan

| Test ID | File | Description |
|---------|------|-------------|
| PC-1 | tests/python/test_pre_commit.py | Clean staged .py → exit 0 |
| PC-2 | tests/python/test_pre_commit.py | Staged .py with syntax error → exit 1 |
| PC-3 | tests/python/test_pre_commit.py | Staged .js with syntax error → exit 1 |
| PC-4 | tests/python/test_pre_commit.py | Clean staged .js → exit 0 |
| PC-5 | tests/python/test_pre_commit.py | Only .md staged (no .py/.js) → exit 0 |
| PC-6 | tests/python/test_pre_commit.py | SKIP_GITLEAKS honoured; no gitleaks dep → exit 0 |

## 6. Docs to update

- [x] CHANGELOG.md
- [x] README.md (Git hooks section)
- [x] AGENTS.md (make hooks mention)
- [x] backlog.md (mark #28 done)
- [x] docs/specs/pre-commit-hook.md (this file)

## 7. Risks / edge cases

- **Symlink vs. copy:** symlink preferred (edits take effect immediately); falls
  back to `cp` on exotic setups where symlinks fail. Documented in README.
- **Bash 3.2 on macOS:** `pre-commit.sh` already avoids bash 4+ features.
- **No gitleaks installed:** hook gracefully skips with a warning message (already
  handled in the script).
- **Worktrees / different `GIT_DIR`:** test harness exercises this via env-var override.

## 8. Review checklist

- [x] Implementation matches spec sections 3–5
- [x] `./run-tests.sh --coverage` passes
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated (section 6)
- [x] Memory note written
