---
alwaysApply: true
---

# Role: DevSecOps (security is everyone's job, shifted left and machine-enforced)

Security is not a separate phase — it is woven through every RAIL role. This rule
makes the **DevSecOps** practices concrete. Governing principle: **minimal, audited
runtime surface** (`docs/principles.md` §1–2).

## Secure by default (apply while implementing)

- **Secrets live only in `.env`** (git-ignored). Never hardcode, log, echo, or
  commit a key/token/password. `/config` returns only non-secret fields + `has_*`
  flags; the proxy injects the API key server-side.
- **Validate all input.** Every endpoint reading a body enforces a size limit;
  every filesystem path is confined to its intended folder and rejects `..` /
  absolute escapes (reference: `get_memory_dir`'s `relative_to` guard, `_slugify`).
- **Escape before render.** Model/user content is HTML-escaped then whitelisted
  (reference: `renderMarkdown`) — never inject raw HTML (XSS).
- **Least privilege & safe binding.** Default bind is `127.0.0.1`; `0.0.0.0` only
  inside the container via `HOST`. The container runs as a non-root user.
- **Minimal runtime surface.** No new runtime dependency without strong
  justification; prefer the stdlib. Dev/CI security tooling is fine (it ships
  nothing into the app).

## Shift left — deterministic scanning (not just LLM judgment)

Beyond the `security-review` `/check` (an LLM gate), run the deterministic scanners
for any non-trivial change touching `server.py`, dependencies, or infra:

```bash
./scripts/security-scan.sh      # gitleaks (secrets) + bandit (SAST) + pip-audit (CVEs)
make scan                       # same, via the IaC Makefile
```

These also run in CI (`.github/workflows/tests.yml` → `security` job) on every
push/PR. **Don't disable or weaken a scanner** to make a change pass — fix the
finding or document an explicit, reviewed exception.

## Threat-model the change (quick mental pass)

For each change ask: *What new input does this trust? Where could a secret leak?
Could this path escape its folder? Does this widen what's exposed to the browser or
the network?* Address answers in code + tests (add a regression test for any
security fix).

## Checks that enforce this role

`security-review`, `dependency-and-supply-chain-review`, and (for infra)
`iac-review` — all run via `/check` / `scripts/cli-check.sh`.
