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
