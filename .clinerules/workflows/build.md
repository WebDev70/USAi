# Workflow: /build
# Cline RAIL — Implementation Engine

> **Concern: Cline dev harness** — this workflow is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Mode:** ACT MODE

**Purpose:** Read the spec at `docs/specs/<feature>.md` and implement *exactly* what
it describes — no more, no less. This workflow covers **Role 1 (Code Planner review)
+ Role 2 (Architect) + Role 3 (Developer / SME) + Role 4 (Tester)** in sequence.
Each role has its own Execute → Review → Improve → Approve sub-cycle.

---

## Pre-flight check

Before writing a single line of code:

1. **Locate the spec.** Ask which spec to build if none is obvious:
   `docs/specs/<feature>.md`. Read it completely.
2. **Recall prior context.** Search the Obsidian vault for relevant memory:
   ```
   <OBSIDIAN_VAULT_PATH>/Cline/memories/
   <OBSIDIAN_VAULT_PATH>/Continue Extension/memories/
   <OBSIDIAN_VAULT_PATH>/USAi/memories/
   ```
3. **Confirm Status is "Ready"** (not Draft). If it's still Draft, pause and ask
   the user to finish `/spec` first.
4. **Confirm the backlog item is `[~]` In Progress.** Open `backlog.md` and
   verify the item for this spec is set to `[~]` with a spec link. If it is still
   `[ ]` Not started (i.e. the spec was written before the Step 3b rule existed),
   fix it now — flip to `[~]` and append `— spec: <path>` — before touching any
   code. This ensures the backlog accurately reflects work in flight.
5. **Confirm you understand all 8 sections** of the spec before acting.
6. **Check the `Type:` field** and apply role-skipping accordingly:

   | Type | Roles to skip / adapt |
   |------|-----------------------|
   | `feature` | None — all RAIL roles apply. |
   | `bugfix` | Skip Role 0 (PO). Regression test is required before any fix code. |
   | `chore` / `refactor` | Skip Role 0 (PO). Tester gate still applies; no new features. |
   | `docs` | Skip Role 0 (PO). Skip Role 4 (Tester) gate unless code changed. Skip security scan unless code changed. |
   | `css` | Skip Role 0 (PO). The CSS bump (`styles.css?v=N` in `index.html`) is the primary gate; verify visually. |

   If `Type:` is absent from the spec, treat it as `feature` (safest default) and note the gap.

---

## Role 1 — Code Planner (re-read + plan)

Re-read the spec and produce a brief internal build plan:

- What files will be touched (from spec §3)?
- What is the implementation order (tests first, then code)?
- Are there any ambiguities in the spec that need clarification before starting?

If an ambiguity is found, ask the user to clarify — **do not guess or expand scope**.

---

## Role 2 — Architect (design validation)

Silently validate against USAi conventions before writing code:

| Check | Pass / Flag |
|---|---|
| No new *runtime* dependencies | Use only vanilla JS / Python stdlib + python-dotenv |
| New endpoint? | `_handler` method + `routes` dict registration + input-size validation |
| New tool? | `TOOL_REGISTRY` entry + `getEnabledTools()` gate |
| `/config` safety | Only non-secret fields + `has_*` flags |
| Filesystem safety | Reject path traversal; confine writes to intended folder |
| CSS change? | Bump `styles.css?v=N` in `index.html` |
| SSRF | Upstreams validated by `is_safe_upstream_url` |
| Comments | Explain *why*, not just *what* — match existing style |

Flag any conflict here before proceeding. If a convention cannot be satisfied,
stop and explain the conflict to the user — do not work around it silently.

---

## Role 3 — Developer / SME (TDD implementation loop)

Follow **Red → Green → Refactor** strictly:

### 3a. RED — write failing tests first

From spec §5 (Test plan), write **all specified tests** before touching production
code. Run them to confirm they fail for the *right* reason:

```bash
node --test tests/js/              # JS tests
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'  # Python tests
```

Confirm each new test fails before proceeding.

**Red receipt (TDD evidence):** paste the failing-test output into the current
session memory note in `Cline/memories/` *before* writing any production code.
The memory note should record the exact error message and test names that are
failing. This is the proof that tests were written first — it is required by the
`/review` §6a TDD check. A build without a Red receipt is considered a TDD
violation and will be flagged as a GAP.

### 3b. GREEN — minimum code to pass

Write the minimum production code to make the failing tests pass without breaking
existing ones. Implement only what spec §4 (Technical approach) describes.

**Scope discipline:** if you notice a tempting improvement outside the spec, note it
as a future backlog item — do not implement it now.

After each file is edited, run the relevant tests:

```bash
node --check app.js               # JS syntax gate
python3 -m py_compile server.py   # Python syntax gate
```

### 3c. REFACTOR — clean up under green

- Remove duplication, improve names, add *why* comments.
- Re-run the full suite to confirm still green.
- Do not change behavior during refactor.

### 3d. Docs in sync

Update docs **in the same turn** as the code change (per spec §6):
- `CHANGELOG.md` — always, under `[Unreleased]`
- `docs/USER_GUIDE.md` — if user-facing
- `README.md` — if setup/env/config changed
- `backlog.md` — mark item done if applicable

---

## Role 4 — Tester (coverage gate)

Run the full suite with coverage gates:

```bash
./run-tests.sh --coverage
```

Gates:
- `server.py` ≥ **90%** line coverage
- JS exported helpers ≥ **70%** branch coverage

If a gate fails:
1. Identify which lines/branches are uncovered.
2. Write additional tests to cover them (do not lower the gate).
3. Re-run until both gates pass.

---

## Build complete — handoff to /review

When all of the following are true, announce completion and trigger `/review`:

- [ ] All spec §5 tests written and passing
- [ ] `./run-tests.sh --coverage` passes both gates
- [ ] No existing tests broken
- [ ] Docs updated per spec §6
- [ ] No scope creep — only spec §3–4 was implemented

> **Next step:** Run `/review` to compare this build against the spec and run all
> quality gates. Do not declare done until `/review` passes cleanly.
