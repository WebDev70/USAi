#!/usr/bin/env bash
# scripts/analyze-logs.sh
# RAIL Log Analyzer — shell wrapper for CI / RAIL workflow gates.
#
# Usage:
#   ./scripts/analyze-logs.sh [log-dir]   # default: logs/
#
# Exit codes:
#   0 — no error-level log entries (or no log files found)
#   1 — error-level entries found (advisory in /review; BLOCKING only if recurring in /govern)
#
# Called by:
#   .clinerules/workflows/review.md  §6g (advisory gate)
#   .clinerules/workflows/build.md   pre-flight step 3b (informational)
#   .clinerules/workflows/govern.md  SE-5 (log-trend audit)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ANALYZER="${SCRIPT_DIR}/analyze_logs.py"

# Locate Python — prefer the project venv, fall back to system python3.
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "analyze-logs.sh: ERROR — python3 not found" >&2
    exit 2
fi

# Pass the optional log-dir argument through to the Python script.
if [[ $# -ge 1 ]]; then
    exec "${PYTHON}" "${ANALYZER}" "$1"
else
    exec "${PYTHON}" "${ANALYZER}"
fi
