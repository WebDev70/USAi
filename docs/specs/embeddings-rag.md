# Spec: Real Embeddings for File RAG (#7)

**Status:** Ready
**Type:** feature
**Created:** 2026-06-25
**Updated:** 2026-06-26
**Author:** Cline
**Prior context:** #16 Phase 3 (2026-06-26) shipped `POST /embeddings` proxy in `server.py`, `cosineSimilarity()` and `embedTexts()` helpers in `app.js`, and `has_embeddings` in `/config`. All shared plumbing for this item is already in production — this spec wires it into the file-chunk RAG path.

---

## 1. Goal & scope

### Goal
Replace the in-browser keyword scorer (`scoreChunkByKeywords`) with **semantic
embeddings + cosine similarity** for file-chunk retrieval. When `EMBED_MODEL` is
configured, uploaded file chunks receive real embedding vectors; each user query
is also embedded at query-time, and retrieval ranks chunks by cosine similarity
rather than keyword overlap. Searching "automobile" should surface a chunk that
says "car"; "annual revenue" should surface "yearly income".

The shared infrastructure — `POST /embeddings` endpoint, `cosineSimilarity()`,
`embedTexts()`, and `has_embeddings` flag — was already delivered by #16 Phase 3
and requires no server-side changes.

### Out of scope
- #16 Phase 3 embeddings-based *memory* search (already done).
- Reranking, cross-encoder, or hybrid BM25+vector fusion.
- Server-side vector store (Chroma, Pinecone, etc.).
- Dimension reduction or quantisation.
- Automatic re-embed when `EMBED_MODEL` changes mid-session (handled by per-chunk `embedModel` field mismatch check on restore).

---

## 2. User story & acceptance criteria

*As a USAi user uploading files, I want retrieval to match on meaning (not just
shared words) so that relevant excerpts surface even when my wording differs from
the document.*

- [ ] **AC-1** — With `EMBED_MODEL` set and the **Semantic search** toggle ON, uploaded
  text/PDF/DOCX chunks receive real embedding vectors (batched call to `POST /embeddings`
  via the existing `embedTexts()` helper); `getRelevantChunks` ranks by cosine similarity.
- [ ] **AC-2** — With `EMBED_MODEL` unset **or** Semantic search toggle OFF **or** an
  embeddings API error → retrieval silently falls back to `scoreChunkByKeywords`; no
  error is surfaced to the user.
- [ ] **AC-3** — `/config` already returns `has_embeddings: true/false` (no change needed);
  the **Semantic search** toggle is only shown when `appConfig.has_embeddings` is true.
- [ ] **AC-4** — Vectors are persisted in `saveChunkCache`/`restoreFromCache` so reopening
  a session with the same files does not trigger a re-embed call. Each chunk stores an
  `embedModel` field; on restore, if `c.embedModel !== appConfig.embed_model`, chunks are
  re-embedded.
- [ ] **AC-5** — `getRelevantChunks` is made `async` and exported; the cosine path and
  keyword fallback path are each covered by a `node --test` test.
- [ ] **AC-6** — Query-embed failure (network/API error) → keyword fallback with no
  uncaught throw.
- [ ] **AC-7** — All callers of `getRelevantChunks` are updated to `await` it.
- [ ] **AC-8** — `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%).
- [ ] **AC-9** — `./scripts/security-scan.sh` clean; no new runtime dependencies.

---

## 3. Affected files

| File | Change |
|------|--------|
| `app.js` | Make `getRelevantChunks` async + embedding-aware; embed chunks on upload (batched, ≤96/batch); `semanticSearchEnabled` boolean gated on `appConfig.has_embeddings`; `saveChunkCache`/`restoreFromCache` carry `embedding` + `embedModel` per chunk; `prepareContextMessages` and `search_file` tool `run()` `await` the updated function; Semantic search toggle wired; export `getRelevantChunks` for tests. |
| `index.html` | Add Semantic search toggle (`<input id="semanticSearch">`) in settings panel, hidden when `!appConfig.has_embeddings`; bump `styles.css?v=N`. |
| `styles.css` | No change expected; version bumped only if `index.html` requires it. |
| `server.py` | No change — `POST /embeddings`, `has_embeddings`, `embed_model` already shipped. |
| `.env.example` | Add `EMBED_MODEL=` and `EMBED_INPUT_TYPE=search_document` with comments (if not already present). |
| `tests/js/app.test.mjs` | New tests: `getRelevantChunks` cosine path; keyword fallback when no embeddings; query-embed failure → fallback; toggle-off → keyword path. |
| `tests/python/test_server.py` | No new Python tests needed — `POST /embeddings` + `has_embeddings` already covered by #16 Ph3 tests. |
| `CHANGELOG.md` | Add entry under `[Unreleased]`. |
| `docs/USER_GUIDE.md` | Add "Semantic file search" section. |
| `README.md` | Add `EMBED_MODEL` / `EMBED_INPUT_TYPE` to the configuration table (if not already present). |
| `backlog.md` | Mark #7 `[~]` In Progress → `[x]` Done when complete. |

---

## 4. Technical approach

### Role 2 — Architect sign-off

**Key insight:** `cosineSimilarity()`, `embedTexts()`, and `POST /embeddings` already exist
in `app.js` / `server.py` (shipped with #16 Ph3). This item wires them into the file-RAG
path. No new endpoint and no new server-side code required.

#### 4.1 New `app.js` variable + toggle

```js
// Semantic file search — enabled when has_embeddings && toggle on
let semanticSearchEnabled = false;
```

The Semantic search checkbox (`#semanticSearch`) is shown only when `appConfig.has_embeddings`
is true, and its state is persisted under `usai.settings.v1.semanticSearch`.

#### 4.2 Embed on upload (`handleFileUpload`)

After chunking, if embeddings are available:

```js
if (appConfig.has_embeddings && semanticSearchEnabled) {
  try {
    const BATCH = 96;
    const allVecs = [];
    for (let i = 0; i < texts.length; i += BATCH) {
      const batch = await embedTexts(texts.slice(i, i + BATCH), 'search_document');
      allVecs.push(...batch);
    }
    allVecs.forEach((v, i) => {
      fileChunks[offset + i].embedding = v;
      fileChunks[offset + i].embedModel = appConfig.embed_model;
    });
  } catch (err) {
    addLog('warn', 'Embeddings failed on upload; falling back to keyword search');
  }
}
```

#### 4.3 Make `getRelevantChunks` async and embedding-aware

```js
async function getRelevantChunks(query, topK = 5) {
  if (!fileChunks.length) return [];
  const hasVectors = fileChunks.some(c => c.embedding);
  if (hasVectors && semanticSearchEnabled && appConfig.has_embeddings) {
    try {
      const queryVec = (await embedTexts([query], 'search_query'))[0];
      if (queryVec) {
        const scored = fileChunks.map(c => ({
          ...c,
          score: cosineSimilarity(c.embedding, queryVec),
        }));
        scored.sort((a, b) => b.score - a.score);
        return scored.slice(0, topK).map(({ fileName, text, score }) => ({ fileName, text, score }));
      }
    } catch (_) {
      // fall through to keyword
    }
  }
  // keyword fallback
  const scored = fileChunks.map(c => ({ ...c, score: scoreChunkByKeywords(c.text, query) }));
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK).map(({ fileName, text, score }) => ({ fileName, text, score }));
}
```

`prepareContextMessages` and the `search_file` tool `run()` function must `await getRelevantChunks(...)`.

#### 4.4 Cache persistence

`saveChunkCache` payload per chunk gains `embedding` (float array or null) and `embedModel` (string or null) fields.
`restoreFromCache` checks `c.embedModel === appConfig.embed_model` and re-embeds if mismatch.

**Conventions applied:**
- [x] No new runtime dependency added
- [x] New endpoint follows `_handler` + `routes` pattern (N/A — no new endpoint)
- [x] New tool follows `TOOL_REGISTRY` + gate pattern (N/A — no new tool)
- [x] `/config` exposes no secrets (already enforced; `has_embeddings` already present)
- [x] Path traversal rejected on filesystem access (N/A)
- [x] CSS bump applied (`styles.css?v=N` bumped in `index.html`)
- [x] SSRF guard — `/embeddings` already uses `is_safe_upstream_url()` (shipped in #16 Ph3)

---

## 5. Test plan (Role 4 — Tester, written BEFORE implementation)

| # | Test description | File | Type |
|---|-----------------|------|------|
| JS-1 | `getRelevantChunks` uses cosine path when chunks have embeddings and toggle is on | `tests/js/app.test.mjs` | unit |
| JS-2 | `getRelevantChunks` falls back to keyword when no chunk has an embedding | `tests/js/app.test.mjs` | unit |
| JS-3 | `getRelevantChunks` falls back to keyword when `semanticSearchEnabled = false` | `tests/js/app.test.mjs` | unit |
| JS-4 | `getRelevantChunks` falls back to keyword when `embedTexts` rejects (no uncaught throw) | `tests/js/app.test.mjs` | unit |
| JS-5 | Results are sorted descending by cosine score when embeddings path used | `tests/js/app.test.mjs` | unit |

**TDD order:** write all JS-1…JS-5 first (Red) → implement → Green → refactor.

**Note:** `cosineSimilarity` unit tests (orthogonal/identical/opposite/zero) are already
present in `tests/js/app.test.mjs` from #16 Ph3 — no duplication needed.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — add "Semantic file search (embeddings)" section
- [ ] `README.md` — add `EMBED_MODEL` / `EMBED_INPUT_TYPE` to configuration table (if not already present)
- [ ] `backlog.md` — mark #7 done; transition `[~]` → `[x]`
- [ ] `AGENTS.md` / `CONTINUE.md` — no changes needed

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| Upload latency — embedding 100+ chunks adds one or more round-trips | Batched ≤96 per call; progress shown via `addLog`; embedding is async and does not block UI feedback |
| Batch size > model limit | Cap at 96 texts/request; loop until all chunks are embedded |
| Dimension mismatch on restore (model changed) | Store `embedModel` per chunk; re-embed on mismatch on next upload/restore |
| `getRelevantChunks` is now async — callers must await | Only two call sites: `prepareContextMessages` (already in async context) and `search_file` tool `run()` (already async); straightforward to update |
| Query embed latency per message | Single text, one API call, typically < 100ms; acceptable |
| `cosineSimilarity` receives a null embedding (chunk failed to embed) | `cosineSimilarity` already returns 0 for null inputs (#16 Ph3 implementation) — will sort to bottom |
| Toggle hidden when `has_embeddings` is false | Gate handled at `appConfig.has_embeddings` check; no raw API key exposure |

---

## 8. Review checklist (filled by `/review`)

- [ ] Implementation matches spec §3–§5 exactly
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §6
- [ ] Acceptance criteria AC-1…AC-9 all verified
- [ ] `getRelevantChunks` exported for test import
- [ ] Toggle hidden when `!appConfig.has_embeddings`
- [ ] Fallback path exercised by JS-2, JS-3, JS-4
- [ ] Memory note written to `Cline/memories/`
