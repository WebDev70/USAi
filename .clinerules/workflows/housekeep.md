# /housekeep — Standalone Housekeeping & Hygiene Sweep
# (Senior Housekeeping & Hygiene Steward — USAi Chat)

> **Concern: Cline dev harness** — this workflow is the on-demand standalone
> version of the SHK role. It runs the same checklist as the sprint-close
> `/govern` SHK pass, but can be triggered independently at any time.
>
> **Charter reference:** `docs/governance.md` §5 (SHK full charter and rubric).
> **Per-item lightweight gate:** `/review §6h` (leave-no-trace gate, subset).

---

## When to use this workflow

| Trigger | Description |
|---------|-------------|
| **`/housekeep`** | Explicit user request for a standalone hygiene sweep |
| **Between sprints** | When the team wants to clean up before starting a new sprint |
| **After a burst of feature work** | When several items have been closed in quick succession |
| **Sprint-close (auto)** | Also triggered automatically by `.clinerules/scrum-artifacts.md` sprint-close step as the 5th role in `/govern` |

---

## Pre-flight

1. Confirm the current working directory is the repo root.
2. Recall memory: search `Cline/memories/`, `Continue Extension/memories/`, and
   `USAi/memories/` in the Obsidian vault for any prior housekeeping notes or
   identified cleanup debt.
3. Note the current date — all findings will be dated.

---

## Step 1 — Spec / backlog reconciliation

For every spec file in `docs/specs/`:

1a. Find the matching backlog item in `backlog.md` by title or number.
1b. If the backlog item is `[x]` Done → verify the spec's `Status:` header is also `Done`.
    - Finding if **Status: mismatch**: the spec still says `In Progress` or `Ready` but the backlog item is Done.
1c. If no matching backlog item exists → flag as **orphaned spec** (created without a backlog item, or backlog item was deleted without closing the spec).
1d. If a backlog item is `[x]` Done but **no spec file exists** → verify this is expected (bugfixes/chores don't always have a spec). Log as INFO if no spec was ever linked.

**Emit:** list of Status-mismatched specs and orphaned spec files.

---

## Step 2 — Backlog `[x]` Done-pile hygiene

Scan every `[x]` Done item in `backlog.md`:

2a. Confirm each has:
    - `Done (YYYY-MM-DD)` date
    - One-line outcome (not just a blank or "done")
    - Spec link (`Spec: docs/specs/<kebab>.md`) if a spec was produced

2b. Count total `[x]` Done items. If > 50, propose archival of the oldest items to `backlog-archive.md`. (Do NOT archive without user confirmation.)

**Emit:** list of incomplete Done entries; archival proposal if threshold exceeded.

---

## Step 3 — Dead code and scratch file audit

3a. Search for inline TODOs, FIXMEs, XXXs, and HACKs:
    ```bash
    grep -rn "TODO\|FIXME\|XXX\|HACK" server.py app.js scripts/ --include="*.py" --include="*.js" --include="*.sh"
    ```
    - For each hit: is it tracked in `backlog.md`? If not, propose a backlog item.

3b. Check for committed scratch or temp files:
    ```bash
    git ls-files | grep -E '\.(tmp|bak|orig)$|implementation_plan\.md|wip-.*\.md|scratch'
    ```
    - `implementation_plan.md` in the repo root is a scratch artifact — propose removal or move to `docs/specs/`.
    - `.DS_Store` should be in `.gitignore`.

3c. Check `.gitignore` covers: `*.tmp`, `*.bak`, `.DS_Store`, `__pycache__/`, `.venv/`, `logs/*.jsonl` (if intended).

**Emit:** punch-list of untracked TODOs and any committed scratch files.

---

## Step 4 — Log and cache bloat

4a. Check the size and age of runtime data stores:
    ```bash
    du -sh logs/ .chat_sessions/ .chunk_cache/ 2>/dev/null | sort -h
    find logs/ .chat_sessions/ .chunk_cache/ -type f -mtime +30 2>/dev/null | wc -l
    ```
    - **Threshold:** recommend pruning if any store exceeds 50 MB or contains files older than 30 days.
    - Do NOT auto-prune — emit a recommendation only.

**Emit:** store sizes, age of oldest files, pruning recommendation if threshold exceeded.

---

## Step 5 — Doc-consistency drift

5a. Run the doc-consistency check:
    ```bash
    ./scripts/doc-consistency-check.sh
    ```
    Report any failures.

5b. Verify `styles.css?v=N` in `index.html` matches the latest CSS version (cross-reference with CHANGELOG.md and git log for the last CSS edit).

5c. Check `CHANGELOG.md` — is the `[Unreleased]` section non-empty if code has changed since the last release tag? If it is empty but `git log` shows changes, propose a CHANGELOG update.

5d. Verify `.env.example` keys match `.env` (without exposing values):
    ```bash
    diff <(grep -v '^#' .env.example | cut -d= -f1 | sort) <(grep -v '^#' .env | cut -d= -f1 | sort)
    ```

**Emit:** doc-consistency failures, stale CSS v-bump, missing CHANGELOG entries, .env.example drift.

---

## Step 6 — Dependency freshness

6a. Run:
    ```bash
    ./scripts/dev-deps-check.sh
    ```
    Report any outdated or missing pins.

6b. Verify every package in `requirements.txt` and `requirements-dev.txt` is still actually imported in `server.py` or a test file. Flag unused entries as candidates for removal.

**Emit:** outdated pins and unused dependency candidates.

---

## Step 7 — Vault memory hygiene

7a. Check `Cline/memories/` for duplicate same-date session notes — they should have been appended rather than creating new files. Flag any pair of notes that share the same date prefix without a unique time suffix.

7b. Re-run the canonical memory-note secret scan (check 4/4) rather than maintaining
    a duplicate regex:
    ```bash
    OBSIDIAN_VAULT_PATH="${OBSIDIAN_VAULT_PATH:?export the vault path}" \
      SKIP_GITLEAKS=1 SKIP_BANDIT=1 SKIP_PIP_AUDIT=1 ./scripts/security-scan.sh
    ```
    A check-4/4 failure is BLOCKING; its output is deliberately redacted.

**Emit:** duplicate note pairs (ADVISORY), secret hits (BLOCKING).

---

## Step 8 — Findings consolidation

Emit a punch-list organized by classification:

```
## SHK Housekeeping Report — YYYY-MM-DD

### 🚨 BLOCKING
- (list any blocking findings — e.g. secrets in vault notes)

### 📋 ADVISORY
- (list advisory findings — e.g. stale spec Status headers, untracked TODOs)

### 🧹 CLEANUP
- (list cleanup candidates — e.g. archival proposal, scratch file removal)

### ✅ Clean
- (list areas that passed)
```

**Rule:** if any finding is ADVISORY or higher, propose **at least one tracked `backlog.md`
cleanup item** before closing the report.

---

## Step 9 — Output: propose backlog items and save report

9a. For each BLOCKING or ADVISORY finding, propose a `backlog.md` entry (do NOT write it without user confirmation).

9b. Save the report to the Obsidian vault:
    ```
    Cline/scrum/governance/YYYY-MM-DD-HHMMSS-housekeeping-report.md
    ```

9c. Append the report summary to the current sprint note in `Cline/scrum/sprints/sprint-NN.md`.

9d. Write (or append to today's) memory note:
    ```
    Cline/memories/YYYY-MM-DD-HHMMSS-housekeeping-sweep.md
    ```
    Frontmatter: `tags: [usai-chat, housekeeping, hygiene, shk]`

9e. Emit the closing **`Recommended Next Step`** section. `/housekeep` is a
    *terminal* workflow — the task ends here — so the mandatory closing section
    applies. The recommended step is normally the highest-severity BLOCKING
    finding from Step 8. See `.clinerules/recommended-next-step.md`.

---

## Distinction: /housekeep vs /review §6h (leave-no-trace gate)

| | `/housekeep` (this workflow) | `/review §6h` |
|-|------------------------------|---------------|
| **Scope** | Whole project, all historical items | Single RAIL item being reviewed |
| **When** | Sprint-close or on demand | Every item's `/review` pass |
| **Checks** | Full 7-step sweep above | Lightweight 4-point gate (see `/review §6h`) |
| **Output** | Full punch-list + vault report | Pass/fail gate in review checklist |

---

*References: `docs/governance.md` §5 · `.clinerules/rail-pipeline.md` · `.clinerules/workflows/govern.md` · `.clinerules/workflows/review.md` §6h*
