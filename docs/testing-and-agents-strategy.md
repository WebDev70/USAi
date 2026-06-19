# Testing & Agent Pipeline Strategy — USAi Chat

This document defines (1) the **unit-testing strategy** for USAi Chat and (2) a
**five-role agent pipeline** that automates planning, implementation, testing, QA
review, and continuous improvement as we make changes. It is the reference for the
rules (`.continue/rules/`), checks (`.continue/checks/`), and agents
(`.continue/agents/`) we add to the repo.

> Status: **PLAN (approved).** Implementation lands incrementally; this doc is the
> source of truth. Tracked as backlog item **#17**.

---

## 1. Guiding principles

- **Zero new runtime dependencies.** USAi Chat is intentionally dependency-light
  (vanilla JS frontend + Python stdlib backend + `python-dotenv`). The test stack
  must honor that.
- **Test the logic, not the framework.** Focus on pure, deterministic functions
  and the security-critical backend behavior; avoid brittle DOM/network tests.
- **Automation via Continue.** Use Continue **rules** (personas/standards),
  **checks** (`/check` pass-fail gates), and **agents** (dedicated modes), wired
  together through `AGENTS.md`. Optional CI (GitHub Actions / git hook) can run the
  same commands unattended later.
- **Docs + memory stay in the loop.** Every change keeps docs in sync (existing
  rule) and the Continuous-Improvement role records learnings to Obsidian.

---

## 2. Test stack (no new deps)

| Layer | Tool | Rationale |
|-------|------|-----------|
| **Python backend** (`server.py`) | **`unittest`** (stdlib) | No install; first-class for stdlib HTTP server logic. |
| **JS frontend** (`app.js`) | **`node --test`** (Node 18+ built-in test runner) | No npm install, no framework; tests pure functions. |
| **Syntax gates** | `node --check`, `python3 -m py_compile` | Already part of the workflow; cheap and fast. |

### Why not pytest / jest / vitest?
They're excellent, but each adds dependencies/build tooling that conflicts with the
project's "no build step, stdlib-only" philosophy. We can revisit if the suite
outgrows the stdlib runners.

### What to test first (high value, low friction — pure functions)

**JS (`app.js`)** — extract/test pure helpers:
- `renderMarkdown(src)` — escaping + whitelist (XSS safety is security-relevant).
- `extractJson(text)` — recovers JSON from fenced/prose-wrapped replies.
- `formatUsage(usage)` — tolerant of `prompt_tokens`/`input_tokens` naming.
- `getExcludedParams(model)` / `MODEL_PARAM_EXCLUSIONS` — per-model param omission.
- `buildResponseFormat(inputs)` — json_object vs json_schema shaping.

**Python (`server.py`)** — security & filesystem behavior:
- `get_memory_dir()` — resolves `<vault>/<subdir>/memories`, **rejects traversal**.
- `_get_config` — returns **only** non-secret fields + `has_*` flags (never keys).
- `/memory/save` + `/memory/list`/`/memory/read`/`/memory/search` — round-trip,
  filename sanitization, frontmatter, confinement to the memory folder.
- Route registration in `do_GET`/`do_POST`/`do_DELETE` — input-size limits.

> **Testability note:** some helpers are currently inline. Part of this effort is
> *lightly* refactoring a few pure functions so they're importable/exportable for
> tests **without** changing behavior (e.g. guard `module.exports` in `app.js` for
> Node, keep functions module-level in `server.py`).

### Layout & conventions

```
tests/
├── python/
│   └── test_server.py        # unittest.TestCase classes; run with `python3 -m unittest`
└── js/
    └── app.test.mjs          # node:test + node:assert; run with `node --test`
```
- **Naming:** `test_*.py` (Python), `*.test.mjs` (JS).
- **Determinism:** no live network/API calls; stub/monkeypatch where needed.
- **Speed:** the whole suite should run in seconds.

### One-command runner (documented in README/CONTINUE.md)

```bash
# Syntax gates
node --check app.js && python3 -m py_compile server.py
# Unit tests
node --test $(find tests/js -name '*.test.mjs')
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'
```

---

## 3. The five-role agent pipeline

A closed loop that turns a request into reviewed, tested, documented code — and
feeds learnings back in.

```
Code Planner → Development SME → Full Test Suite → QA Review → Continuous Improvement
     ▲                                                                   │
     └──────────── new rules/checks/tests, backlog items, learnings ◄────┘
```

| # | Role | Implemented as | Responsibility |
|---|------|----------------|----------------|
| 1 | **Code Planner** | rule `code-planner.md` (always-on for non-trivial changes) + optional `agents/planner.yaml` mode | Produce a structured **plan** (below) before editing. |
| 2 | **Development SME** | rule `development-sme.md` | Implement the plan idiomatically — vanilla JS / stdlib Python, no new deps, security-first, bump `styles.css?v=N` on CSS. |
| 3 | **Full Test Suite** | rule `testing-standards.md` + `tests/` scaffold | Write/maintain tests for the change and run the suite. |
| 4 | **QA Review** | checks in `.continue/checks/` run via `/check` | Automated **pass/fail** gates (test-coverage, security, code-quality, docs-in-sync). |
| 5 | **Continuous Improvement** | rule `continuous-improvement.md` + optional `agents/improver.yaml` | Reflect after each cycle; **propose** new checks/rules/tests + backlog items; **record a learning note** to Obsidian. |

### Code Planner — required plan template
The Planner outputs a brief plan (skip for trivial edits) that seeds every later
role:
- **Goal & scope** (what / why)
- **Affected files** (+ any new files)
- **Approach** (functions/endpoints to add or change; conventions to respect —
  tool-gating in `getEnabledTools`, `/config` redaction, path-traversal guards,
  CSS `?v=N` bump)
- **Test plan** (specific cases → which test file)
- **Docs to update** (CHANGELOG / USER_GUIDE / README / etc.)
- **Risks / edge cases / out-of-scope**

### QA Review — the checks (pass/fail)
- **`test-coverage`** — new/changed code has corresponding tests following the
  conventions in §2.
- **`security-review`** — no hardcoded secrets; `/config` exposes no keys; any
  filesystem endpoint validates input and rejects path traversal.
- **`code-quality-review`** — matches project conventions; **no new runtime deps**;
  CSS changes bump `styles.css?v=N`; comments explain *why*.
- **`docs-in-sync`** — the right docs were updated this change (ties to the existing
  `keep-docs-in-sync` rule).
- **`ui-ux-review`** — *(frontend changes only)* the UI stays accessible (WCAG AA
  contrast, visible focus, semantic/ARIA, reduced-motion), responsive, and
  token-driven, with no new frontend dependency. Paired with the
  `ui-ux-design` rule below.

### Quality axis — Front-End Design (UI/UX) role
Alongside the five *correctness* roles, a **Front-End Design (UI/UX) SME** keeps
`index.html`/`styles.css` modern and user-friendly. It is an **auto-attached rule**
(`.continue/rules/ui-ux-design.md`, scoped via `globs` to the frontend files) plus
the `ui-ux-review` check above — so it adds no overhead to backend-only changes.

- **Constraints:** "latest innovative design" = modern **vanilla CSS** (fluid
  `clamp()` type, `color-mix()`, logical properties, container queries / `:has()`,
  View Transitions) — **never** a framework, icon pack, or build step. Extend the
  existing CSS-custom-property token system + light/dark themes; don't rewrite them.
- **Accessibility is the core of "user-friendly":** WCAG AA contrast in both themes,
  `:focus-visible`, semantic landmarks + ARIA on icon-only controls,
  `prefers-reduced-motion`, adequate hit targets.
- **Context7 in the loop:** consult Context7 for authoritative guidance and cite it
  — preferred reference is **USWDS** (`/uswds/uswds-site`), apt for "USAi"; adapt
  its *principles* to our vanilla CSS (don't add the package). Also query ARIA/WCAG
  and modern-CSS docs when a specific technique is in question.

### Continuous Improvement — autonomy & memory
- **Propose, don't auto-apply.** Suggests new checks/rules/tests and backlog edits
  for human approval.
- **Harvest recurring QA findings → automation.** If a check/review keeps catching
  the same class of issue, propose a new check/rule so it's caught automatically
  (a documented Continue pattern).
- **Record a learning note** to Obsidian `Continue Extension/memories/` each cycle
  (what shipped, what failed QA, what we automated, follow-ups) so the next task's
  Planner can **recall** it.

---

## 4. Triggering / automation

**Now (Continue-native):** wire the pipeline into `AGENTS.md` so the agent follows
*Plan → Implement → Test → `/check` → Improve* and runs `/check` after changes,
fixing failures before declaring done.

**CI (done):** a GitHub Actions workflow (`.github/workflows/tests.yml`) runs the
same §2 commands on every push / pull request — JS via `node --test` and Python
`unittest` on 3.9 + 3.11, plus syntax gates. A pre-commit git hook running
`./run-tests.sh` remains an optional future add for catching failures before they
leave a developer's machine.

---

## 5. Rollout plan (incremental)

1. **This doc + backlog #17** (done).
2. **Rules:** `code-planner.md`, `development-sme.md`, `testing-standards.md`,
   `continuous-improvement.md`.
3. **Checks:** `test-coverage.md`, `security-review.md`, `code-quality-review.md`,
   `docs-in-sync.md`.
4. **`tests/` scaffold** + a starter test proving the stack (e.g. `renderMarkdown`
   in JS and `get_memory_dir` traversal guard in Python), plus minimal refactors to
   make those functions importable.
5. **`AGENTS.md` workflow** wiring + **README/CONTINUE.md** "Running tests" update.
6. **(Optional) agents/modes** `planner.yaml`, `improver.yaml`.
7. **(Optional) CI** GitHub Actions / pre-commit.

---

## 6. References
- Continue Checks — quickstart, running locally, generating checks
  (https://docs.continue.dev/checks/quickstart).
- Continue Rules — `.continue/rules` for codebase-aware agent behavior.
- USWDS — U.S. Web Design System (Context7 `/uswds/uswds-site`), the preferred
  accessibility/UX reference for the Front-End Design role.
- `AGENTS.md` (this repo) — agent operating rules + memory directive.
- `.continue/rules/keep-docs-in-sync.md` — docs-as-part-of-done rule.
