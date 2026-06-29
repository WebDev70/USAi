# Spec: RAIL Log Analysis — Closing the Runtime→QA Loop (#52)

**Status:** Done
**Type:** feature
**Created:** 2026-06-28
**Author:** Cline

---

## Prior context recalled

- `self-improvement-log.md` Entry 003: No self-improvement loop from prior mistakes —
  sessions captured *what happened* but not a searchable lessons document. This spec
  is the direct extension: surfacing *runtime* behavior as a first-class RAIL input.
- Specs #49 (log directory persistence — Done) and #50 (log file viewer — In Progress)
  built the infrastructure this spec consumes: `logs/*.jsonl` JSONL files, schema
  `{timestamp, level, component, message, details}`, `PERSIST_LOGS` toggle wired.
- No prior context found in `Continue Extension/memories/` or `USAi/memories/`.

---

## 1. Goal & scope

**Goal:** Wire `logs/*.jsonl` runtime files into RAIL's QA and self-improvement loop
so real app behavior — errors, latency outliers, proxy failures — is surfaced during
every `/review` gate and every `/govern` sprint-close audit. This closes the gap
between *writing to the log* (Observability today) and *reading and acting on it*.

**Five phases (all in scope; one `/loop` pass):**

| Phase | Deliverable |
|-------|-------------|
| 1 | `scripts/analyze-logs.sh` + `scripts/analyze_logs.py` (stdlib Python) |
| 2 | `/review` §6g — advisory "Runtime log review" gate |
| 3 | `/build` pre-flight step 3b — log recall before touching components |
| 4 | `/govern` SE-5 — log-trend audit at sprint close |
| 5 | Doc/rule updates: `observability.md`, `rail-pipeline.md`, CHANGELOG, USER_GUIDE |

**Out of scope:** log streaming, remote sinks, alerting, auto-remediation, log
search/filter UI, changing `PERSIST_LOGS` default, changes to `/logs` HTTP endpoint.

---

## 2. User story & acceptance criteria

As a developer running USAi Chat with `PERSIST_LOGS=true`, I want RAIL's `/review`
gate and `/govern` audit to automatically analyze session log files and surface
errors, latency outliers, and recurring failures — so that real runtime problems
feed back into the backlog and self-improvement log without requiring manual JSONL
inspection.

### Phase 1 — Analyzer script
- [ ] **AC-1:** `./scripts/analyze-logs.sh [log-dir]` runs without error when files exist.
- [ ] **AC-2:** Emits summary: total entries, counts by `level`, counts by `component`,
  top-3 most frequent error messages, `fetch` entries with `latency_ms > 2000`.
- [ ] **AC-3:** Exits **1** if any `"level": "error"` entries found; **0** otherwise.
- [ ] **AC-4:** When no `*.jsonl` files exist, prints friendly message and exits **0**.
- [ ] **AC-5:** `message` or `str(details)` matching `sk-`, `Bearer `, `api_key=`,
  `password=` is replaced with `[REDACTED]` in all output.

### Phase 2 — `/review` §6g gate
- [ ] **AC-6:** `review.md` has §6g "Runtime log review" running the analyzer;
  results surfaced as `ADVISORY [logs]:` lines — never a FAIL verdict.
- [ ] **AC-7:** §6g explicitly marked advisory — never converts PASS to FAIL.

### Phase 3 — `/build` pre-flight log recall
- [ ] **AC-8:** `build.md` pre-flight gains step **3b** — run analyzer, note component
  errors for files being edited. Informational only.
- [ ] **AC-9:** Pre-flight log recall never blocks the build.

### Phase 4 — `/govern` SE log-trend audit
- [ ] **AC-10:** `govern.md` SE role gains **SE-5: Log-trend audit**; recurring errors
  feed into self-improvement log and backlog proposals.
- [ ] **AC-11:** SE-5 ADVISORY if errors found; BLOCKING only if same component errors
  appear in two consecutive governance reports.

### Phase 5 — Docs & rule updates
- [ ] **AC-12:** `observability.md` updated: Observability = *write* AND *analyze* logs.
- [ ] **AC-13:** `docs/rail-pipeline.md` §5 entry #11 added; Observability row updated.
- [ ] **AC-14:** `CHANGELOG.md` updated under `[Unreleased]`.
- [ ] **AC-15:** `docs/USER_GUIDE.md` §10 updated with RAIL log analysis note.

---

## 3. Affected files

| File | Change |
|------|--------|
| `scripts/analyze-logs.sh` | **New** — shell wrapper |
| `scripts/analyze_logs.py` | **New** — stdlib Python analyzer |
| `tests/python/test_analyze_logs.py` | **New** — 8 tests AL-1…AL-8 |
| `.clinerules/workflows/review.md` | Add §6g advisory gate |
| `.clinerules/workflows/build.md` | Add pre-flight step 3b |
| `.clinerules/workflows/govern.md` | Add SE-5 log-trend audit |
| `.continue/rules/observability.md` | Extend: write AND analyze |
| `docs/rail-pipeline.md` | §5 entry #11; Observability row |
| `CHANGELOG.md` | `[Unreleased]` entry |
| `docs/USER_GUIDE.md` | §10 Troubleshooting — log analysis note |
| `backlog.md` | Mark #52 done |

---

## 4. Technical approach

### 4a. `scripts/analyze_logs.py` (stdlib: json, pathlib, sys, collections, re)

```python
SENSITIVE = re.compile(r'sk-|Bearer |api_key=|password=', re.IGNORECASE)
LATENCY_THRESHOLD_MS = 2000
MAX_LINES_PER_FILE = 5000  # cap for large files

def scrub(text: str) -> str:
    return SENSITIVE.sub('[REDACTED]', text)

def analyze(log_dir: Path) -> dict:
    # Returns: {files_read, total_entries, by_level, by_component,
    #           top_errors (list of {component,message,count}),
    #           latency_outliers (list of {url,latency_ms,timestamp}),
    #           has_errors (bool)}
```

Output (stdout):
```
=== RAIL Log Analysis ===
Files read    : 6      Total entries : 312
By level      : info=298  warn=9  error=5
By component  : proxy=87  fetch=124  memory=31 ...
Top errors (up to 3):
  [proxy] upstream unreachable /api/v1/chat  (×3)
Latency outliers (>2000ms):
  GET /api/v1/chat  3421ms  2026-06-28T09:12:44
Exit code: 1  (errors found)
```

No-files output:
```
=== RAIL Log Analysis ===
No log files found in 'logs/' — PERSIST_LOGS may be disabled.
Exit code: 0
```

### 4b. `scripts/analyze-logs.sh`

```bash
#!/usr/bin/env bash
# analyze-logs.sh — RAIL log analyzer wrapper
# Usage: ./scripts/analyze-logs.sh [log-dir]  (default: logs/)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${1:-logs}"
python3 "${SCRIPT_DIR}/analyze_logs.py" "${LOG_DIR}"
```

`chmod +x` required.

### 4c. `/review` §6g insert (after §6f, before Verdict)

```markdown
### 6g. Runtime log review (advisory)

If `PERSIST_LOGS=true` and log files exist:
\`\`\`bash
./scripts/analyze-logs.sh
\`\`\`
| Result | Action |
|--------|--------|
| Exit 0 | ✅ Log review — clean |
| Exit 1 (errors found) | Append `ADVISORY [logs]: N error entries — top: <list>` to gap list |
| No files / disabled | Note "log review skipped (persistence disabled)" — not a gap |

**Advisory only — never converts PASS to FAIL.**
```

### 4d. `/build` pre-flight step 3b (insert after step 3)

```markdown
3b. **Runtime log recall (informational).** If `PERSIST_LOGS=true`:
    \`\`\`bash
    ./scripts/analyze-logs.sh
    \`\`\`
    Scan for error entries in the `component` matching files being edited.
    Record relevant errors in the session memory note as build context.
    **Informational only — never blocks the build.**
    If persistence off or no files: skip ("log recall skipped").
```

### 4e. `/govern` SE-5 (after SE-4)

```markdown
### SE-5: Log-trend audit

\`\`\`bash
./scripts/analyze-logs.sh
\`\`\`
- `component` with errors → ADVISORY + proposed backlog item.
- Same `component` errors in two consecutive reports → BLOCKING + append
  to `self-improvement-log.md`.
- `PERSIST_LOGS=false` / no files → SE-5 **N/A**.
```

### 4f. Shift-left governance pre-check (§4b)

| Check | Assessment |
|-------|-----------|
| G-1 AC testability | All 15 AC binary pass/fail ✅ |
| G-2 Scope / value | Closes the runtime→QA gap; no gold-plating ✅ |
| G-3 Dependency coherence | Pure stdlib Python + shell; zero new runtime deps ✅ |

---

## 5. Test plan

New file: `tests/python/test_analyze_logs.py` (unittest.TestCase + tempfile)

| ID | Description | Expected |
|----|-------------|---------|
| AL-1 | Empty log dir | `has_errors: False`, exit 0 |
| AL-2 | All-info JSONL | exit 0, `by_level["error"] == 0` |
| AL-3 | One error entry | exit 1, `has_errors: True` |
| AL-4 | Multiple errors same component | `top_errors[0]["count"] >= 2` |
| AL-5 | Fetch entry `latency_ms > 2000` | outlier present |
| AL-6 | Fetch entry `latency_ms <= 2000` | outlier absent |
| AL-7 | `sk-` in message | output shows `[REDACTED]` |
| AL-8 | Malformed JSON line | skipped, rest parsed, no exception |

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — `[Unreleased]` entry
- [ ] `docs/USER_GUIDE.md` — §10 Troubleshooting: "RAIL log analysis" subsection
- [ ] `docs/rail-pipeline.md` — §5 entry #11; Observability row in §3 table
- [ ] `.continue/rules/observability.md` — extend definition
- [ ] `backlog.md` — mark #52 done

---

## 7. Risks / edge cases

| Risk | Mitigation |
|------|-----------|
| Large log files | Cap at 5000 lines per file (streaming read) |
| Malformed JSONL | `try/except json.JSONDecodeError: continue` |
| `PERSIST_LOGS=false` (default) | All workflow hooks check no-files → skip gracefully |
| Sensitive data in `details` | `scrub()` applied to `str(details)` |
| Advisory gate fatigue | Explicitly advisory; never converts PASS to FAIL |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §6
- [x] All 15 AC verified (AC-1…AC-15)
- [x] Memory note written to `Cline/memories/`

## Spec changelog

> *Populated only when a spec amendment is made during `/build`.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|

