# Eval Dataset Quality Gate

Use when data in `data/processed/` is used to evaluate AI behavior.

## Dataset metadata

- Dataset name:
- Source data:
- Created by:
- Date/version:
- Intended use:
- Out-of-scope use:

## Quality checklist

- [ ] Source provenance is recorded.
- [ ] Processing method is documented.
- [ ] Expected outputs or labels are defined.
- [ ] Labeling rules are documented.
- [ ] Edge cases are included.
- [ ] Failure cases are included.
- [ ] Sensitive data is removed, masked, or approved for use.
- [ ] Dataset has a version or date.
- [ ] Drift risks are known.

## Split discipline, if applicable

| Split | Purpose | Location | Notes |
|---|---|---|---|
| Train/examples | Prompt examples or demonstrations |  |  |
| Dev/tuning | Prompt or tool iteration |  |  |
| Test/holdout | Final evaluation |  |  |

## Blocking failures

- Expected outputs are missing.
- Sensitive data handling is unknown.
- Dataset source is unknown.
- Evaluation set is changed during final scoring without recording a version change.
