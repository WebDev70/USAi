# RAIL Scorecard

Score a completed task from 1 to 5 in each category. Use this scorecard after the review checklist and before final acceptance.

## Pass/fail policy

A task passes only when all of these conditions are true:

- No automatic fail condition is present.
- No unresolved blocking gaps remain.
- Overall average score is 4.0 or higher.
- No individual required category scores below 3.
- Deferred advisory follow-ups are recorded in the follow-up log or target project backlog.

## Automatic fail conditions

- Missing Definition of Ready for feature or product-facing work.
- Missing acceptance criteria evidence for required user-facing behavior.
- Required full check-suite not run and no approved justification recorded.
- Security review missing for non-trivial work.
- Secret, credential, or sensitive private data found in committed artifacts.
- Failing required test/eval/check with no accepted deferment.
- Out-of-scope changes not explained in the spec compliance matrix.
- User-facing control or interaction added with no stated user goal.
- Multi-step user-facing interaction added with no described user flow.
- Control placed in the wrong information-architecture area without documented rationale.
- Blocking gap deferred without owner, rationale, and due date.

## Score table

| Category | 1 | 3 | 5 | Score |
|---|---|---|---|---|
| Requirements clarity | Unclear | Mostly clear | Clear, testable acceptance criteria |  |
| Plan quality | No plan | Basic plan | Complete files/tests/docs/risks plan |  |
| Product Owner gates | Missing | One gate present | Readiness and acceptance both evidenced |  |
| TDD discipline | No evidence | Partial evidence | Red to Green to Refactor documented |  |
| Test confidence | Weak or absent | Adequate | Strong targeted and regression coverage |  |
| UX & UI SME | Not considered for user-facing work | Basic accessibility or visual review | UX user need/flow/IA plus UI accessibility/design/frontend constraints evidenced |  |
| Security review | Not considered | Basic review | Explicit threat, secret, dependency, and boundary checks |  |
| Data and prompt discipline | Not considered | Basic metadata | Versioned prompts/data linked to evals and constraints |  |
| Documentation | Missing | Partial | Complete user/dev/changelog updates where relevant |  |
| Review rigor | Self-attested | Some evidence | Checks and spec comparison documented |  |
| Housekeeping | Artifacts scattered | Mostly organized | Final artifacts discoverable; scratch and follow-ups handled |  |
| Continuous improvement | None | Follow-ups noted | Lessons converted into prompts/tests/checklists |  |

## Summary

- Overall score:
- Automatic fail condition present: yes/no
- Blocking gaps:
- Deferred advisory follow-ups:
- Product Owner acceptance decision:
- Recommended process improvement:
- Final decision: PASS/FAIL
