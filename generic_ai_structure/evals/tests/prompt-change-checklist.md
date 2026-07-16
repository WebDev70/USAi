# Prompt Change Checklist

Use whenever a prompt file changes.

## Prompt metadata

- Prompt file:
- Purpose:
- Owner:
- Expected inputs:
- Expected outputs:
- Known failure modes:
- Related evals:

## Change checklist

- [ ] Reason for prompt change is documented.
- [ ] Expected behavior change is explicit.
- [ ] Prompt inputs and outputs remain clear.
- [ ] Prompt does not request secrets or unsafe behavior.
- [ ] Prompt avoids conflicting instructions.
- [ ] Prompt includes enough constraints for reliable operation.
- [ ] Related evals were run or updated.
- [ ] Before/after behavior is captured in a trace when practical.

## Blocking failures

- Prompt change weakens safety requirements.
- Prompt change introduces conflicting role or tool instructions.
- Prompt change affects production behavior but has no eval or manual verification.
