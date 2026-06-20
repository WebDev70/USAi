#!/usr/bin/env bash
# USAi Chat — run all syntax gates and unit tests (zero third-party RUNTIME deps).
#
# Usage:
#   ./run-tests.sh             syntax gates + JS + Python unit/integration tests
#   ./run-tests.sh --coverage  also measure coverage and enforce thresholds
#
# Coverage tooling is DEV-ONLY (never shipped in the app):
#   • Python: coverage.py installed in .venv (not in requirements.txt)
#   • JS:     Node's built-in --experimental-test-coverage (needs Node >= 22)
#
# Mirrors the commands in docs/testing-and-agents-strategy.md so contributors and
# the Continue agent pipeline (`/check`) run the exact same thing.
set -euo pipefail
cd "$(dirname "$0")"

COVERAGE=0
[ "${1:-}" = "--coverage" ] && COVERAGE=1

# Coverage thresholds (ratchet UP over time; never lower to make a change pass).
PY_MIN=90        # server.py line coverage %
JS_MIN=70        # app.js BRANCH coverage % of the exported/tested helpers

# Prefer the venv's Python (so python-dotenv is available); fall back to python3.
PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "── Syntax gates ───────────────────────────────────────────"
node --check app.js
"$PY" -m py_compile server.py
echo "  ✓ syntax OK"

if [ "$COVERAGE" -eq 1 ]; then
  echo "── JS unit tests + coverage gate (Node built-in) ──────────"
  node tests/js-coverage.mjs "$JS_MIN"

  echo "── Python unit/integration tests + coverage gate ─────────"
  if ! "$PY" -c "import coverage" 2>/dev/null; then
    echo "  coverage.py not installed in the venv. Install it (dev-only):"
    echo "    $PY -m pip install coverage"
    exit 1
  fi
  "$PY" -m coverage run --source=server -m unittest discover -s tests/python -p 'test_*.py'
  "$PY" -m coverage report -m
  "$PY" -m coverage report --fail-under="$PY_MIN" >/dev/null \
    && echo "  ✓ server.py coverage ≥ ${PY_MIN}%" \
    || { echo "  ✕ server.py coverage below ${PY_MIN}% — add tests."; exit 1; }
else
  echo "── JS unit tests (node --test) ────────────────────────────"
  # Enumerate test files with `find` and pass them explicitly. This is portable:
  # directory args to `node --test` require Node >= 21, and a quoted `**` glob
  # isn't expanded by bash (globstar off). `find` works everywhere.
  node --test $(find tests/js -name '*.test.mjs')

  echo "── Python unit/integration tests (unittest) ──────────────"
  "$PY" -m unittest discover -s tests/python -p 'test_*.py'
fi

echo "── All checks passed ✓ ────────────────────────────────────"
