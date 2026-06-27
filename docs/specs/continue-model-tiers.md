# Spec: Continue Dev-Workflow Model Tiers (Guided)

**Status:** Done
**Type:** docs
**Created:** 2026-06-26
**Author:** Cline / user
**Prior context:** Backlog notes confirm #18 was flagged "needs AC grooming". Live
gateway query (`GET /api/v1/models` on https://api.gsa.usai.gov) confirmed the three
model IDs. Continue assigns models to fixed built-in roles — tier switching is manual.

---

## 1. Goal & scope

### Goal
Define three guided model tiers for the RAIL roles so each role uses the right level
of reasoning. Switching is **manual** via Continue's model-picker; role rules advise
which tier to select. Deliver: (1) `docs/continue-config.sample.yaml`, (2) a
"Model tiers (guided)" subsection in `docs/rail-pipeline.md` §3, and (3) a one-line
tier hint in each of the three role rules.

### Out of scope
- USAi web-app automatic model router (backlog #19).
- Modifying `~/.continue/config.yaml`.
- Any runtime code change (`server.py`, `app.js`, `index.html`, `styles.css`).
- `autocomplete` or `embed` roles in the sample.

---

## 2. User story & acceptance criteria

As a **developer using Continue** I want a sample config and role-rule hints telling
me which model tier to pick for each RAIL role so I use the right reasoning level.

- [ ] **AC-1:** `docs/continue-config.sample.yaml` exists and is valid YAML.
- [ ] **AC-2:** The sample defines exactly three models (one per tier) using IDs
  confirmed live: `claude_4_8_opus`, `claude_4_6_sonnet`, `claude_4_5_haiku`.
- [ ] **AC-3:** Each model uses `provider: openai`,
  `apiBase: https://api.gsa.usai.gov/api/v1`, `roles: [chat, edit]`, and
  `${{ secrets.USAI_API_KEY }}` — no literal secret in the file.
- [ ] **AC-4:** `docs/rail-pipeline.md` §3 has a new "Model tiers (guided)" subsection
  with a tier→role→model table and a note that switching is manual.
- [ ] **AC-5:** `.continue/rules/code-planner.md` contains a tier hint line.
- [ ] **AC-6:** `.continue/rules/development-sme.md` contains a tier hint line.
- [ ] **AC-7:** `.continue/rules/continuous-improvement.md` contains a tier hint line.
- [ ] **AC-8:** No runtime dependency added; no change to app source files.
- [ ] **AC-9:** `backlog.md` #18 is `[x]` with Done date, outcome, and spec link.
- [ ] **AC-10:** `CHANGELOG.md` has an entry under `[Unreleased]`.

---

## 3. Affected files

| File | Change |
|------|--------|
| `docs/specs/continue-model-tiers.md` | **New** — this spec |
| `docs/continue-config.sample.yaml` | **New** — sample Continue config, three tiers |
| `docs/rail-pipeline.md` | Add "Model tiers (guided)" subsection to §3 |
| `.continue/rules/code-planner.md` | Add one-line tier hint |
| `.continue/rules/development-sme.md` | Add one-line tier hint |
| `.continue/rules/continuous-improvement.md` | Add one-line tier hint |
| `CHANGELOG.md` | Add entry under `[Unreleased]` |
| `backlog.md` | #18: `[~]` → `[x]` with Done date + outcome + spec link |

---

## 4. Technical approach

### Role 2 — Architect sign-off

Docs/DX change only — no production code modified.

**`docs/continue-config.sample.yaml`:** `%YAML 1.1` header + anchors to de-duplicate
`provider`/`apiBase`/`apiKey`. Three `models:` entries with `name`, `provider: openai`,
`model`, `apiBase: https://api.gsa.usai.gov/api/v1`, `apiKey: ${{ secrets.USAI_API_KEY }}`,
`roles: [chat, edit]`, and `defaultCompletionOptions.temperature`. Comments explain
tier intent and direct the user to `GET /api/v1/models` to verify IDs.

**`docs/rail-pipeline.md`:** Insert new subsection after "Sequential roles" table.

**Role-rule hints (appended to end of each file):**
- `code-planner.md`: "**Model tier:** High (Opus) for complex/arch plans and hard QA; Low (Haiku) for trivial/docs plans."
- `development-sme.md`: "**Model tier:** Medium (Sonnet) for implementation and test-writing (default)."
- `continuous-improvement.md`: "**Model tier:** Low (Haiku) for retros/notes; High (Opus) for in-depth post-mortem."

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint / tool / `/config` / CSS — all N/A

---

## 5. Test plan (docs type — coverage gates skipped)

| # | Validation | Method |
|---|-----------|--------|
| V-1 | Sample YAML is valid | `python3 -c "import yaml; yaml.safe_load(open('docs/continue-config.sample.yaml'))"` |
| V-2 | No secret in sample | `./scripts/security-scan.sh` |
| V-3 | Existing suite unaffected | `./run-tests.sh` |

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `backlog.md` — mark #18 done
- [ ] `docs/USER_GUIDE.md` — DX only, skip
- [ ] `README.md` — no setup/config change, skip

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Secret leaked into sample | `${{ secrets.USAI_API_KEY }}` placeholder only; gitleaks confirms |
| Model IDs go stale | Comment in sample: "Verify with `GET /api/v1/models`" |
| Wrong `apiBase` path | `openai` provider appends `/chat/completions`; `.../api/v1` is correct |
| YAML anchors syntax | Include `%YAML 1.1` header per Continue docs example |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py 93% ≥ 90%, JS branch 72.56% ≥ 70%)
- [x] `./scripts/security-scan.sh` clean (bandit + pip-audit ✅; gitleaks skipped locally — runs in CI)
- [x] Docs updated per §6 (CHANGELOG ✅, backlog [x] ✅, scrum mirror ✅)
- [x] Acceptance criteria AC-1…AC-10 all verified
- [x] Memory note written to `Cline/memories/2026-06-26-223000-continue-model-tiers-done.md`
