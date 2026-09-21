#!/usr/bin/env bash
# scripts/mode-b-check.sh
# USAi Chat — Mode B self-improvement enforcement check (DEV/CI tooling; ships nothing in the app).
#
# WHY this exists:
#   RAIL's govern.md SPMS-5 requires every session memory note to contain a
#   "## Mode B self-improvement" section — either a workflow-improvement proposal
#   or an explicit "no improvement found" statement. Sprint-19 governance report
#   ADVISORY-03 found 0 of 5 recent notes recorded this outcome (backlog #92).
#   This script makes the check deterministic and machine-enforceable.
#
# Usage:
#   ./scripts/mode-b-check.sh              # checks the newest Cline/memories/*.md note
#   ./scripts/mode-b-check.sh <note-path>  # checks a specific note
#
# Exit codes:
#   0  Mode B section found, OR vault unavailable (skip) OR SKIP_MODE_B=1
#   1  Mode B section absent from the target note
#
# Environment variables:
#   OBSIDIAN_VAULT_PATH   Path to the Obsidian vault root (required unless passing explicit path)
#   SKIP_MODE_B=1         Skip the check entirely (exit 0 with a warning)
#
# Security (G-4):
#   This script uses grep for detection only (exit status). Diagnostic output
#   always reads "path:line_number [REDACTED]" -- never the matched line text.
#   Note content is never echoed to stdout or stderr.
#
# NOTE: ls -t is used to find the newest file by mtime. This is supported on
#   macOS and Linux (the only platforms this dev tooling targets).
set -uo pipefail

# ---------------------------------------------------------------------------
# SKIP_MODE_B=1 short-circuit — mirrors SKIP_GITLEAKS/SKIP_BANDIT pattern.
# ---------------------------------------------------------------------------
if [ "${SKIP_MODE_B:-0}" = "1" ]; then
  echo "  ⚠ mode-b-check: skipped (SKIP_MODE_B=1)"
  exit 0
fi

# ---------------------------------------------------------------------------
# Determine the target note.
# ---------------------------------------------------------------------------
if [ -n "${1:-}" ]; then
  # Explicit path argument supplied.
  TARGET="$1"
  if [ ! -f "$TARGET" ]; then
    echo "  ✕ mode-b-check: file not found: $TARGET"
    exit 1
  fi
else
  # No argument: find newest *.md in $OBSIDIAN_VAULT_PATH/Cline/memories/.

  # Skip cleanly when the vault path is unset or the directory doesn't exist.
  if [ -z "${OBSIDIAN_VAULT_PATH:-}" ]; then
    echo "  ⚠ mode-b-check: skipping (OBSIDIAN_VAULT_PATH unset)"
    exit 0
  fi

  MEM_DIR="${OBSIDIAN_VAULT_PATH}/Cline/memories"
  if [ ! -d "$MEM_DIR" ]; then
    echo "  ⚠ mode-b-check: skipping (directory missing: $MEM_DIR)"
    exit 0
  fi

  # Find the newest .md file by mtime. ls -t lists most-recent first.
  TARGET="$( ls -t "$MEM_DIR"/*.md 2>/dev/null | head -1 )"
  if [ -z "$TARGET" ]; then
    echo "  ⚠ mode-b-check: skipping (no *.md files found in $MEM_DIR)"
    exit 0
  fi
fi

# ---------------------------------------------------------------------------
# Detect the "## Mode B self-improvement" heading (case-insensitive).
# grep -i: case-insensitive; -q: quiet (exit status only, no output).
# The pattern anchors to the start of a Markdown h2 heading.
# ---------------------------------------------------------------------------
if grep -iq "^## Mode B" "$TARGET"; then
  echo "  ✓ Mode B self-improvement section found in: $TARGET"
  exit 0
else
  # Failure output: report file path only — never echo note content (G-4 redaction).
  # Find the line number of the nearest h2 (any h2) for context, but redact the text.
  echo "  ✕ Mode B section missing in: $TARGET"
  echo "    Expected a '## Mode B self-improvement' heading."
  echo "    Add the section (proposal or 'no improvement found') to satisfy /review §6d."
  echo "    [REDACTED — note contents not shown; path:$(wc -l < "$TARGET") total lines]"
  exit 1
fi
