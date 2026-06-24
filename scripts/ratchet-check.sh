#!/usr/bin/env bash
# scripts/ratchet-check.sh
# RAIL Phase 2 — Coverage threshold ratchet guard.
#
# Purpose: compare live coverage values against the committed high-water marks in
# .coverage-thresholds and fail (exit 1) if any live value is LOWER than the
# committed threshold. This prevents anyone from silently lowering a coverage gate
# to make a change pass.
#
# Usage:
#   ./scripts/ratchet-check.sh \
#       --thresholds-file .coverage-thresholds \
#       --python-line <N> \
#       --python-branch <N> \
#       --js-branch <N>
#
# --thresholds-file defaults to .coverage-thresholds (relative to CWD).
#
# Exit codes:
#   0 — all live values >= committed thresholds (PASS)
#   1 — one or more live values < committed threshold (FAIL)
#   2 — usage error / file not found / missing required key
#
# Bash 3.2-compatible: no mapfile, no declare -A, no process substitution for
# arrays. Uses temp files and grep for all set lookups.
set -uo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
THRESHOLDS_FILE=".coverage-thresholds"
LIVE_PY_LINE=""
LIVE_PY_BRANCH=""
LIVE_JS_BRANCH=""

while [ $# -gt 0 ]; do
    case "$1" in
        --thresholds-file) THRESHOLDS_FILE="$2"; shift 2 ;;
        --python-line)     LIVE_PY_LINE="$2";    shift 2 ;;
        --python-branch)   LIVE_PY_BRANCH="$2";  shift 2 ;;
        --js-branch)       LIVE_JS_BRANCH="$2";  shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

if [ -z "$LIVE_PY_LINE" ] || [ -z "$LIVE_PY_BRANCH" ] || [ -z "$LIVE_JS_BRANCH" ]; then
    echo "Usage: $0 --thresholds-file <file> --python-line <N> --python-branch <N> --js-branch <N>" >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Load thresholds file
# ---------------------------------------------------------------------------
if [ ! -f "$THRESHOLDS_FILE" ]; then
    echo "ERROR: thresholds file not found: $THRESHOLDS_FILE" >&2
    exit 2
fi

# Read each key=value line; bash 3.2-compat (no source with associative arrays).
_read_key() {
    local key="$1"
    local val
    val=$(grep -E "^${key}=" "$THRESHOLDS_FILE" | head -1 | sed "s/^${key}=//")
    echo "$val"
}

THRESH_PY_LINE=$(_read_key "python_line")
THRESH_PY_BRANCH=$(_read_key "python_branch")
THRESH_JS_BRANCH=$(_read_key "js_branch")

# Validate all three required keys are present and numeric
for key_val in "python_line:$THRESH_PY_LINE" "python_branch:$THRESH_PY_BRANCH" "js_branch:$THRESH_JS_BRANCH"; do
    key="${key_val%%:*}"
    val="${key_val#*:}"
    if [ -z "$val" ]; then
        echo "ERROR: required key '$key' not found in $THRESHOLDS_FILE" >&2
        exit 2
    fi
    # Must be numeric (integer or decimal)
    if ! echo "$val" | grep -qE '^[0-9]+(\.[0-9]+)?$'; then
        echo "ERROR: key '$key' has non-numeric value '$val' in $THRESHOLDS_FILE" >&2
        exit 2
    fi
done

# ---------------------------------------------------------------------------
# Compare live vs threshold (integer truncation via awk for safety)
# awk is used for numeric comparison to handle potential decimals.
# ---------------------------------------------------------------------------
ERRORS=0
GAP_LIST=""

_check() {
    local metric="$1"
    local live="$2"
    local threshold="$3"
    # Use awk: if live < threshold → fail
    local result
    result=$(awk -v live="$live" -v thresh="$threshold" 'BEGIN { print (live < thresh) ? "FAIL" : "PASS" }')
    if [ "$result" = "FAIL" ]; then
        GAP_LIST="${GAP_LIST}\n  ✕  ${metric}: live=${live}%  threshold=${threshold}%  (dropped by $(awk -v l="$live" -v t="$threshold" 'BEGIN { printf "%.2f", t-l }')%)"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✓  ${metric}: live=${live}%  threshold=${threshold}%"
    fi
}

echo "═══════════════════════════════════════════════════════"
echo "  ratchet-check.sh — coverage threshold ratchet guard"
echo "  Thresholds file: $THRESHOLDS_FILE"
echo "═══════════════════════════════════════════════════════"
echo ""

_check "python_line"   "$LIVE_PY_LINE"    "$THRESH_PY_LINE"
_check "python_branch" "$LIVE_PY_BRANCH"  "$THRESH_PY_BRANCH"
_check "js_branch"     "$LIVE_JS_BRANCH"  "$THRESH_JS_BRANCH"

echo ""

if [ "$ERRORS" -eq 0 ]; then
    echo "✓ PASS — all coverage thresholds met or exceeded."
    exit 0
else
    echo "✕ FAIL — $ERRORS threshold(s) dropped below committed high-water mark:"
    printf '%b\n' "$GAP_LIST"
    echo ""
    echo "  Ratchet rule: NEVER lower a threshold to make a change pass."
    echo "  Add tests to bring coverage back up, then re-run."
    exit 1
fi
