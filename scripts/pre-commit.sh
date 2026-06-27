#!/usr/bin/env bash
# scripts/pre-commit.sh
# Git pre-commit hook — fast, deterministic syntax + secret gates.
#
# Install as a git hook:
#   make hooks     (symlinks .git/hooks/pre-commit → this file)
# Or invoke manually:
#   bash scripts/pre-commit.sh
#
# Exit codes:
#   0 — all checks passed
#   1 — at least one check failed
#
# Environment variables:
#   SKIP_GITLEAKS  set to any non-empty value to skip the gitleaks secret scan
#                  (useful in CI environments without gitleaks, or during tests)
#
# Checks performed (in order):
#   1. Python syntax  — python3 -m py_compile on every staged *.py file
#   2. JS syntax      — node --check on every staged *.js file
#   3. Secret scan    — gitleaks detect --staged (skipped if SKIP_GITLEAKS set)

set -uo pipefail

PASS=0
FAIL=1

# Track overall result — we run all checks before exiting so the developer
# sees every failure in one pass, not just the first.
overall_rc=0
staged_py_errors=()
staged_js_errors=()

# ---- Resolve repo root and Python interpreter --------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_SCRIPT_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Respect GIT_WORK_TREE when set (allows test harness to point at a temp repo).
REPO_ROOT="${GIT_WORK_TREE:-${_SCRIPT_REPO_ROOT}}"

if [[ -x "${_SCRIPT_REPO_ROOT}/.venv/bin/python" ]]; then
    PY="${_SCRIPT_REPO_ROOT}/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    echo "ERROR: No Python interpreter found." >&2
    exit 1
fi

# ---- Get staged files -------------------------------------------------------
# Use GIT_DIR / GIT_WORK_TREE if set (allows test harness override).
# Avoid mapfile (bash 4+) — use a process-substitution while-read loop instead,
# which works on macOS's bash 3.2 and any POSIX sh.
STAGED=()
while IFS= read -r line; do
    [[ -n "${line}" ]] && STAGED+=("${line}")
done < <(
    git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || \
    git diff --name-only HEAD 2>/dev/null || true
)

# ---- 1. Python syntax -------------------------------------------------------
echo "==> Pre-commit: Python syntax check"
for f in "${STAGED[@]:-}"; do
    [[ "${f}" == *.py ]] || continue
    abs="${REPO_ROOT}/${f}"
    [[ -f "${abs}" ]] || continue
    if "${PY}" -m py_compile "${abs}" 2>&1; then
        echo "  ✓ ${f}"
    else
        echo "  ✕ ${f}: syntax error"
        staged_py_errors+=("${f}")
        overall_rc=1
    fi
done

if [[ ${#staged_py_errors[@]} -gt 0 ]]; then
    echo "FAIL: Python syntax errors in staged files."
else
    echo "  (ok)"
fi

# ---- 2. JS syntax -----------------------------------------------------------
echo "==> Pre-commit: JS syntax check"
if command -v node &>/dev/null; then
    for f in "${STAGED[@]:-}"; do
        [[ "${f}" == *.js ]] || continue
        abs="${REPO_ROOT}/${f}"
        [[ -f "${abs}" ]] || continue
        if node --check "${abs}" 2>&1; then
            echo "  ✓ ${f}"
        else
            echo "  ✕ ${f}: syntax error"
            staged_js_errors+=("${f}")
            overall_rc=1
        fi
    done
    if [[ ${#staged_js_errors[@]} -gt 0 ]]; then
        echo "FAIL: JS syntax errors in staged files."
    else
        echo "  (ok)"
    fi
else
    echo "  (skipped — node not found)"
fi

# ---- 3. Secret scan ---------------------------------------------------------
echo "==> Pre-commit: secret scan"
if [[ -n "${SKIP_GITLEAKS:-}" ]]; then
    echo "  (skipped — SKIP_GITLEAKS set)"
elif command -v gitleaks &>/dev/null; then
    if gitleaks detect --staged --no-banner 2>&1; then
        echo "  ✓ no secrets found"
    else
        echo "  ✕ gitleaks detected a potential secret — commit blocked"
        overall_rc=1
    fi
else
    echo "  (skipped — gitleaks not installed)"
fi

# ---- Final result -----------------------------------------------------------
if [[ "${overall_rc}" -eq 0 ]]; then
    echo ""
    echo "✓ Pre-commit checks passed."
else
    echo ""
    echo "✕ Pre-commit checks FAILED — commit blocked."
fi

exit "${overall_rc}"
