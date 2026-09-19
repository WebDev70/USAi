# Spec: Project Chunk Embeddings (MVP — new uploads only)

**Status:** Done
**Created:** 2026-09-17
**Author:** Cline (backlog #65 closeout)

## 1. Goal & scope

Enable semantic (embedding-based) search over project file chunks so that
`getRelevantChunks` can rank a project's uploaded knowledge by meaning, not
just keyword overlap. This closes backlog **#65 — Embeddings for project
chunks**.

**In scope (this spec):**
- Generate embeddings for chunks belonging to files uploaded *after* this
  feature ships, via a new `POST /generate-embeddings` endpoint.
- Wire the Project Settings file-upload flow to call that endpoint
  automatically once a file's chunks have been cached.
- Use embeddings when present to rank project (and per-chat) chunks by cosine
  similarity; fall back to the existing keyword ranking when embeddings are
  absent or the embeddings call fails, so search never hard-fails.

**Explicitly out of scope:**
- **Legacy backfill.** Files uploaded to a project *before* this feature
  existed have chunk-cache entries with no `embedding` field. This spec does
  **not** add any startup migration, lazy backfill-on-read, or admin/CLI tool
  to retroactively embed them. Those files continue to be ranked via the
  keyword fallback indefinitely, until a separate feature is built.
  → **Tracked as new backlog item — see §6.**
- Any change to per-chat (non-project) file embeddings — only project chunk
  files are covered by this endpoint's typical caller, though the endpoint
  itself is generic over `filename` + `chunkIds` and does not special-case
  project vs. per-chat callers.
- Changing the embedding model/provider selection — reuses whatever
  OpenAI-compatible `/embeddings`-capable model is already configured for the
  active endpoint.

## 2. User story & acceptance criteria

As a user who uploads files into a Project, I want my project's files to be
searchable by meaning (not just exact keyword matches) so that the assistant
can find relevant context even when my question doesn't share vocabulary with
the source text.

- [x] AC-1: `POST /generate-embeddings?projectId=<id>` (or without
      `projectId` for per-chat cache) accepts `{ filename, chunkIds }`,
      generates embedding vectors for the named chunks via the configured
      embeddings-capable model, and persists them into the chunk-cache file
      in place.
- [x] AC-2: The Project Settings file uploader calls
      `POST /generate-embeddings` automatically after a successful
      `POST /project-files/<id>` upload, passing the `chunkIds` returned by
      the upload response.
- [x] AC-3: `projectId` is read from the URL query string (not the JSON
      body) — matches the convention used by every other project-scoped
      chunk-cache endpoint (`_resolve_chunk_cache_dir`). A regression test
      (EMB-3 negative) locks this in: `projectId` in the body is ignored.
- [x] AC-4: When ranking chunks for RAG context, chunks with a stored
      `embedding` are scored by cosine similarity against the query
      embedding; chunks without one fall back to keyword-overlap scoring in
      the same ranked list — no all-or-nothing gate that disables search
      entirely just because some chunks lack embeddings.
- [x] AC-5: If the embeddings call itself fails (network error, bad
      response, missing API key), the upload still succeeds and the file's
      chunks remain searchable via keyword fallback — embedding generation
      is best-effort and never blocks or reverts the upload.
- [x] AC-6: Traversal guards on `projectId` and `filename` are enforced
      identically to the existing project-file endpoints (reuses
      `_resolve_chunk_cache_dir` / `_safe_project_id`).

## 3. Affected files

- `backend/session_handlers.py` — `_post_generate_embeddings` handler:
  resolves the chunk-cache directory, loads the cached chunk file, calls the
  embeddings API for the requested `chunkIds`, writes vectors back in place.
- `backend/server.py` — routes `POST /generate-embeddings` to the handler.
- `frontend/app.js` — project file upload flow (`uploadProjectFile` /
  Settings-modal handler) calls `/generate-embeddings` after a successful
  upload; `getRelevantChunks` scores chunks by cosine similarity when an
  `embedding` is present, keyword overlap otherwise.
- `backend/tests/python/test_server_http.py` — `EMB-1`
  (`test_emb1_generate_embeddings_endpoint`), `EMB-3`
  (`test_emb3_full_project_upload_round_trip`), `EMB-3` negative
  (`test_emb3_negative_regression_project_id_in_body`).
- `frontend/tests/js/app.test.mjs` — `PFU-*` project-file-upload regression
  tests covering the upload → embeddings call contract.
- `CHANGELOG.md` — documents the `/generate-embeddings` endpoint and the
  keyword-fallback ranking change.

## 4. Technical approach

- **Endpoint:** `POST /generate-embeddings` follows the same pattern as
  other chunk-cache endpoints — `projectId` (optional) is a query-string
  param resolved via `_resolve_chunk_cache_dir`, which applies the same
  path-traversal guard (`_safe_project_id`) used by `/project-files/<id>`.
  Request body is `{ filename, chunkIds }`. Response is best-effort: on
  provider failure it returns an error status but does not corrupt or
  truncate the existing chunk-cache file.
- **Storage:** embeddings are stored as an `embedding: number[]` field added
  directly onto each chunk record inside the existing
  `.chunk_cache/projects/<id>/<file>.json` (or the per-chat equivalent)
  structure — no new storage location or schema migration.
- **Ranking:** `getRelevantChunks` in `frontend/app.js` checks each
  candidate chunk for a truthy `embedding`; when present it computes cosine
  similarity against the query's embedding, otherwise it falls back to the
  pre-existing keyword-overlap score. Both paths feed the same ranked
  result list, so a project with a mix of embedded and non-embedded chunks
  degrades gracefully rather than being rejected outright.
- **Trigger point:** embeddings are generated **only** at project-file
  upload time (`POST /project-files/<id>` → chunk cached → client calls
  `POST /generate-embeddings` with the new chunk ids). There is no
  server-side hook that runs on project open, chat restore, or any other
  read path — confirmed by exhaustive grep for re-index/backfill call
  sites during this review; none exist.
- **Security:** reuses existing SSRF guard and traversal-rejection
  conventions (`_safe_project_id`, `_resolve_chunk_cache_dir`) — no new
  attack surface. No new runtime dependency; uses the same
  OpenAI-compatible HTTP call pattern (`urllib`) as the rest of the proxy.

## 5. Test plan

| Test | File | Description |
|------|------|--------------|
| EMB-1 | `backend/tests/python/test_server_http.py::test_emb1_generate_embeddings_endpoint` | `POST /generate-embeddings` creates embeddings for a cached file's chunks. |
| EMB-3 | `backend/tests/python/test_server_http.py::test_emb3_full_project_upload_round_trip` | Full project file upload + embedding generation round trip. |
| EMB-3 negative | `backend/tests/python/test_server_http.py::test_emb3_negative_regression_project_id_in_body` | `projectId` posted in the JSON body (old, wrong contract) is ignored; query string is authoritative. |
| PFU-* | `frontend/tests/js/app.test.mjs` | Project-file-upload regression tests covering the upload → `/generate-embeddings` call contract. |

All of the above were green prior to this closeout (`./run-tests.sh --coverage`
passing: JS 125/125, Python 389/389, coverage gates met).

## 6. Docs to update

- [x] `CHANGELOG.md` — entry already documents `POST /generate-embeddings`
      and the keyword-fallback ranking change (see "Project embeddings"
      entry). Scope note added: new uploads only.
- [x] `docs/USER_GUIDE.md` — no change needed; embeddings are an internal
      ranking improvement with no new user-facing control surface.
- [x] `backlog.md` — mark **#65** done, scoped to new uploads only; add a
      **new backlog item** for legacy-file embedding backfill (pre-existing
      project files uploaded before this feature shipped remain keyword-only
      until that item is picked up).

## 7. Risks / edge cases

- **Legacy files never get embeddings** unless a user re-uploads them or the
  future backfill item is implemented. This is an accepted, explicit
  limitation of this MVP slice, not a bug.
- **Provider failure during embedding generation** (bad API key, network
  error, rate limit) is non-fatal — the upload itself has already succeeded
  and the chunk is simply left without an `embedding`, falling back to
  keyword ranking. No retry loop exists yet; a user can re-trigger by
  re-uploading if desired.
- **Mixed embedded / non-embedded corpora** are expected and handled by the
  graceful per-chunk fallback in `getRelevantChunks` rather than an
  all-or-nothing gate.

## 8. Review checklist (filled by Reviewer role)

- [x] Implementation matches spec sections 3–5 (verified against existing,
      already-merged code — this spec formalizes prior work, no new code
      changes were required).
- [x] `./run-tests.sh --coverage` passes (JS 125/125, Python 389/389;
      `server.py` ≥ 90% lines, JS branch ≥ 70%).
- [x] `./scripts/security-scan.sh` clean (no secrets, no new runtime deps,
      traversal guards verified).
- [x] Docs updated (§6).
- [x] Memory note written (Obsidian `Cline/memories/`).



