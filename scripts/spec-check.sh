#!/usr/bin/env bash
# scripts/spec-check.sh  <spec-file>
# RAIL Phase 1 — Spec↔Build compliance checker.
#
# Purpose: verify that the set of files changed in the current git working tree
# (staged + unstaged against HEAD) matches the spec's declared scope:
#
#   §3 Affected files — every listed file must appear in the diff (hard error if
#      absent); files in the diff that are NOT in §3 generate a scope-creep
#      warning (non-blocking), except for exempt paths (docs/, CHANGELOG.md,
#      backlog.md, and the spec file itself).
#
#   §5 Test plan — every tests/ path listed in the table must appear in the
#      diff (hard error if absent).
#
# Exit codes:
#   0 — §3 files all present in diff AND §5 test files all present in diff
#   1 — one or more §3 or §5 files are MISSING from the diff (hard failures)
#   2 — usage error (wrong number of arguments or spec file not found)
#
# Scope-creep (diff contains a file not in §3 and not exempt) is printed as a
# WARNING but does NOT change the exit code — it is informational so the
# developer can decide whether to update the spec.
#
# Usage:
#   ./scripts/spec-check.sh docs/specs/my-feature.md
#
# The script runs from the repository root (or any directory inside a git repo).
# It calls `git diff --name-only HEAD` (staged+unstaged vs HEAD).
#
# Requirements: bash 3.2+, git, grep, sed, awk (all standard on macOS / Linux).
set -uo pipefail

# ---------------------------------------------------------------------------
# Usage check
# ---------------------------------------------------------------------------
if [ "${1:-}" = "" ]; then
    echo "Usage: $0 <spec-file>" >&2
    exit 2
fi

SPEC_FILE="$1"

if [ ! -f "$SPEC_FILE" ]; then
    echo "ERROR: spec file not found: $SPEC_FILE" >&2
    exit 2
fi

SPEC_BASENAME=$(basename "$SPEC_FILE")

# ---------------------------------------------------------------------------
# Temporary files (cleaned up on exit)
# Bash 3.2-compatible: no associative arrays, no mapfile.
# We store lists as newline-delimited temp files and use grep for set lookups.
# ---------------------------------------------------------------------------
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

S3_FILE="$TMP_DIR/s3_files.txt"     # §3 file list
S5_FILE="$TMP_DIR/s5_files.txt"     # §5 test file list
DIFF_FILE="$TMP_DIR/diff_files.txt" # git diff file list

touch "$S3_FILE" "$S5_FILE" "$DIFF_FILE"

# ---------------------------------------------------------------------------
# Parse spec §3 — Affected files
# Matches table rows of the form:  | `path/to/file` | ... |
# Lines like "| File |" (header) are skipped (no slash in path token).
# ---------------------------------------------------------------------------
in_section3=0
while IFS= read -r line; do
    # Enter §3
    if echo "$line" | grep -qE "^## 3\."; then
        in_section3=1
        continue
    fi
    # Exit §3 on next ##-level heading or --- separator
    if [ "$in_section3" -eq 1 ]; then
        if echo "$line" | grep -qE "^(##|---)"; then
            in_section3=0
            continue
        fi
        # Table row with a backtick-quoted token in the first column
        if echo "$line" | grep -qE "^\| \`[^\`]+\`"; then
            token=$(echo "$line" | grep -oE "\`[^\`]+\`" | head -1 | sed 's/`//g')
            # Skip header "File" and blank; require a "/" (path separator) to
            # filter out single-word tokens that are column headers
            if [ -n "$token" ] && [ "$token" != "File" ]; then
                echo "$token" >> "$S3_FILE"
            fi
        fi
    fi
done < "$SPEC_FILE"

# ---------------------------------------------------------------------------
# Parse spec §5 — Test plan
# Matches table rows containing a backtick-quoted tests/ path.
# ---------------------------------------------------------------------------
in_section5=0
while IFS= read -r line; do
    if echo "$line" | grep -qE "^## 5\."; then
        in_section5=1
        continue
    fi
    if [ "$in_section5" -eq 1 ]; then
        if echo "$line" | grep -qE "^(##|---)"; then
            in_section5=0
            continue
        fi
        if echo "$line" | grep -qE "^\|.*\`tests/[^\`]+\`"; then
            # Extract all backtick tokens, keep those starting with tests/
            echo "$line" | grep -oE "\`[^\`]+\`" | sed 's/`//g' | grep "^tests/" >> "$S5_FILE"
        fi
    fi
done < "$SPEC_FILE"

# ---------------------------------------------------------------------------
# Validate parsing
# ---------------------------------------------------------------------------
S3_COUNT=$(wc -l < "$S3_FILE" | tr -d ' ')
S5_COUNT=$(wc -l < "$S5_FILE" | tr -d ' ')

if [ "$S3_COUNT" -eq 0 ]; then
    echo "WARNING: could not find any file entries in spec §3 (Affected files)." >&2
    echo "  Check that §3 uses the | \`path\` | format." >&2
fi

# ---------------------------------------------------------------------------
# Build git diff file list — staged + unstaged vs HEAD
# ---------------------------------------------------------------------------
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "ERROR: not inside a git repository (required for git diff)." >&2
    exit 2
fi

# Collect both staged (--cached) and unstaged (HEAD) changes; deduplicate
{
    git diff --name-only HEAD 2>/dev/null
    git diff --cached --name-only 2>/dev/null
} | sort -u > "$DIFF_FILE"

DIFF_COUNT=$(wc -l < "$DIFF_FILE" | tr -d ' ')

# ---------------------------------------------------------------------------
# Helper: is a path exempt from scope-creep checks?
# Exempt: docs/*, CHANGELOG.md, backlog.md, the spec file itself.
# ---------------------------------------------------------------------------
is_exempt() {
    local path="$1"
    case "$path" in
        docs/*)       return 0 ;;
        CHANGELOG.md) return 0 ;;
        backlog.md)   return 0 ;;
    esac
    # Spec file (absolute or relative)
    [ "$path" = "$SPEC_FILE" ] && return 0
    # Spec basename match (e.g. docs/specs/rail-improvements.md)
    case "$path" in
        *"$SPEC_BASENAME"*) return 0 ;;
    esac
    return 1
}

# ---------------------------------------------------------------------------
# Check 1 — §3 files present in diff
# ---------------------------------------------------------------------------
ERRORS=0
MISSING_S3=""
while IFS= read -r spec_path; do
    [ -z "$spec_path" ] && continue
    if ! grep -qxF "$spec_path" "$DIFF_FILE"; then
        MISSING_S3="$MISSING_S3\n  ✕  $spec_path"
        ERRORS=$((ERRORS + 1))
    fi
done < "$S3_FILE"

# ---------------------------------------------------------------------------
# Check 2 — §5 test files present in diff
# ---------------------------------------------------------------------------
MISSING_S5=""
while IFS= read -r test_path; do
    [ -z "$test_path" ] && continue
    if ! grep -qxF "$test_path" "$DIFF_FILE"; then
        MISSING_S5="$MISSING_S5\n  ✕  $test_path"
        ERRORS=$((ERRORS + 1))
    fi
done < "$S5_FILE"

# ---------------------------------------------------------------------------
# Check 3 — diff files not in §3 (scope creep warning, non-blocking)
# ---------------------------------------------------------------------------
SCOPE_CREEP=""
while IFS= read -r diff_path; do
    [ -z "$diff_path" ] && continue
    is_exempt "$diff_path" && continue
    if ! grep -qxF "$diff_path" "$S3_FILE"; then
        SCOPE_CREEP="$SCOPE_CREEP\n  ⚠  $diff_path"
    fi
done < "$DIFF_FILE"

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
echo "═══════════════════════════════════════════════════════"
echo "  spec-check.sh — $SPEC_BASENAME"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Spec §3 files listed : $S3_COUNT"
echo "Spec §5 test files   : $S5_COUNT"
echo "Git diff files       : $DIFF_COUNT"
echo ""

if [ -n "$MISSING_S3" ]; then
    echo "ERROR — §3 file(s) missing from git diff (not yet changed):"
    printf '%b\n' "$MISSING_S3"
    echo ""
fi

if [ -n "$MISSING_S5" ]; then
    echo "ERROR — §5 test file(s) missing from git diff (tests not written yet):"
    printf '%b\n' "$MISSING_S5"
    echo ""
fi

if [ -n "$SCOPE_CREEP" ]; then
    echo "WARNING — file(s) in diff not listed in spec §3 (possible scope creep):"
    printf '%b\n' "$SCOPE_CREEP"
    echo "  (Update spec §3 if these changes are intentional.)"
    echo ""
fi

if [ "$ERRORS" -eq 0 ]; then
    echo "✓ PASS — all §3 files and §5 test files are present in the diff."
    exit 0
else
    echo "✕ FAIL — $ERRORS error(s) found. Fix the gaps above before /review."
    exit 1
fi
