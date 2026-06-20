#!/usr/bin/env bash
# kill-stale-obsidian-mcp.sh
#
# Diagnose and clean up stale `obsidian-mcp` MCP server processes.
#
# Background (see backlog #23): the obsidian-mcp stdio server occasionally
# times out in Continue (`Request timed out` / JSON-RPC error -32001). The
# observed cause is MULTIPLE stale obsidian-mcp processes running at once —
# typically left behind by `npx` launches whose `npm exec` wrapper and child
# `node` orphan independently on MCP reload. They then contend for the same
# vault/stdio pipe, so Continue's requests hang.
#
# The durable fix is in `.continue/mcpServers/new-mcp-server.yaml` (launch
# `node` against a globally installed obsidian-mcp instead of `npx`, so Continue
# owns exactly one process). This script is the manual escape hatch when an
# orphan still sneaks through: it lists, then kills, any obsidian-mcp processes.
#
# Usage:
#   ./scripts/kill-stale-obsidian-mcp.sh          # list + kill, then verify
#   ./scripts/kill-stale-obsidian-mcp.sh --list   # list only (no kill)
#
# After running, reload the MCP server in Continue (or reload the VS Code
# window) so exactly one fresh instance spawns.

set -euo pipefail

PATTERN="obsidian-mcp"

list_procs() {
  # -f matches the full command line; exclude this script + the grep itself.
  ps aux | grep -i "$PATTERN" | grep -v "grep" | grep -v "kill-stale-obsidian-mcp" || true
}

echo "── Current ${PATTERN} processes ──────────────────────────"
PROCS="$(list_procs)"
if [[ -z "$PROCS" ]]; then
  echo "none running ✓"
else
  echo "$PROCS"
fi

# --list: report only, do not kill.
if [[ "${1:-}" == "--list" ]]; then
  exit 0
fi

if [[ -z "$PROCS" ]]; then
  echo "Nothing to clean up."
  exit 0
fi

echo
echo "── Killing ${PATTERN} processes ──────────────────────────"
# pkill -f matches against the full command line. Returns non-zero if nothing
# matched, which we tolerate (set -e is disabled for this line).
pkill -f "$PATTERN" || true
sleep 1

echo
echo "── Verifying ────────────────────────────────────────────"
REMAINING="$(list_procs)"
if [[ -z "$REMAINING" ]]; then
  echo "all clear ✓"
  echo
  echo "Now reload the MCP server in Continue (or reload the VS Code window)"
  echo "so a single fresh obsidian-mcp instance spawns."
else
  echo "WARNING: some processes survived (may need a stronger signal):"
  echo "$REMAINING"
  echo
  echo "Try: pkill -9 -f \"$PATTERN\""
  exit 1
fi
