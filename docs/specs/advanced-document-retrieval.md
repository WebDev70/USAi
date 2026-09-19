# Spec: Advanced Document Retrieval — Structure-Aware Chunking, Hybrid Search & Hierarchical Whole-Document Analysis

**Status:** In Progress (#69 Done · #70/#71 pending)
**Created:** 2026-09-17
**Author:** Cline (backlog #69/#70/#71 — architecture spec)

## 1. Goal & scope

Today, file/project retrieval in USAi Chat is fixed-size (200-line, non-overlapping)
line chunking with either pure keyword scoring or an **all-or-nothing** semantic
gate (`getRelevantChunks` in `frontend/app.js` requires *every* candidate chunk to
carry an `embedding` before it will do cosine scoring at all — one un-embedded
chunk in the merged `fileChunks + projectChunks` set silently disables semantic
ranking for the whole query). There is no structural awareness (headings, code
declarations), no hybrid rank fusion, no neighbor expansion, and no path for
"whole document" questions — large files are always truncated to `topChunksPerQuery`
excerpts even when a user asks to "summarize the whole document."

This spec defines the target architecture for three backlog items that ship
independently, in this order:

- **#69 Retrieval foundations** — structure-aware chunking, per-chunk semantic
  fallback (replacing the all-or-nothing gate), lexical/semantic hybrid rank
  fusion, neighbor expansion, versioned chunk-cache schema + legacy migration.
- **#70 Whole-document analysis** — prompt-budget estimation, full-document
  bypass when it fits, intent routing (focused vs. whole-document questions),
  hierarchical map-reduce for documents that don't fit.
- **#71 Optional reranking** — a bounded second-stage reranker over the fused
  top-N, disabled by default, config-gated.

**In scope (this document):** the full architecture, data model, algorithms,
routing rules, and doc corrections shared by all three items, so `/build` for
each slice has one source of truth and the slices stay compatible with each
other's assumptions.

**Out of scope:**
- Server-side vector store (Chroma, Pinecone, FAISS, etc.) — chunk/embedding
  storage stays in the existing JSON chunk-cache files.
- Cross-encoder models beyond a generic HTTP reranker call — no bundled ML.
- A tokenizer dependency — token/char budget estimation stays heuristic
  (character-count based), per the minimal-runtime-surface convention.
- Backlog **#68** (backfill embeddings for pre-#65 project files) — tracked
  separately; see §1a for the relationship.
- Any change to Obsidian memory search (`embedMemorySearch`) — unaffected.

### 1a. Relationship to backlog #68

#68 (embedding backfill for legacy project files) is **not blocked by, and does
not block,** #69. #69's per-chunk semantic fallback (§4.3) already treats a
missing `embedding` as "score this chunk lexically" rather than "disable
semantic scoring for everyone," so a project with a mix of backfilled and
never-backfilled chunks degrades gracefully today and after #69 ships. However,
**#69 changes the chunk-cache schema** (adds `schemaVersion`, `ordinal`,
`headingPath`, `previousChunkId`/`nextChunkId`, etc. — §3). Any backfill tooling
built for #68 should target the **post-#69 schema**, so the recommended
implementation order is #69 → #68 → #70 → #71. This spec's migration logic
(§4.2) already normalizes legacy caches on load, so #68's backfill can run
against normalized data without a separate migration path.

## 2. User story & acceptance criteria

As a user who uploads documents (per-chat or project-level), I want retrieval to
respect document structure, degrade gracefully when only some chunks are
embedded, combine keyword and semantic signal, and correctly answer both
narrow factual questions and "analyze/summarize the whole document" requests —
so that relevant context isn't lost at arbitrary line boundaries and large
documents don't get silently truncated when the question needs all of them.

- [x] AC-1: A single chunk (per-chat or project) lacking an `embedding` no
      longer disables semantic scoring for the rest of the candidate set —
      each chunk is scored lexically and, if embedded, semantically; results
      are fused (§4.4).
- [x] AC-2: New uploads are split on structural boundaries (Markdown
      headings / blank-line paragraphs / common code declarations where
      cheaply detectable) instead of pure fixed-line windows, while still
      respecting the existing chunk-size **upper bound** setting and the
      50–1000 line UI range.
- [x] AC-3: Legacy chunk-cache JSON (no `schemaVersion`, no structural
      metadata) continues to load and rank correctly — normalized in place
      on read, never dropped or hard-failed.
- [x] AC-4: Lexical and semantic rankings are combined via Reciprocal Rank
      Fusion (RRF) rather than comparing raw incomparable scores; ties break
      deterministically by source order.
- [x] AC-5: Top-ranked seed chunks are expanded with their immediate
      structural neighbors (same file, adjacent `ordinal`), deduplicated, and
      re-ordered by source position before being placed in the prompt.
- [ ] AC-6: *(deferred to #70)* When every uploaded/project document relevant to the current
      turn fits inside a configured character budget (with headroom for the
      rest of the prompt), the assistant receives the **complete** document
      text in source order instead of a retrieval excerpt.
- [ ] AC-7: *(deferred to #70)* Explicit whole-document requests ("summarize this document",
      "review the whole file", "compare all sections") that do **not** fit
      the budget are answered via hierarchical map-reduce (§4.7) over
      structural chunks, not a single-shot truncated context.
- [ ] AC-8: *(deferred to #70)* Ambiguous / narrow queries continue to use hybrid retrieval
      (§4.4–4.5) by default — map-reduce only triggers on a recognized
      whole-document intent, never automatically for a plain factual
      question, so the number of extra model calls stays predictable.
- [ ] AC-9: *(deferred to #71)* An optional reranker (§4.8), when explicitly configured, reorders
      only the bounded fused top-N candidates and falls back to the fused
      order on error/timeout/malformed output; when not configured, behavior
      is identical to AC-4/AC-5 (zero regression for existing users).
- [x] AC-10: `docs/ARCHITECTURE.md` §4d is corrected to describe the current
      fixed-line, non-overlapping chunking accurately *before* this feature
      lands, and updated again once each slice (#69/#70/#71) ships to
      describe the real, then-current behavior — never describes unshipped
      behavior as current.
- [x] AC-11: Existing behaviors are unaffected: global vs. project chunk
      merge, `search_file` tool, cache CRUD endpoints, path-traversal guards,
      and keyword-only operation with no `EMBED_MODEL` configured.

## 3. Chunk-cache schema (target — versioned)

```jsonc
{
  "schemaVersion": 2,
  "chunks": [
    {
      "chunkId": 0,            // stable within a file's cache entry
      "ordinal": 0,            // 0-based source order — drives neighbor expansion
      "fileName": "report.md",
      "text": "...",
      "startLine": 1,
      "endLine": 42,
      "headingPath": ["Introduction", "Background"],  // [] if undetected
      "sectionType": "prose",  // "prose" | "code" | "list" | "table" | "unknown"
      "previousChunkId": null,
      "nextChunkId": 1,
      "embedding": null,       // number[] | null
      "embedModel": null       // string | null — must match current EMBED_MODEL
    }
  ]
}
```

- `schemaVersion` is absent on legacy files → treated as version 1 and
  normalized on read (§4.2): line-based chunks get `ordinal` assigned by
  array position, `headingPath: []`, `sectionType: "unknown"`, and
  `previous/nextChunkId` linked by adjacency.
- `chunkId` remains the stable key `POST /generate-embeddings` already uses
  (`chunkIds: number[]`) — unchanged contract, so #65's endpoint keeps working
  unmodified.
- An `embedding` is only trusted for scoring if `embedModel` matches the
  currently configured `EMBED_MODEL`; a mismatch (e.g. provider/model
  changed) is treated the same as "no embedding" (falls back to lexical for
  that chunk) rather than silently mixing incompatible vector spaces.

## 4. Technical approach

### 4.1 Structure-aware chunking (`chunkText` → `chunkTextStructured`)

Replace the pure `for (i += lineSize)` sliding window in `chunkText()`
(`frontend/app.js:2025`) with a two-pass, dependency-free splitter:

1. **Segment** the raw text into an ordered list of structural blocks using
   only regex/string scanning (no parser library):
   - Markdown ATX headings (`^#{1,6}\s+.*$`) start a new section and push a
     `headingPath` frame (same detection tier as `renderMarkdown`'s existing
     heading regex at `frontend/app.js:64`, reused for detection only).
   - Blank-line-delimited paragraphs are block boundaries within a section.
   - Fenced code blocks (`` ``` ``) are captured whole as `sectionType: "code"`
     and never split mid-fence.
   - Anything else falls back to paragraph/line boundaries with
     `sectionType: "prose"`.
2. **Pack** consecutive small blocks together and split oversized blocks with
   a bounded sliding window (reusing the old line-based algorithm as the
   fallback splitter) so every emitted chunk's line count stays within
   `[minChunkLines, chunkLineSize]` (the existing 50–1000 setting becomes the
   **upper bound**, not the exact size). A configurable small overlap
   (default 0, max ~10% of `chunkLineSize`) may be carried across a forced
   split only — never across a natural structural boundary.
3. Every emitted chunk gets `ordinal`, `startLine`/`endLine`, `headingPath`,
   `sectionType`, and neighbor links assigned in the same pass.
4. **Coverage guarantee:** concatenating all chunks' `[startLine, endLine]`
   spans (minus the bounded overlap) reproduces the original file's line
   range exactly — a test (§5) asserts no lines are silently dropped.

`chunkText()` keeps its old signature/behavior available for tests and
rollback; `chunkTextStructured()` is the new default called from
`handleFileUpload()` and the project-file chunking step in `app.js` (project
files are chunked client-side before `POST /project-files/<id>`, same as
per-chat files — confirmed by reading the upload flow; no backend chunking
logic changes needed).

### 4.2 Legacy cache normalization

Add `normalizeChunkCache(cacheData)` (pure function, unit-testable) called
wherever a chunk-cache JSON file is read into memory: `restoreFromCache()`
and the `GET /chunk-cache` response handler in `app.js`. Normalize
**client-side on load** (one code path — `app.js` already owns all
chunking/ranking logic): legacy entries get `ordinal` from array position,
`headingPath: []`, `sectionType: "unknown"`, and adjacency-linked
`previous/nextChunkId`; the in-memory shape is always schema v2 downstream of
this function. The on-disk file is left as-is until the *next* write
(`saveChunkCache()` / `/generate-embeddings`), which persists forward in the
new schema — no batch migration script, no startup scan, matching the
existing best-effort convention used by #65.

### 4.3 Per-chunk semantic fallback (replaces the all-or-nothing gate)

Replace this block in `getRelevantChunks()` (`frontend/app.js:2118-2120`):

```js
const hasEmbeds = chunks.every(c => Array.isArray(c.embedding) && c.embedding.length > 0);
if (useSemantic && appConfig.has_embeddings && hasEmbeds) { ... }
```

with per-chunk eligibility:

```js
const embedded = chunks.filter(c => Array.isArray(c.embedding) && c.embedding.length > 0
  && c.embedModel === currentEmbedModel);
if (useSemantic && appConfig.has_embeddings && embedded.length > 0) {
  // embed the query once; score `embedded` by cosine; score ALL chunks lexically;
  // fuse (§4.4). Chunks outside `embedded` get no semantic contribution but
  // still rank via their lexical score.
}
```

If the query-embedding call itself fails, fall through to pure lexical
scoring for every chunk (existing behavior, preserved) — there is no query
vector to fuse with in that case.

### 4.4 Hybrid rank fusion (Reciprocal Rank Fusion)

Given a lexical ranking (all chunks, via `scoreChunkByKeywords`) and a
semantic ranking (only `embedded` chunks, via cosine similarity), compute a
fused score per chunk:

```
RRF(chunk) = Σ over each ranking R containing chunk of  1 / (k + rank_R(chunk))
```

with `k = 60` (standard RRF constant — no tuning surface needed for v1). A
chunk present in only one ranking (e.g. un-embedded) still gets a fused score
from that ranking alone. Sort descending by fused score; break exact ties by
ascending `ordinal` then `fileName` for determinism. This avoids ever
comparing raw keyword counts to cosine similarities directly, which are not
on the same scale.

### 4.5 Neighbor expansion

After fusion, take the top `topChunksPerQuery` (or a slightly larger seed
pool, e.g. `topChunksPerQuery * 2` capped at 20) fused chunks as **seeds**.
For each seed, pull in its `previousChunkId`/`nextChunkId` neighbors from the
same file (one hop each direction by default) to restore local context that
a hard chunk boundary may have split. Deduplicate by `chunkId`, then sort the
final set by `(fileName, ordinal)` so the model reads each file in natural
order rather than relevance-shuffled. Enforce the existing `CONTEXT_CHAR_LIMIT`
(120,000 chars, `frontend/app.js:2778`) **after** expansion — if expansion
would exceed budget, drop the lowest-fused-score seed (and its neighbors)
first, never truncate mid-chunk.

### 4.6 Adaptive full-document context

Before running retrieval, compute each candidate file's total character
length (sum of its chunks' `text.length`, or cache the original length at
upload time) and compare the sum of all relevant files' lengths against a
new `FULL_DOC_CHAR_BUDGET` (default 80,000 chars — chosen to leave headroom
under the existing 120,000-char `CONTEXT_CHAR_LIMIT` for the model's own
answer and any Context7/memory context also being injected this turn). Char
count is used instead of a tokenizer to keep zero new runtime dependencies;
this is a conservative heuristic (average ~4 chars/token), documented as
such in code comments.

- If the sum fits: skip retrieval/fusion entirely for those files and inject
  the **complete** text of each, concatenated in upload order, labeled per
  file (§4.9).
- If it doesn't fit: fall through to hybrid retrieval (§4.3–4.5) for a
  focused query, or hierarchical map-reduce (§4.7) for a recognized
  whole-document intent (§4.6a).

#### 4.6a Whole-document intent detection

A lightweight, dependency-free heuristic classifier (regex/keyword-based, no
model call) flags a query as "whole-document" when it matches patterns like:
`\b(summariz|review|analy[sz]e|compare)\b.*\b(document|file|whole|entire|all)\b`,
or explicit phrases ("summarize this", "give me an overview of the file").
This is intentionally conservative (AC-8) — anything not matched stays on
the focused hybrid-retrieval path. The classifier is a pure function
(`detectWholeDocumentIntent(query)`) so it's independently unit-testable and
tunable without touching retrieval code.

### 4.7 Hierarchical map-reduce

Triggered only when: whole-document intent detected (§4.6a) **and** the
adaptive-fit check (§4.6) fails for the relevant file(s). Algorithm:

1. **Map (leaf level):** group the file's structural chunks (in `ordinal`
   order) into batches that fit a per-call sub-budget (e.g. 40,000 chars).
   For each batch, send an isolated, non-streamed chat completion with a
   fixed system instruction ("extract the key facts/points from this excerpt
   relevant to: `<original query>`; cite the section heading and line range
   for each point") and no tools enabled. Collect each batch's summary text
   tagged with `fileName`, `headingPath`, `startLine`–`endLine`.
2. **Reduce:** concatenate the batch summaries (in order) and check if they
   fit the model's normal context alongside the original query. If yes, this
   becomes the final context for the user-visible answer. If the summaries
   themselves are still too large, repeat the reduce step recursively — batch
   the summaries and reduce again — until the result fits or a max recursion
   depth (3) is reached, at which point the deepest-level summaries are
   truncated with a clear "additional sections omitted" marker rather than
   silently dropped.
3. **Final answer:** the normal `sendMessage`/`runWithTools` path runs once
   more with the reduced context injected as a system message (same
   mechanism as `prepareContextMessages`), answering the user's original
   question — tools remain enabled for this final call only.
4. **Cancellation:** the existing `activeAbortController` is checked between
   map batches; if the user hits Stop, in-flight batch calls are aborted and
   no further batches are dispatched. A batch failure (network/HTTP error) is
   recorded as an omitted-section marker for that range rather than aborting
   the whole operation, so one bad batch doesn't sink the summary.
5. **Progress UI:** `document.getElementById('responseLog')` is updated with
   `Analyzing document — batch N of M...` during the map phase (same pattern
   already used for upload progress), so a multi-call operation isn't
   perceived as a hang.

Map/reduce calls use `stream: false` and no tool schema — only the final
answer call uses the user's normal stream/tools settings.

### 4.8 Optional reranking (#71)

A generic `rerank(query, candidates, fetchFn)` hook, disabled by default,
activated only when a new config flag (`appConfig.has_rerank`, mirroring the
`has_embeddings` pattern) and a configured reranker model/endpoint are both
present. When active, it is called **after** fusion+neighbor-expansion, over
the bounded seed set only (never the full corpus), via the same
OpenAI-compatible HTTP call pattern already used for `/embeddings` (reusing
the SSRF guard `is_safe_upstream_url` server-side if a proxy endpoint is
added, or client-side `fetchFn` injection consistent with `embedTexts`). On
any error, timeout (fixed client-side timeout, e.g. 8s), or a response that
doesn't parse into the expected ranked-index shape, the reranker result is
discarded and the pre-rerank fused order is used unchanged — this must be
provably a no-regression path when unconfigured (AC-9).

### 4.9 Context provenance

Every context block injected into the prompt (retrieval, full-document, or
map-reduce reduce output) is labeled with at minimum `fileName`; when
available, `headingPath` and `startLine`–`endLine` are appended, e.g.
`[report.md § Introduction > Background, lines 12-42]`. Expanded neighbor
chunks are visually distinguished in the label (e.g. a `(context)` suffix) so
a developer inspecting `showContextPreview()` output can tell primary hits
from expansion. Map-reduce summaries retain their source file/heading tags
through both the map and reduce stages so the final answer can still be
traced back to source sections.

### 4.10 Security & convention compliance

- No new runtime dependency — all parsing is regex/string-based stdlib JS.
- Map-reduce and rerank calls reuse the existing proxy/`fetch` path and the
  server-side SSRF guard (`is_safe_upstream_url`) — no new outbound surface.
- Traversal guards (`_safe_project_id`, `_resolve_chunk_cache_dir`) are
  unchanged — chunk-cache filenames/paths are not touched by this feature.
- No secrets are logged; map/reduce batch content is not persisted beyond
  the in-memory session unless the user explicitly saves the conversation
  (same as any other assistant output today).

## 5. Slice breakdown (backlog items)

| Item | Size | Covers | Depends on |
|------|------|--------|-------------|
| **#69 Retrieval foundations** | L | §3, §4.1–4.5, §4.9 (provenance for retrieval path), §4.10 | none |
| **#70 Whole-document analysis** | L | §4.6, §4.6a, §4.7, §4.9 (provenance for map-reduce) | #69 (uses its chunk schema + neighbor links) |
| **#71 Optional reranking** | M | §4.8 | #69 (reranks the fused seed set) |

Each slice gets its own `/build` pass but should reference this document as
the architecture source of truth rather than re-deriving the design. Per-slice
spec files may be created at `/build` time if `/loop` needs a narrower,
slice-scoped acceptance checklist — see `docs/specs/embeddings-rag.md` and
`docs/specs/project-chunk-embeddings.md` for precedent on this pattern (a
follow-on spec is fine; it should link back here rather than duplicate design).

## 6. Test plan (representative — exact names finalized in `/build`)

| # | Test description | File | Type |
|---|---|---|---|
| RET-1 | `chunkTextStructured` splits on Markdown headings and records `headingPath` | `frontend/tests/js/app.test.mjs` | unit |
| RET-2 | `chunkTextStructured` never splits inside a fenced code block | `frontend/tests/js/app.test.mjs` | unit |
| RET-3 | `chunkTextStructured` coverage guarantee — concatenated spans reproduce source lines | `frontend/tests/js/app.test.mjs` | unit |
| RET-4 | Oversized section falls back to bounded-window split within `[min, chunkLineSize]` | `frontend/tests/js/app.test.mjs` | unit |
| RET-5 | `normalizeChunkCache` upgrades a legacy (v1) cache object to v2 shape without dropping chunks | `frontend/tests/js/app.test.mjs` | unit |
| RET-6 | `getRelevantChunks` semantically scores embedded chunks and lexically scores un-embedded chunks in the same mixed set (no all-or-nothing gate) | `frontend/tests/js/app.test.mjs` | unit |
| RET-7 | `embedModel` mismatch on a stored embedding is treated as "no embedding" for that chunk | `frontend/tests/js/app.test.mjs` | unit |
| RET-8 | RRF fusion produces deterministic order; ties break by `ordinal` then `fileName` | `frontend/tests/js/app.test.mjs` | unit |
| RET-9 | Neighbor expansion pulls adjacent chunks, dedupes, and preserves source order | `frontend/tests/js/app.test.mjs` | unit |
| RET-10 | Neighbor expansion respects `CONTEXT_CHAR_LIMIT`, dropping lowest-score seeds first | `frontend/tests/js/app.test.mjs` | unit |
| RET-11 | Context labels carry `fileName`, `headingPath`, line range, and a `(context)` marker on expanded neighbors (§4.9) | `frontend/tests/js/app.test.mjs` | unit |
| RET-12 | The reported retrieval-method label distinguishes fused hybrid results from keyword-only results (§4.9) | `frontend/tests/js/app.test.mjs` | unit |
| WDA-1 | `detectWholeDocumentIntent` flags known whole-document phrasings, rejects narrow factual queries | `frontend/tests/js/app.test.mjs` | unit |
| WDA-2 | Full-document bypass triggers when combined char length fits `FULL_DOC_CHAR_BUDGET` | `frontend/tests/js/app.test.mjs` | unit |
| WDA-3 | Full-document bypass falls back to retrieval when budget exceeded | `frontend/tests/js/app.test.mjs` | unit |
| WDA-4 | Map-reduce map phase batches respect the sub-budget and cover 100% of chunks | `frontend/tests/js/app.test.mjs` | unit |
| WDA-5 | Map-reduce reduce phase recurses when summaries still exceed budget, stops at max depth with an omitted-section marker | `frontend/tests/js/app.test.mjs` | unit |
| WDA-6 | Map-reduce aborts remaining batches when `activeAbortController` is triggered mid-map | `frontend/tests/js/app.test.mjs` | unit |
| WDA-7 | A single failed map batch is recorded as an omitted-section marker without aborting the whole operation | `frontend/tests/js/app.test.mjs` | unit |
| RRK-1 | `rerank()` reorders the bounded seed set when configured and returns a well-formed response | `frontend/tests/js/app.test.mjs` | unit |
| RRK-2 | `rerank()` falls back to the pre-rerank fused order on timeout/error/malformed response | `frontend/tests/js/app.test.mjs` | unit |
| RRK-3 | `rerank()` is never invoked when `appConfig.has_rerank` is unset (zero-regression path) | `frontend/tests/js/app.test.mjs` | unit |
| INT-1 | End-to-end: project + per-chat chunks merge, structural chunking, and hybrid retrieval still return relevant results together | `backend/tests/python/test_server_http.py` | integration |
| INT-2 | `search_file` tool `run()` still awaits `getRelevantChunks` correctly post-refactor | `frontend/tests/js/app.test.mjs` | unit |
| INT-3 | Legacy chunk-cache JSON round-trips through `/chunk-cache` and `/generate-embeddings` unchanged in on-disk contract | `backend/tests/python/test_server_http.py` | integration |

## 7. Docs to update

- [x] `CHANGELOG.md` — entry per slice as each ships (#69 done; #70/#71 pending).
- [ ] `docs/USER_GUIDE.md` — document the whole-document analysis behavior
      (§4.6a/§4.7) as user-facing once #70 ships. **#69 done:** "Chunk size" is
      now documented as an upper bound, with neighbour context and excerpt
      labelling explained.
- [x] `docs/EMBEDDINGS_GUIDE.md` — chunking description, §6 flow diagram, and
      the "Key points in the flow" table updated for #69's structural chunking,
      per-chunk fallback, rank fusion, and neighbour expansion.
- [x] `docs/ARCHITECTURE.md` §4d — **two updates, both done for #69**:
      (1) corrected the description of the *pre-#69* behavior as part of this
      spec's own doc-fix scope; (2) rewritten to describe shipped #69 behavior,
      with #70/#71 explicitly listed as not yet implemented. To be updated again
      as each remaining slice ships (never ahead of shipped code).
- [x] `backlog.md` — **#69, #70, #71** added (this `/spec` run); **#69** flipped
      `[~]` → `[x]` with Done date, outcome, and spec link on ship; #70/#71 stay
      `[ ]` until their own `/spec`/`/build` cycle starts.
- [x] Scrum mirror — `Cline/scrum/product-backlog.md` Open Items table gained
      #69/#70/#71 rows; #69 moved to In-Progress on the `[~]` flip and into the
      Completed table on the `[x]` flip. Sprint 16 review/retro + `sprint-index.md`
      closed out.

## 8. Risks / edge cases

| Risk | Mitigation |
|------|-----------|
| Structural chunking regex misdetects headings/code in non-Markdown files (plain `.txt`, source code) | Falls back to paragraph/line boundaries (`sectionType: "unknown"`/`"prose"`) — never fails, just less precise metadata; existing fixed-size behavior remains available as `chunkText()` for comparison in tests. |
| Legacy cache normalization run on every load could be slow for very large cached projects | Normalization is O(n) over chunks already being iterated for rendering/scoring — no new full-file re-read; acceptable given existing chunk counts (hundreds, not millions). |
| `FULL_DOC_CHAR_BUDGET` heuristic (chars, not tokens) under/over-estimates true token usage for non-English text or code-heavy content | Documented as a conservative heuristic; erring toward retrieval/map-reduce (safer) rather than overflowing the model's context is the deliberate failure direction. |
| Map-reduce adds real latency/cost (multiple extra model calls) for a whole-document request | Gated tightly by conservative intent detection (§4.6a, AC-8) so it only fires when clearly asked for; progress UI keeps the user informed; Stop button remains functional mid-operation. |
| `docs/EMBEDDINGS_GUIDE.md` §"Chunking" row already claims "overlapping chunks" today, which is currently false (`chunkText` is non-overlapping) | Corrected as part of this spec's immediate doc-fix scope (§7), independent of the code changes — a pure accuracy fix that can land ahead of #69's implementation. |
| Existing `EMB-*`/`PFU-*` tests assume today's cache shape | `normalizeChunkCache` guarantees old-shape objects still satisfy the fields those tests assert on; regression tests (INT-3) explicitly lock the on-disk legacy contract. |
| Reranker/HTTP dependency adds a new outbound call surface | Reuses the existing proxy + SSRF guard rather than introducing a new fetch path; disabled by default; bounded to the seed set (never the full corpus). |

## 9. Review checklist (filled by Reviewer role, per slice)

### Slice #69 — Retrieval foundations (reviewed 2026-09-17: PASS)

- [x] Implementation matches this spec's §3, §4.1–4.5, §4.9, §4.10
- [x] `./run-tests.sh --coverage` passes — 391 Python tests OK, 123 JS tests
      pass; server.py line 95% (≥90%), branch 93.42% (≥80%), JS branch 77.75%
      (≥70%), ratchet guard PASS
- [x] `./scripts/security-scan.sh` clean (exit 0; gitleaks + bandit + pip-audit.
      Check 4/4 memory-note scan, when `OBSIDIAN_VAULT_PATH` is exported, reports
      only pre-existing **false positives** — its patterns match the notes'
      safety-checklist prose, not secrets; filed as backlog #72)
- [x] Docs updated per §7 for the slice shipped
- [x] Acceptance criteria AC-1…AC-5, AC-10, AC-11 verified (AC-6…AC-9 explicitly
      deferred to #70/#71)
- [x] `docs/ARCHITECTURE.md` §4d accurately reflects shipped behavior (no
      ahead-of-code claims; #70/#71 named as unimplemented)
- [x] Memory note written to `Cline/memories/`
      (`2026-09-17-190500-backlog-69-retrieval-foundations-shipped.md`)

### Slices #70 / #71 — pending

- [ ] Implementation matches this spec's §3–5 for the slice under review
- [ ] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated per §7 for the slice shipped
- [ ] Acceptance criteria (§2) relevant to the slice all verified
- [ ] `docs/ARCHITECTURE.md` §4d accurately reflects shipped behavior (no
      ahead-of-code claims)
- [ ] Memory note written to `Cline/memories/`

## Spec changelog

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|
| 2026-09-17 | §2, §7, §9 | Ticked AC-1…AC-5/AC-10/AC-11 and the #69 doc items; marked AC-6…AC-9 as deferred to #70/#71; split §9 into a completed #69 checklist and a pending #70/#71 checklist; header Status → "In Progress (#69 Done)". | #69 shipped; the spec is the review source of truth and must record which slice satisfied which AC. |
| 2026-09-17 | §6 (test plan) | Implementation added **RET-11** (context-label format incl. `(context)` marker) and **RET-12** (retrieval-method label) beyond the table, covering §4.9 provenance which had no explicit test row. | §4.9 was specified but untested; provenance labels are user-visible so they needed direct coverage. |




