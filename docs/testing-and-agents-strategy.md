# Testing & Agent Pipeline Strategy — USAi Chat

This document defines (1) the **TDD-first unit/integration-testing strategy** for
USAi Chat and (2) **RAIL** — the **five-role agent pipeline** that automates
planning, implementation, testing, QA review, and continuous improvement as we make
changes. It is the reference for the rules (`.continue/rules/`), checks
(`.continue/checks/`), and agents (`.continue/agents/`) we add to the repo.

> ### What we call this — **RAIL** (Rule-governed Agentic Iteration Loop)
> The pipeline's name is **RAIL**. The acronym captures its two defining traits —
> it is **Rule**-governed (every role is an always-on rule in `.continue/rules/`
> plus pass/fail `/check` gates in `.continue/checks/`) and **Agentic** (the LLM,
> not a controller program, self-sequences through the roles). "Iteration **Loop**"
> reflects both the inner TDD cycle (Red → Green → Refactor) and the outer
> self-improvement loop (Continuous Improvement feeds new rules/checks/tests back
> in). The name also evokes *guardrails* — exactly what the rules and checks are:
> they keep an autonomous agent on track. Throughout the docs, "the **RAIL**
> pipeline" and "the five-role agent pipeline" refer to the same thing.

> Status: **ACTIVE.** The TDD workflow + coverage gates are in force. Tracked as
> backlog items **#17** (pipeline) and **#25** (TDD + coverage rigor).

---

## 0. Test-Driven Development (the default workflow)

We practice **TDD** for any non-trivial change to testable logic. The loop is
**Red → Green → Refactor** (see `.continue/rules/tdd-workflow.md`):

1. **RED** — write the failing test(s) first in `tests/js/*.test.mjs` or
   `tests/python/test_*.py`; run the suite and confirm they fail for the right
   reason.
2. **GREEN** — write the minimum code to pass without breaking existing tests.
3. **REFACTOR** — clean up under green; re-run the suite.

Bug fixes start with a **regression test** that fails before the fix. DOM-only
wiring and pure copy/CSS edits are relaxed (verified by syntax gates + manual/in
browser), but any real logic should be pushed into a tested pure helper.

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

## 2. Test stack (no new RUNTIME deps)

| Layer | Tool | Rationale |
|-------|------|-----------|
| **Python backend** (`server.py`) | **`unittest`** (stdlib) — unit **and** HTTP integration tests | No install; integration tests boot the real `ThreadingHTTPServer` on an ephemeral port and hit routes with `urllib`. |
| **JS frontend** (`app.js`) | **`node --test`** (Node 18+ built-in test runner) | No npm install, no framework; tests pure functions. |
| **Coverage (dev-only)** | **`coverage.py`** (Python) + Node's built-in **`--experimental-test-coverage`** (Node ≥ 22) | Measures + gates coverage. Installed only in the dev venv / used via Node — **never** shipped in the app. |
| **Syntax gates** | `node --check`, `python3 -m py_compile` | Already part of the workflow; cheap and fast. |

### Coverage gates (enforced)

- **Python:** `server.py` ≥ **90%** lines (gate in `.coveragerc` `fail_under`;
  bootstrap glue like `run()`/`install_dependencies()`/`__main__` and a couple of
  defensive `except` branches are excluded — see `.coveragerc`).
- **JS:** **branch** coverage of the *exported* helpers ≥ **70%** (gate in
  `tests/js-coverage.mjs`). Whole-file line-% reads low on purpose because browser
  DOM/event wiring isn't unit-tested — judge the exported helpers, not the file.
- Run locally with **`./run-tests.sh --coverage`**; CI enforces both on every push.
- **Ratchet thresholds up** over time; never lower a gate to make a change pass —
  add tests instead.

### Why not pytest / jest / vitest?
They're excellent, but each adds dependencies/build tooling that conflicts with the
project's "no build step, stdlib-only" philosophy. (Dev-only tools that ship no
runtime dependency, like `coverage.py`, are fine.) We can revisit if the suite
outgrows the stdlib runners.

### What to test (layers, high → moderate value)

**Pure functions (JS `app.js`)** — `renderMarkdown` (XSS safety), `extractJson`,
`formatUsage`, `getExcludedParams`/`MODEL_PARAM_EXCLUSIONS`, `buildResponseFormat`,
`enforceStrictSchema`, `safeTrim`, `chunkText`, `scoreChunkByKeywords`,
`normalizeAssistantText` (exposed via the Node-only `module.exports` guard).

**Pure functions / helpers (Python `server.py`)** — `get_memory_dir` (traversal
guard), `_slugify`, `_resolve_memory_file`, `add_log` (rotation), `load_config`.

**HTTP integration (Python `server.py`)** — boot the real server and exercise:
`/config` (redaction + `has_*` flags), the `/memory/*` lifecycle (save/list/read/
search, tag handling, size limits, traversal 404), `/sessions` &amp; `/chunk-cache`
round-trips + delete, `/chat-history` + `/new-chat-session` archiving, `/logs` +
`/logs/clear`, routing 404s, malformed-body 400s, and the `/api/*` proxy +
`/context7` (key injection, client-auth passthrough, SSE streaming relay, and
upstream-error / unreachable-upstream paths via a fake stdlib upstream server).

**Browser DOM wiring** — verified by the `node --check` syntax gate + manual/in
browser testing; we deliberately avoid a jsdom/headless-browser dependency.

> **Testability note:** keep helpers pure and module-level so they're importable.
> In `app.js`, the Node-only `module.exports` guard at the bottom exposes helpers
> to the test runner with no browser effect.

### Layout & conventions

```
tests/
├── python/
│   ├── test_server.py            # unit tests for pure helpers
│   ├── test_server_http.py       # HTTP integration: config, memory, sessions, cache, limits
│   ├── test_server_branches.py   # HTTP integration: branches, malformed bodies, logs
│   └── test_server_proxy.py      # HTTP integration: /api proxy + /context7 (fake upstream)
├── js/
│   └── app.test.mjs              # node:test + node:assert; run with `node --test`
└── js-coverage.mjs               # dev-only JS coverage gate (Node built-in coverage)
```
- **Naming:** `test_*.py` (Python), `*.test.mjs` (JS).
- **Determinism:** no live network/API calls; integration tests use a local fake
  upstream and temp dirs (never the real vault / runtime files).
- **Speed:** the whole suite runs in seconds.

### One-command runner (documented in README/CONTINUE.md)

```bash
./run-tests.sh             # syntax gates + JS + Python (unit + integration)
./run-tests.sh --coverage  # the above + coverage measurement and gates
```

---

## 3. RAIL — the five-role agent pipeline

**RAIL** (Rule-governed Agentic Iteration Loop) is a closed loop that turns a
request into reviewed, tested, documented code — and feeds learnings back in.

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
