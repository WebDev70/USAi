# Scrum Artifacts — Cline Always-On Rule
# (Agile/Scrum artifact maintenance for USAi Chat)

> **Concern: Cline dev harness** — this rule governs the *Cline* VS Code extension
> only. It is NOT part of the USAi Chat app and NOT the Continue harness.
> See `docs/ORGANIZATION.md` for the full three-concern map.
>
> **Canonical scrum reference:** `<OBSIDIAN_VAULT_PATH>/Cline/scrum/README.md`

---

## Purpose

Keep all Agile/Scrum artifacts up to date in the Obsidian vault under `Cline/scrum/`
as work flows through the RAIL pipeline. Cline owns and maintains this folder;
no other harness writes here.

---

## Vault paths

| Path | Purpose |
|------|---------|
| `Cline/scrum/README.md` | Index, cadence guide, conventions |
| `Cline/scrum/definition-of-ready.md` | DoR checklist |
| `Cline/scrum/definition-of-done.md` | DoD checklist |
| `Cline/scrum/product-backlog.md` | Themed backlog overview (canonical: `backlog.md`) |
| `Cline/scrum/sprint-index.md` | Running sprint table |
| `Cline/scrum/templates/sprint-template.md` | Sprint note template |
| `Cline/scrum/sprints/sprint-NN.md` | Per-sprint notes |

**Access route (preferred — primary):** Direct filesystem I/O. The vault is a plain
folder at `$OBSIDIAN_VAULT_PATH` (e.g. `/Users/ronaldbblake/Documents/Obsidian Vault`).
Write Markdown files directly; Obsidian auto-indexes them. This never times out.

**Access route (secondary):** `obsidian` MCP server tools (`create-note`, `edit-note`).
Use only when richer tag/note operations are needed. Falls back to filesystem if the
server times out with JSON-RPC `-32001`.

---

## When to create / update artifacts

### On sprint start

When a new sprint is agreed (user requests `/spec` for a new backlog item, or asks
to start a sprint):

1. **Create** `Cline/scrum/sprints/sprint-NN.md` by copying the template from
   `Cline/scrum/templates/sprint-template.md`.
2. Fill in Sprint Goal, Sprint Backlog (verify each item passes `definition-of-ready`),
   dates, and Status: Active.
3. **Append** a new row to `Cline/scrum/sprint-index.md`:
   `| [[sprints/sprint-NN\|Sprint NN]] | Active | <goal> | YYYY-MM-DD | — | N | — | — |`
4. **Update** `Cline/scrum/product-backlog.md` — move item(s) from open to in-progress.

### On item completion (RAIL `/loop` Done criteria met)

When a RAIL loop passes all Done criteria for a backlog item:

1. **Update** the sprint note `Cline/scrum/sprints/sprint-NN.md`:
   - Change the sprint backlog item status from `in-progress` → `done` and tick `[x]`.
   - Record actual acceptance criteria outcomes (✅ / ❌) in the item detail section.
2. **Update** `Cline/scrum/product-backlog.md`:
   - Move item from open/in-progress to the Completed table.

### On sprint close (Review + Retrospective + Governance)

When all sprint items are complete (or sprint cadence expires):

1. **Append** the Sprint Review section to `Cline/scrum/sprints/sprint-NN.md`:
   - What shipped (outcomes), what didn't ship, metrics (items completed, coverage gates, security scan).
2. **Append** the Sprint Retrospective section:
   - What went well, what didn't, improvements for next sprint.
3. **Update** `Cline/scrum/sprint-index.md` — fill in End date, Velocity, Outcome, Status: Done.
4. **Write** a Cline memory note:
   `Cline/memories/YYYY-MM-DD-HHMMSS-sprint-NN-retro.md` with frontmatter
   `tags: [usai-chat, scrum, sprint-retro, sprint-NN]` summarising goal, outcome,
   velocity, top retro item.
5. **Trigger Governance Board audit.** Announce:
   > "Sprint NN is closed. Triggering Governance Board sprint-close audit (`/govern`)."
   Then run the `/govern` workflow (`.clinerules/workflows/govern.md`) — all four
   roles (SBA · SA · SE · SPMS) across the whole project. File the report to
   `Cline/scrum/governance/YYYY-MM-DD-HHMMSS-governance-report.md`.
   Append the governance summary to the sprint note. Present BLOCKING/ADVISORY/
   INNOVATION findings to the user for confirmation before any backlog changes.

---

## Note conventions

- All scrum notes: YAML frontmatter with `title`, `created`, `updated`, `tags`, `source: cline`.
- Sprint-scoped notes: add `sprint: N` and `status: Planning | Active | Done | Archived`.
- Tags always include `usai-chat` and `scrum`, plus the artifact-type tag.
- Sprint backlog item line:
  `- [ ] **#NN <title>** — *(size: S/M/L)* — owner: Cline — status: todo|in-progress|review|done — [[backlog#NN]]`
- **Never delete or overwrite** existing sprint notes — append new sections only.
- **Confine all writes** to `Cline/scrum/` and `Cline/memories/`. Never write to
  `USAi/memories/`, `Continue Extension/memories/`, or any other harness subfolder.

---

## Recall

At the start of any non-trivial task (especially sprint planning or grooming),
**search all three memory locations** for relevant prior context before proceeding:
- `Cline/memories/`
- `Cline/scrum/`
- `Continue Extension/memories/`
- `USAi/memories/`

---

## Security

- Never include API keys, Bearer tokens, or passwords in any scrum note.
- Never include `sk-` prefixed values.
- `scripts/security-scan.sh` memory-note scan (4/4) applies to `Cline/memories/`.

---

*References: `docs/ORGANIZATION.md` · `.clinerules/rail-pipeline.md` · `AGENTS.md` · `Cline/scrum/README.md`*
