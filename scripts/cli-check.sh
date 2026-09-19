#!/usr/bin/env bash
# Temporary compatibility entry point for callers using the former CLI gate name.
# The implementation is intentionally tool-neutral; remove this wrapper only after
# all live callers use scripts/quality-gate.sh directly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/quality-gate.sh" "$@"
