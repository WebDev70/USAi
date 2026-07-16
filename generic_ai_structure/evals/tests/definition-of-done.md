# Definition of Done

Use before declaring any non-trivial task complete.

## Done checklist

- [ ] Definition of Ready was completed or marked N/A.
- [ ] Acceptance criteria are met and evidenced.
- [ ] Spec compliance matrix is complete.
- [ ] Required tests/evals passed.
- [ ] Required coverage or quality thresholds passed, or justified when unavailable.
- [ ] TDD evidence exists for non-trivial testable logic, or no-test justification is recorded.
- [ ] Security review has no blocking findings.
- [ ] Dependency and supply-chain review has no blocking findings.
- [ ] Infrastructure/config review has no blocking findings.
- [ ] Code/artifact quality review has no blocking findings.
- [ ] Documentation, prompt, data, and changelog updates are complete or N/A.
- [ ] Gap list contains no unresolved blocking gaps.
- [ ] Advisory gaps are tracked in a follow-up artifact.
- [ ] Trace is complete.
- [ ] Scorecard is complete for non-trivial work.
- [ ] Continuous-improvement lessons are captured when applicable.

## Automatic fail conditions

The task is not done if any of these are true:

- Any required acceptance criterion is unmet.
- Required full check suite fails.
- Required tests were skipped without justification.
- Secrets or credentials are exposed.
- Security review has unresolved blocking findings.
- Spec compliance fails for required scope.
- Documentation or prompt updates are required but missing.
- Blocking gaps remain unresolved.

## Done decision

- Decision: Done | Not Done | Done with tracked advisory follow-ups
- Evidence summary:
- Deferred advisory items:
- Approver/reviewer:
