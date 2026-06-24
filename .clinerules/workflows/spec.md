# Workflow: /spec
# Cline RAIL — Specification Writer

> **Concern: Cline dev harness** — this workflow is part of the *Cline* VS Code
> extension config only. It is NOT the USAi app and NOT the Continue harness.
> See `docs/ORGANIZATION.md`.

**Mode:** PLAN MODE (interview phase) → ACT MODE (write spec file)

**Purpose:** Turn a goal into a reviewed, ready-to-build spec document at
`docs/specs/<feature>.md`. This is **Role 0 (Product Owner) + Role 1 (Code Planner)**
in the RAIL pipeline. The spec becomes the source of truth for `/build` and `/review`.

---

## Step 0 — Recall first (Code Planner)

Before asking a single question, search the Obsidian vault for relevant prior context:

```
Search locations (all three — recall everything relevant):
  <OBSIDIAN_VAULT_PATH>/Cline/memories/
  <OBSIDIAN_VAULT_PATH>/Continue Extension/memories/
  <OBSIDIAN_VAULT_PATH>/USAi/memories/
```

Surface any prior decisions, lessons learned, or related specs that bear on this
feature. Note what was found (or "no prior context found") in the spec's preamble.

---

## Step 1 — Product Owner interview (PLAN MODE)

Ask these questions **one at a time** — wait for each answer before the next:

1. **What is the goal?** — What problem are we solving, and for whom?
2. **What does success look like?** — Name 2–4 concrete, testable acceptance
   criteria. (e.g. "The endpoint returns 200 with JSON", "The test passes",
   "The button is visible in both themes".)
3. **What is explicitly out of scope?** — What are we *not* building right now?
4. **Any constraints?** — Performance, security, backward-compat, design,
   timeline, size (S/M/L/XL)?
5. **Which files do you expect to touch?** — Best guess is fine; the Architect
   role will refine.

Once you have all five answers, declare: "Definition of Ready — confirmed ✓" and
proceed to Step 2.

---

## Step 2 — Architecture validation (Architect role)

Before writing the spec, run a silent mental check against USAi conventions:

| Convention | Check |
|---|---|
| No new runtime deps | New code uses only vanilla JS / Python stdlib + python-dotenv |
| New endpoint? | Needs `_handler` + `routes` entry + input-size validation |
| New tool? | Needs `TOOL_REGISTRY` entry + `getEnabledTools()` gate |
| Secrets | `/config` exposes only `has_*` flags; proxy injects key server-side |
| Filesystem endpoints | Reject path traversal; confine writes to intended folder |
| CSS change? | Bump `styles.css?v=N` in `index.html` |
| SSRF | Upstream calls go through `is_safe_upstream_url` |

Flag any conflicts in the spec's Risks section.

---

## Step 3 — Write the spec file (Code Planner output)

Write `docs/specs/<kebab-case-feature-name>.md` using **exactly** this template.
Set **Status: Ready** once the Definition of Ready is confirmed.

```markdown
# Spec: <Feature Name>

**Status:** Ready
**Created:** <YYYY-MM-DD>
**Author:** Cline / <user>
**Prior context:** <one sentence — what was recalled from Obsidian, or "none">

---

## 1. Goal & scope

### Goal
<What we are building and why — 2–4 sentences.>

### Out of scope
- <item>
- <item>

---

## 2. User story & acceptance criteria

As a <user> I want <goal> so that <value>.

- [ ] AC-1: <testable, observable — e.g. "GET /endpoint returns 200 + JSON body">
- [ ] AC-2: <...>
- [ ] AC-3: <...>

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | <description> |
| `app.js` | <description> |
| `index.html` | <description — or "none"> |
| `styles.css` | <description — or "none"> |
| `tests/python/test_*.py` | <new/updated tests> |
| `tests/js/app.test.mjs` | <new/updated tests — or "none"> |
| `docs/...` | <spec + any doc updates> |

---

## 4. Technical approach

### Role 2 — Architect sign-off
<Describe the design: functions/endpoints/components to add or change.>

**Conventions applied:**
- [ ] No new runtime dependency added
- [ ] New endpoint follows `_handler` + `routes` pattern (or N/A)
- [ ] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A)
- [ ] `/config` exposes no secrets (or N/A)
- [ ] Path traversal rejected on filesystem access (or N/A)
- [ ] CSS bump applied (or N/A)

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | <description> | `tests/python/test_server.py` | unit |
| T-2 | <description> | `tests/python/test_server_http.py` | integration |
| T-3 | <description> | `tests/js/app.test.mjs` | unit |

**TDD order:** write these tests first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — if user-facing feature
- [ ] `README.md` — if setup/config/env var changes
- [ ] `backlog.md` — mark relevant item done / add new items
- [ ] `AGENTS.md` / `CONTINUE.md` — if conventions change

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| <risk> | <mitigation> |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-N all verified
- [ ] Memory note written to `Cline/memories/`
```

---

## Step 4 — Handoff

After writing the spec, announce:

> **Spec written:** `docs/specs/<name>.md`
> **Next step:** Run `/loop` (or `/build` then `/review`) in ACT MODE to implement it.
> The spec is your source of truth — `/build` must not deviate from it.
