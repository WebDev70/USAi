#!/usr/bin/env bash
# scripts/doc-consistency-check.sh
# RAIL Phase 3 — Convention-duplication detector.
#
# WHY: The USAi coding-convention rules (CSS cache-bust, SSRF guard, tool-gating,
# etc.) have a single canonical source: docs/rail-pipeline.md.  If any of these
# convention phrases appears verbatim in another "enforcing" file (AGENTS.md,
# .clinerules/rail-pipeline.md, docs/tooling/*.md) it will silently drift out of
# sync when the canonical copy is updated.  This script detects that duplication
# and exits non-zero so the CI / /review gate can catch it.
#
# Usage:
#   ./scripts/doc-consistency-check.sh       # from project root
#
#   REPO_ROOT=/path/to/repo ./scripts/doc-consistency-check.sh   # for tests
#
# Exit codes:
#   0 — all convention phrases appear only in the canonical source (or exempt files)
#   1 — one or more phrases found verbatim in ≥1 non-canonical enforcing file
#   2 — usage/setup error (canonical source file missing)
#
# Design decisions:
#   - CANONICAL_FILE is docs/rail-pipeline.md — the single source of truth.
#   - ENFORCING_FILES are the "rule-restating" surface: AGENTS.md, the .clinerules
#     always-on rule, and the harness tooling guides.  These should LINK to the
#     canonical source, not copy it.
#   - EXEMPT_FILES are docs-of-record (CHANGELOG, backlog, ARCHITECTURE, specs,
#     this script itself) where the phrases appear legitimately for history or
#     architecture explanation — not as rule repetition.
#   - Bash 3.2-compatible: no mapfile, no declare -A.

set -uo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
CANONICAL_FILE="docs/rail-pipeline.md"

# Files we actively enforce "no duplication of convention prose" against.
# Only these files are checked — everything else (CHANGELOG, specs, etc.) is
# excluded to avoid false positives on legitimate historical/architectural refs.
ENFORCING_FILES=(
    "AGENTS.md"
    ".clinerules/rail-pipeline.md"
    "docs/tooling/cline.md"
    "docs/tooling/continue.md"
)

# ---------------------------------------------------------------------------
# Convention phrases to check.
# These are the "fingerprint" of each convention rule in the canonical source.
# A phrase triggers a failure if it is found verbatim (case-sensitive) in any
# ENFORCING_FILE (other than the canonical source itself).
#
# Phrase selection criteria:
#   - Specific enough to identify the rule (not a common English fragment)
#   - Present verbatim in docs/rail-pipeline.md
#   - Short enough to avoid false-positive matching across docs
# ---------------------------------------------------------------------------
PHRASES=(
    "styles.css?v=N"
    "is_safe_upstream_url"
    "TOOL_REGISTRY"
    "getEnabledTools"
    "_handler"
)

# ---------------------------------------------------------------------------
# Validate canonical source exists
# ---------------------------------------------------------------------------
CANONICAL_ABS="$REPO_ROOT/$CANONICAL_FILE"
if [ ! -f "$CANONICAL_ABS" ]; then
    echo "ERROR: canonical source not found: $CANONICAL_ABS" >&2
    echo "  (Set REPO_ROOT to the project root if running outside the repo.)" >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Check each phrase against each enforcing file
# ---------------------------------------------------------------------------
ERRORS=0
OFFENDERS=""

echo "═══════════════════════════════════════════════════════════════"
echo "  doc-consistency-check.sh — convention-duplication detector"
echo "  Canonical source: $CANONICAL_FILE"
echo "  REPO_ROOT: $REPO_ROOT"
echo "═══════════════════════════════════════════════════════════════"
echo ""

for phrase in "${PHRASES[@]}"; do
    phrase_has_offender=0
    for rel_file in "${ENFORCING_FILES[@]}"; do
        abs_file="$REPO_ROOT/$rel_file"
        # Skip if the enforcing file doesn't exist (not yet created, or optional)
        [ -f "$abs_file" ] || continue

        # Check if the phrase appears verbatim in the enforcing file
        if grep -qF "$phrase" "$abs_file" 2>/dev/null; then
            OFFENDERS="${OFFENDERS}\n  ✕  Phrase '${phrase}' found in '${rel_file}'"
            ERRORS=$((ERRORS + 1))
            phrase_has_offender=1
        fi
    done
    if [ "$phrase_has_offender" -eq 0 ]; then
        echo "  ✓  '${phrase}' — canonical only"
    fi
done

echo ""

# ---------------------------------------------------------------------------
# Guard 1 — Stale-path guard (AC-1, item #58)
#
# WHY: The directory reorg in #56 moved tests to frontend/tests/js/ and
# backend/tests/python/.  Workflow docs in .clinerules/ and docs/tooling/
# must not reference the old flat paths or they silently mislead.
#
# Stale phrases to detect (verbatim substring match):
#   tests/js/         — old flat JS test dir
#   tests/python/     — old flat Python test dir
#   node --check app.js      — old syntax gate (app.js moved to frontend/)
#   py_compile server.py     — old syntax gate (server.py moved to backend/)
#
# Note: 'tests/js/' is a stale substring of 'frontend/tests/js/' only if
# the full string appears without the 'frontend/' prefix.  grep -F looks for
# the exact substring, so 'tests/js/' will match inside 'frontend/tests/js/'
# too — we therefore match the bare path WITHOUT a preceding word character,
# i.e. we use grep -E '(^|[^/a-z])tests/js/' to avoid false positives on
# the correct 'frontend/tests/js/' form.  For simplicity and Bash 3.2
# compat, we use grep with a negative look-behind equivalent: check for the
# stale form but exclude lines that contain the correct prefix.
# ---------------------------------------------------------------------------
echo "--- Guard 1: Stale-path check ---"

STALE_PHRASES=(
    "tests/js/"
    "tests/python/"
    "node --check app.js"
    "py_compile server.py"
)

# Correct prefixes: if the line also contains these, it is the new path form.
STALE_CORRECT_SUBSTITUTES=(
    "frontend/tests/js/"
    "backend/tests/python/"
    "node --check frontend/app.js"
    "py_compile backend/server.py"
)

# Dirs to scan (recursive, only .md files)
STALE_SCAN_DIRS=(
    ".clinerules"
    "docs/tooling"
)

for i in 0 1 2 3; do
    stale_phrase="${STALE_PHRASES[$i]}"
    correct_form="${STALE_CORRECT_SUBSTITUTES[$i]}"
    for scan_dir in "${STALE_SCAN_DIRS[@]}"; do
        abs_scan="$REPO_ROOT/$scan_dir"
        [ -d "$abs_scan" ] || continue
        # Find .md files in this dir tree
        while IFS= read -r abs_file; do
            rel_file="${abs_file#$REPO_ROOT/}"
            # Check if the stale phrase appears in this file
            if grep -qF "$stale_phrase" "$abs_file" 2>/dev/null; then
                # Exclude lines where the correct form also appears on the same line
                # (i.e. the stale string appears as a substring of the correct path)
                # Use grep to find lines with the stale phrase but NOT the correct form
                matching_lines=$(grep -F "$stale_phrase" "$abs_file" | grep -vF "$correct_form")
                if [ -n "$matching_lines" ]; then
                    OFFENDERS="${OFFENDERS}\n  ✕  Stale path '${stale_phrase}' found in '${rel_file}'"
                    OFFENDERS="${OFFENDERS}\n     (use '${correct_form}' instead)"
                    ERRORS=$((ERRORS + 1))
                fi
            fi
        done < <(find "$abs_scan" -name "*.md" -type f 2>/dev/null)
    done
done

echo ""

# ---------------------------------------------------------------------------
# Guard 2 — Role-count consistency guard (AC-3, item #58)
#
# WHY: The RAIL pipeline has exactly 7 roles numbered 0–6.  The canonical
# phrase is "The RAIL roles (0-6)" in .clinerules/rail-pipeline.md.
# Sub-check A: that phrase must be PRESENT in .clinerules/rail-pipeline.md.
# Sub-check B: conflicting count phrases ("five roles", "six roles",
#              "seven roles") must NOT appear in any enforcing file.
# ---------------------------------------------------------------------------
echo "--- Guard 2: Role-count consistency check ---"

CLINERULES_RAIL="$REPO_ROOT/.clinerules/rail-pipeline.md"
# The canonical phrase uses an en-dash (U+2013) between 0 and 6. grep -F will
# match the UTF-8 byte sequence \xe2\x80\x93 which is what the file contains.
CANONICAL_ROLE_PHRASE="The RAIL roles (0"

# Sub-check A: canonical phrase "The RAIL roles (0…6)" must be present in
# .clinerules/rail-pipeline.md.  We grep for the prefix "The RAIL roles (0"
# which is unique enough regardless of whether an ASCII hyphen or en-dash is used.
if [ -f "$CLINERULES_RAIL" ]; then
    if ! grep -qF "$CANONICAL_ROLE_PHRASE" "$CLINERULES_RAIL" 2>/dev/null; then
        OFFENDERS="${OFFENDERS}\n  ✕  Role-count drift: 'The RAIL roles (0-6)' heading is absent from '.clinerules/rail-pipeline.md'"
        OFFENDERS="${OFFENDERS}\n     Add the '## The RAIL roles (0-6)' section heading back to keep role-count canonical."
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✓  'The RAIL roles (0-6)' present in .clinerules/rail-pipeline.md"
    fi
else
    echo "  ⚠  .clinerules/rail-pipeline.md not found — skipping role-count check"
fi

# Sub-check B: conflicting count phrase "N roles" must NOT appear in docs/tooling/
# files (NOT in .clinerules/ — the .clinerules/rail-pipeline.md legitimately says
# "seven roles numbered 0-6" and "six roles" referring to a subset, and
# .clinerules/workflows/govern.md has its own "five roles" for the governance board).
# We scope this check to docs/tooling/ where these phrases should never appear.
CONFLICTING_COUNTS=("five roles" "six roles" "seven roles")
ROLE_COUNT_SCAN_FILES=(
    "docs/tooling/cline.md"
    "docs/tooling/continue.md"
    "AGENTS.md"
)

for count_phrase in "${CONFLICTING_COUNTS[@]}"; do
    for rel_file in "${ROLE_COUNT_SCAN_FILES[@]}"; do
        abs_file="$REPO_ROOT/$rel_file"
        [ -f "$abs_file" ] || continue
        if grep -qiF "$count_phrase" "$abs_file" 2>/dev/null; then
            OFFENDERS="${OFFENDERS}\n  ✕  Role-count conflict: '${count_phrase}' found in '${rel_file}'"
            OFFENDERS="${OFFENDERS}\n     Use 'The RAIL roles (0-6) (apply in order)' or link to .clinerules/rail-pipeline.md."
            ERRORS=$((ERRORS + 1))
        fi
    done
done

echo ""

# ---------------------------------------------------------------------------
# Guard 3 — Mandatory-gate guard (AC-4, item #58)
#
# WHY: ./scripts/cli-check.sh --review is a mandatory gate — never optional.
# If any Cline doc describes it as "optional", that is incorrect and misleads
# developers into skipping a quality gate.
#
# Check: if "optional" appears on the same line as "cli-check.sh --review"
# in any .clinerules/ or docs/tooling/cline.md file, flag it.
# ---------------------------------------------------------------------------
echo "--- Guard 3: Mandatory-gate check ---"

GATE_PHRASE="cli-check.sh --review"

GATE_SCAN_FILES=(
    "docs/tooling/cline.md"
)

GATE_SCAN_DIRS=(
    ".clinerules"
)

for rel_file in "${GATE_SCAN_FILES[@]}"; do
    abs_file="$REPO_ROOT/$rel_file"
    [ -f "$abs_file" ] || continue
    # Find lines containing the gate phrase that also contain 'optional'
    bad_lines=$(grep -iF "$GATE_PHRASE" "$abs_file" | grep -i "optional")
    if [ -n "$bad_lines" ]; then
        OFFENDERS="${OFFENDERS}\n  ✕  Mandatory-gate drift: '${GATE_PHRASE}' described as optional in '${rel_file}'"
        OFFENDERS="${OFFENDERS}\n     cli-check.sh --review is a mandatory gate. Remove or correct the 'optional' qualifier."
        ERRORS=$((ERRORS + 1))
    fi
done

for scan_dir in "${GATE_SCAN_DIRS[@]}"; do
    abs_scan="$REPO_ROOT/$scan_dir"
    [ -d "$abs_scan" ] || continue
    while IFS= read -r abs_file; do
        rel_file="${abs_file#$REPO_ROOT/}"
        bad_lines=$(grep -iF "$GATE_PHRASE" "$abs_file" | grep -i "optional")
        if [ -n "$bad_lines" ]; then
            OFFENDERS="${OFFENDERS}\n  ✕  Mandatory-gate drift: '${GATE_PHRASE}' described as optional in '${rel_file}'"
            ERRORS=$((ERRORS + 1))
        fi
    done < <(find "$abs_scan" -name "*.md" -type f 2>/dev/null)
done

echo ""

# ---------------------------------------------------------------------------
# Guard 4 — Referenced-path existence guard (AC-2, item #59)
#
# WHY: Workflow docs in .clinerules/ and docs/tooling/ reference real files and
# directories (e.g. backend/server.py, frontend/app.js, scripts/cli-check.sh).
# If a directory reorg moves those files without updating the docs, the docs
# silently mislead contributors.  This guard extracts every backend/…,
# frontend/…, scripts/… path token and asserts it exists under $REPO_ROOT.
#
# Matching pattern:
#   (backend|frontend|scripts)/[A-Za-z0-9_./-]+
#
# Skipped tokens (no false positives):
#   - Tokens containing * (shell glob patterns — can't resolve to a specific path)
#   - Tokens containing $ (shell variable expansions — runtime value unknown)
#   - Tokens ending with _ (partial captures truncated just before a glob *)
#   - Tokens where the last path segment contains no . and the last char is not
#     alphanumeric (catches truncated captures like "frontend/backend" from prose)
#   - Trailing punctuation characters (., ), ', ") stripped before testing
#
# Bash 3.2-compatible: no mapfile, no declare -A.
# ---------------------------------------------------------------------------
echo "--- Guard 4: Referenced-path existence check ---"

REF_SCAN_DIRS=(
    ".clinerules"
    "docs/tooling"
)
# The pattern anchors to start of a path segment boundary: require that the
# captured token starts at a word boundary so "frontend/backend" prose is only
# captured as a whole token when followed by more path characters.
# We match at least two path segments (root/leaf) to skip prose words like
# "frontend/backend" that have no deeper path.
REF_PATH_PATTERN='(backend|frontend|scripts)/[A-Za-z0-9_./-]+'

for scan_dir in "${REF_SCAN_DIRS[@]}"; do
    abs_scan="$REPO_ROOT/$scan_dir"
    [ -d "$abs_scan" ] || continue
    while IFS= read -r abs_file; do
        rel_file="${abs_file#$REPO_ROOT/}"
        # Extract all path tokens matching the pattern, one per line
        while IFS= read -r token; do
            [ -z "$token" ] && continue
            # Skip tokens containing shell glob or variable characters
            case "$token" in
                *\** | *\$*) continue ;;
            esac
            # Strip trailing punctuation that grep captured alongside the path
            # (e.g. "backend/server.py." → "backend/server.py").
            # Use a two-pass approach: first strip trailing dot/comma/paren,
            # then strip trailing quote characters — Bash 3.2 + BSD sed safe.
            token=$(printf '%s' "$token" | sed 's/[.,)]*$//' | sed "s/['\"]//g")
            [ -z "$token" ] && continue
            # Skip bare directory references (token ends with /): these are
            # intentional path-prefix mentions, not file paths to validate.
            case "$token" in
                */) continue ;;
            esac
            # Skip tokens whose last character is a non-alphanum/dot (e.g.
            # "backend/tests/python/test_" captured just before a glob "*").
            last_char="${token##*[A-Za-z0-9.]}"
            if [ -n "$last_char" ]; then
                continue
            fi
            # Skip shallow two-segment tokens that contain no dot in the leaf
            # (e.g. "frontend/backend" extracted from prose "frontend/backend
            # SME routing" — a real file would have an extension or be a
            # known directory).  Shallow = exactly one slash, no dot in leaf.
            slash_count=$(printf '%s' "$token" | tr -cd '/' | wc -c | tr -d ' ')
            if [ "$slash_count" -eq 1 ]; then
                leaf="${token##*/}"
                case "$leaf" in
                    *.*) ;;          # has extension → validate normally
                    *)   continue ;; # no extension, no deeper path → skip
                esac
            fi
            target="$REPO_ROOT/$token"
            if [ ! -e "$target" ]; then
                OFFENDERS="${OFFENDERS}\n  ✕  Missing path '${token}' referenced in '${rel_file}'"
                ERRORS=$((ERRORS + 1))
            fi
        done < <(grep -Eo "$REF_PATH_PATTERN" "$abs_file" 2>/dev/null || true)
    done < <(find "$abs_scan" -name "*.md" -type f 2>/dev/null)
done

echo ""

# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------
if [ "$ERRORS" -eq 0 ]; then
    echo "✓ PASS — all convention phrases are confined to the canonical source."
    echo "         ($CANONICAL_FILE)"
    exit 0
else
    echo "✕ FAIL — $ERRORS convention phrase(s) duplicated in enforcing file(s):"
    printf '%b\n' "$OFFENDERS"
    echo ""
    echo "  Fix: replace the duplicated prose in each offending file with a"
    echo "  reference link to the canonical source:"
    echo "    docs/rail-pipeline.md"
    echo ""
    echo "  Ratchet rule: conventions live in ONE place only."
    exit 1
fi
