#!/usr/bin/env bash
# scripts/mutation-audit.sh — Opt-in mutation testing wrapper for server.py.
#
# Runs mutmut against server.py, extracts the kill-rate summary, and always
# exits 0 (informational, not a hard gate — run manually or via `make mutation`).
#
# Usage:
#   ./scripts/mutation-audit.sh
#   make mutation
#
# Why: mutation testing catches tests that pass even when source logic is
# changed — it verifies that tests are actually checking meaningful behaviour,
# not just exercising code paths.  The kill rate is tracked for visibility; a
# drop in kill rate is a signal to add more assertion-rich tests.
#
# Requires: mutmut (install with `pip install mutmut` or via requirements-dev.txt)
# Bash 3.2 compatible (macOS default shell).

set -euo pipefail

PY="${PYTHON:-python3}"
PATHS_TO_MUTATE="${MUTMUT_PATHS:-server.py}"

echo "══ Mutation audit: mutmut → ${PATHS_TO_MUTATE} ═══════════════════════════"

# ── Check for mutmut ─────────────────────────────────────────────────────────
if ! "$PY" -m mutmut --version >/dev/null 2>&1 && ! command -v mutmut >/dev/null 2>&1; then
    echo "⚠  mutmut not found — install it to run mutation tests:"
    echo "     pip install mutmut"
    echo "   (listed in requirements-dev.txt)"
    echo ""
    echo "Kill rate: N/A (mutmut not installed)"
    exit 0
fi

# Prefer the python module form so it uses the active venv's mutmut.
MUTMUT_CMD="$PY -m mutmut"
if ! $MUTMUT_CMD --version >/dev/null 2>&1; then
    MUTMUT_CMD="mutmut"
fi

# ── Run mutations ─────────────────────────────────────────────────────────────
echo "Running: $MUTMUT_CMD run --paths-to-mutate ${PATHS_TO_MUTATE}"
echo "(This may take several minutes...)"
echo ""

# Run mutmut; capture exit code but do not abort script (always-exits-0 contract).
set +e
$MUTMUT_CMD run --paths-to-mutate "${PATHS_TO_MUTATE}" 2>&1
MUTMUT_RUN_EXIT=$?
set -e

# ── Extract and display summary ───────────────────────────────────────────────
echo ""
echo "── Mutation results ──────────────────────────────────────────────────────"

set +e
RESULTS=$($MUTMUT_CMD results 2>&1)
set -e
echo "$RESULTS"
echo ""

# Parse killed / survived / timeout counts from results output.
KILLED=$(echo "$RESULTS" | grep -c "^[0-9]*: " 2>/dev/null || true)

# mutmut results exits with categories; use junitxml or direct count approach.
# Try parsing the summary line first (mutmut 2.x: "Killed N/M mutants ...").
SUMMARY_LINE=$(echo "$RESULTS" | grep -E "Killed [0-9]|survived|killed" | head -1 || true)

if [ -n "$SUMMARY_LINE" ]; then
    echo "Summary: $SUMMARY_LINE"
else
    # Fallback: count lines per category from results output.
    KILLED_COUNT=$(echo "$RESULTS" | grep -c "killed" || echo 0)
    SURVIVED_COUNT=$(echo "$RESULTS" | grep -c "survived" || echo 0)
    TIMEOUT_COUNT=$(echo "$RESULTS" | grep -c "timeout" || echo 0)
    TOTAL=$((KILLED_COUNT + SURVIVED_COUNT + TIMEOUT_COUNT))

    if [ "$TOTAL" -gt 0 ]; then
        # Integer percentage (awk for bash 3.2 compat — no $(( )) float arithmetic).
        KILL_RATE=$(awk "BEGIN { printf \"%d\", ($KILLED_COUNT / $TOTAL) * 100 }")
        echo "Killed:   $KILLED_COUNT"
        echo "Survived: $SURVIVED_COUNT"
        echo "Timeout:  $TIMEOUT_COUNT"
        echo "Total:    $TOTAL"
        echo "Kill rate: ${KILL_RATE}%"
    else
        echo "(No mutation results to summarise — mutmut may have found no viable mutations.)"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Mutation audit complete. Exit code: 0 (informational — not a hard gate)."
exit 0
