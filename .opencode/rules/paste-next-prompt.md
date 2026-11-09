# Paste-Next Prompt — OpenCode closing hand-off

> **Scope: OpenCode harness only.** Loaded through `opencode.json` → `instructions`.
> Cline and Continue keep their own wiring (`.clinerules/recommended-next-step.md`,
> `.continue/rules/recommended-next-step.md`).

Every *terminal* task — one that hands control back to the user — ends with the
`Recommended Next Step` section defined in
[`docs/rail-pipeline.md`](../../docs/rail-pipeline.md) § "Recommended Next Step",
followed by a **paste-ready prompt**. The user copies that prompt into the next turn
or a fresh session, so it must work without this conversation's context.

## Required shape

The section ends with these parts, in this order:

1. **Paste this next value:** a value the user must supply before the next step can
   run, such as an owner decision, a credential name, or an approval. If none is
   needed, write `Not needed now`. Never ask for a secret value itself; name where it
   lives instead (for example, "`CONTEXT7_API_KEY` is set in `.env`").
2. **Why:** one sentence explaining the value, or why none is needed.
3. **Paste this next:** a fenced `text` code block containing the prompt, with these
   labelled lines:
   - `Concrete next action:` one action, naming the item, file, or gap.
   - `Scope boundary:` what is in scope and what is explicitly out of scope.
   - `Source artifacts:` the files and records to read first, as repo-relative paths.
   - `Allowed autonomous actions:` what the agent may do without asking.
   - `Stop conditions:` when to stop and ask, and what it must never do in that run.
   - `Verification checks:` the tests, gates, or evidence that prove it is done.
   - `Evidence destination:` where results are recorded (files, `CHANGELOG.md`, the
     memory note).
   - `Finish with a fresh continuity block.` (always the last line)
4. **Next best step:** one sentence naming the step after that one, so the user can
   see the sequence.

## Rules

- **Self-contained.** No "as discussed" or "the fix above". Name paths and items.
- **Grounded.** Every path, test, and gate in the prompt must exist or be one the
  task will create. Derive it from verified state, not from an earlier block.
- **One action.** Same constraint as the `Recommended Next Step` section.
- **Policy-aware.** Respect constraints the user has stated (for example, no
  Homebrew on this machine). Turn missing tools or access into stop conditions.
- **No secrets.** The prompt never contains keys, tokens, or `.env` values.
