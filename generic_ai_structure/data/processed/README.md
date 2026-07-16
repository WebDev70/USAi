# Processed Data

Processed data should be reproducible from raw inputs whenever possible.

## Processing note template

For each processed artifact, record:

- Artifact name:
- Source raw file(s):
- Processing date:
- Processor or tool:
- Processing steps:
- Schema or format:
- Quality checks:
- Known limitations:
- Privacy/security constraints:
- Related prompt(s):
- Related eval(s):
- Expected output file, if applicable:

## Eval datasets

Use `eval-dataset-template.md` for golden or regression datasets. Keep expected outputs, split policy, labels, and exclusion criteria explicit enough that another reviewer can reproduce the evaluation.
