# Spec: Clarify the "Max tokens" cap so it stops steering users into truncated answers

**Status:** Done
**Type:** bugfix
**Created:** 2026-09-20
**Author:** Cline (RAIL Role 0 skipped — bugfix; Role 1 Code Planner)
**Backlog:** #95 — 📋 ADVISORY — small default `max_tokens` truncates answers / clarify the cap *(XS)*

> **Prevention-rule recall:** Entry 001 (stale server — restart before diagnosing
> config) — *does not apply*, no server restart or `.env` change is involved here.
> No other self-improvement-log entries apply.
>
> **Prior-context recall:** Searched `Cline/memories/`, `Continue Extension/memories/`,
> `USAi/memories/`. Found the two #94 notes (project-context-isolation, same 2026-09-20
> user report that surfaced #95) and the 2026-09-20 push note. No prior decision on
> `max_tokens` behavior beyond CHANGELOG history: the input `max` ceiling was raised
> `96768 → 131072` on 2026-06-23, but the live `index.html` field currently shows
> `max="32768"` — a discrepancy this spec notes but does **not** change (see §1 Out of scope).

## 1. Goal & scope

**Goal.** A user reported LLM answers felt "so small" (observed 452 and 323 output
tokens). Investigation confirmed the app does **not** hard-cap output: `sendMessage()`
payload logic only sends `max_tokens` when the user has typed a positive value, and
that value is the ceiling. The real culprit is a **misleading UI hint** — the
`index.html` field uses `placeholder="e.g. 512 (or leave blank)"`, which nudges users
to type a small number (512) that then truncates every reply.

The fix is a **UX-clarity + documentation change only**, with **no behavior change** to
the request payload:
1. Replace the small-number placeholder with a neutral, non-steering hint that makes
   "blank = the model's own (large) default" the obvious, recommended choice.
2. Make the label/help text state plainly that leaving the field blank lets the model
   use its full default output length.
3. Document the same in `docs/USER_GUIDE.md` (the parameters table + a callout, and the
   "answers cut off / too short" troubleshooting entry).

**In scope**
- `frontend/index.html` — the `#maxTokens` `<input>` placeholder + its `<label>` help text.
- `docs/USER_GUIDE.md` — parameters table wording, the blank-means-omit callout, and a
  troubleshooting line for "answers feel too short."
- `CHANGELOG.md` — `[Unreleased] → ### Changed` (UI copy) entry.
- A JS regression test asserting the payload behavior the fix must **not** regress:
  blank → no `max_tokens` sent; a positive number → that exact `max_tokens` sent; and
  the value is still omitted for models that exclude `max_tokens` handling.

**Out of scope**
- Changing the default *behavior* — blank stays "omit the parameter." We are **not**
  adding a server-side default, a `DEFAULT_MAX_TOKENS` config, or a non-empty default value.
- Reconciling the `index.html` `max="32768"` attribute vs the historical `131072`
  ceiling. It is noted here as a known discrepancy but left for a separate chore so this
  XS bugfix stays minimal and behavior-neutral.
- Any reasoning-model param logic (`max_completion_tokens`, `temperature` exclusions) —
  must remain exactly as-is; the regression test guards it.
- CSS — no style change, so no `styles.css?v=N` bump.

## 2. User story & acceptance criteria

> As a **chat user**, I want the **Max tokens** field to *not* suggest a tiny value,
> so that my answers aren't silently truncated and I understand that leaving it blank
> gives me the model's full-length response.

- [ ] **AC-1** The `#maxTokens` placeholder no longer suggests `512` (or any small
  number that steers users into truncation). It reads as a neutral hint such as
  `Blank = model default (recommended)`.
- [ ] **AC-2** The field's label/help text makes clear that **blank = the model's own
  (large) default output length**, consistent with the existing `(blank = ...)` badge.
- [ ] **AC-3** Behavior is unchanged and proven by test: when Max tokens is **blank**
  (NaN) or `0` the request would send **no** `max_tokens`; when set to a positive
  integer N it would send `max_tokens === N`.
- [ ] **AC-4** No regression for models that exclude `max_tokens`: when the selected
  model is in the exclusion set, `max_tokens` is still omitted (and the existing
  `max_completion_tokens`/`temperature` exclusion logic is untouched).
- [ ] **AC-5** `docs/USER_GUIDE.md` states blank = model default in the parameters
  table and callout, and the troubleshooting section has an "answers feel too short →
  raise or clear Max tokens" entry.


## 3. Affected files

- `frontend/index.html` — `#maxTokens` `<input>` `placeholder` + surrounding `<label>`
  title/help copy (~L107–108). No `type`/`min`/`max` change.
- `frontend/app.js` — extract the inline `max_tokens` decision into a pure exported
  helper `shouldSendMaxTokens()` (behavior-preserving); use it in `sendMessage()`.
- `frontend/tests/js/max-tokens-payload.test.mjs` *(new)* — regression test for the
  payload-assembly behavior guarded by AC-3/AC-4.
- `docs/USER_GUIDE.md` — parameters table (~L187), callout (~L190), troubleshooting (~L617).
- `CHANGELOG.md` — `[Unreleased] → ### Changed`.

> **Note on testability:** `sendMessage()` builds the payload inline and is not a pure,
> exported function. The regression test targets the *decision predicate* directly —
> the same `!excludedParams.has('max_tokens') && !Number.isNaN(maxTokens) && maxTokens > 0`
> condition — via the exported pure helper `shouldSendMaxTokens(excludedSet, maxTokens)`
> extracted in §4, so the test exercises real code, not a copy.

## 4. Technical approach

**Frontend (index.html) — copy only.**
- Change `placeholder="e.g. 512 (or leave blank)"` → `placeholder="Blank = model default (recommended)"`.
- Adjust the label help/title so it reads e.g. `Max tokens (blank = model's full default)`
  — keep the existing muted `(blank = ...)` badge pattern already used for Temperature.

**Frontend (app.js) — behavior-preserving refactor for testability.**
- Extract the existing inline condition into a pure helper (placed near `getExcludedParams`):
  ```js
  // Decide whether to include max_tokens in the payload. Extracted so the
  // behavior contract (blank/0/NaN => omit; positive => include; excluded model
  // => omit) is unit-testable. Pure; no DOM/network.
  function shouldSendMaxTokens(excludedParams, maxTokens) {
    return !excludedParams.has('max_tokens') && !Number.isNaN(maxTokens) && maxTokens > 0;
  }
  ```
- Replace the two-branch `if/else if` block in `sendMessage()` so the `if` uses
  `shouldSendMaxTokens(excludedParams, inputs.maxTokens)` and the `else if` keeps the
  existing "omitted — not supported" log for the excluded-model case. Net behavior is
  byte-for-byte identical; only the boolean is now named and reusable.
- Export `shouldSendMaxTokens` in the `module.exports` block near `getExcludedParams`.

**Docs (USER_GUIDE.md).**
- Parameters table row for **Max tokens**: clarify that blank means the model uses its
  own (large) default and that a small value here will truncate replies.
- Callout: extend to mention that a *small* Max tokens value is the usual cause of
  short answers.
- Troubleshooting (~L617 area): add "Answers feel too short / cut off → clear the **Max
  tokens** field (or raise it) — a small value caps the reply length."

## 5. Test plan

| Test | File | Description |
|------|------|-------------|
| MT-1 | `frontend/tests/js/max-tokens-payload.test.mjs` | Blank/`NaN` maxTokens ⇒ `shouldSendMaxTokens` returns `false` (payload omits) — AC-3 |
| MT-2 | same | `maxTokens = 0` ⇒ `false` (omit) — AC-3 boundary |
| MT-3 | same | `maxTokens = 4096` with empty exclusion set ⇒ `true` — AC-3 |
| MT-4 | same | `maxTokens = 4096` but exclusion set contains `max_tokens` ⇒ `false` — AC-4 |
| MT-5 | same | `getExcludedParams` for a reasoning model still returns a Set (exclusion source untouched) — AC-4 |

Run: `./run-tests.sh --coverage` (JS branch ratchet currently 76.07% — the new pure
helper adds easily-covered branches; must not drop below the ratchet). No Python change,
so `server.py` coverage is unaffected.

## 6. Docs to update

- [ ] CHANGELOG.md — `[Unreleased] → ### Changed`
- [ ] docs/USER_GUIDE.md — parameters table + callout + troubleshooting (user-facing)
- [ ] README.md — not needed (no setup/config change)
- [ ] backlog.md — mark #95 done (+ scrum mirror)

## 7. Risks / edge cases

- **Behavior drift risk:** the only functional edit is a *pure extraction*; the
  regression test locks the truth table so a future edit can't silently change it. Low.
- **`max="32768"` discrepancy:** intentionally left alone (out of scope) — noted so a
  reviewer doesn't flag it as an omission.
- **Placeholder length:** the new placeholder is longer; verify it isn't visually
  clipped in the narrow sidebar input (manual check; no CSS change expected).
- **Reasoning models:** untouched — MT-4/MT-5 guard the exclusion path.

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ ratchet 76.07%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-5 all verified
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
