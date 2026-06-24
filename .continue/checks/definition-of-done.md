---
name: Definition of Done
description: The change satisfies the full finish line — tests+coverage, security scan, QA checks, acceptance, docs, and a memory note
---

Meta-check that asserts the **single finish line** from the Agile workflow
(`.continue/rules/agile-workflow.md`). It confirms the *other* gates and the
non-code "done" obligations were satisfied — so nothing ships half-finished.

Pass only if **all applicable** items hold (skip the ones that genuinely don't
apply to this change, e.g. acceptance criteria for a pure bugfix):

1. **Tests-first & green.** New/changed logic has corresponding tests (ideally
   written first, TDD), and `./run-tests.sh` passes. Bug fixes include a regression
   test. *(Overlaps `test-coverage`.)*
2. **Coverage gates pass.** `./run-tests.sh --coverage` meets thresholds
   (`server.py` ≥ 90%, JS branch ≥ 70%).
3. **Security gate clean.** No runtime dependency added; `scripts/security-scan.sh`
   findings are clean or explicitly triaged. *(Overlaps `security-review` /
   `dependency-and-supply-chain-review`.)*
4. **Infra/config sane** (if touched). `.env.example` is in sync; no secrets in
   infra; commands declarative. *(Overlaps `iac-review`.)*
5. **Acceptance criteria met** (features). *(Overlaps `acceptance-criteria`.)*
6. **Docs in sync.** CHANGELOG always; USER_GUIDE/README/backlog/CONTINUE/AGENTS as
   applicable. *(Overlaps `docs-in-sync`.)*
7. **Memory note recorded.** A learning/session note was (or will be) written to
   `Continue Extension/memories/` per the Continuous Improvement role and
   `AGENTS.md`.

Flag as **failing** if any applicable item above is clearly unmet — most commonly:
a feature with no CHANGELOG/USER_GUIDE update, code with no tests, a skipped
security scan, or no memory note for a substantive change.

If the change is trivial (typo/comment/config-only with no behavior change), pass.
