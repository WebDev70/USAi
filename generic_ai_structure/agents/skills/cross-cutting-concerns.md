# Skill: Cross-Cutting Concerns

Apply these concerns inside every RAIL role. They are not a separate final step.

## Security

- Do not expose secrets in prompts, traces, logs, datasets, screenshots, or examples.
- Validate trust boundaries before using external inputs or tools.
- Prefer least privilege for tool and agent capabilities.
- Record security assumptions and abuse cases for non-trivial changes.
- Treat missing security evidence as a review gap.

## Infrastructure and configuration

- Keep runtime, configuration, and environment assumptions explicit.
- Prefer reproducible setup instructions over hidden local state.
- Record required commands and expected outcomes.
- Track configuration drift and undocumented manual setup.

## Observability and auditability

- Preserve enough trace evidence to reconstruct decisions and checks.
- Log outcomes and errors without secrets or private data.
- Link traces to specs, scorecards, evals, datasets, and follow-ups.
- Record skipped checks with rationale and approval status.

## Data quality and privacy

- Track source, license or usage constraints, and transformation steps.
- Separate raw data from processed data.
- Maintain expected outputs for eval datasets.
- Redact or exclude sensitive information unless an approved handling process exists.

## Accessibility, UX, and UI

For user-facing work, review both how the experience works and how it looks.

- **UX, how it works:** state the user need; map the user flow for multi-step interactions; verify information architecture and control placement against user-facing docs; review clarity, errors, edge cases, recovery paths, and task completion.
- **UI, how it looks:** verify visual consistency with the target design system, token usage, accessibility, keyboard and `:focus-visible` behavior where applicable, responsive behavior, reduced-motion preferences, and project-specific frontend constraints.
- Confirm acceptance criteria with observable user behavior, not only implementation notes.

## Blocking failures

- A cross-cutting risk is identified but not reviewed.
- Sensitive information appears in an artifact without an approved handling process.
- Required evidence is missing and no justified N/A decision is recorded.
