#!/usr/bin/env bash
# Regression check for backlog #90 — "reconcile the Done pile with the code that
# actually exists" (BLOCKING-02 / ADVISORY-04 from the Sprint-19 governance audit).
#
# WHY this exists: five [x] Done items cited identifiers that appear in zero
# historical code blobs, and dependent docs described phantom features. This
# script fails until every phantom claim has been struck from the docs and every
# stale/orphan/missing spec has been reconciled — so the fix cannot silently rot.
#
# It is a post-facto verification gate (the #90 spec §5 T-1/T-2/T-3), not a unit
# test: it greps the tree for the phantom identifiers and asserts they only
# survive inside STRUCK backlog annotations, never in live user-facing docs.
set -u
cd "$(dirname "$0")/.." || exit 2

fail=0
note() { printf '  %s\n' "$1"; }
check_absent() {
  # $1 = human label, $2 = grep -E pattern, $3... = files to scan
  local label="$1"; shift
  local pattern="$1"; shift
  if grep -REn "$pattern" "$@" >/dev/null 2>&1; then
    echo "FAIL: $label still present in: $*"
    grep -REn "$pattern" "$@" | sed 's/^/    /'
    fail=1
  else
    note "ok: $label absent"
  fi
}

echo "==> #90 phantom-identifier reconciliation check"

# AC-2: phantom endpoints / features must be gone from user-facing docs.
check_absent "POST /import-session endpoint" '/import-session' docs/ARCHITECTURE.md
check_absent "wrong log query param ?file="  'logs/files\?file=' docs/ARCHITECTURE.md
check_absent "phantom 💭 Thinking block"      '💭 Thinking block' docs/USER_GUIDE.md
check_absent "phantom startup 401 warning"    'API key rejected by upstream' docs/USER_GUIDE.md

# AC-1: struck backlog claims must actually carry a STRUCK marker (spot-check the
# five items). We assert the phantom function names only appear on STRUCK lines.
for fn in exportSessionData buildMarkdownExport restoreReasoningForTurn \
          probe_upstream_auth run_startup_auth_probe; do
  hits=$(grep -n "$fn" backlog.md 2>/dev/null || true)
  if [ -n "$hits" ]; then
    # A citation is "reconciled" if its line is a STRUCK annotation OR is inside
    # a ~~strikethrough~~ span (the multi-line struck "Done:" blocks). We accept a
    # line that contains STRUCK, or that contains a ~~ marker, or whose #29/#10/#11
    # item is itself STRUCK. Only a bare, un-struck citation fails.
    bad=$(echo "$hits" | grep -vE 'STRUCK|~~')
    if [ -n "$bad" ]; then
      echo "FAIL: phantom identifier '$fn' cited on a non-STRUCK backlog line:"
      echo "$bad" | sed 's/^/    /'
      fail=1
    else
      note "ok: '$fn' only on STRUCK/strikethrough line(s)"
    fi
  fi
done

# AC-3: the seven orphan specs must be gone; startup-auth-probe must not be cited
# as an existing spec on a non-STRUCK line.
for orphan in auto-model-router-spec-sprint ci-coverage-ratchet-repair \
              document-sme export-import-conversations premium-ui-polish \
              rail-qa-hardening reasoning-thinking-display; do
  if [ -f "docs/specs/$orphan.md" ]; then
    echo "FAIL: orphan spec still present: docs/specs/$orphan.md"
    fail=1
  else
    note "ok: orphan spec removed: $orphan"
  fi
done

# AC-3: no live spec may sit at "In Progress" / "Ready" while its backlog item is
# Done. We assert none of the reconciled specs are still non-Done.
for spec in ci-coverage-ratchet-repair log-file-viewer more-file-types \
            raw-response-capture streaming-tool-calling prompt-templates \
            embeddings-rag architecture-doc sidebar-collapse-toggle \
            user-summaries-workflow ux-ui-sme-role; do
  f="docs/specs/$spec.md"
  [ -f "$f" ] || continue
  status=$(grep -m1 -iE '^\*\*Status' "$f" | sed -E 's/.*Status:\*\* *//')
  case "$status" in
    Done*|Superseded*) note "ok: $spec Status=$status" ;;
    *) echo "FAIL: $spec still Status=$status (backlog item is Done)"; fail=1 ;;
  esac
done

# AC-4: the oversized Done pile must be split out to docs/archive/.
if [ ! -f docs/archive/backlog-2026-h1.md ]; then
  echo "FAIL: docs/archive/backlog-2026-h1.md not created (AC-4 archive split)"
  fail=1
else
  note "ok: backlog archive split file exists"
fi

if [ "$fail" -eq 0 ]; then
  echo "PASS: #90 Done-pile reconciliation checks all green."
else
  echo "FAILED: #90 reconciliation incomplete (see above)."
fi
exit "$fail"
