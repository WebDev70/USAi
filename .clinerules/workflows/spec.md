# Workflow: /spec
# Cline RAIL — Specification Writer

> **Concern: Cline dev harness** — this workflow is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Mode:** PLAN MODE (interview phase) → ACT MODE (write spec file)

**Purpose:** Turn a goal into a reviewed, ready-to-build spec document at
`docs/specs/<feature>.md`. This is **Role 0 (Product Owner) + Role 1 (Code Planner)**
in the RAIL pipeline. The spec becomes the source of truth for `/build` and `/review`.

---

## Step 0 — Recall first (Code Planner)

Before asking a single question, search the Obsidian vault for relevant prior context:

```
Search locations (all three — recall everything relevant):
  <OBSIDIAN_VAULT_PATH>/Cline/memories/
  <OBSIDIAN_VAULT_PATH>/Continue Extension/memories/
  <OBSIDIAN_VAULT_PATH>/USAi/memories/
```

Surface any prior decisions, lessons learned, or related specs that bear on this
feature. Note what was found (or "no prior context found") in the spec's preamble.

**Prevention-rule recall receipt.** Also read `self-improvement-log.md` in
`<OBSIDIAN_VAULT_PATH>/Cline/memories/`. Scan each entry and emit:
- `Prevention-rule recall: none apply` — if no entries are relevant to this task.
- `Prevention-rule recall: Entry 001 (stale server), Entry 003 (no log)` — list
  all relevant entries by number and a one-word description.

This receipt must appear before the first interview question. It cannot be skipped.

---

## Step 1 — Product Owner interview (PLAN MODE)

Ask these questions **one at a time** — wait for each answer before the next:

0. **What type of change is this?** — `feature | bugfix | chore | docs | css`

   The type determines which RAIL roles and gates apply:

   | Type | Role 0 (PO) | Regression test req'd? | CSS bump req'd? | Notes |
   |------|-------------|------------------------|-----------------|-------|
   | `feature` | ✅ Required — full Definition of Ready gate | Recommended | Only if CSS changed | All RAIL roles apply |
   | `bugfix` | ⬜ Skip | ✅ Yes — write a test that reproduces the bug first | Only if CSS changed | Omit PO gate; all other roles apply |
   | `chore` / `refactor` | ⬜ Skip | ⬜ No (unless behaviour change) | Only if CSS changed | Lightweight — skip PO gate; Tester gate still applies |
   | `docs` | ⬜ Skip | ⬜ No | Only if CSS changed | Tester/Security gates skipped when no code changed |
   | `css` | ⬜ Skip | ⬜ No | ✅ Required — bump `styles.css?v=N` in `index.html` | CSS bump is the primary gate; verify visually |

   Record the answer in the spec as a **`Type:`** field immediately after **`Status:`**.

1. **What is the goal?** — What problem are we solving, and for whom?
2. **What does success look like?** — Name 2–4 concrete, testable acceptance
   criteria. (e.g. "The endpoint returns 200 with JSON", "The test passes",
   "The button is visible in both themes".)
3. **What is explicitly out of scope?** — What are we *not* building right now?
4. **Any constraints?** — Performance, security, backward-compat, design,
   timeline, size (S/M/L/XL)?
5. **Which files do you expect to touch?** — Best guess is fine; the Architect
   role will refine.

Once you have all answers, declare: "Definition of Ready — confirmed ✓" and
proceed to Step 2.

---

## Step 2 — Architecture validation (Architect role)

Before writing the spec, run a silent mental check against USAi conventions:

| Convention | Check |
|---|---|
| No new runtime deps | New code uses only vanilla JS / Python stdlib + python-dotenv |
| New endpoint? | Needs `_handler` + `routes` entry + input-size validation |
| New tool? | Needs `TOOL_REGISTRY` entry + `getEnabledTools()` gate |
| Secrets | `/config` exposes only `has_*` flags; proxy injects key server-side |
| Filesystem endpoints | Reject path traversal; confine writes to intended folder |
| CSS change? | Bump `styles.css?v=N` in `index.html` |
| SSRF | Upstream calls go through `is_safe_upstream_url` |

Flag any conflicts in the spec's Risks section.

---

## Step 2b — Shift-left governance check (SBA/SA-lite)

> **Scope:** This is a *per-requirement* subset of the full Governance Board rubric.
> It catches the three most common requirement-level failures **before** they bake
> into a spec. The full four-role `/govern` audit (SBA · SA · SE · SPMS) remains
> a **sprint-close / on-demand** activity — those macro-assessment roles require a
> body of completed work to assess and cannot be meaningfully run per-spec.

Run the following three lightweight checks **silently** (no user interruption unless
a check fails). Record the outcome in **§4b of the spec template** (see below).
All findings are **advisory** — they are recorded in the spec but do not block
Status: Ready on their own.

### Check G-1 — AC testability (SBA-3)
For each acceptance criterion from Step 1 Q2:
- Is it **binary** — can it only pass or fail, with no ambiguity?
- Is it **observable** — testable by a unit/integration test or verifiable in the
  running app with a specific, repeatable action?
- **Flag** any AC that is vague (e.g. "feels faster", "looks better", "improves UX").
- **Rewrite** flagged ACs as specific, binary criteria before proceeding.
  - *Bad:* "The UI is more responsive."
  - *Good:* "The loading spinner appears within 100 ms of submitting a message."

### Check G-2 — Scope / value justification (SBA-2)
- Does every item in scope map to the stated goal for the stated user?
- Is there any element that adds complexity without clear user value (**scope creep**)?
- Is any item being built *beyond* what users need right now (**gold-plating**)?
- If yes to either: propose trimming to the stated goal. Record as advisory finding.

### Check G-3 — Dependency coherence (SBA-5-lite)
- Does this spec assume that a separate backlog item is already done?
  (e.g. "Requires backlog #7 to ship first" or "Calls an endpoint added in #22.")
- If so: name the dependency explicitly in §7 (Risks) and confirm whether the
  prerequisite is already done (`[x]` in `backlog.md`) or still open.
- Open prerequisites are advisory, not blocking — but they must be named.

### Outcome
- All three checks pass → proceed to Step 3 with no further action.
- One or more flags → rewrite the affected AC / trim scope / note the dependency,
  then record the findings in **§4b** of the spec. Do not block or re-interview
  the user unless a rewrite requires their input.

---

## Step 3 — Write the spec file (Code Planner output)

Write `docs/specs/<kebab-case-feature-name>.md` using **exactly** this template.
Set **Status: Ready** once the Definition of Ready is confirmed.

```markdown
# Spec: <Feature Name>

**Status:** Ready
**Type:** <feature | bugfix | chore | docs | css>
**Created:** <YYYY-MM-DD>
**Author:** Cline / <user>
**Prior context:** <one sentence — what was recalled from Obsidian, or "none">

---

## 1. Goal & scope

### Goal
<What we are building and why — 2–4 sentences.>

### Out of scope
- <item>
- <item>

---

## 2. User story & acceptance criteria

As a <user> I want <goal> so that <value>.

- [ ] AC-1: <testable, observable — e.g. "GET /endpoint returns 200 + JSON body">
- [ ] AC-2: <...>
- [ ] AC-3: <...>

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | <description> |
| `app.js` | <description> |
| `index.html` | <description — or "none"> |
| `styles.css` | <description — or "none"> |
| `tests/python/test_*.py` | <new/updated tests> |
| `tests/js/app.test.mjs` | <new/updated tests — or "none"> |
| `docs/...` | <spec + any doc updates> |

---

## 4. Technical approach

### Role 2 — Architect sign-off
<Describe the design: functions/endpoints/components to add or change.>

**Conventions applied:**
- [ ] No new runtime dependency added
- [ ] New endpoint follows `_handler` + `routes` pattern (or N/A)
- [ ] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A)
- [ ] `/config` exposes no secrets (or N/A)
- [ ] Path traversal rejected on filesystem access (or N/A)
- [ ] CSS bump applied (or N/A)

---

## 4b. Shift-left governance findings (Step 2b output)

> Filled by Cline during `/spec`. Advisory — does not block Status: Ready.

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass / ⚠️ Rewritten / N/A | <detail or "all ACs are binary and observable"> |
| G-2 Scope / value | ✅ Pass / ⚠️ Advisory | <detail or "no scope creep identified"> |
| G-3 Dependency coherence | ✅ Pass / ⚠️ Advisory | <detail or "no prerequisite backlog items"> |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | <description> | `tests/python/test_server.py` | unit |
| T-2 | <description> | `tests/python/test_server_http.py` | integration |
| T-3 | <description> | `tests/js/app.test.mjs` | unit |

**TDD order:** write these tests first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — if user-facing feature
- [ ] `README.md` — if setup/config/env var changes
- [ ] `backlog.md` — mark relevant item done / add new items
- [ ] `AGENTS.md` / `CONTINUE.md` — if conventions change

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| <risk> | <mitigation> |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-N all verified
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

> *Optional — populated only when a spec amendment is made during `/build`
> (see build.md §3d). Leave empty if no amendments were needed.*

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
```

---

## Step 3b — Backlog status: mark In Progress

Immediately after writing the spec file, update `backlog.md`:

1. **Find the matching backlog item** (search by feature name / number).
   - If one exists (status `[ ]`): flip it to `[~]` and append a spec link:
     ```
     - [~] **N. <title>** *(size)* — spec: docs/specs/<kebab-name>.md
     ```
   - If no item exists yet: add a new `[~]` entry in the appropriate backlog section.
2. **Mirror into the scrum backlog** (`Cline/scrum/product-backlog.md`):
   - Move the item from the Open table to the In-Progress table (per `scrum-artifacts.md`).
3. Do this **in the same turn** as writing the spec — do not defer.

> **Why:** The `[ ]` → `[~]` transition is the only visible signal that a spec exists and
> work is committed. Without it, `backlog.md` stays frozen and can't be used as a work-queue.

---

## Step 4 — Handoff

After writing the spec and updating the backlog, announce:

> **Spec written:** `docs/specs/<name>.md`
> **Backlog updated:** item #N set to `[~]` In Progress.
> **Next step:** Run `/loop` (or `/build` then `/review`) in ACT MODE to implement it.
> The spec is your source of truth — `/build` must not deviate from it.

### User Summary (optional)

For any `feature` or `docs` type spec that introduces a **new concept or workflow** —
one that a non-technical stakeholder would benefit from reading in plain English —
offer to write a User Summary note alongside the spec.

**When to offer:** the spec introduces a new process, pattern, tool, workflow, or
architectural concept. Skip for bugfixes, chores, pure-CSS, or purely mechanical changes.

**How to offer** (interactive session):
> "This spec introduces a new [concept/workflow]. Would you like me to write a
> plain-English User Summary to `Cline/User Summaries/YYYY-MM-DD-<topic>-user-summary.md`?"

Write it if the user confirms, or immediately if the workflow is unattended.

**File convention:**
```
Vault path:  <OBSIDIAN_VAULT_PATH>/Cline/User Summaries/
File name:   YYYY-MM-DD-<topic-slug>-user-summary.md
```

YAML frontmatter:
```yaml
---
title: "<Concept Name> — Plain-English Summary"
created: YYYY-MM-DD
tags: [usai-chat, user-summary, <topic-tags>]
source: cline
---
```

A good User Summary contains: **What is it?** · **Why does it matter?** ·
**How does it work?** (simple flow/table) · **Where to learn more** (links to spec/docs).
Keep it ≤ 2 pages. Link related notes with `[[wikilinks]]`.

**This step is non-blocking** — missing a User Summary does not fail `/review` or
block `/loop` completion. See also: `.clinerules/workflows/self-improve.md` §User Summary.
