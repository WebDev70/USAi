# Spec: Reconcile ARCHITECTURE §3 with the live routes (+ doc-drift guard)

**Status:** Done
**Type:** docs
**Created:** 2026-09-20
**Author:** Cline / user
**Prior context:** Sprint-19 governance report ADVISORY-01 (SA-2) filed this as #91; the
#90/#97 reconciliation already removed `POST /import-session` from §3b and fixed
`/logs/files?file=` → `?name=`. Prior audits (Entry 011) showed doc claims drift from
live code unless a control executes the check. Related memory notes:
[[2026-09-19-180404-sprint-19-governance-audit]],
[[2026-09-20-210000-backlog-90-97-done-pile-reconciliation-shipped]].

---

## 1. Goal & scope

### Goal
Make `docs/ARCHITECTURE.md` §3 an accurate mirror of the HTTP routes that
`backend/server.py` actually dispatches, and add an automated guard so the two can
never silently drift again. The §3b endpoint catalog is currently missing several
live routes, its §3a example still uses handler names that do not exist
(`_get_config_handler`, `_get_models_handler`, `_proxy_api` mapped to `/proxy`,
`_put_projects`, `_delete_projects`), and it lists no `GET /context7`,
`POST /embeddings`, `POST /generate-embeddings`, `POST /logs`, `POST /logs/clear`,
`GET /chat-history`, `POST /chat-history`, `POST /new-chat-session`, or the `/api/`
proxy-prefix dispatch. A drift-guard test asserts parity in both directions.

### Out of scope
- No production `server.py` behavior change — this is documentation + a new test only.
- No new endpoints, no renamed endpoints, no removed endpoints.
- Auto-*generating* the markdown table from code (considered, rejected — a read-only
  parity guard is simpler and needs no build step); the guard fails loudly instead.
- Reconciling any doc other than `docs/ARCHITECTURE.md` §3 (§3a example + §3b table).

---

## 2. User story & acceptance criteria

As a contributor reading `ARCHITECTURE.md`, I want the endpoint catalog to list exactly
the routes the server serves, so that I can trust the doc instead of re-reading
`server.py`.

- [x] AC-1: Every path key in the `do_GET`, `do_POST`, `do_PATCH`, `do_PUT`, and
  `do_DELETE` `routes` dicts (plus the prefix dispatches `/api/`, `/projects/<id>`,
  `/sessions/<id>`) appears as a row in ARCHITECTURE §3b.
- [x] AC-2: Every method+path row in ARCHITECTURE §3b maps to a real live route or
  prefix dispatch in `server.py` — no phantom rows remain.
- [x] AC-3: The §3a "simplified" `routes` example uses only handler method names that
  exist in the codebase (verified by grep), or is reduced to real names.
- [x] AC-4: A new deterministic test (`test_arch_endpoint_parity.py`) fails when a route
  is added to `server.py` without a matching §3b row, and fails when a §3b row cites a
  path the server does not dispatch. It passes on the reconciled tree.


---

## 3. Affected files

| File | Change |
|------|--------|
| `docs/ARCHITECTURE.md` | §3a: fix handler names in the example to real ones; §3b: add missing rows (`GET /context7`, `GET /chat-history`, `POST /chat-history`, `POST /new-chat-session`, `POST /logs`, `POST /logs/clear`, `POST /embeddings`, `POST /generate-embeddings`, `DELETE /chunk-cache`, `/api/*` proxy prefix); confirm existing rows still map. |
| `backend/tests/python/test_arch_endpoint_parity.py` | **New** — parses the `routes` dicts out of `server.py` and the method+path rows out of §3b, asserts bidirectional parity. |
| `CHANGELOG.md` | `[Unreleased]` → Changed/Docs entry. |
| `backlog.md` | Flip #91 `[ ]` → `[~]` with spec link (this turn); mark `[x]` at `/loop` close. |
| `Cline/scrum/product-backlog.md` | Mirror #91 Open → In-Progress (vault). |

---

## 4. Technical approach

### Role 2 — Architect sign-off
The guard is a stdlib-only `unittest` test — no new runtime or dev dependency. It reads
`backend/server.py` as text and extracts the string literals inside each `routes = {…}`
block using a narrow regex anchored to the `do_<VERB>` methods, plus the known
prefix-dispatch paths (`/api/`, `/projects/`, `/sessions/`). It reads
`docs/ARCHITECTURE.md`, isolates the "### 3b. Endpoint catalog" table, and parses the
`| METHOD | \`/path\` |` rows. Query-string suffixes (`?id=`, `?name=`, `?projectId=`)
and path params (`<id>`) are normalized to their base path before comparison so
`GET /raw-responses` and `GET /raw-responses?id=` collapse to one route key.

The assertion is **set-based and bidirectional**: `live_routes - documented == ∅` and
`documented - live_routes == ∅`, with a readable diff message naming any offender. This
is the "execute the control, don't read it" lesson from Entry 011 applied to docs.

**Conventions applied:**
- [x] No new runtime dependency added (stdlib `re`/`pathlib`/`unittest`)
- [x] New endpoint follows `_handler` + `routes` pattern — N/A (no new endpoint)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern — N/A
- [x] `/config` exposes no secrets — N/A (unchanged)
- [x] Path traversal rejected on filesystem access — N/A (test reads repo files only)
- [x] CSS bump applied — N/A (no CSS change)

---

## 4b. Shift-left governance findings (Step 2b output)

| Check | Result | Notes |
|-------|--------|-------|
| G-1 AC testability | ✅ Pass | All four ACs are binary/observable; AC-1/2/4 asserted by the parity test, AC-3 by grep. |
| G-2 Scope / value | ✅ Pass | Docs-only + one guard test; no scope creep. Auto-generation explicitly rejected as gold-plating. |
| G-3 Dependency coherence | ✅ Pass | #90/#97 (Done) already did the `?name=` fix and `/import-session` removal; #91 completes the remaining absent/omitted-route audit. No open prerequisite. |
| G-4 Grep-based security specs | N/A | The parity test greps route strings, not secrets — a doc-drift guard, not a security scanner. |

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | Extract live `routes` keys + prefix dispatches from `server.py`; assert each has a §3b row (`live - documented == ∅`). | `backend/tests/python/test_arch_endpoint_parity.py` | unit |
| T-2 | Parse §3b rows; assert each maps to a live route (`documented - live == ∅`). | `backend/tests/python/test_arch_endpoint_parity.py` | unit |
| T-3 | Regression/positive-control: inject a fake route key into the parsed live set (in-test fixture) and assert the parity helper reports it as an offender — proves the guard actually fails on drift rather than passing vacuously (Entry 011). | `backend/tests/python/test_arch_endpoint_parity.py` | unit |

**TDD order:** write T-1…T-3 first (Red — §3b is currently missing rows) → reconcile the
doc (Green) → refactor the parser helper under green.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — `[Unreleased]` Changed/Docs entry
- [x] `docs/USER_GUIDE.md` — N/A (not user-facing)
- [x] `README.md` — N/A
- [x] `docs/ARCHITECTURE.md` — the reconciliation itself (§3a + §3b)
- [x] `backlog.md` — mark #91 done at `/loop` close
- [x] `AGENTS.md` / `CONTINUE.md` — N/A (no convention change)

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Parser is brittle against `routes` dict formatting changes | Anchor the regex to `'/path': self._handler` lines inside each `do_<VERB>` block; T-3 positive control makes a broken parser fail loudly rather than pass vacuously. |
| Query-string / path-param rows over- or under-match | Normalize `?…` and `<id>` to base path before set comparison; document the normalization in the test. |
| §3b splits one route into two descriptive rows (e.g. `/raw-responses?id=`) | Collapse to base path in the comparison set; keep the human-readable rows in the doc. |
| Future new endpoint lands without a doc row | That is the intended failure — the guard blocks until §3b is updated (the recurrence prevention #91 asks for). |
| `/proxy` vs `/api/` mismatch (stale §3a example said `/proxy`) | Live code proxies the `/api/` prefix, not `/proxy`; fix the §3a example and add an `/api/*` catalog row. |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §6
- [x] Acceptance criteria AC-1…AC-4 all verified
- [x] Memory note written to `Cline/memories/`

## Spec changelog

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|

