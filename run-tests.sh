#!/usr/bin/env bash
# USAi Chat — run all syntax gates and unit tests (zero third-party RUNTIME deps).
#
# Usage:
#   ./run-tests.sh             syntax gates + JS + Python unit/integration tests
#   ./run-tests.sh --coverage  also measure coverage and enforce thresholds
#   ./run-tests.sh --ci-python simulate the CI Python job locally: temporarily hide
#                              node_modules and skip the JS suites, so the Python
#                              tests are proven to pass with no npm packages present
#                              (exactly what the GitHub Actions `python` job does).
#                              Combinable with --coverage.
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
set -x
cd "$(dirname "$0")"

COVERAGE=0
CI_PYTHON=0
# Parse flags positionally-agnostically so `--ci-python --coverage` and
# `--coverage --ci-python` behave identically. Unknown flags are rejected loudly
# rather than silently ignored — a typo'd gate flag must never look like a pass.
for arg in "$@"; do
  case "$arg" in
    --coverage)  COVERAGE=1 ;;
    --ci-python) CI_PYTHON=1 ;;
    *)
      echo "run-tests.sh: unknown option '$arg'" >&2
      echo "Usage: ./run-tests.sh [--coverage] [--ci-python]" >&2
      exit 2
      ;;
  esac
done

# --ci-python: reproduce the CI Python job by hiding node_modules for the run.
# Moved to a sibling directory in the repo root so the rename stays on one
# filesystem (atomic, unlike a copy to /tmp). The EXIT trap restores it even if
# a test fails, the script exits early via `set -e`, or the user hits Ctrl-C.
#
# ONE trap for the whole script: bash replaces (not appends) EXIT handlers, so the
# coverage branch below must NOT install its own `trap ... EXIT` — doing so would
# silently drop the node_modules restore and leave the tree broken.
TMP_NM_DIR=""
COVERAGE_JSON=""
cleanup() {
  [ -n "$COVERAGE_JSON" ] && rm -f "$COVERAGE_JSON"
  if [ -n "$TMP_NM_DIR" ] && [ -d "$TMP_NM_DIR" ]; then
    rm -rf node_modules
    mv "$TMP_NM_DIR" node_modules
  fi
  return 0
}
trap cleanup EXIT INT TERM
if [ "$CI_PYTHON" -eq 1 ] && [ -d node_modules ]; then
  TMP_NM_DIR=".tmp_node_modules_ci_local_$$"
  mv node_modules "$TMP_NM_DIR"
fi

# Coverage thresholds (ratchet UP over time; never lower to make a change pass).
# Also committed in .coverage-thresholds for the machine-enforced ratchet guard.
PY_MIN=90        # server.py line coverage %
PY_BRANCH_MIN=90 # server.py branch coverage % (RAIL Phase 2)
JS_MIN=75        # app.js BRANCH coverage % of the exported/tested helpers

# Prefer the venv's Python (so python-dotenv is available); fall back to python3.
PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "── Syntax gates ───────────────────────────────────────────"
# The JS syntax gate needs node but not node_modules, so it still runs in
# --ci-python mode — it mirrors the CI `javascript` job's `node --check` step.
node --check frontend/app.js
# Compile every backend module, not just a hand-maintained list — new modules
# from the server split (#64) were silently escaping the syntax gate.
"$PY" -m py_compile backend/*.py
echo "  ✓ syntax OK"
# NOTE: the delegation-policy check (scripts/delegation-policy-check.py) lives on
# the feat/zoo-migration branch and is wired in by backlog #86, not here — main
# must not invoke a script it doesn't ship.

if [ "$COVERAGE" -eq 1 ]; then
  # --ci-python mirrors the CI `python` job, which installs no npm packages and
  # therefore never runs the JS coverage gate (that lives in the `javascript` job).
  if [ "$CI_PYTHON" -eq 0 ]; then
    echo "── JS unit tests + coverage gate (Node built-in) ──────────"
    node tests/js-coverage.mjs "$JS_MIN"
  else
    echo "── JS coverage gate skipped (--ci-python) ─────────────────"
  fi

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
  #   set by other classes in the same discover batch.
  #   WORKAROUND: run the two sensitive classes separately if intermittent failures occur.
  PYTHONPATH="$(pwd)/backend" "$PY" -m coverage run --branch --source=backend -m unittest discover -s backend/tests/python -p 'test_*.py'
  "$PY" -m coverage report -m
  "$PY" -m coverage report --fail-under="$PY_MIN" >/dev/null \
    && echo "  ✓ server.py line coverage ≥ ${PY_MIN}%" \
    || { echo "  ✕ server.py line coverage below ${PY_MIN}% — add tests."; exit 1; }

  # --- Branch coverage gate (RAIL Phase 2) ---
  # Extract branch % from coverage JSON report and enforce PY_BRANCH_MIN.
  # Trailing X's only: BSD/macOS mktemp substitutes the Xs solely at the END of
  # the template, so a `...XXXXXX.json` pattern is taken LITERALLY and the second
  # run dies with "File exists". Keep the random part last (no suffix) so the
  # template is portable across BSD and GNU mktemp.
  COVERAGE_JSON=$(mktemp "/tmp/usai-coverage-json.XXXXXX")
  # No `trap` here — the single `cleanup` EXIT handler installed above removes
  # this file. Installing another EXIT trap would replace it and skip the
  # node_modules restore that --ci-python depends on.
  "$PY" -m coverage json -o "$COVERAGE_JSON" >/dev/null
  PY_BRANCH_PCT=$("$PY" -c "
import json, sys
d = json.load(open('$COVERAGE_JSON'))
s = d['files']['backend/server.py']['summary']
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
  # --ci-python mirrors the CI `python` job: no npm packages, so no JS suites.
  if [ "$CI_PYTHON" -eq 0 ]; then
    echo "── JS unit tests (node --test) ────────────────────────────"
    # Pure-helper unit tests (no jsdom). Behavior + structure tests (which need
    # jsdom) run separately below so a missing jsdom install can't fail this gate.
    node --test $(find frontend/tests/js -name '*.test.mjs' \
      ! -name 'app.behavior.test.mjs' \
      ! -name 'index-html-structure.test.mjs')

    echo "── JS behavior tests (jsdom, dev-only) ────────────────────"
    if [ -d "node_modules/jsdom" ]; then
      node --test frontend/tests/js/app.behavior.test.mjs frontend/tests/js/index-html-structure.test.mjs
    else
      echo "  ⚠ jsdom not installed — skipping behavior + structure tests."
      echo "    Run: npm install  (or: make dev-setup)"
    fi
  else
    echo "── JS suites skipped (--ci-python) ────────────────────────"
  fi

  echo "── Python unit/integration tests (unittest) ──────────────"
  PYTHONPATH="$(pwd)/backend" "$PY" -m unittest discover -s backend/tests/python -p 'test_*.py'
fi

echo "── All checks passed ✓ ────────────────────────────────────"
