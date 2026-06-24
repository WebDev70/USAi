---
alwaysApply: true
---

# Role: Observability (you can't operate what you can't see)

Make USAi Chat's behavior **visible and debuggable** — the "monitor" phase of
DevSecOps — without adding runtime dependencies or leaking secrets.

## Logging standards

- **Use the structured log buffer, not bare `print`.** Server-side, record notable
  events with `add_log(level, component, message, details=None)` so they appear in
  the in-app **Debug Logs** panel (`/logs`) with a timestamp, level, component, and
  optional details. Pick a sensible `level` (`info` / `warn` / `error`) and a stable
  `component` string (e.g. `memory`, `proxy`, `server`).
- **Log decisions and failures, not noise.** Record: requests proxied, memory
  saves/searches, config (re)loads, rejected/oversized inputs, upstream errors, and
  anything a developer would need to diagnose a problem. Avoid per-token or
  tight-loop spam.
- **Never log secrets.** No API keys, `Authorization` headers, or full request
  bodies that may contain sensitive content. Redact/omit — mirror the `/config`
  redaction discipline.
- **Frontend errors surface too.** Client-side failures should be reported into the
  Debug Logs panel so users can copy them when reporting issues, rather than dying
  silently in the console.

## Health & operability (IaC tie-in)

- The non-secret **`/config`** endpoint doubles as a liveness signal; the container
  `HEALTHCHECK` uses it. Keep it cheap and side-effect-free.
- If you add a long-running or failure-prone operation, make its success/failure
  observable via `add_log` so the Debug Logs panel and server terminal tell the
  full story.

## Testing observability

- `add_log` rotation is already unit-tested (`tests/python/test_server.py`). If you
  change logging behavior (levels, rotation, redaction), add/adjust a test.

This role has no dedicated `/check`; the `code-quality-review` and `security-review`
checks cover "uses the log buffer" and "never logs secrets" respectively.
