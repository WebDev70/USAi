# Workflow: /self-improve
# Cline RAIL — Self-Scoring Rewrite Loop

> **Concern: Cline dev harness** — this workflow is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Mode:** ACT MODE (or any sub-task within /build or /spec)

**Purpose:** Apply an iterative self-improvement loop to any discrete output — a
function, a doc section, a spec, a test, or a paragraph of prose. The AI scores
its own work and rewrites it until the score meets the bar or three iterations
have passed. This is the "single-paragraph prompt" technique adapted as a
reusable workflow.

---

## When to use this

Use `/self-improve` as a sub-task inside any RAIL role when quality matters and a
single-pass output may not be good enough:

| Context | Scoring axes |
|---------|-------------|
| Writing spec §1–4 (Goal, AC, Approach) | Clarity · Completeness · Testability |
| Writing a complex function | Correctness · Edge-case coverage · Readability |
| Writing tests | Coverage · Specificity · Determinism |
| Writing CHANGELOG / docs | Accuracy · Conciseness · Audience |
| Writing a security fix | Correctness · No regression · Defense depth |

---

## The self-scoring prompt (drop this into any sub-task)

> Complete the task below. When finished, score your output from **1–10** on
> **[pick the relevant axes from the table above]**. If your score is below **9**,
> identify the **top 1–3 weaknesses**, rewrite the output to address them, and
> score again. Repeat until you reach **9 or higher**, or until you have iterated
> **three times**, whichever comes first. Show only the **final output** and your
> **last score**.

---

## Step-by-step (how Cline applies it)

### Step 1 — Complete the task
Produce the first-pass output for the sub-task.

### Step 2 — Score it
Score the output 1–10 on the chosen axes. Be honest — a 6 should read like a 6.

```
Score: X/10
Axes:  Correctness: X | Clarity: X | Coverage: X | [other axes]: X
```

### Step 3 — If score ≥ 9 → done
Emit the output and the score. No further iteration needed.

### Step 4 — If score < 9 → identify weaknesses + rewrite
List the top 1–3 weaknesses concisely (one line each), then rewrite the output
to address them. Score the rewrite.

```
Weaknesses:
1. <weakness>
2. <weakness (if any)>
3. <weakness (if any)>

[Rewritten output]

Score: Y/10
```

### Step 5 — Repeat once more if score still < 9
If the rewrite is still below 9, do one final iteration (iteration 3). After the
third iteration, emit the best output regardless of score, with a note on what
remains imperfect.

### Step 6 — Emit final result
Show **only** the final output + the final score. Do not show intermediate drafts
unless the user asks.

---

## Example: scoring a spec's acceptance criteria section

> Task: write acceptance criteria for "the /health endpoint returns 200 + JSON".
>
> Draft 1: "The endpoint works correctly."
> Score: 2/10 — Correctness: 3 | Testability: 1 | Specificity: 1
> Weaknesses: 1) Not testable as written. 2) No HTTP method specified. 3) No
>   response shape described.
>
> Draft 2:
> - [ ] AC-1: `GET /health` returns HTTP 200
> - [ ] AC-2: Response body is valid JSON with key `"status": "ok"`
> - [ ] AC-3: Response includes `Content-Type: application/json` header
> Score: 9/10 — Correct, testable, specific. Minor: doesn't cover error case.
>
> Final output: [Draft 2]
> Final score: 9/10

---

## Notes

- The loop is bounded at 3 iterations — it never runs indefinitely.
- Use this within `/build` when implementing a particularly complex function.
- Use this within `/spec` when drafting acceptance criteria or a tricky risk section.
- The self-scoring is honest, not inflated — 9/10 means "ready to ship", not
  "I tried my best".

---

## Proposing improvements after `/self-improve`

If `/self-improve` surfaces a structural improvement to the project (a new check,
rule, test, or process change), record it in **both** sinks — not as an inline chat
suggestion:

### Sink 1 — `backlog.md`

Add a new `- [ ] **N. <title>** *(size)*` entry under the appropriate backlog
section. The entry must include:
- A one-sentence description of the improvement.
- Why it was identified (context from the self-improvement loop).
- A size estimate (S / M / L / XL).

Do this in the **same turn** — do not defer to "the user can add it later".

### Sink 2 — Obsidian

Write a tagged note to `Cline/memories/`:

```
File: <OBSIDIAN_VAULT_PATH>/Cline/memories/YYYY-MM-DD-HHMMSS-<topic>-proposals.md
Tags: [usai-chat, rail-loop, proposals, self-improve, <topic-tags>]
```

Include each proposal with a brief rationale and a link to the `backlog.md` entry
(e.g. "→ backlog #N").

**Never leave a proposal as a chat suggestion only.** If you identify an improvement,
it belongs in both sinks so it survives the session.

---

## User Summary (optional)

After any `/self-improve` session that produces a **structural explanation** of a
process, concept, or workflow — one with clear standalone value for non-technical
readers — offer to write a plain-English **User Summary** note to the Obsidian vault.

### When to write one

Write a User Summary when the session output includes:
- A new explanation of a RAIL role, workflow, or concept (e.g. "how `/spec` works")
- A newly coined convention or pattern (e.g. "how memory notes are structured")
- Any rewrite that a non-developer stakeholder would benefit from reading

Do **not** write one for pure mechanical fixes (typo corrections, formatting, minor
refactors) that have no conceptual content.

### File convention

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

### How to offer it

In an **interactive session** (user is present), announce after the main output:

> "This session produced a structural explanation. Would you like me to write a
> plain-English User Summary to `Cline/User Summaries/YYYY-MM-DD-<topic>-user-summary.md`?"

Write it if the user confirms, or immediately if the workflow is unattended.

### What to include

A good User Summary contains:
- **What is it?** — one-paragraph plain-English answer (no jargon)
- **Why does it matter?** — the problem it solves or the value it adds
- **How does it work?** — a simple flow or table; no code unless essential
- **Where to learn more** — links to the technical docs (spec, rule file, etc.)

Link related notes with `[[wikilinks]]`. Keep it ≤ 2 pages.

### This step is non-blocking

Missing a User Summary does **not** fail `/review` or block `/loop` completion.
It is a value-add output, not a quality gate.
