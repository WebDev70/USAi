# RAIL Review Checklist

Use this before declaring a task done. Treat this as the high-assurance manual review gate.

## 1. Definition of Ready gate

- [ ] Definition of Ready was completed before implementation or marked N/A with justification.
- [ ] Feature/product-facing work has a user story or clear goal.
- [ ] Acceptance criteria are testable.
- [ ] Scope, out-of-scope, dependencies, and risks are explicit.

## 2. Full check-suite gate

- [ ] Target project full check-suite command was run.
- [ ] Required tests passed.
- [ ] Required lint/format/type checks passed.
- [ ] Required coverage or quality thresholds passed.
- [ ] Any skipped check has a written justification.

## 3. Spec compliance gate

- [ ] The work matches the stated goal.
- [ ] Planned affected files/artifacts were addressed or explained.
- [ ] Planned tests/evals were created or explained.
- [ ] No out-of-scope changes were added.
- [ ] Every acceptance criterion is mapped to test evidence or observable behavior.

## 4. TDD evidence gate

- [ ] New or changed testable logic has Red → Green → Refactor evidence.
- [ ] Bug fixes include regression evidence when practical.
- [ ] No-test decisions include a clear justification.

## 5. Security review gate

- [ ] No secrets are exposed in code, logs, prompts, traces, docs, or datasets.
- [ ] Inputs are validated where relevant.
- [ ] File, network, and permission boundaries are respected.
- [ ] Dependency or supply-chain risk is reviewed where relevant.
- [ ] Logging and traces avoid sensitive data.

## 6. Dependency and supply-chain gate

- [ ] New dependencies are justified.
- [ ] Versions are pinned or locked where practical.
- [ ] Known vulnerabilities are scanned or reviewed.
- [ ] Any exception is documented with owner and expiration/review date.

## 7. Infrastructure and configuration gate

- [ ] Environment/config changes are reproducible and documented.
- [ ] Secrets are not hardcoded.
- [ ] Deployment/runtime assumptions are explicit.
- [ ] Config drift risks are reviewed.

## 8. Code and artifact quality gate

- [ ] Work follows target project conventions.
- [ ] Changes are minimal and cohesive.
- [ ] Comments explain why, not obvious what.
- [ ] Generated, temporary, or scratch artifacts are not accidentally committed.

## 9. Documentation and prompt sync gate

- [ ] User-facing docs updated where relevant.
- [ ] Developer docs updated where relevant.
- [ ] Changelog or release notes updated where relevant.
- [ ] Prompt changes include metadata and eval notes where relevant.
- [ ] Follow-up work captured.

## 10. UX & UI SME gate, if applicable

### UX sub-discipline, how it works

- [ ] User-facing controls or interactions have a stated user need, goal, or job-to-be-done.
- [ ] Multi-step interactions include a described user flow or journey.
- [ ] New controls are placed in the correct information-architecture location and checked against user-facing docs or product structure.
- [ ] Friction, empty states, errors, recovery paths, and task completion were reviewed.

### UI sub-discipline, how it looks

- [ ] Accessibility reviewed, including semantic structure and WCAG-targeted concerns where applicable.
- [ ] Keyboard/focus behavior reviewed, including visible focus treatment where applicable.
- [ ] Responsive behavior reviewed.
- [ ] Motion and animation respect reduced-motion expectations where applicable.
- [ ] Visual change is consistent with the design system, tokens, or project conventions.
- [ ] Frontend implementation constraints were preserved, including any no-new-runtime-dependency or cache-busting requirements.

Fail this gate when a user goal is absent, a multi-step flow is undescribed, or a control is placed in the wrong information-architecture area without a documented rationale.

## 11. Product Owner acceptance gate

- [ ] Each acceptance criterion is verified.
- [ ] Product-facing behavior is accepted or explicitly rejected with gaps.
- [ ] Deferred scope is captured as follow-up.

## 12. Housekeeping gate

- [ ] Task trace exists.
- [ ] Scorecard completed for non-trivial work.
- [ ] Gap list is empty or contains only tracked advisory gaps.
- [ ] Follow-up log/backlog updated.
- [ ] No stale TODO/FIXME/HACK items were introduced without tracking.

## Final decision

- [ ] PASS: no blocking gaps remain.
- [ ] FAIL: specific gap list created and returned to implementation.

Fail-closed rule: if evidence is missing for a required gate, mark the gate failed until evidence is supplied or a justified N/A decision is recorded.
