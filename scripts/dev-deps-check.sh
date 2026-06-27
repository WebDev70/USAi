#!/usr/bin/env bash
# scripts/dev-deps-check.sh
# Verify that every dev/CI tool pinned in requirements-dev.txt matches the
# version actually installed in the active Python environment.
#
# Exit codes:
#   0 — all installed versions match the pins
#   1 — at least one installed version differs from its pin
#   2 — usage/config error: missing pin file, or a checked package has no pin entry
#
# Environment variables:
#   REQUIREMENTS_DEV_TXT   path to the pin file (default: requirements-dev.txt
#                          in the same directory as this script's parent, i.e. repo root)
#   PYTHON_EXE             Python interpreter to use for `pip show`
#                          (default: first python3 on PATH, or .venv/bin/python)
#
# Packages checked: coverage, bandit, pip-audit (the three RAIL dev tools).
# Add more to the CHECKED_PACKAGES array as needed.

set -euo pipefail

# ---- Resolve repo root and defaults ----------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REQ_DEV="${REQUIREMENTS_DEV_TXT:-${REPO_ROOT}/requirements-dev.txt}"

# Resolve Python executable
if [[ -n "${PYTHON_EXE:-}" ]]; then
    PY="${PYTHON_EXE}"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PY="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    echo "ERROR: No Python interpreter found. Set PYTHON_EXE or activate a venv." >&2
    exit 2
fi

# ---- Packages to verify -----------------------------------------------------
# CHECKED_PACKAGES_OVERRIDE: space-separated list of package names that
# overrides the default list below.  Used by tests to inject a fake package
# and verify the "pinned but not installed" exit-1 path.
if [[ -n "${CHECKED_PACKAGES_OVERRIDE:-}" ]]; then
    # shellcheck disable=SC2206  # intentional word-split on the override value
    read -r -a CHECKED_PACKAGES <<< "${CHECKED_PACKAGES_OVERRIDE}"
else
    # Add new dev tools here as they are pinned in requirements-dev.txt.
    # mutmut is included so an absent installation is flagged (exit 1) rather
    # than silently skipped — this closes the "pinned but not installed" gap
    # identified in the RAIL QA Hardening closeout (2026-06-24).
    CHECKED_PACKAGES=("coverage" "bandit" "pip-audit" "mutmut")
fi

# ---- Validate pin file exists -----------------------------------------------
if [[ ! -f "${REQ_DEV}" ]]; then
    echo "ERROR: requirements-dev.txt not found at: ${REQ_DEV}" >&2
    exit 2
fi

# ---- Helper: look up pinned version for a package ---------------------------
# Reads lines like:  coverage==7.10.7 \
# Returns the version string, or empty string if not found.
_pinned_version() {
    local pkg="${1}"
    # Match lines like "coverage==7.10.7" (with optional trailing \)
    # Case-insensitive for the package name; handle underscore/hyphen variants.
    local normalized_pkg
    normalized_pkg="$(echo "${pkg}" | tr '[:upper:]' '[:lower:]' | tr '_' '-')"
    grep -i "^${normalized_pkg}==" "${REQ_DEV}" \
        | head -1 \
        | sed 's/[[:space:]]*\\[[:space:]]*$//' \
        | grep -oE '[0-9][0-9a-zA-Z._-]*$' \
        || true
}

# ---- Helper: get installed version via pip show -----------------------------
_installed_version() {
    local pkg="${1}"
    "${PY}" -m pip show "${pkg}" 2>/dev/null \
        | grep -i "^Version:" \
        | awk '{print $2}' \
        || true
}

# ---- Main check loop --------------------------------------------------------
overall_rc=0
missing_pins=()
mismatches=()

for pkg in "${CHECKED_PACKAGES[@]}"; do
    pinned="$(_pinned_version "${pkg}")"
    if [[ -z "${pinned}" ]]; then
        missing_pins+=("${pkg}")
        continue
    fi

    installed="$(_installed_version "${pkg}")"
    if [[ -z "${installed}" ]]; then
        echo "  ✕ ${pkg}: not installed (pin: ${pinned})"
        mismatches+=("${pkg}")
    elif [[ "${installed}" == "${pinned}" ]]; then
        echo "  ✓ ${pkg}==${installed}"
    else
        echo "  ✕ ${pkg}: installed ${installed} ≠ pin ${pinned}"
        mismatches+=("${pkg}")
    fi
done

# ---- Report missing pin entries (exit 2) ------------------------------------
if [[ ${#missing_pins[@]} -gt 0 ]]; then
    echo ""
    echo "ERROR: The following packages have no pin entry in ${REQ_DEV}:" >&2
    for p in "${missing_pins[@]}"; do
        echo "  - ${p}" >&2
    done
    exit 2
fi

# ---- Report version mismatches (exit 1) -------------------------------------
if [[ ${#mismatches[@]} -gt 0 ]]; then
    echo ""
    echo "FAIL: ${#mismatches[@]} package(s) do not match their pin. Run \`make dev-setup\` to fix."
    exit 1
fi

echo ""
echo "✓ All dev tools match their pinned versions."
exit 0
