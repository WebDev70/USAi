#!/usr/bin/env bash
# purge-orphan-test-projects.sh — safe cleanup for backlog #94 (project isolation).
#
# WHY: 537 project dirs accumulated under the git-ignored data dirs during
#      2026-09-13 manual QA against the live dev server (191 "EmbeddingTest",
#      190 "Test Project EMB3", 156 "EmbeddingNegTest"). They are not created by
#      the automated suite (Python tests use TemporaryDirectory). This tool
#      removes ONLY projects whose display name matches a known test pattern,
#      DRY-RUN by default, and never touches the git tree (data dirs are ignored).
#
# SAFETY:
#   - Dry-run first: prints what WOULD be deleted; deletes nothing without --apply.
#   - Name-allowlist only: a project is a purge candidate ONLY if its `name`
#     matches one of the TEST_NAME_PATTERNS below. Real projects are never named
#     these, so they are never touched.
#   - Reversible until --apply: moves matched dirs to a timestamped backup under
#     .purge-backup/ rather than hard-deleting, so a mistake can be restored.
#
# Usage:
#   ./scripts/purge-orphan-test-projects.sh            # dry run (default)
#   ./scripts/purge-orphan-test-projects.sh --apply    # move matches to backup
#   ./scripts/purge-orphan-test-projects.sh --apply --hard   # permanent delete
set -uo pipefail
cd "$(dirname "$0")/.."   # project root

PROJECTS_DIR=".projects"
CHUNK_CACHE_DIR=".chunk_cache/projects"

# Test-project display-name patterns (extended regex). Real projects must never
# use these names. Add patterns here if new test names appear.
TEST_NAME_PATTERNS='^(EmbeddingTest|EmbeddingNegTest|Test Project EMB3)$'

APPLY=0
HARD=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --hard)  HARD=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [ ! -d "$PROJECTS_DIR" ]; then
  echo "No $PROJECTS_DIR directory — nothing to purge."
  exit 0
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR=".purge-backup/$STAMP"

count=0
echo "Scanning $PROJECTS_DIR for orphan test projects (patterns: $TEST_NAME_PATTERNS)"
echo

for meta in "$PROJECTS_DIR"/*.json; do
  [ -e "$meta" ] || continue
  # Extract the "name" field with stdlib python (no jq dependency).
  name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("name",""))' "$meta" 2>/dev/null)"
  pid="$(basename "$meta" .json)"
  if printf '%s' "$name" | grep -Eq "$TEST_NAME_PATTERNS"; then
    count=$((count + 1))
    if [ "$APPLY" -eq 1 ]; then
      if [ "$HARD" -eq 1 ]; then
        rm -f "$meta"
        rm -rf "${CHUNK_CACHE_DIR:?}/$pid"
        echo "DELETED  $pid  (name: $name)"
      else
        mkdir -p "$BACKUP_DIR/projects" "$BACKUP_DIR/chunk_cache"
        mv "$meta" "$BACKUP_DIR/projects/"
        [ -d "$CHUNK_CACHE_DIR/$pid" ] && mv "$CHUNK_CACHE_DIR/$pid" "$BACKUP_DIR/chunk_cache/"
        echo "BACKED-UP $pid  (name: $name) -> $BACKUP_DIR"
      fi
    else
      echo "WOULD PURGE  $pid  (name: $name)"
    fi
  fi
done

echo
if [ "$APPLY" -eq 1 ]; then
  if [ "$HARD" -eq 1 ]; then
    echo "Permanently deleted $count orphan test project(s)."
  else
    echo "Moved $count orphan test project(s) to $BACKUP_DIR (restore by moving back)."
  fi
else
  echo "DRY RUN — $count orphan test project(s) matched. Re-run with --apply to act."
fi
