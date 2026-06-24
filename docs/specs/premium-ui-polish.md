# Spec: Premium UI Polish

**Status:** Ready
**Type:** css
**Created:** 2026-06-24
**Author:** Cline / user
**Prior context:** Obsidian MCP timed out at task start; no prior design context surfaced.

---

## 1. Goal & scope

### Goal
Elevate the existing USAi chat app dashboard (`index.html` + `styles.css`) to feel
modern, premium, and polished — keeping the green accent (#10a37f) but adding depth,
richer typography (Inter web font), glassy/elevated surfaces, a refined shadow scale,
smoother micro-interactions, and a consistent spacing language. Both light and dark
themes must benefit equally. No markup, behavior, or test changes.

### Out of scope
- New features, pages, or routes
- Changes to `app.js`, `server.py`, or any test file
- A marketing/landing page or brand redesign
- Changing the green accent hue (keep #10a37f family)

---

## 2. User story & acceptance criteria

As a daily user of the USAi chat dashboard, I want the interface to look and feel
premium so that it inspires trust and is a pleasure to use.

- [ ] AC-1: The app renders with Inter as the display font (system fallback intact); heading weights and letter-spacing feel premium.
- [ ] AC-2: Light mode has a refined off-white/subtle surface gradient; dark mode has richer layered depths — both feel elevated, not flat.
- [ ] AC-3: The chat header and composer input have a frosted-glass / elevated look (backdrop-filter blur with solid fallback).
- [ ] AC-4: The send button uses the accent gradient + soft glow on hover; all interactive elements have smooth, premium-feeling transitions.
- [ ] AC-5: Example-prompt chips, session items, and sidebar buttons feel tactile (hover lift/ring, active press).
- [ ] AC-6: `styles.css?v=` version is bumped in `index.html` (v23 → v24).
- [ ] AC-7: `./run-tests.sh` passes cleanly (no logic changes, no test regressions).

---

## 3. Affected files

| File | Change |
|------|--------|
| `styles.css` | Token refresh, Inter import, glassy surfaces, shadow scale, micro-interactions, spacing |
| `index.html` | Add Inter `<link>` in `<head>`; bump `styles.css?v=23` → `?v=24` |
| `docs/specs/premium-ui-polish.md` | This spec |
| `CHANGELOG.md` | Entry under `[Unreleased]` |
| `tests/python/test_*.py` | None |
| `tests/js/app.test.mjs` | None |

---

## 4. Technical approach

### Role 2 — Architect sign-off
CSS-only polish on top of the existing token system. Key changes:

1. **`:root` token refresh** — add `--color-accent-gradient`, `--color-accent-glow`,
   `--color-accent-soft`, `--color-bg-base`, `--color-bg-elevated-glass`; refine
   shadow scale to a 4-stop ambient+key system; add `--font-sans` pointing to Inter.
2. **Inter web font** — `<link rel="preconnect">` + `<link rel="stylesheet">` for
   `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`.
   System stack (`-apple-system, BlinkMacSystemFont …`) stays as fallback in `--font-sans`.
3. **Glassy surfaces** — `backdrop-filter: blur(12px) saturate(1.4)` on `.chat-header`,
   `.input-area` (in-conversation), and `.debug-panel`; `position: sticky` on header.
   Solid fallback via `@supports not (backdrop-filter: blur(1px))`.
4. **Depth / elevation** — refined `--shadow-*` using layered box-shadows (ambient low-opacity + key medium-opacity); apply to `.message-input`, `.empty-chat-icon`, `.example-prompt-chip`, `.new-chat-btn`, `.session-item.active`.
5. **Send button** — `background: var(--color-accent-gradient)`; `box-shadow` glow on hover; scale(0.95) press.
6. **Typography** — `font-family: var(--font-sans)` on `body`; tighten heading `letter-spacing`, set `font-feature-settings: 'cv02','cv03','cv04','cv11'` for Inter optical tuning; increase greeting to `1.75rem` weight 700.
7. **Micro-interactions** — all interactive elements transition at `0.15s cubic-bezier(0.4,0,0.2,1)` (material easing); hover states add `translateY(-1px)` or `translateY(-2px)` lift; active states compress back.
8. **Chip & session refinements** — chips get `border-radius: var(--radius-lg)` and an accent border on hover; active session item gets a left-border accent stripe.

**Conventions applied:**
- [x] No new runtime dependency added (web font is a link, not a JS runtime dep)
- [x] New endpoint follows `_handler` + `routes` pattern (or N/A) — N/A
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (or N/A) — N/A
- [x] `/config` exposes no secrets (or N/A) — N/A
- [x] Path traversal rejected on filesystem access (or N/A) — N/A
- [x] CSS bump applied — `?v=23` → `?v=24`

---

## 5. Test plan (Role 4 — Tester)

CSS-only change — no logic to unit-test. Gate is:

| # | Test description | File | Type |
|---|-----------------|------|------|
| T-1 | `./run-tests.sh` full suite passes (no JS/Python behavior touched) | all | regression |
| T-2 | Visual: light mode — depth, Inter font, glassy header visible | browser | visual |
| T-3 | Visual: dark mode — layered depths, glow, no color blowout | browser | visual |
| T-4 | `node --check app.js` clean | app.js | syntax |
| T-5 | `python3 -m py_compile server.py` clean | server.py | syntax |

**TDD order:** N/A for pure CSS — run gates after implementation.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — no user-facing behavior change, skip
- [ ] `README.md` — no setup/config change, skip
- [ ] `backlog.md` — mark any related item done
- [ ] `AGENTS.md` / `CONTINUE.md` — no convention change, skip

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| `backdrop-filter` unsupported (Firefox < 103, old Safari) | Solid fallback via `@supports not (backdrop-filter: blur(1px))` |
| Inter font slow/offline load | `font-display: swap` in font URL; system stack fallback |
| Dark mode contrast regression on glassy surfaces | Test both themes; ensure contrast ≥ 4.5:1 on text over glass |
| Google Fonts blocked in some networks | System stack renders cleanly without it |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-7 all verified
- [ ] Memory note written to `Cline/memories/`
