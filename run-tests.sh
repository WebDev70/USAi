#!/usr/bin/env bash
# USAi Chat — run all syntax gates and unit tests (zero third-party deps).
# Usage:  ./run-tests.sh        (from the project root)
#
# Mirrors the commands in docs/testing-and-agents-strategy.md so contributors and
# the Continue agent pipeline (`/check`) run the exact same thing.
set -euo pipefail
cd "$(dirname "$0")"

# Prefer the venv's Python (so python-dotenv is available); fall back to python3.
PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "── Syntax gates ───────────────────────────────────────────"
node --check app.js
"$PY" -m py_compile server.py
echo "  ✓ syntax OK"

echo "── JS unit tests (node --test) ────────────────────────────"
# Enumerate test files with `find` and pass them explicitly. This is portable:
# directory args to `node --test` require Node >= 21, and a quoted `**` glob
# isn't expanded by bash (globstar off). `find` works everywhere.
node --test $(find tests/js -name '*.test.mjs')

echo "── Python unit tests (unittest) ───────────────────────────"
"$PY" -m unittest discover -s tests/python -p 'test_*.py'

echo "── All checks passed ✓ ────────────────────────────────────"
