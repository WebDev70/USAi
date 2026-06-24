# RAIL Pipeline & Testing Strategy — USAi Chat

> **Harness-agnostic.** This document defines the shared **RAIL** pipeline concept
> and the **TDD-first testing strategy** for USAi Chat. It is reference material for
> *both* agent harnesses (Continue and Cline) and for human contributors.
> Harness-specific implementation details live in:
> - **[`docs/tooling/continue.md`](tooling/continue.md)** — Continue-only reference
> - **[`docs/tooling/cline.md`](tooling/cline.md)** — Cline-only reference
>
> The engineering *why* behind the pipeline lives in **[`docs/principles.md`](principles.md)**.

> ### What we call this — **RAIL** (Rule-governed Agentic Iteration Loop)
> The pipeline's name is **RAIL**. The acronym captures its two defining traits —
> it is **Rule**-governed (every role is expressed as behavioral guidance plus
> pass/fail gates) and **Agentic** (the LLM, not a controller program,
> self-sequences through the roles). "Iteration **Loop**" reflects both the inner
> TDD cycle (Red → Green → Refactor) and the outer self-improvement loop (Continuous
> Improvement feeds new rules/checks/tests back in). The name also evokes
> *guardrails* — exactly what the rules and checks are: they keep an autonomous
> agent on track.
>
> **The name still fits as the pipeline grows.** RAIL describes the *shape* of the
> workflow (rule-governed, agentic, iterating loop), not a fixed headcount of roles.
> It now has **six sequential roles** (a Product Owner bookends the loop) plus
> **cross-cutting concerns** (DevSecOps, Infrastructure as Code, Observability) woven
> through every role. Avoid the stale phrase "five-role pipeline"; say "the RAIL
> roles."

> **Status: ACTIVE.** The TDD workflow + coverage gates are in force. Tracked as
> backlog items **#17** (pipeline), **#25** (TDD + coverage rigor), and **#26**
> (Agile + DevSecOps + IaC hardening).

---

## 0. Test-Driven Development (the default workflow)

We practice **TDD** for any non-trivial change to testable logic. The loop is
**Red → Green → Refactor**:

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

- **Minimal, audited *runtime* surface (the "zero-dependency" rule, correctly
  framed).** USAi Chat is intentionally dependency-light (vanilla JS frontend +
  Python stdlib backend + `python-dotenv`). What we protect is the *shipped*
  surface — **dev/CI tooling that ships nothing into the running app is allowed and
  encouraged** (coverage, gitleaks, bandit, pip-audit, Docker, make). The full
  rationale + the RUNTIME-vs-DEV/CI litmus test live in
  **[`docs/principles.md`](principles.md)** (the canonical reference for this and
  the DevSecOps/IaC/Agile principles below).
- **Test the logic, not the framework.** Focus on pure, deterministic functions
  and the security-critical backend behavior; avoid brittle DOM/network tests.
- **Security & infra are machine-enforced, not just prose (DevSecOps + IaC).**
  Deterministic gates run the same way every time: `./scripts/security-scan.sh`
  (gitleaks/bandit/pip-audit) and the IaC config-drift guard
  (`tests/python/test_env_example_sync.py`), in addition to LLM-judgment checks.
  See `docs/principles.md` §2–3.
- **Value-first, vertically sliced (Agile).** A Product Owner role bookends RAIL
  with a Definition of Ready and an acceptance gate; a single Definition of Done is
  the finish line. See `docs/principles.md` §4.
- **Docs + memory stay in the loop.** Every change keeps docs in sync and the
  Continuous-Improvement role records learnings to Obsidian.

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

### One-command runner

```bash
./run-tests.sh             # syntax gates + JS + Python (unit + integration)
./run-tests.sh --coverage  # the above + coverage measurement and gates
```

---

## 3. RAIL — the role-based agent pipeline

**RAIL** (Rule-governed Agentic Iteration Loop) is a closed loop that turns a
request into reviewed, tested, documented, *valuable* code — and feeds learnings
back in. It is **bookended by a Product Owner** (Agile) and has **cross-cutting
concerns** (DevSecOps, Infrastructure as Code, Observability) woven through every
role rather than bolted on at the end.

```
Product Owner (Definition of Ready)
   → Code Planner → Development SME → Full Test Suite → QA Review
   → Product Owner (acceptance) → Continuous Improvement
        ▲                                                              │
        └────────── new rules/checks/tests, backlog items, learnings ◄─┘

  cross-cutting (apply inside every role): DevSecOps · IaC · Observability
```

### Sequential roles

| # | Role | Responsibility |
|---|------|----------------|
| 0 | **Product Owner** *(features only)* | Gate the **start** with a **Definition of Ready** (user story, testable acceptance criteria, vertical slice, size/priority); gate the **end** with **acceptance** (criteria met). Skip for pure bugfixes/chores/refactors/docs. |
| 1 | **Code Planner** | Produce a structured **plan** (below) before editing. |
| 2 | **Development SME** | Implement the plan idiomatically — vanilla JS / stdlib Python, minimal runtime surface, security-first, bump `styles.css?v=N` on CSS changes. |
| 3 | **Full Test Suite** | Write/maintain tests (TDD: Red → Green → Refactor) and run the suite + coverage gates. |
| 4 | **QA Review** | Automated pass/fail gates (see below). Each harness runs these differently — see the tooling docs. |
| 5 | **Continuous Improvement** | Reflect after each cycle; **propose** new checks/rules/tests + backlog items; **record a learning note** to Obsidian. |

### Cross-cutting concerns (apply *inside* every role, not as a separate step)

| Concern | Enforced by |
|---------|-------------|
| **DevSecOps** — security shifted left & machine-enforced | Deterministic `scripts/security-scan.sh` (gitleaks + bandit + pip-audit), run in CI too. |
| **Infrastructure as Code** — declarative, reproducible env/config | `tests/python/test_env_example_sync.py` config-drift guard; `Dockerfile`/`docker-compose.yml`/`Makefile`. |
| **Observability** — make behavior visible, never log secrets | `add_log` for all server logging; secrets never echoed. |

### Code Planner — required plan template
The Planner outputs a brief plan (skip for trivial edits) that seeds every later role:
- **Goal & scope** (what / why)
- **Affected files** (+ any new files)
- **Approach** (functions/endpoints to add or change; conventions to respect —
  tool-gating in `getEnabledTools`, `/config` redaction, path-traversal guards,
  SSRF guard `is_safe_upstream_url`, `HOST`/`PORT` via `resolve_bind_address`, CSS
  `?v=N` bump)
- **Test plan** (specific cases → which test file, **written first**)
- **Docs to update** (CHANGELOG / USER_GUIDE / README / etc.)
- **Risks / edge cases / out-of-scope**

### QA Review — the checks (pass/fail)
- **`definition-of-ready`** — *(features)* the work item is well-formed and valuable
  before planning (Product Owner, start gate).
- **`test-coverage`** — tests written first; new/changed code has tests; coverage
  gates pass; handler changes have integration tests.
- **`security-review`** — no hardcoded secrets; `/config` exposes no keys; any
  filesystem endpoint validates input and rejects path traversal; upstreams are
  http(s) only; no secrets logged.
- **`dependency-and-supply-chain-review`** — no unjustified runtime dependency; any
  new dep is vetted/pinned; `pip-audit` clean (or an ignore is documented &
  justified).
- **`iac-review`** — env/config stays declarative, reproducible, drift-free; no
  hardcoded host/port/secret; container stays non-root; CI ≡ Makefile/scripts.
- **`code-quality-review`** — matches project conventions; **minimal runtime
  surface** (no new *runtime* dep); CSS changes bump `styles.css?v=N`; comments
  explain *why*; logs via `add_log`.
- **`docs-in-sync`** — the right docs were updated this change.
- **`ui-ux-review`** — *(frontend changes only)* the UI stays accessible (WCAG AA
  contrast, visible focus, semantic/ARIA, reduced-motion), responsive, and
  token-driven, with no new frontend dependency.
- **`acceptance-criteria`** — *(features)* each acceptance criterion is met,
  verified by test/observable behavior (Product Owner, end gate).
- **`definition-of-done`** — the **meta-gate**: asserts *all* of: tests + coverage,
  security scan, docs in sync, acceptance met (features), and a memory note
  recorded.

How each harness *runs* these checks is harness-specific — see
[`docs/tooling/continue.md`](tooling/continue.md) (Continue's `/check` + `cli-check.sh`)
and [`docs/tooling/cline.md`](tooling/cline.md) (Cline's `/review` workflow).

### Quality axis — Front-End Design (UI/UX)
Alongside the sequential *correctness* roles, a **Front-End Design (UI/UX) SME**
keeps `index.html`/`styles.css` modern and user-friendly. It is scoped to frontend
files so it adds no overhead to backend-only changes.

- **Constraints:** "latest innovative design" = modern **vanilla CSS** (fluid
  `clamp()` type, `color-mix()`, logical properties, container queries / `:has()`,
  View Transitions) — **never** a framework, icon pack, or build step. Extend the
  existing CSS-custom-property token system + light/dark themes; don't rewrite them.
- **Accessibility is the core of "user-friendly":** WCAG AA contrast in both themes,
  `:focus-visible`, semantic landmarks + ARIA on icon-only controls,
  `prefers-reduced-motion`, adequate hit targets.
- **Context7 in the loop:** consult Context7 for authoritative guidance — preferred
  reference is **USWDS** (`/uswds/uswds-site`), apt for "USAi"; adapt principles to
  our vanilla CSS (don't add the package).

### Continuous Improvement — autonomy & memory
- **Propose, don't auto-apply.** Suggests new checks/rules/tests and backlog edits
  for human approval.
- **Harvest recurring QA findings → automation.** If a check/review keeps catching
  the same class of issue, propose a new check/rule so it's caught automatically.
- **Record a learning note** to the Obsidian vault each cycle (what shipped, what
  failed QA, what we automated, follow-ups) so the next task's Planner can
  **recall** it.

---

## 4. CI

A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the same §2 commands
on every push / pull request — JS via `node --test` and Python `unittest` on 3.9 +
3.11, plus syntax gates and a deterministic `security` job (gitleaks + bandit +
pip-audit).

A pre-commit git hook running `./run-tests.sh` remains an optional future add for
catching failures before they leave a developer's machine (backlog **#28**).

---

## 5. Rollout history (incremental)

1. **Strategy doc + backlog #17** (done).
2. **Correctness rules + checks** (done — `code-planner`, `development-sme`,
   `testing-standards`, `tdd-workflow`, `continuous-improvement`; checks
   `test-coverage`, `security-review`, `code-quality-review`, `docs-in-sync`,
   `ui-ux-review`).
3. **`tests/` scaffold** + unit **and** HTTP integration tests + coverage gates
   (done, backlog #25).
4. **`AGENTS.md` workflow wiring** + README/CONTINUE.md "Running tests" (done).
5. **Agile + DevSecOps + IaC hardening** (done, backlog #26): `docs/principles.md`;
   rules `product-owner`, `agile-workflow`, `devsecops`, `infrastructure-as-code`,
   `observability`; checks `definition-of-ready`, `acceptance-criteria`,
   `definition-of-done`, `dependency-and-supply-chain-review`, `iac-review`;
   agent modes `product-owner/planner/security/improver`;
   `scripts/security-scan.sh` + `Dockerfile`/`docker-compose.yml`/`Makefile` + the
   `.env.example` drift guard.
6. **CI** GitHub Actions — tests + coverage **and** a deterministic `security` job
   (done).
7. **Three-concern documentation refactor** (done, backlog #30): harness-specific
   narrative split into `docs/tooling/continue.md` and `docs/tooling/cline.md`;
   this doc renamed from `testing-and-agents-strategy.md` to be
   harness-agnostic.

---

## 6. References
- `docs/principles.md` (this repo) — the engineering principles (minimal runtime
  surface, DevSecOps, IaC, Agile) the pipeline enforces.
- `docs/tooling/continue.md` — Continue-only implementation reference.
- `docs/tooling/cline.md` — Cline-only implementation reference.
- `docs/ORGANIZATION.md` — the three-concern map (app / Continue / Cline).
- `AGENTS.md` — shared agent operating rules + memory directive.
- USWDS — U.S. Web Design System (Context7 `/uswds/uswds-site`), the preferred
  accessibility/UX reference for the Front-End Design role.
- Continue Checks — https://docs.continue.dev/checks/quickstart
- Obsidian guide — `Continue Extension/guides/RAIL-Pipeline-Guide.md` (the
  newcomer-friendly deep dive).
