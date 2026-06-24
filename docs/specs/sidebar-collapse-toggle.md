# Spec: Sidebar Collapse Toggle — Discoverability & Persistence

**Status:** Ready
**Created:** 2026-06-23
**Author:** Cline / user
**Prior context:** No prior context found in Obsidian vault memories on this topic.

---

## 1. Goal & scope

### Goal
The left-panel sidebar already has a functional ☰ collapse/expand button in the
chat header, but users don't notice it because the tooltip doesn't hint at the
action, and the collapsed state is forgotten on every page reload. We will make
the toggle more discoverable with a dynamic tooltip / `aria-label` that says
"Collapse sidebar" or "Expand sidebar", and we will persist the user's last
choice to `localStorage` so the sidebar is restored to its previous state on
reload without a visible flash.

### Out of scope
- Replacing the ☰ icon with a chevron (may be done later; spec note only).
- Adding a second collapse button inside the sidebar panel itself.
- Any server-side changes.

---

## 2. User story & acceptance criteria

As a user I want the sidebar collapse button to clearly tell me what it does
and remember my preference so that I don't have to re-collapse it on every visit.

- [ ] AC-1: Clicking the ☰ button collapses the sidebar (existing behaviour preserved).
- [ ] AC-2: Clicking it again expands the sidebar (existing behaviour preserved).
- [ ] AC-3: The button's `title` attribute reads **"Collapse sidebar"** when expanded and **"Expand sidebar"** when collapsed.
- [ ] AC-4: The button's `aria-label` matches the `title` (same dynamic value).
- [ ] AC-5: The collapsed/expanded state is saved to `localStorage` key `sidebarCollapsed` (`"1"` / `"0"`).
- [ ] AC-6: On page load, the sidebar is restored to its previous state **without a visible flash** (applied before first paint).
- [ ] AC-7: No new runtime dependencies are introduced.

---

## 3. Affected files

| File | Change |
|------|--------|
| `app.js` | Refactor sidebar toggle handler into `applySidebarCollapsed(collapsed)` helper; persist to `localStorage`; restore state on `DOMContentLoaded` |
| `index.html` | Update `title` attribute on `#sidebarToggle` to initial "Collapse sidebar"; bump `styles.css?v=21` **only if CSS changes** |
| `styles.css` | No changes expected (all collapse CSS already exists) |
| `tests/js/app.test.mjs` | Add tests: helper updates DOM correctly; toggle saves to localStorage; DOMContentLoaded restores collapsed state |
| `CHANGELOG.md` | Add entry under `[Unreleased]` |
| `docs/USER_GUIDE.md` | One sentence noting the toggle and persistence |
| `backlog.md` | Mark relevant item done if present |

---

## 4. Technical approach

### Role 2 — Architect sign-off

**`app.js`** — three changes:

1. **Extract helper** `applySidebarCollapsed(collapsed)`:
   ```js
   function applySidebarCollapsed(collapsed) {
     document.querySelector('.app-container')?.classList.toggle('sidebar-collapsed', collapsed);
     const btn = document.getElementById('sidebarToggle');
     if (!btn) return;
     const label = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
     btn.setAttribute('aria-expanded', String(!collapsed));
     btn.setAttribute('aria-label', label);
     btn.setAttribute('title', label);
   }
   ```

2. **Click handler** (replaces current handler at ~line 2562):
   ```js
   document.getElementById('sidebarToggle')?.addEventListener('click', () => {
     const willCollapse = !document.querySelector('.app-container')
       ?.classList.contains('sidebar-collapsed');
     applySidebarCollapsed(willCollapse);
     localStorage.setItem('sidebarCollapsed', willCollapse ? '1' : '0');
   });
   ```

3. **Restore on load** — at the top of the `DOMContentLoaded` block (before any
   theme code), so the sidebar class is set before the browser paints:
   ```js
   const _sc = localStorage.getItem('sidebarCollapsed');
   if (_sc === '1') applySidebarCollapsed(true);
   else applySidebarCollapsed(false); // sets initial aria-label / title
   ```

**`index.html`** — change `title="Toggle sidebar"` on `#sidebarToggle` to
`title="Collapse sidebar"` (the JS will keep it correct thereafter). No CSS
changes → no `?v=` bump needed.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A) — N/A
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A) — N/A
- [x] `/config` exposes no secrets (or N/A) — N/A
- [x] Path traversal rejected on filesystem access (or N/A) — N/A
- [x] CSS bump applied (or N/A) — N/A (no CSS changes)

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | `applySidebarCollapsed(true)` adds `.sidebar-collapsed`, sets `aria-expanded="false"`, `aria-label="Expand sidebar"` | `tests/js/app.test.mjs` | unit |
| T-2 | `applySidebarCollapsed(false)` removes `.sidebar-collapsed`, sets `aria-expanded="true"`, `aria-label="Collapse sidebar"` | `tests/js/app.test.mjs` | unit |
| T-3 | Clicking toggle saves `"1"` to `localStorage.sidebarCollapsed` when collapsing | `tests/js/app.test.mjs` | unit |
| T-4 | Clicking toggle saves `"0"` to `localStorage.sidebarCollapsed` when expanding | `tests/js/app.test.mjs` | unit |
| T-5 | On init with `localStorage.sidebarCollapsed = '1'`, sidebar starts collapsed | `tests/js/app.test.mjs` | unit |
| T-6 | On init with no localStorage value, sidebar starts expanded with correct labels | `tests/js/app.test.mjs` | unit |

**TDD order:** write these tests first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — note sidebar toggle + persistence
- [ ] `README.md` — no changes needed
- [ ] `backlog.md` — mark relevant item done / add if missing
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention changes

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Flash of collapsed sidebar on load | Apply `applySidebarCollapsed` synchronously inside `DOMContentLoaded` before any await; CSS transition is 0.18s but class is set before paint |
| `#sidebarToggle` not in DOM during tests | Helper guards with `?` optional chaining; tests provide a minimal DOM stub |
| Existing `aria-expanded` value conflicts | `applySidebarCollapsed` is the single source of truth — replaces the old inline `setAttribute` call |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-7 all verified
- [ ] Memory note written to `Cline/memories/`
