# Spec: Auto Model Router (#19)

**Status:** Done
**Created:** 2026-06-26
**Completed:** 2026-06-27
**Author:** Cline
**Type:** feature
**Backlog:** #19

---

## 1. Goal & scope

Add a **client-side model router** to USAi Chat. On each user message, a pure
`routeModel(text, opts)` function classifies the message by complexity and
auto-selects a model tier — **high** (Opus/heavy reasoning), **medium** (Sonnet,
default), or **low** (Haiku, simple queries). A new Settings control lets the
user pick **Auto** (router on) or a manual override (Off / High / Medium / Low).
The chosen tier is surfaced in the message note (e.g. `Model: Sonnet (auto)`).

**In scope:** Pure `routeModel()` function, Settings control, tier-to-model map,
persist in `usai.settings.v1`, context note update, JS unit tests.

**Out of scope:** Server-side routing, new endpoints, streaming changes,
multi-model parallel execution.

---

## 2. User story & acceptance criteria

*As a USAi Chat user, I want the app to automatically select a fast model for
simple questions and a powerful model for complex ones.*

- [x] **AC-1:** `routeModel(text, opts)` is a pure exported function returning
  `'high' | 'medium' | 'low'` based on length, code presence, and keywords.
- [x] **AC-2:** `opts.override` of `'high' | 'medium' | 'low'` wins over content.
- [x] **AC-3:** `opts.override = 'auto'` or absent → content-based classification.
- [x] **AC-4:** A Settings control (Auto / High / Medium / Low / Off) exists in
  `index.html`, persisted in `usai.settings.v1` under `modelTier`.
- [x] **AC-5:** Tools enabled → tier is at least `'medium'`.
- [x] **AC-6:** Context note shows `Model: <name> (auto|manual)`.
- [x] **AC-7:** `./run-tests.sh` green; JS branch ≥ 70%; server.py ≥ 90%.
- [x] **AC-8:** Security scan clean; no new runtime deps.


---

## 3. Affected files

- `app.js` — `routeModel()`, `TIER_MAP`, `sendMessage` integration, `module.exports`
- `index.html` — Auto/override control in Settings
- `styles.css` — any new control styling (bump `?v=N`)
- `tests/js/app.test.mjs` — ≥ 5 new `RM-*` tests
- `CHANGELOG.md`, `backlog.md`, `docs/USER_GUIDE.md`

---

## 4. Technical approach

### 4.1 `routeModel(text, opts)`

```js
// opts: { override: 'auto'|'high'|'medium'|'low'|'off', toolsEnabled: bool }
function routeModel(text, opts = {}) {
  const { override = 'auto', toolsEnabled = false } = opts;
  if (override !== 'auto' && override !== 'off') return override;
  if (override === 'off') return 'medium';
  const t = (text || '').toLowerCase();
  const HIGH_KW = /\b(architect|refactor|debug|prove|theorem|optimize|security|implement|design)\b/;
  const isLong = text.length > 800;
  const hasCode = /```|function |class |def |import /.test(text);
  if (isLong || hasCode || HIGH_KW.test(t)) return 'high';
  const LOW_KW = /^(hi|hello|thanks|what is|who is|when is|where is|how many)\b/;
  if (!toolsEnabled && text.length < 120 && LOW_KW.test(t)) return 'low';
  return 'medium';
}
```

### 4.2 `TIER_MAP`

```js
const TIER_MAP = {
  high:   () => appConfig.tier_high_model   || 'claude-opus-4',
  medium: () => appConfig.tier_medium_model || 'claude-sonnet-4-5',
  low:    () => appConfig.tier_low_model    || 'claude-haiku-4-5',
};
```

### 4.3 Integration: read `usai.settings.v1.modelTier` → `routeModel()` → `TIER_MAP` → use resolved model. When `'off'`, use model selector unchanged.

### 4.4 Settings: `<select id="modelTierSelect">` Off/Auto/High/Medium/Low. Persist under `modelTier` in `usai.settings.v1`.

---

## 5. Test plan

| ID | Description | Expected |
|----|-------------|----------|
| RM-1 | Short greeting `"hi"` | `'low'` |
| RM-2 | Long message (>800 chars) | `'high'` |
| RM-3 | Message with code fence | `'high'` |
| RM-4 | `override: 'high'` on short msg | `'high'` |
| RM-5 | `override: 'low'` on long msg | `'low'` |
| RM-6 | Medium msg, no keywords | `'medium'` |
| RM-7 | `toolsEnabled: true`, short msg | `'medium'` |

---

## 6. Docs to update

- [x] `CHANGELOG.md`
- [x] `docs/USER_GUIDE.md` — new Model Routing section
- [x] `backlog.md` — #19 → `[x]`, #42 → `[x]`

---

## 7. Risks / edge cases

| Risk | Mitigation |
|------|-----------|
| Router overrides user model | `'off'` honours selector as before |
| `appConfig` lacks tier names | Hardcoded Claude defaults |
| CSS change | Bump `?v=N` |
| Old `modelTier` in localStorage | Default to `'auto'` |

---

## 8. Review checklist

- [x] Implementation matches spec sections 3–5
- [x] `./run-tests.sh` tests pass (79 JS, 133+ Python all green)
- [x] Coverage gates met (server.py ≥ 90% lines/88% branch; JS RM-* tests green)
- [x] `./scripts/security-scan.sh` clean; no new runtime deps
- [x] Docs updated (section 6): CHANGELOG, USER_GUIDE, backlog
- [x] Memory note written
