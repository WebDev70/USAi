# Continue Dev Harness — Reference Guide

> **Concern: Continue dev harness** — this document covers the VS Code
> [Continue](https://continue.dev/) extension configuration only. It is NOT part
> of the USAi Chat app and NOT the Cline harness. See
> [`docs/ORGANIZATION.md`](../ORGANIZATION.md) for the full three-concern map.

The Continue extension reads `.continue/` to govern how an AI coding assistant
behaves while building USAi Chat. Nothing in `.continue/` is part of the running
application.

**Canonical cross-harness reference:** [`docs/rail-pipeline.md`](../rail-pipeline.md)
(RAIL concept + testing strategy, harness-agnostic).

---

## Directory layout

| Path | Role |
|------|------|
| `.continue/rules/` | Always-on (or glob-scoped) behavioral rules — the "how to work" |
| `.continue/checks/` | `/check` QA pass/fail gates — the "verify it was done" |
| `.continue/agents/` | Selectable agent modes (product-owner, planner, security, improver) |
| `.continue/mcpServers/` | MCP server connections (Obsidian, etc.) |
| `.continue/rules/CONTINUE.md` | Full architecture reference + troubleshooting (deep Continue-specific reference) |
| `scripts/cli-check.sh` | CLI equivalent of `/check` — runs the coverage-gated suite, optionally `cn review` |

---

## How Continue implements RAIL

The **RAIL pipeline** in Continue is expressed as:

| RAIL mechanism | Continue artifact | Trigger |
|----------------|-------------------|---------|
| Behavioral guidance per role | **Rules** (`.continue/rules/*.md`) | Always-on (`alwaysOn: true`) or glob-scoped (`globs: [...]`) or manually invoked |
| QA pass/fail gates | **Checks** (`.continue/checks/*.md`) | Run via `/check` command in VS Code (or `scripts/cli-check.sh` from CLI) |
| Dedicated role modes | **Agents** (`.continue/agents/*.yaml`) | Selected from the agent dropdown |

### Rule trigger types

| Type | How it activates | Which of our rules |
|------|------------------|--------------------|
| **Always-on** | Loaded for every chat in this project | `code-planner`, `development-sme`, `testing-standards`, `tdd-workflow`, `continuous-improvement`, `product-owner`, `agile-workflow`, `devsecops`, `infrastructure-as-code`, `observability`, `keep-docs-in-sync`, `CONTINUE.md` |
| **Auto-attached (glob)** | Loaded when matching files are open | `ui-ux-design` (`index.html`, `styles.css`) |
| **Agent-requested** | Explicitly invoked from the agent dropdown | Any of the dedicated agent modes |

### Checks (QA gates)

Checks live in `.continue/checks/` and are evaluated when you run `/check` in VS Code.
Each file is a pass/fail criterion. The full list:

- `definition-of-ready.md` — start gate for features
- `test-coverage.md` — TDD + coverage gates met
- `security-review.md` — no secrets, no traversal, SSRF guard
- `dependency-and-supply-chain-review.md` — no unjustified runtime dep
- `iac-review.md` — env/config declarative + drift-free
- `code-quality-review.md` — conventions + minimal runtime surface
- `docs-in-sync.md` — docs updated in same turn
- `ui-ux-review.md` — accessibility + token-driven (frontend only)
- `acceptance-criteria.md` — end gate for features
- `definition-of-done.md` — meta-gate: all of the above

See [`docs/rail-pipeline.md`](../rail-pipeline.md) §3 for what each check verifies.

### Agent modes

| Agent YAML | Role | When to use |
|------------|------|-------------|
| `agents/product-owner.yaml` | Product Owner | Groming backlog items; Definition of Ready; acceptance review |
| `agents/planner.yaml` | Code Planner | Complex plan-before-code tasks |
| `agents/security.yaml` | Security | Focused security review pass |
| `agents/improver.yaml` | Continuous Improvement | Post-cycle retrospective; proposing new rules/checks |

---

## Running QA gates

### In VS Code
Run **`/check`** — Continue evaluates every check file in `.continue/checks/` and
reports pass/fail for each criterion.

### From the CLI (Continue CLI / headless)
The `/check` QA-gate is a **VS Code extension** feature — the Continue CLI (`cn`)
has no `/check` command. Use `scripts/cli-check.sh` instead:

```bash
./scripts/cli-check.sh              # coverage-gated test suite only (matches test-coverage check)
./scripts/cli-check.sh --review     # suite + cn review with all check files as rules
./scripts/cli-check.sh --review-only# skip tests; AI review pass only
```

The script:
1. Runs `./run-tests.sh --coverage` (same gate as the `test-coverage` check).
2. Optionally feeds each `.continue/checks/*.md` file into `cn review --rule` so
   the AI review applies security, code-quality, docs-in-sync, and ui-ux standards.
3. Falls back to `npx @continuedev/cli --config ~/.continue/config.yaml` when `cn`
   isn't on `PATH`.
4. Exits non-zero on gate failure (CI / pre-push friendly).

> **Note:** The **rules** in `.continue/rules/` *are* loaded automatically by the
> Continue CLI when launched from the project root — only the **checks** need the
> script.

---

## Obsidian memory (Continue's own)

Continue writes session notes to **`Continue Extension/memories/`** in the vault.
The directive lives in `AGENTS.md` (shared operating contract). Prefer direct
filesystem I/O over the MCP server — the vault is just a folder, it never times out,
and Obsidian auto-indexes new files.

```
<your OBSIDIAN_VAULT_PATH>/
└── Continue Extension/
    └── memories/                   ← Continue writes here
        └── YYYY-MM-DD-HHMMSS-title.md
```

Recall: at the start of any non-trivial task, search **all three** memory subfolders
(`USAi/memories/`, `Continue Extension/memories/`, `Cline/memories/`) so nothing
from Cline sessions is missed.

---

## MCP setup (Obsidian)

The optional `obsidian-mcp` bridge is configured in
`.continue/mcpServers/new-mcp-server.yaml`. It is **secondary** to direct filesystem
I/O and known to intermittently time out (`-32001`).

**Reliable ritual if MCP hangs:**
1. `./scripts/kill-stale-obsidian-mcp.sh` — kill orphaned processes.
2. **Fully quit VS Code** (Cmd+Q) → reopen.
3. Confirm **exactly one** `obsidian-mcp` process: `ps aux | grep obsidian-mcp`.
4. If a single process still times out, reload the MCP server / VS Code window.

The binary must use a compatible Node version (Node 20 LTS recommended). If you
manage multiple Node versions with nvm, re-run `npm i -g obsidian-mcp` for the
active version and update both `command` and `args[0]` in the YAML to point to it.

**Harmless companion error:** `-32601 Method not found` at load = Continue probing
for "resource templates"; obsidian-mcp exposes tools, not that optional capability.

For detailed troubleshooting see `.continue/rules/CONTINUE.md` §7.

---

## Coding conventions enforced by Continue rules

> **Canonical source:** [`docs/rail-pipeline.md` §3](../rail-pipeline.md)
> lists all USAi coding conventions (CSS cache-bust, tool gating, endpoint
> pattern, SSRF guard, minimal runtime surface). This section is a concise
> pointer — the rail-pipeline doc is the single source of truth.

- **No new runtime deps.** Frontend = vanilla JS; backend = stdlib + `python-dotenv`.
- **Security first.** Secrets stay server-side; `/config` returns only `has_*` flags.
- **Path safety.** Any FS endpoint must reject traversal and confine writes.
- **Docs in same turn.** CHANGELOG for every notable change; USER_GUIDE for
  user-facing features; README for setup/config.
- **TDD.** Write the failing test first (Red → Green → Refactor).
- For CSS bump, tool gating, new-endpoint pattern, and SSRF guard details see
  [`docs/rail-pipeline.md` §3 — Code Planner approach](../rail-pipeline.md).

---

## References

- [`docs/rail-pipeline.md`](../rail-pipeline.md) — shared RAIL concept + testing strategy
- [`docs/ORGANIZATION.md`](../ORGANIZATION.md) — three-concern map
- [`docs/tooling/cline.md`](cline.md) — Cline harness reference
- [`.continue/rules/CONTINUE.md`](../../.continue/rules/CONTINUE.md) — deep Continue architecture reference + troubleshooting
- `AGENTS.md` — shared operating contract (memory, security, conventions)
- Continue Checks docs — https://docs.continue.dev/checks/quickstart
