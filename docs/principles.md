# Engineering Principles — USAi Chat

This document states the *why* behind USAi Chat's core constraints, so future
contributors (human and agent) apply them correctly instead of treating slogans as
laws. It is the canonical reference for the dependency, security, and infrastructure
philosophy that the RAIL pipeline (`docs/rail-pipeline.md`) enforces.

---

## 1. Minimal, Audited Runtime Surface (the "zero-dependency" rule, correctly framed)

Older docs phrase this as **"zero runtime dependencies."** That slogan is a useful
default but is easy to misread. The real principle is:

> **Keep the *shipped, runtime* surface minimal and auditable. Dev/CI-time tooling
> that ships *nothing* into the running app is allowed and encouraged.**

### What this protects (and why it's good *here*)
- **Supply-chain security (DevSecOps).** Every runtime dependency is attack surface
  (cf. `event-stream`, `colors.js`, Log4Shell). USAi Chat is a proxy that handles
  an API key, so a tiny, readable surface is a genuine security control.
- **Longevity / no bit-rot.** Vanilla JS + Python stdlib + `python-dotenv` will run
  for years with no `npm install` to break and no transitive-dep churn.
- **Auditability.** A reviewer can read the *entire* runtime codebase — no
  `node_modules` black box. (This matters for the government-adjacent deployment
  target implied by the gateway URL.)
- **Zero build step.** Clone and run; low onboarding friction.

### The crucial distinction: RUNTIME vs. DEV/CI tooling

| Category | Rule | Examples |
|----------|------|----------|
| **Runtime** (ships in / is imported by the running app) | **Forbidden** to add without strong justification. Frontend = plain HTML/CSS/JS. Backend = Python stdlib + `python-dotenv`. | a JS framework, an icon pack, `requests`, `flask`, a CSS bundler |
| **Dev / CI** (runs only on a developer/CI machine, ships nothing to production) | **Allowed and encouraged**, especially for quality & security. | `coverage.py`, Node's built-in coverage, `gitleaks`, `bandit`, `pip-audit`, `osv-scanner`, Docker, `make` |

**Litmus test for a new tool:** *Does it get imported by `app.js`/`server.py`, or
add a `node_modules`/transitive runtime dependency the app needs to run?*
- **Yes →** it's runtime; treat it as forbidden-by-default (justify or find a stdlib
  way).
- **No (only runs in tests/CI/build/deploy) →** it's dev/CI tooling; fine.

### Is "minimal runtime surface" industry best practice?
- **As an absolute "never use libraries" rule: no.** Most software *should* use
  vetted, maintained libraries rather than re-implement crypto/parsing/HTTP.
- **As a deliberate constraint for a small, security-sensitive, long-lived
  proxy/UI like this one: yes** — and it aligns with the DevSecOps practice of
  minimizing the dependency/attack surface. We keep it.

---

## 2. Security is shifted left and *machine-enforced* (DevSecOps)

Reviews by a human or an LLM catch a lot, but top-tier means **deterministic gates**
that fail loudly and the same way every time:

- **Secret scanning** (`gitleaks`) — no secret ever reaches git history.
- **SAST** (`bandit`) — static analysis of `server.py` for insecure patterns.
- **Dependency CVE audit** (`pip-audit`) — even our tiny runtime dep is checked.
- These run in **`scripts/security-scan.sh`**, in **CI**, and via
  **`scripts/cli-check.sh`**, complementing (not replacing) the
  `security-review` / `dependency-and-supply-chain-review` `/check` gates.

All of the above are dev/CI tooling per §1 — they ship nothing into the app.

---

## 3. The environment is Infrastructure as Code (IaC)

Running the app should be **declarative and reproducible**, never a list of manual
steps a human must remember:

- **`Dockerfile` + `docker-compose.yml`** describe the runtime environment
  declaratively; `docker compose up` is the reproducible bootstrap. (Docker is
  dev/deploy tooling per §1 — the *container* still contains only the minimal
  runtime surface.)
- **`Makefile`** provides one-word entry points (`make run`, `make test`,
  `make scan`, `make check`) so the same commands work locally and in CI.
- **Config is code and validated:** `.env.example` is the declarative contract for
  configuration, and a test (`tests/python/test_env_example_sync.py`) fails if it
  drifts from what `load_config()` actually reads. No hidden/undocumented config.

---

## 4. Agile: value first, vertically sliced, with explicit Ready/Done

- A **Product Owner** role guards **Definition of Ready** (a backlog item is
  well-formed, valuable, sized, with acceptance criteria) *before* the Code Planner
  starts, and confirms **acceptance criteria** are met *after* QA.
- Changes are **vertical slices** that deliver user-visible value, not horizontal
  layers.
- **Definition of Done** is a single gate that asserts *all* of: tests + coverage,
  security scan, docs in sync, acceptance criteria met, and a memory note recorded.

See `docs/rail-pipeline.md` for how these map onto the RAIL roles,
rules, and checks.
