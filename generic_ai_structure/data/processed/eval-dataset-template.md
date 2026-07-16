# Eval Dataset Template

Use this file as a model for documenting AI evaluation datasets.

## Metadata

- Dataset name:
- Version/date:
- Owner:
- Source raw data:
- Processing script or method:
- Intended evaluation:
- License/usage constraints:
- Privacy/security constraints:

## Schema

| Field | Type | Description | Required? |
|---|---|---|---|
| id | string | Stable example ID | yes |
| input | string/object | Input to the AI/system | yes |
| expected_output | string/object | Expected behavior or answer | yes |
| tags | list | Scenario tags | no |
| notes | string | Special handling notes | no |

## Example record

```json
{
  "id": "example-001",
  "input": "",
  "expected_output": "",
  "tags": ["happy-path"],
  "notes": ""
}
```

## Quality notes

- Include happy paths, edge cases, and known failure modes.
- Keep final test/holdout examples stable.
- Record any dataset changes before comparing scores across versions.
- Do not include sensitive data unless approved controls exist.
