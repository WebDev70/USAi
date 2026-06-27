# Spec: Embeddings-Based Memory Search (#16 Phase 3)

**Status:** Done
**Type:** feature
**Created:** 2026-06-26
**Author:** Cline
**Prior context:** #7 (Real embeddings for RAG) was recorded as Done in backlog but the code was never committed; #16 Ph3 originally depended on #7 helpers. This spec is self-contained (Option C): it ships its own `cosineSimilarity`, `embedTexts`, and `POST /embeddings` proxy, independent of the file-RAG work that will come later in #7.

---

## 1. Goal & scope

### Goal
Upgrade the Obsidian memory recall endpoints and their two call sites so that memory
search uses **semantic cosine-similarity re-ranking** when `EMBED_MODEL` is configured,
with graceful fallback to the existing keyword scorer when it is not.  All embedding
plumbing (proxy endpoint, helpers) is self-contained in this spec — no other item
needs to ship first.

### Out of scope
- File-chunk RAG embeddings (#7) — that item will reuse the `/embeddings` endpoint
  and `cosineSimilarity`/`embedTexts` helpers added here.
- A new UI toggle — the existing Semantic search toggle
  (`#semanticSearch` → `appConfig.has_embeddings` gate) is reused once `EMBED_MODEL`
  is set; if the toggle does not exist in the DOM the feature still degrades gracefully
  via the `appConfig.has_embeddings` boolean alone.
- Storing note-level embeddings on disk.
- Any changes to `/memory/save`, `/memory/list`, `/memory/read`, or `save_memory` tool.

---

## 2. User story & acceptance criteria

**As a** USAi user with `EMBED_MODEL` configured, **I want** Obsidian memory
auto-recall and the `search_memory` tool to re-rank results by semantic similarity
so that a search for "vehicle" surfaces a note about "car", and "annual revenue"
surfaces one about "yearly income".

- [x] AC-1: `load_config()` reads `EMBED_MODEL` and `EMBED_INPUT_TYPE` from `.env`;
  `/config` response includes `"has_embeddings": true` when `EMBED_MODEL` + `BASE_URL`
  are both set, `false` otherwise.
- [x] AC-2: `POST /embeddings` proxy endpoint exists; it validates `EMBED_MODEL` is set
  (else 400), applies the SSRF guard on `BASE_URL` (else 502), injects the API key
  server-side, and forwards to `<base_url>/v1/embeddings`.
- [x] AC-3: `/memory/search` response always includes `"embed_available": bool(CONFIG.get('embed_model'))`.
- [x] AC-4: `cosineSimilarity(a, b)` pure helper in `app.js` returns dot(a,b)/(|a|·|b|),
  0 for zero-length vectors; no NaN/throw.
- [x] AC-5: `embedTexts(texts, fetchFn)` async helper POSTs to `/embeddings`; throws
  on error (caller catches and falls back).
- [x] AC-6: `embedMemorySearch(query, k, fetchFn)` exported helper: fetches keyword results from
  `/memory/search`, and — when `appConfig.has_embeddings` is true — calls `embedTexts`
  to embed query + snippets and re-ranks by cosine similarity. Falls back silently on
  any error or when `has_embeddings` is false.
- [x] AC-7: Both `prepareContextMessages` auto-recall and `search_memory` tool `run()`
  call `embedMemorySearch` instead of the bare `fetch('/memory/search?…')`.
- [x] AC-8: `embedMemorySearch` ≥ 3 unit tests in `tests/js/app.test.mjs`
  (semantic path, fallback on embedTexts error, fallback when has_embeddings false). **MS-1, MS-2, MS-3 all pass ✅**
- [x] AC-9: Python test in `tests/python/test_server_branches.py` verifies
  `/memory/search` response always includes `embed_available` field. **MS-4 ✅**
- [x] AC-10: `./run-tests.sh --coverage` passes; coverage gates: server.py 93% ✅, JS branch 71% ✅
- [x] AC-11: `./scripts/security-scan.sh` clean; no new runtime deps. ✅

---

## 3. Affected files

| File | Change |
|------|--------|
| `server.py` | `load_config()` + `/config`: add `embed_model`, `embed_input_type`, `has_embeddings`; add `POST /embeddings` handler; `_memory_search`: add `embed_available` to response |
| `app.js` | New `cosineSimilarity(a,b)`, `embedTexts(texts, inputType)`, `embedMemorySearch(query,k)` helpers; update two call sites |
| `tests/js/app.test.mjs` | ≥ 3 new MS-* tests for `embedMemorySearch` |
| `tests/python/test_server_branches.py` | 1 new test: MS-4 `embed_available` always present |
| `CHANGELOG.md` | Add entry under `[Unreleased]` |
| `docs/USER_GUIDE.md` | Note semantic memory search |
| `backlog.md` | Mark #16 Phase 3 done; reset #7 to `[ ]` with a note that `/embeddings` now exists |

---

## 4. Technical approach

### Role 2 — Architect sign-off

**server.py — `load_config()`** add:
```python
'embed_model': os.getenv('EMBED_MODEL', ''),
'embed_input_type': os.getenv('EMBED_INPUT_TYPE', 'search_document'),
```

**server.py — `_get_config()`** add:
```python
'has_embeddings': bool(CONFIG.get('base_url') and CONFIG.get('embed_model')),
```

**server.py — new `_post_embeddings()` handler** (after `_get_context7`):
```python
def _post_embeddings(self):
    """POST /embeddings — proxy to <base_url>/api/v1/embeddings with key injection."""
    if not CONFIG.get('embed_model'):
        self._json_response(400, {'error': 'EMBED_MODEL not configured'})
        return
    base_url = CONFIG.get('base_url', '').rstrip('/')
    if not base_url:
        self._json_response(400, {'error': 'BASE_URL not configured'})
        return
    upstream_url = base_url + '/api/v1/embeddings'
    if not CONFIG.get('_test_allow_loopback') and not is_safe_upstream_url(upstream_url):
        self._json_response(502, {'error': 'upstream URL rejected by SSRF guard'})
        return
    length = int(self.headers.get('Content-Length', 0))
    raw = self.rfile.read(length) if length > 0 else b'{}'
    try:
        body = json.loads(raw)
    except Exception:
        self._json_response(400, {'error': 'invalid JSON'})
        return
    body.setdefault('model', CONFIG['embed_model'])
    body.setdefault('input_type', CONFIG.get('embed_input_type', 'search_document'))
    auth = ''
    if CONFIG.get('api_key'):
        auth = 'Bearer ' + CONFIG['api_key']
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if auth:
        headers['Authorization'] = auth
    req = Request(upstream_url, data=json.dumps(body).encode('utf-8'),
                  headers=headers, method='POST')
    try:
        with urlopen(req) as resp:  # nosec B310 — URL validated by is_safe_upstream_url() above
            result = json.loads(resp.read())
        self._json_response(200, result)
    except HTTPError as e:
        self._json_response(e.code, {'error': f'upstream error {e.code}'})
    except Exception as e:
        self._json_response(502, {'error': str(e)})
```

Wire to `routes` dict:
```python
'POST /embeddings': self._post_embeddings,
```

**server.py — `_memory_search()`** — add `embed_available` to response:
```python
self._json_response(200, {
    'ok': True, 'query': query, 'results': results,
    'embed_available': bool(CONFIG.get('embed_model')),
})
```

**app.js — new pure helper `cosineSimilarity(a, b)`**:
```js
function cosineSimilarity(a, b) {
  if (!a || !b || a.length !== b.length) return 0;
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i]*b[i]; na += a[i]*a[i]; nb += b[i]*b[i]; }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom === 0 ? 0 : dot / denom;
}
```

**app.js — new async helper `embedTexts(texts, inputType)`**:
```js
async function embedTexts(texts, inputType = 'search_document') {
  const resp = await fetch('/embeddings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ input: texts, input_type: inputType }),
  });
  if (!resp.ok) throw new Error(`/embeddings ${resp.status}`);
  const data = await resp.json();
  return (data.data || []).sort((a, b) => a.index - b.index).map(d => d.embedding);
}
```

**app.js — new async helper `embedMemorySearch(query, k = 5)`**:
```js
async function embedMemorySearch(query, k = 5) {
  const resp = await fetch(`/memory/search?q=${encodeURIComponent(query)}&k=${k * 3}`);
  if (!resp.ok) return [];
  const data = await resp.json();
  const results = data?.results ?? [];
  if (!appConfig.has_embeddings || !results.length) return results.slice(0, k);
  try {
    const snippets = results.map(r => r.snippet || r.path);
    const vectors = await embedTexts([query, ...snippets], 'search_query');
    if (!vectors.length) return results.slice(0, k);
    const queryVec = vectors[0];
    const ranked = results.map((r, i) => ({
      ...r, _sim: cosineSimilarity(queryVec, vectors[i + 1] ?? null),
    }));
    ranked.sort((a, b) => b._sim - a._sim);
    return ranked.slice(0, k);
  } catch (_) {
    return results.slice(0, k);
  }
}
```

**app.js — call site 1** (`search_memory` tool, line ~593):
```js
// Before:
const resp = await fetch(`/memory/search?q=${encodeURIComponent(query)}&k=5`);
const data = await resp.json();
const results = (resp.ok && data?.results) ? data.results : [];
// After:
const results = await embedMemorySearch(query, 5);
```

**app.js — call site 2** (`prepareContextMessages` auto-recall, line ~1854):
```js
// Before:
const resp = await fetch(`/memory/search?q=${encodeURIComponent(inputs.content)}&k=5`);
const data = await resp.json();
const results = (resp.ok && data?.results) ? data.results : [];
// After:
const results = await embedMemorySearch(inputs.content, 5);
```

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern — `_post_embeddings` + `'POST /embeddings'`
- [x] No new tool in TOOL_REGISTRY (embedMemorySearch is an internal helper, not user-facing)
- [x] `/config` exposes `has_embeddings` boolean only — no model string in response
- [x] Path traversal N/A
- [x] CSS bump N/A (no UI change)
- [x] SSRF guard applied on `POST /embeddings` via `is_safe_upstream_url()`

---

## 5. Test plan (TDD — write tests FIRST)

| # | Test description | File | Type |
|---|-----------------|------|------|
| MS-1 | `embedMemorySearch semantic path` | `tests/js/app.test.mjs` | unit |
| MS-2 | `embedMemorySearch falls back when embedTexts throws` | `tests/js/app.test.mjs` | unit |
| MS-3 | `embedMemorySearch falls back when has_embeddings false` | `tests/js/app.test.mjs` | unit |
| MS-4 | `/memory/search response always includes embed_available` | `tests/python/test_server_branches.py` | integration |
| MS-5 | `POST /embeddings returns 400 when EMBED_MODEL unset` | `tests/python/test_server_branches.py` | integration |
| MS-6 | `POST /embeddings SSRF guard rejects loopback` | `tests/python/test_server_branches.py` | integration |
| MS-7 | `has_embeddings true when EMBED_MODEL + BASE_URL set` | `tests/python/test_server.py` | unit |
| MS-8 | `has_embeddings false when EMBED_MODEL unset` | `tests/python/test_server.py` | unit |

**TDD order:** write MS-* tests first (Red) → implement (Green) → refactor.

---

## 6. Docs to update

- [x] `CHANGELOG.md` — entry added under `[Unreleased]`
- [x] `docs/USER_GUIDE.md` — "Semantic re-ranking (optional)" section added
- [x] `README.md` — `EMBED_MODEL` + `EMBED_INPUT_TYPE` added to Obsidian `.env` block
- [x] `backlog.md` — #16 Phase 3 sub-item `[x]` done; #7 reset to `[ ]` with `/embeddings` note

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Empty/very-short snippet → noisy cosine | Filter `results` where `snippet.trim().length > 0` before embedding |
| `embedTexts` batching limit | Memory searches are tiny (k ≤ 20 + 1 query = 21 texts max) — no batching needed |
| `has_embeddings` vs DOM toggle | Gate on `appConfig.has_embeddings` boolean only; no DOM reference in helper |
| `/embeddings` request body exceeds upstream limit | Memory snippets are short; no practical risk at k≤20 |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 93%, JS branch ≥ 71%)
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §6
- [x] Acceptance criteria AC-1…AC-11 all verified
- [x] Memory note written to `Cline/memories/2026-06-26-210836-embeddings-memory-search-done.md`
