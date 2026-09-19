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

## Analyzing logs — closing the runtime→QA loop

Observability means **both writing and reading** the logs. The RAIL pipeline is
wired to analyze session logs as part of its QA and self-improvement process:

- **`scripts/analyze_logs.py`** + **`scripts/analyze-logs.sh`** — stdlib Python
  analyzer that reads `logs/*.jsonl`, counts errors by component, surfaces latency
  outliers (>2000ms), and scrubs sensitive patterns (`sk-`, `Bearer `, etc.).
  Exits 1 if any `"level":"error"` entries exist; exits 0 otherwise.
- **`/review` §6g** — advisory runtime log gate runs `analyze-logs.sh` at every
  review. Results surface as `ADVISORY [logs]:` lines — never converts PASS to FAIL.
- **`/build` pre-flight step 3b** — log recall before touching component files
  (informational only — never blocks the build).
- **`/govern` SE-5** — log-trend audit at sprint close: recurring errors in the same
  component across two consecutive reports escalate to BLOCKING.

## Health & operability (IaC tie-in)

- The non-secret **`/config`** endpoint doubles as a liveness signal; the container
  `HEALTHCHECK` uses it. Keep it cheap and side-effect-free.
- If you add a long-running or failure-prone operation, make its success/failure
  observable via `add_log` so the Debug Logs panel and server terminal tell the
  full story.

## Testing observability

- `add_log` rotation is already unit-tested (`backend/tests/python/test_server.py`). If you
  change logging behavior (levels, rotation, redaction), add/adjust a test.
- The log analyzer has its own test suite: `backend/tests/python/test_analyze_logs.py`
  (AL-1…AL-8 covering empty dirs, error detection, scrubbing, malformed lines).

This role has no dedicated `/check`; the `code-quality-review` and `security-review`
checks cover "uses the log buffer" and "never logs secrets" respectively.

