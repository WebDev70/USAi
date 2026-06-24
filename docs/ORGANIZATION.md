# Project Organization — The Three Concerns

This repository contains **three distinct and separate things**. They share one
codebase folder but serve different purposes. Understanding the separation prevents
confusion when reading documentation or deciding where to put new files.

---

## The three concerns at a glance

| # | Concern | What it is | Who uses it |
|---|---------|------------|-------------|
| **1** | [**USAi Chat app**](#1-usai-chat-app) | The web application end users actually run | End users + developers |
| **2** | [**Continue dev harness**](#2-continue-dev-harness) | VS Code Continue extension config that helps *build* the app | Developers using Continue |
| **3** | [**Cline dev harness**](#3-cline-dev-harness) | VS Code Cline extension config that helps *build* the app | Developers using Cline |

\#1 is **the thing being built**. \#2 and \#3 are **two independent agent harnesses**
that help you build it. They share the same underlying pipeline concept (**RAIL**) and
the same Obsidian vault for memory — but they are *not* the same tool and should not
be confused.

---

## 1. USAi Chat app

> **The product.** A lightweight browser-based chat interface that connects to
> USAi-compatible model APIs. This is what users run.

### Files

| File / Directory | Role |
|------------------|------|
| `index.html` | Static chat UI |
| `app.js` | Browser logic (model selection, streaming, tools, memory) |
| `styles.css` | UI styling |
| `server.py` | Python stdlib backend — API proxy + local persistence endpoints |
| `requirements.txt` | Python runtime dependency (`python-dotenv`) |
| `Dockerfile` / `docker-compose.yml` | Container packaging |
| `Makefile` | One-word entry points (`run`, `test`, `scan`, `check`, …) |
| `tests/` | Zero-runtime-dep test suite (`node --test` + Python `unittest`) |
| `.env` / `.env.example` | Runtime configuration (API keys, URLs, vault path) |
| `docs/USER_GUIDE.md` | End-user guide |
| `docs/ARCHITECTURE.md` | Architecture & engineering reference — component map, request flow, endpoints, data stores, security |
| `docs/principles.md` | Engineering principles behind the app architecture |
| `docs/specs/` | Feature specs written during development (Cline → `/spec`) |
| `README.md` | Project setup and usage |
| `CHANGELOG.md` | Change history |
| `backlog.md` | Prioritized feature/improvement list |

### Obsidian memory (app's own)

The app writes Obsidian notes only to **`USAi/memories/`** in the vault.
Controlled by `.env → OBSIDIAN_MEMORY_SUBDIR=USAi`.

---

## 2. Continue dev harness

> **A VS Code extension config.** The [Continue](https://continue.dev/) extension
> reads `.continue/` to govern how an AI coding assistant behaves while working on
> the USAi app. Nothing in `.continue/` is part of the running application.

### Files

| File / Directory | Role |
|------------------|------|
| `.continue/rules/` | Always-on (or glob-scoped) behavioral rules — the "how to work" |
| `.continue/checks/` | `/check` QA pass/fail gates — the "verify it was done" |
| `.continue/agents/` | Selectable agent modes (product-owner, planner, security, improver) |
| `.continue/mcpServers/` | MCP server connections (Obsidian, etc.) |
| `.continue/rules/CONTINUE.md` | Full architecture reference + troubleshooting (Continue-specific) |
| `docs/tooling/continue.md` | Continue harness reference guide |
| `scripts/cli-check.sh` | CLI equivalent of `/check` (Continue checks without the VS Code UI) |

### How Continue implements RAIL

The **RAIL pipeline** in Continue is expressed as:
- **Rules** (`.continue/rules/*.md`) — always-on behavioral guidance for each role
- **Checks** (`.continue/checks/*.md`) — `/check` pass/fail gates run at QA Review
- **Agents** (`.continue/agents/*.yaml`) — optional dedicated modes per role

### Obsidian memory (Continue's own)

Continue writes notes to **`Continue Extension/memories/`** in the vault.
Governed by the memory directive in `AGENTS.md`.

---

## 3. Cline dev harness

> **A VS Code extension config.** The [Cline](https://github.com/cline/cline)
> extension reads `.clinerules/` to govern how it behaves while working on the
> USAi app. Nothing in `.clinerules/` is part of the running application.

### Files

| File / Directory | Role |
|------------------|------|
| `.clinerules/rail-pipeline.md` | Always-on RAIL rule — Cline's operating contract |
| `.clinerules/workflows/spec.md` | `/spec` workflow — PLAN MODE interview → writes `docs/specs/<feature>.md` |
| `.clinerules/workflows/build.md` | `/build` workflow — ACT MODE implementation engine |
| `.clinerules/workflows/review.md` | `/review` workflow — compares build vs spec, runs gates |
| `.clinerules/workflows/loop.md` | `/loop` workflow — iterates `/build` → `/review` until clean |
| `.clinerules/workflows/self-improve.md` | `/self-improve` workflow — continuous-improvement retro |
| `docs/tooling/cline.md` | Cline harness reference guide |
| `docs/specs/` | Output target — spec files written by `/spec` and consumed by `/build` |

### How Cline implements RAIL

The **RAIL pipeline** in Cline is expressed as slash-command workflows:

```
Goal
  ↓
/spec   (PLAN MODE — interview → write docs/specs/<feature>.md)
  ↓
/loop   (ACT MODE  — iterates /build → /review until clean)
  ├─ /build   (implement spec: Roles 1–4)
  └─ /review  (compare vs spec, run gates — repeat if failing)
  ↓
Done
```

### Obsidian memory (Cline's own)

Cline writes notes to **`Cline/memories/`** in the vault — its own subfolder,
separate from both the app (`USAi/memories/`) and Continue
(`Continue Extension/memories/`).

---

## Shared pieces

These two things are shared across all three concerns:

### RAIL — the pipeline concept

**RAIL** (*Rule-governed Agentic Iteration Loop*) is the shared pipeline *concept*
that both Continue and Cline implement. The roles are the same in both harnesses:

| Role | Description |
|------|-------------|
| 0. Product Owner | Definition of Ready + acceptance gate (features only) |
| 1. Code Planner | Structured plan before any editing |
| 2. Architect / SME | Validate design + implement TDD (Red → Green → Refactor) |
| 3. Tester | Write/run tests, enforce coverage gates |
| 4. Security | Deterministic security scan |
| 5. Reviewer (QA) | Full check suite, compare vs spec |

Cross-cutting: **DevSecOps** · **Infrastructure as Code** · **Observability**

The canonical harness-agnostic reference is
[`docs/rail-pipeline.md`](rail-pipeline.md) — covers the RAIL concept, TDD
strategy, test stack, and coverage gates. Harness-specific details live in
[`docs/tooling/continue.md`](tooling/continue.md) and
[`docs/tooling/cline.md`](tooling/cline.md).

### Obsidian vault — three separate writers

All three concerns share one Obsidian vault but write to **different subfolders**
so notes never collide:

| Writer | Saves to | Controlled by |
|--------|----------|---------------|
| **USAi Chat app** | `USAi/memories/` | `.env → OBSIDIAN_MEMORY_SUBDIR=USAi` |
| **Continue extension** | `Continue Extension/memories/` | Memory directive in `AGENTS.md` |
| **Cline extension** | `Cline/memories/` | Memory directive in `.clinerules/rail-pipeline.md` |

### `AGENTS.md` — the shared operating contract

`AGENTS.md` is read by **both** Continue and Cline (and any other agent). It
contains the shared rules that apply regardless of which harness is in use:
memory directive, security non-negotiables, coding conventions, and
running/validating commands. Each harness-specific concern (Continue `/check`,
Cline `/spec`→`/loop`) lives in its own config directory.

---

## Where to put new things

| What you're adding | Where it goes |
|--------------------|--------------|
| A new feature / bug fix in the app | `index.html`, `app.js`, `server.py`, `styles.css`, `tests/` |
| A new Continue rule (behavioral guidance) | `.continue/rules/` |
| A new Continue QA check | `.continue/checks/` |
| A new Continue agent mode | `.continue/agents/` |
| A new Cline workflow | `.clinerules/workflows/` |
| A spec for a new feature | `docs/specs/<feature>.md` (written by `/spec`) |
| A note about what the app does for users | `docs/USER_GUIDE.md` |
| A note about engineering principles | `docs/principles.md` |
| App architecture (component map, endpoints, data stores) | `docs/ARCHITECTURE.md` |
| Harness-agnostic pipeline / testing docs | `docs/rail-pipeline.md` |
| Continue-specific tooling docs | `docs/tooling/continue.md` |
| Cline-specific tooling docs | `docs/tooling/cline.md` |
