#!/usr/bin/env bash
# USAi Chat — CLI equivalent of the VS Code extension's `/check` QA gate.
#
# WHY this exists:
#   The extension's `/check` workflow (which executes the .continue/checks/*.md
#   review files) is an EXTENSION-ONLY feature — the Continue CLI (`cn`) has no
#   `/check` slash command. This script reproduces the *intent* of that gate for
#   CLI / headless use by:
#     1. Running the real automated validation those checks ultimately enforce
#        (syntax gates + tests + coverage via ./run-tests.sh --coverage), and
#     2. (optionally) launching `cn review` with the repo's check criteria fed in
#        as rules, so the AI review applies the same standards as the extension.
#
# This keeps RAIL's QA-Review step (Step 4) usable from the terminal.
#
# Usage:
#   ./scripts/cli-check.sh              # run the automated gate only (tests + coverage)
#   ./scripts/cli-check.sh --review     # also run `cn review` with the check files as rules
#   ./scripts/cli-check.sh --review-only# skip tests; just run the AI review gate
#
# Exit code is non-zero if the automated gate fails (so it's CI/pre-push friendly).
set -euo pipefail
cd "$(dirname "$0")/.."   # project root

REVIEW=0
RUN_TESTS=1
case "${1:-}" in
  --review)      REVIEW=1 ;;
  --review-only) REVIEW=1; RUN_TESTS=0 ;;
  "")            ;;
  *) echo "Unknown option: $1"; echo "Use: --review | --review-only | (no args)"; exit 2 ;;
esac

# The repo's check definitions — the same files the extension's /check runs.
# Product-Owner-gated checks (definition-of-ready / acceptance-criteria /
# definition-of-done) are included here so the full ten-check QA gate described in
# docs/rail-pipeline.md is reachable from the CLI.
CHECKS_DIR=".continue/checks"
CHECK_FILES=(
  "$CHECKS_DIR/test-coverage.md"
  "$CHECKS_DIR/security-review.md"
  "$CHECKS_DIR/dependency-and-supply-chain-review.md"
  "$CHECKS_DIR/iac-review.md"
  "$CHECKS_DIR/code-quality-review.md"
  "$CHECKS_DIR/docs-in-sync.md"
  "$CHECKS_DIR/ui-ux-review.md"
  "$CHECKS_DIR/definition-of-ready.md"
  "$CHECKS_DIR/acceptance-criteria.md"
  "$CHECKS_DIR/definition-of-done.md"
)

if [ "$RUN_TESTS" -eq 1 ]; then
  echo "══ Automated gate: ./run-tests.sh --coverage ════════════════════"
  # Mirrors test-coverage.md: syntax gates + JS/Python tests + coverage thresholds.
  ./run-tests.sh --coverage
  echo "✓ Automated gate passed"

  echo
  echo "══ DevSecOps gate: ./scripts/security-scan.sh --strict ══════════"
  # Mirrors security-review.md + dependency-and-supply-chain-review.md with
  # DETERMINISTIC scanners (gitleaks/bandit/pip-audit). --strict causes the gate
  # to FAIL if any scanner is absent — this is a QA gate, not a quick local scan,
  # so all three scanners must be installed (run `make setup` first).
  ./scripts/security-scan.sh --strict

  # Spec↔build compliance check (RAIL Phase 1).
  # Run spec-check.sh if a spec file is provided via SPEC_FILE env var.
  # In CI or manual use: SPEC_FILE=docs/specs/my-feature.md ./scripts/cli-check.sh
  if [ -n "${SPEC_FILE:-}" ]; then
    echo
    echo "══ Spec↔build gate: ./scripts/spec-check.sh ═════════════════════"
    # Mirrors /review §6a: verifies §3 file list and §5 test plan match the diff.
    ./scripts/spec-check.sh "$SPEC_FILE"
    echo "✓ Spec compliance gate passed"
  fi

  echo
  echo "══ Convention-duplication gate: ./scripts/doc-consistency-check.sh ═"
  # RAIL Phase 3: verifies convention phrases live only in docs/rail-pipeline.md
  # and have been removed from AGENTS.md, .clinerules/, and docs/tooling/*.md.
  ./scripts/doc-consistency-check.sh
  echo "✓ Convention-duplication gate passed"
fi

if [ "$REVIEW" -eq 1 ]; then
  # `cn review` runs an AI review on the working changes. We pass the repo's check
  # criteria as rules (the CLI's --rule accepts file paths) so the review applies
  # the same standards the extension's /check enforces. We only include check files
  # that actually exist, so the script keeps working if a check is added/removed.
  RULE_ARGS=()
  for f in "${CHECK_FILES[@]}"; do
    [ -f "$f" ] && RULE_ARGS+=(--rule "$f")
  done

  echo
  echo "══ AI review: cn review (with .continue/checks/*.md as rules) ════"
  if ! command -v cn >/dev/null 2>&1 && [ -z "${CN_CMD:-}" ]; then
    # No `cn` on PATH (you installed via npx). Fall back to npx with the local config.
    CN_CMD="npx @continuedev/cli --config $HOME/.continue/config.yaml"
  fi
  CN_CMD="${CN_CMD:-cn}"
  echo "  using: $CN_CMD review ${RULE_ARGS[*]}"
  # shellcheck disable=SC2086
  $CN_CMD review "${RULE_ARGS[@]}"
fi

echo
echo "══ cli-check complete ✓ ═════════════════════════════════════════"
