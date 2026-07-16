# Data

Store inputs the AI reads here.

## Subfolders

| Folder | Purpose |
|---|---|
| `raw/` | Original source inputs, exports, transcripts, documents, examples, logs, or datasets. |
| `processed/` | Cleaned, summarized, chunked, labeled, or otherwise prepared context. |

## RAIL guidance

Data should be traceable. When data is transformed, record:

- Source file or source system.
- Processing steps.
- Date or version.
- Known limitations.
- Privacy or security constraints.
- Related prompts, evals, and expected outputs.

Use `processed/eval-dataset-template.md` for golden or regression eval datasets. Run `../evals/tests/eval-dataset-quality.md` when adding or changing datasets used for evaluation.

Never store secrets unless the project has an explicit, secure secret-handling process.
