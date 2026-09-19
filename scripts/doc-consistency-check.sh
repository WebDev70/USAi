#!/usr/bin/env bash
# Detect duplicated conventions, stale paths, role-count drift, and broken paths
# in live policy documents. Historical records are intentionally outside this scan.
set -uo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
CANONICAL_FILE="docs/rail-pipeline.md"
CANONICAL_ABS="$REPO_ROOT/$CANONICAL_FILE"

if [ ! -f "$CANONICAL_ABS" ]; then
    echo "ERROR: canonical source not found: $CANONICAL_FILE" >&2
    exit 2
fi

ERRORS=0
OFFENDERS=""

add_error() {
    OFFENDERS="${OFFENDERS}\n  ✕  $1"
    ERRORS=$((ERRORS + 1))
}

# ---------------------------------------------------------------------------
# Scan scopes — deliberately PER-GUARD, not one unified list.
#
# WHY per-guard (#87): the phrase guard is intentionally NARROW — only the four
# "rule-restating" files that are supposed to LINK to the canonical doc rather
# than copy it.  The stale-path, mandatory-gate and referenced-path guards are
# intentionally WIDE — recursive over whole rule/workflow directories, because a
# broken path misleads a contributor wherever it appears.
#
# Collapsing these into a single list is what silently narrowed this guard: once
# unified, the wide dirs had to be dropped to avoid the (legitimate) phrase hits
# in .clinerules/workflows/*.md, which left all 13 Cline rule files unguarded.
# Keep the scopes separate so neither concern can weaken the other.
# ---------------------------------------------------------------------------

# Phrase guard: must link to the canonical doc, never restate it verbatim.
PHRASE_FILES="AGENTS.md
.clinerules/rail-pipeline.md
docs/tooling/cline.md
docs/tooling/continue.md"

# Recursive dirs for the stale-path / mandatory-gate / referenced-path guards.
# Both harnesses' rule dirs are scanned: a broken path misleads a contributor (or
# an agent) wherever it appears, and .continue/rules/ had accumulated 12 stale
# paths precisely because no guard watched it (#87 follow-up).
# docs/quality is included because review-checks/*.md are live gate criteria that
# `cn review` executes against — not historical records.
# .roo/ is optional until the Zoo migration (#86) lands: a missing dir is
# skipped, not an error, so this script works on both branches.
SCAN_DIRS=".clinerules
.continue/rules
docs/tooling
docs/quality
.roo"

# Individually-named live docs for the wide guards. These are listed file-by-file
# rather than scanning docs/ recursively ON PURPOSE: docs/specs/ holds completed
# specs that are historical records — they legitimately cite the paths and commands
# that were correct when they were written, and rewriting them would falsify the
# record. Only docs that describe how the project works TODAY belong here.
SCAN_EXTRA_FILES="README.md
docs/ARCHITECTURE.md
docs/EMBEDDINGS_GUIDE.md
docs/ORGANIZATION.md
docs/USER_GUIDE.md
docs/governance.md
docs/harness-workflow-diagram.md
docs/principles.md
docs/rail-pipeline.md"

# Role-count guard: these must not declare a count competing with the canonical
# doc. .clinerules/ is excluded on purpose — rail-pipeline.md there legitimately
# says "seven roles numbered 0-6" and workflows/govern.md says "five roles" for
# the governance board, both of which are correct in their own context.
ROLE_COUNT_FILES="AGENTS.md
docs/tooling/cline.md
docs/tooling/continue.md"

# Expand a newline-separated list of repo-relative paths to absolute paths,
# dropping entries that do not exist. Bash 3.2-safe (no mapfile/declare -A).
_abs_existing() {
    while IFS= read -r rel; do
        [ -n "$rel" ] || continue
        [ -f "$REPO_ROOT/$rel" ] || continue
        printf '%s\n' "$REPO_ROOT/$rel"
    done
}

# Expand SCAN_DIRS to every .md file inside them (recursive).
SCAN_FILES=""
while IFS= read -r rel_dir; do
    [ -n "$rel_dir" ] || continue
    abs_dir="$REPO_ROOT/$rel_dir"
    [ -d "$abs_dir" ] || continue
    while IFS= read -r file; do
        SCAN_FILES="${SCAN_FILES}${SCAN_FILES:+
}${file}"
    done < <(find "$abs_dir" -type f -name '*.md' 2>/dev/null)
done <<< "$SCAN_DIRS"

# Append the individually-named live docs to the same wide-guard file list.
while IFS= read -r file; do
    [ -n "$file" ] || continue
    SCAN_FILES="${SCAN_FILES}${SCAN_FILES:+
}${file}"
done <<< "$(printf '%s\n' "$SCAN_EXTRA_FILES" | _abs_existing)"

PHRASE_ABS=$(printf '%s\n' "$PHRASE_FILES" | _abs_existing)
ROLE_COUNT_ABS=$(printf '%s\n' "$ROLE_COUNT_FILES" | _abs_existing)

echo "═══════════════════════════════════════════════════════════════"
echo "  doc-consistency-check.sh — live policy consistency"
echo "  Canonical source: $CANONICAL_FILE"
echo "═══════════════════════════════════════════════════════════════"

# Guard 3: The canonical source document MUST contain the canonical role phrase.
CANONICAL_ROLE_PHRASE="The RAIL roles (0"
if ! grep -qF "$CANONICAL_ROLE_PHRASE" "$CANONICAL_ABS"; then
    add_error "Canonical file '$CANONICAL_FILE' is missing required phrase: '$CANONICAL_ROLE_PHRASE'..."
fi

PHRASES=(
    "styles.css?v=N"
    "is_safe_upstream_url"
    "TOOL_REGISTRY"
    "getEnabledTools"
    "_handler"
)

for phrase in "${PHRASES[@]}"; do
    found=0
    while IFS= read -r abs_file; do
        [ -n "$abs_file" ] || continue
        if grep -qF "$phrase" "$abs_file" 2>/dev/null; then
            rel_file="${abs_file#$REPO_ROOT/}"
            add_error "Convention phrase '${phrase}' found in '${rel_file}'"
            found=1
        fi
    done <<< "$PHRASE_ABS"
    if [ "$found" -eq 0 ]; then
        echo "  ✓  '${phrase}' — canonical only"
    fi
done

STALE_PHRASES=(
    "tests/js"
    "tests/python"
    "node --check app.js"
    "py_compile server.py"
)
# Matched as boundary-aware EREs rather than substring + "correct form" filter.
#
# WHY NOT `grep -F stale | grep -vF correct`: that had two defects, both found by
# running the guard over docs/ rather than by reading it.
#   1. FALSE POSITIVE — `tests/js-coverage.mjs` (a real file at the repo root) was
#      reported as stale `tests/js`. The leading `tests/` here is not the test dir
#      at all. A trailing `/` in the phrase used to prevent this by accident; once
#      the slash was dropped to catch `-s tests/python`, the protection went too.
#   2. FALSE NEGATIVE — a line holding BOTH a stale and a correct reference was
#      filtered out wholesale by `grep -vF`, masking genuine drift.
# The patterns below require a non-path character before the match (so
# `backend/tests/python` is excluded structurally, not by subtraction) and a
# non-identifier character after it (so `tests/js-coverage.mjs` is excluded).
STALE_PATTERNS=(
    '(^|[^/A-Za-z0-9_-])tests/js(/|[^A-Za-z0-9_.-]|$)'
    '(^|[^/A-Za-z0-9_-])tests/python(/|[^A-Za-z0-9_.-]|$)'
    'node --check app\.js'
    'py_compile server\.py'
)
STALE_CORRECT_SUBSTITUTES=(
    "frontend/tests/js"
    "backend/tests/python"
    "node --check frontend/app.js"
    "py_compile backend/server.py"
)

for i in 0 1 2 3; do
    stale_phrase="${STALE_PHRASES[$i]}"
    stale_pattern="${STALE_PATTERNS[$i]}"
    correct_form="${STALE_CORRECT_SUBSTITUTES[$i]}"
    while IFS= read -r abs_file; do
        [ -n "$abs_file" ] || continue
        matching_lines=$(grep -nE -- "$stale_pattern" "$abs_file" 2>/dev/null || true)
        if [ -n "$matching_lines" ]; then
            rel_file="${abs_file#$REPO_ROOT/}"
            add_error "Stale path '${stale_phrase}' found in '${rel_file}' (use '${correct_form}')"
        fi
    done <<< "$SCAN_FILES"
done

# The canonical role model belongs only in docs/rail-pipeline.md. Other live
# policy documents may link to it, but must not declare a competing role count.
CONFLICTING_COUNTS=("five roles" "six roles" "seven roles")
for count_phrase in "${CONFLICTING_COUNTS[@]}"; do
    while IFS= read -r abs_file; do
        [ -n "$abs_file" ] || continue
        if grep -qiF "$count_phrase" "$abs_file" 2>/dev/null; then
            rel_file="${abs_file#$REPO_ROOT/}"
            add_error "Role-count conflict '${count_phrase}' found in '${rel_file}'"
        fi
    done <<< "$ROLE_COUNT_ABS"
done

# The neutral gate is mandatory. No live policy document may call it optional.
while IFS= read -r abs_file; do
    [ -n "$abs_file" ] || continue
    bad_lines=$(grep -iF "quality-gate.sh" "$abs_file" 2>/dev/null | grep -i "optional" || true)
    if [ -n "$bad_lines" ]; then
        rel_file="${abs_file#$REPO_ROOT/}"
        add_error "Mandatory gate 'quality-gate.sh' described as optional in '${rel_file}'"
    fi
done <<< "$SCAN_FILES"

REF_PATH_PATTERN='(backend|frontend|scripts)/[A-Za-z0-9_./$*-]+'
while IFS= read -r abs_file; do
    [ -n "$abs_file" ] || continue
    rel_file="${abs_file#$REPO_ROOT/}"
    while IFS= read -r token; do
        [ -n "$token" ] || continue
        case "$token" in
            *\** | *\$*) continue ;;
        esac
        token=$(printf '%s' "$token" | sed 's/[.,)]*$//' | sed "s/['\"]//g")
        [ -n "$token" ] || continue
        case "$token" in
            */) continue ;;
        esac
        last_char="${token##*[A-Za-z0-9.]}"
        [ -z "$last_char" ] || continue
        slash_count=$(printf '%s' "$token" | tr -cd '/' | wc -c | tr -d ' ')
        if [ "$slash_count" -eq 1 ]; then
            leaf="${token##*/}"
            case "$leaf" in
                *.*) ;;
                *) continue ;;
            esac
        fi
        if [ ! -e "$REPO_ROOT/$token" ]; then
            add_error "Missing path '${token}' referenced in '${rel_file}'"
        fi
    done < <(grep -Eo "$REF_PATH_PATTERN" "$abs_file" 2>/dev/null || true)
done <<< "$SCAN_FILES"

if [ "$ERRORS" -eq 0 ]; then
    echo "✓ PASS — live policy documents are consistent with $CANONICAL_FILE"
    exit 0
fi

echo "✕ FAIL — $ERRORS live-policy consistency error(s):"
printf '%b\n' "$OFFENDERS"
echo "  Fix live policy or link it to $CANONICAL_FILE."
exit 1
