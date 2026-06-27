# Workflow: /loop
# Cline RAIL — Build→Review Orchestrator

> **Concern: Cline dev harness** — this workflow is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Mode:** ACT MODE

**Purpose:** Run `/build` then `/review` in a tight loop until the build passes the
review cleanly. This is the "Generate → Evaluate → Fix → Repeat" engine at the heart
of the RAIL pipeline. It will not declare done until all gates are green.

---

## How to invoke

```
/loop [optional: path to spec, e.g. docs/specs/my-feature.md]
```

If no spec is named, Cline will look for the most recently modified spec in
`docs/specs/` with **Status: Ready** or **Status: In Progress**.

---

## The loop

```
Read spec
  ↓
ITERATION 1
  ├─ /build  (Roles 1–4: Plan → Architect → Develop → Test)
  │     └─ exits with build-complete checklist
  ↓
  ├─ /review (Roles 5–6: Security → QA)
  │     ├─ PASS → go to "Done"
  │     └─ FAIL → emit Gap List → go to ITERATION N+1
  ↓
ITERATION N+1
  ├─ /build  (fix only the gaps listed — no new scope)
  └─ /review (re-run all gates)
  ↓
  ...repeat until PASS (max 5 iterations before escalating)
  ↓
Done
```

---

## Iteration rules

### On each /build pass
- Fix **only** the gaps from the most recent `/review` gap list.
- Do not introduce new features or changes beyond the gap fixes.
- Re-run syntax gates after every file edit.
- Re-run the relevant test file after the fix before triggering `/review` again.

### On each /review pass
- Run all gates fresh — do not assume previous passes still hold.
- The gap list must shrink each iteration; if the same gap reappears, flag it as
  a blocking issue and escalate to the user.

### Escalation after 5 iterations
If the build has not passed `/review` after 5 iterations:

1. Stop the loop.
2. Show the user:
   - The current gap list (all unresolved items).
   - A summary of what was attempted each iteration.
   - A recommendation: update the spec, adjust the test gates, or ask for human
     help on the blocking issue.
3. **Write an escalation memory note** to Obsidian immediately — do not wait for
   the user's response. This captures the state so context is not lost:

   File: `<OBSIDIAN_VAULT_PATH>/Cline/memories/YYYY-MM-DD-HHMMSS-<feature>-escalation.md`

   ```markdown
   ---
   title: "RAIL escalation: <feature name>"
   created: YYYY-MM-DD
   tags: [usai-chat, rail-loop, escalation, <topic-tags>]
   source: cline
   ---

   # RAIL Loop Escalation: <Feature Name>

   **Date:** YYYY-MM-DD
   **Spec:** [[docs/specs/<feature>]]
   **Iterations attempted:** 5
   **Status:** ⚠ Escalated — loop stopped, user input needed

   ## Current gap list (unresolved after 5 iterations)
   - GAP-N: <description>

   ## Iteration history
   | Iteration | Gap fixed | New gap introduced |
   |-----------|-----------|-------------------|
   | 1 | — | <description> |
   | 2 | <gap> | <description or none> |
   | ... | | |

   ## Recommendation
   <one paragraph: update spec / adjust gate / human help needed — and why>
   ```

4. Do not keep looping without user input.

---

## Done criteria (all must be true)

- [ ] `/review` emits `✅ REVIEW — PASS`
- [ ] `./run-tests.sh --coverage` passes both coverage gates
- [ ] `./scripts/security-scan.sh` is clean
- [ ] Spec §8 Review checklist is fully checked off
- [ ] Spec **Status** updated to **Done**
- [ ] Docs updated per spec §6
- [ ] **Backlog item flipped `[~]` → `[x]`** with a Done date, one-line outcome,
      and spec link:
      ```
      - [x] **N. <title>** *(size)* — Done (YYYY-MM-DD): <one-line outcome>.
            Spec: docs/specs/<kebab-name>.md
      ```
      If the item is still `[ ]` or `[~]` at loop end, emit it as a `[docs]` GAP.
- [ ] **Scrum mirror updated** (`Cline/scrum/product-backlog.md`): item moved from
      In-Progress to the Completed table (per `scrum-artifacts.md` § "On item completion").
- [ ] Memory note exists in `Cline/memories/` for today's date:
      ```bash
      ls "$OBSIDIAN_VAULT_PATH/Cline/memories/" | grep "$(date +%Y-%m-%d)"
      ```
      If this returns no file, the "Memory note written" checkbox must remain
      **unchecked** and be emitted as a GAP — write the note before declaring done.
- [ ] Memory note written (see below)

---

## Role: Continuous Improvement (post-loop)

After a successful loop, before closing:

1. **Brief retro** — one sentence each:
   - What shipped?
   - What failed review and why?
   - What took the most iterations?

2. **Propose improvements** — for each proposal, write it into **both** sinks:

   a. **`backlog.md`** — add a new `- [ ] **N. <title>** *(size)*` entry under the
      appropriate section. Do this in the same turn; do not leave it as a chat
      suggestion.

   b. **Obsidian** — write a tagged note to `Cline/memories/`:
      ```
      File: <OBSIDIAN_VAULT_PATH>/Cline/memories/YYYY-MM-DD-HHMMSS-<feature>-proposals.md
      Tags: [usai-chat, rail-loop, proposals, <topic-tags>]
      ```
      List each proposal with a brief rationale and a link to the relevant backlog entry.

   Do not auto-apply any proposal — these are recorded for user review and approval.
   If the user approves a proposal, run `/spec` to promote it to a full spec.

3. **Write the memory note** to Obsidian:

   File: `<OBSIDIAN_VAULT_PATH>/Cline/memories/YYYY-MM-DD-HHMMSS-<feature>.md`

   ```markdown
   ---
   title: "RAIL loop: <feature name>"
   created: YYYY-MM-DD
   tags: [usai-chat, conversation-log, rail-loop, <topic-tags>]
   source: cline
   ---

   # RAIL Loop: <Feature Name>

   **Date:** YYYY-MM-DD
   **Spec:** [[docs/specs/<feature>]]
   **Iterations:** N
   **Final verdict:** PASS

   ## What shipped
   <one paragraph>

   ## What failed review (and was fixed)
   - GAP-N: <description> → Fixed by: <action>

   ## Decisions & learnings
   - <key decision or lesson>

   ## Follow-up proposals
   - [ ] <proposed check/rule/test/backlog item>

   ## Memory-note safety checklist
   - [ ] No API keys, Bearer tokens, or passwords in this note
   - [ ] No `sk-` prefixed values
   - [ ] `scripts/security-scan.sh` memory-note scan block passes (4/4)
   ```

---

## Quick-reference: the full loop flow

```
Goal
  ↓
/spec   → docs/specs/<feature>.md  (PLAN MODE)
  ↓
/loop   (ACT MODE)
  │
  ├─ Iteration 1
  │   ├─ /build  → Role 1 (Planner) → Role 2 (Architect) → Role 3 (Dev) → Role 4 (Tester)
  │   └─ /review → Role 5 (Security) → Role 6 (QA)
  │       ├─ PASS ──────────────────────────────────────────────────────┐
  │       └─ FAIL → Gap List                                            │
  │                     ↓                                               │
  ├─ Iteration N                                                        │
  │   ├─ /build  (fix gaps only)                                        │
  │   └─ /review (all gates)                                            │
  │       ├─ PASS ───────────────────────────────────────────────────── ┤
  │       └─ FAIL → (repeat or escalate after 5)                        │
  │                                                                      ↓
  └─ Done: tests green + security clean + docs updated + memory written
```
