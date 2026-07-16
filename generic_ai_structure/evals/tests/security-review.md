# Security Review Gate

Use for every non-trivial task. Security findings are blocking unless explicitly classified as advisory and tracked.

## Secret safety

- [ ] No API keys, tokens, credentials, private keys, or passwords in code.
- [ ] No secrets in prompts, traces, logs, examples, screenshots, or datasets.
- [ ] No secrets in documentation or generated outputs.
- [ ] Secret-like values are placeholders, not real credentials.

Suggested patterns to search for, adapted to the target project:

```text
api_key
apikey
secret
token
Bearer
password
private key
BEGIN RSA PRIVATE KEY
BEGIN OPENSSH PRIVATE KEY
```

## Input and boundary safety

- [ ] Untrusted inputs are validated.
- [ ] File paths are normalized and constrained.
- [ ] Network calls are restricted to expected destinations.
- [ ] Permissions are least-privilege.
- [ ] User data is not exposed across tenants, accounts, or projects.

## Dependency and supply-chain safety

- [ ] New dependencies are justified.
- [ ] Package sources are trusted.
- [ ] Versions are pinned or locked where practical.
- [ ] Known vulnerabilities are scanned or reviewed.
- [ ] Licenses are acceptable for the project.

## Logging, traces, and observability

- [ ] Logs capture useful behavior and errors.
- [ ] Logs do not expose secrets or private data.
- [ ] Traces and scorecards do not include sensitive payloads.
- [ ] Security-relevant failures are visible enough to debug.

## Abuse-case review

| Abuse case | Relevant? | Mitigation | Blocking? |
|---|---|---|---|
| Prompt injection | yes/no |  | yes/no |
| Data exfiltration | yes/no |  | yes/no |
| Path traversal | yes/no |  | yes/no |
| SSRF or unsafe network call | yes/no |  | yes/no |
| Privilege escalation | yes/no |  | yes/no |
| Denial of service | yes/no |  | yes/no |

## Blocking failures

- Real secret committed or exposed.
- Unsafe file/network/permission boundary.
- Known vulnerable dependency without approved exception.
- Private or regulated data exposed in prompts, logs, traces, or eval artifacts.
