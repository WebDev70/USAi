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
# Mirrors the commands in docs/rail-pipeline.md so contributors and
# the Continue agent pipeline (`/check`) run the exact same thing.
#
# RAIL Phase 2 — Branch coverage:
#   Python branch coverage is measured via `coverage run --branch` and enforced
#   at PY_BRANCH_MIN%. The ratchet guard (scripts/ratchet-check.sh) additionally
#   compares live values against the committed .coverage-thresholds file so no
#   threshold can be silently lowered.
set -euo pipefail
cd "$(dirname "$0")"

COVERAGE=0
[ "${1:-}" = "--coverage" ] && COVERAGE=1

# Coverage thresholds (ratchet UP over time; never lower to make a change pass).
# Also committed in .coverage-thresholds for the machine-enforced ratchet guard.
PY_MIN=90        # server.py line coverage %
PY_BRANCH_MIN=80 # server.py branch coverage % (RAIL Phase 2)
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
  # --branch enables branch coverage measurement (RAIL Phase 2).
  # .coveragerc also sets branch=True; explicit here for clarity.
  #
  # SSL-context isolation note (#43 — backlog ADVISORY-03):
  #   Two test classes in test_server_proxy.py are sensitive to CONFIG state
  #   set by other classes in the same discover batch:
  #     • ProxySsrfGuardTests      — sets base_url to a private IP (no _test_allow_loopback)
  #     • ProxyIncrementalStreamingTests — uses a SlowStream upstream + raw socket timing
  #   When these share a discover pass with classes that mutate CONFIG (e.g. those that
  #   set '_test_allow_loopback': True), tearDownClass execution order can leave CONFIG
  #   polluted, causing intermittent failures.
  #
  #   WORKAROUND (if you hit failures): run the two sensitive classes separately and
  #   merge their coverage with --append:
  #     $PY -m coverage run --branch --source=server -m unittest \
  #       tests.python.test_server_proxy.ProxySsrfGuardTests \
  #       tests.python.test_server_proxy.ProxyIncrementalStreamingTests
  #     $PY -m coverage run --branch --source=server --append -m unittest discover \
  #       -s tests/python -p 'test_*.py'
  #   The combined discover below passes reliably in most environments; if you see
  #   intermittent proxy failures, switch to the two-pass form above.
  "$PY" -m coverage run --branch --source=server -m unittest discover -s tests/python -p 'test_*.py'
  "$PY" -m coverage report -m
  "$PY" -m coverage report --fail-under="$PY_MIN" >/dev/null \
    && echo "  ✓ server.py line coverage ≥ ${PY_MIN}%" \
    || { echo "  ✕ server.py line coverage below ${PY_MIN}% — add tests."; exit 1; }

  # --- Branch coverage gate (RAIL Phase 2) ---
  # Extract branch % from coverage JSON report and enforce PY_BRANCH_MIN.
  COVERAGE_JSON=$(mktemp /tmp/coverage-XXXXXX.json)
  trap 'rm -f "$COVERAGE_JSON"' EXIT
  "$PY" -m coverage json -o "$COVERAGE_JSON" >/dev/null
  PY_BRANCH_PCT=$("$PY" -c "
import json, sys
d = json.load(open('$COVERAGE_JSON'))
s = d['files']['server.py']['summary']
nb = s['num_branches']
cb = s['covered_branches']
pct = (cb / nb * 100) if nb > 0 else 100.0
print('%.2f' % pct)
")
  # Truncate to integer for threshold comparison (floor, same as coverage.py display)
  PY_BRANCH_INT=$(echo "$PY_BRANCH_PCT" | awk '{printf "%d", int($1)}')
  if [ "$PY_BRANCH_INT" -ge "$PY_BRANCH_MIN" ]; then
    echo "  ✓ server.py branch coverage ≥ ${PY_BRANCH_MIN}%  (actual: ${PY_BRANCH_PCT}%)"
  else
    echo "  ✕ server.py branch coverage ${PY_BRANCH_PCT}% is below ${PY_BRANCH_MIN}% — add tests."
    exit 1
  fi

  # --- Ratchet guard (RAIL Phase 2 / #37 fix) ---
  # Fail if any threshold dropped below the committed high-water mark.
  # js-coverage.mjs writes the LIVE branch % to a sentinel file (/tmp/usai-js-branch-pct)
  # so we can pass the actual measured value to ratchet-check.sh.
  # Fallback to $JS_MIN only if the sentinel wasn't written (e.g. Node < 22 skip).
  JS_SENTINEL="/tmp/usai-js-branch-pct"
  if [ -f "$JS_SENTINEL" ]; then
    JS_BRANCH_LIVE=$(cat "$JS_SENTINEL")
  else
    JS_BRANCH_LIVE="$JS_MIN"
  fi
  echo "── Coverage ratchet guard (scripts/ratchet-check.sh) ──────"
  ./scripts/ratchet-check.sh \
    --thresholds-file .coverage-thresholds \
    --python-line "$PY_MIN" \
    --python-branch "$PY_BRANCH_INT" \
    --js-branch "$JS_BRANCH_LIVE"
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
