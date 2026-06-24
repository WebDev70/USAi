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
