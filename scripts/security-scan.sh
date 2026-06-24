#!/usr/bin/env bash
# USAi Chat — DevSecOps security scan (DEV/CI-ONLY tooling; ships nothing in the app).
#
# WHY this exists:
#   RAIL's `security-review` /check is an LLM judgment gate. Top-tier DevSecOps also
#   needs DETERMINISTIC, machine-enforced scanning that fails the same way every
#   time. This script shifts security left into three classic gates:
#     1. SECRET SCANNING  — gitleaks: no secret ever reaches git history.
#     2. SAST             — bandit:   static analysis of server.py for insecure code.
#     3. DEPENDENCY AUDIT — pip-audit: CVE check of our (tiny) runtime dependency.
#
#   All three are DEV/CI tooling per docs/principles.md §1 — none is imported by
#   app.js/server.py or added to requirements.txt, so the app's minimal runtime
#   surface is unchanged.
#
# Usage:
#   ./scripts/security-scan.sh            # run every available scanner
#   ./scripts/security-scan.sh --strict   # FAIL (exit 1) if a scanner is missing
#
# Tools are auto-skipped (with install hints) when absent, so the script is usable
# on a fresh machine; CI installs them so the gate is real there. Exit code is
# non-zero if any scanner that DID run found an issue.
set -uo pipefail
cd "$(dirname "$0")/.."   # project root

STRICT=0
[ "${1:-}" = "--strict" ] && STRICT=1

FAILED=0       # a scanner that ran reported a finding
MISSING=0      # a scanner wasn't installed

have() { command -v "$1" >/dev/null 2>&1; }

note_missing() {
  local tool="$1" hint="$2"
  MISSING=1
  if [ "$STRICT" -eq 1 ]; then
    echo "  ✕ $tool not installed (required in --strict). Install: $hint"
    FAILED=1
  else
    echo "  ⚠ $tool not installed — skipping. Install (dev-only): $hint"
  fi
}

echo "══ 1/3 Secret scanning (gitleaks) ════════════════════════════════"
if have gitleaks; then
  # Scan the working tree AND git history for committed secrets.
  if gitleaks detect --no-banner --redact --source . ; then
    echo "  ✓ no secrets detected"
  else
    echo "  ✕ gitleaks found potential secret(s) — see above"
    FAILED=1
  fi
else
  note_missing "gitleaks" "brew install gitleaks"
fi

echo
echo "══ 2/3 SAST (bandit on server.py) ════════════════════════════════"
# Prefer the venv's bandit so it matches the dev environment.
PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"
if "$PY" -m bandit --version >/dev/null 2>&1; then
  # -ll = report medium+ severity; server.py is the only first-party Python file.
  if "$PY" -m bandit -ll -r server.py ; then
    echo "  ✓ no medium+ severity issues"
  else
    echo "  ✕ bandit found issue(s) — see above"
    FAILED=1
  fi
else
  note_missing "bandit" "$PY -m pip install bandit"
fi

echo
echo "══ 3/3 Dependency CVE audit (pip-audit) ══════════════════════════"
# Documented, reviewed advisory ignores. Each MUST have a justification comment.
#   GHSA-mf9w-mj56-hr94 (CVE-2026-28684): python-dotenv set_key()/unset_key()
#     symlink overwrite, fixed in 1.2.2. NOT EXPLOITABLE here — the app only ever
#     calls load_dotenv() (never set_key/unset_key). We can't pin >=1.2.2 because
#     it requires Python >=3.10 and we support the 3.9 baseline, so we ignore this
#     specific advisory ID with the above justification. Revisit when 3.9 is
#     dropped, then pin >=1.2.2 and remove this ignore.
PIP_AUDIT_IGNORE=(--ignore-vuln GHSA-mf9w-mj56-hr94)
if "$PY" -m pip_audit --version >/dev/null 2>&1; then
  if "$PY" -m pip_audit "${PIP_AUDIT_IGNORE[@]}" -r requirements.txt ; then
    echo "  ✓ no known (unignored) vulnerabilities in runtime deps"
  else
    echo "  ✕ pip-audit found vulnerable dependency(ies) — see above"
    FAILED=1
  fi
else
  note_missing "pip-audit" "$PY -m pip install pip-audit"
fi

echo
if [ "$FAILED" -ne 0 ]; then
  echo "══ security-scan FAILED ✕ ════════════════════════════════════════"
  exit 1
fi
if [ "$MISSING" -ne 0 ]; then
  echo "══ security-scan: passed (some scanners skipped) ⚠ ═══════════════"
else
  echo "══ security-scan: all scanners passed ✓ ═════════════════════════"
fi
