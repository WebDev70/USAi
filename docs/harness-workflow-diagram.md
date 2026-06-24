# Cline & Continue Harness — Workflow Diagram

Both harnesses implement the same **RAIL pipeline** but in different ways.
They operate independently yet read from the same shared files.

```mermaid
flowchart LR
    subgraph CLINE["🤖 CLINE  (.clinerules/)"]
        direction TB
        A1["/spec\nPLAN MODE — interview → spec doc"]
        A2["/build\nACT MODE — implement TDD-style"]
        A3["/review\nACT MODE — QA gate, repeat if failing"]
        A1 --> A2 --> A3
    end

    subgraph SHARED["🔗 SHARED FILES"]
        direction TB
        S1["AGENTS.md\n(operating contract)"]
        S2["docs/rail-pipeline.md\n(RAIL concept + testing)"]
        S3["docs/specs/\n(feature spec files)"]
        S4["Obsidian Vault\n(Cline → Cline/memories/\nContinue → Continue Extension/memories/)"]
        S5["USAi app source\n(index.html · app.js · server.py · styles.css · tests/)"]
    end

    subgraph CONT["🔧 CONTINUE  (.continue/)"]
        direction TB
        B1["Rules\n(.continue/rules/) — always-on guidance"]
        B2["Agents\n(.continue/agents/) — role modes"]
        B3["/check\n(.continue/checks/ · cli-check.sh) — QA gate"]
        B1 --> B2 --> B3
    end

    CLINE <--> SHARED
    CONT  <--> SHARED
```

## Legend

| Symbol | Meaning |
|--------|---------|
| `🤖 CLINE` | Cline VS Code extension — slash-command workflows in `.clinerules/` |
| `🔧 CONTINUE` | Continue VS Code extension — rules/checks/agents in `.continue/` |
| `🔗 SHARED` | Files both harnesses read from (neither owns them exclusively) |
| `↔` | Reads from **and** writes to (e.g. Cline's `/spec` writes `docs/specs/`, Continue's `/check` validates the same specs) |

## Key differences

| | Cline | Continue |
|-|-------|----------|
| **Workflow model** | Plan/Act toggle + slash-command workflows | Always-on rules + `/check` command |
| **QA gate** | `/review` workflow | `/check` (VS Code) or `scripts/cli-check.sh` (CLI) |
| **Spec files** | Written by `/spec`, consumed by `/build` | Consumed by checks |
| **Memory subfolder** | `Cline/memories/` | `Continue Extension/memories/` |
| **Private config** | `.clinerules/` | `.continue/` |

## References

- [`docs/ORGANIZATION.md`](ORGANIZATION.md) — three-concern map (USAi app / Cline / Continue)
- [`docs/rail-pipeline.md`](rail-pipeline.md) — shared RAIL concept + testing strategy
- [`docs/tooling/cline.md`](tooling/cline.md) — Cline harness detail
- [`docs/tooling/continue.md`](tooling/continue.md) — Continue harness detail
- `AGENTS.md` — shared operating contract
