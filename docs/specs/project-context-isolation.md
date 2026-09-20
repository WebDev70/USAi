# Spec: Project Context Isolation (RAG leak fix)

**Status:** Ready
**Type:** bugfix (regression test required first; PO acceptance gate skipped)
**Created:** 2026-09-20
**Author:** Cline
**Backlog:** #94 (🚨 BLOCKING)

## 1. Goal & scope

**Goal:** Guarantee that a chat opened inside project *P* can only ever retrieve
document chunks that belong to *P* (its own project-shared files) plus files
attached to that specific chat. No document from any other project may ever be
injected into the LLM context.

**In scope**
- Hard-scope RAG retrieval by `projectId` (primary defense).
- Clear per-chat (`fileChunks`/`uploadedFiles`) and project (`projectChunks`)
  runtime state on every project switch, session restore, new-chat, and
  move-out (belt-and-suspenders defense).
- Regression tests reproducing the observed leak, then proving it is closed.
- Documented, safe purge of the orphaned Sept-13 manual-QA test projects
  (156 `EmbeddingNegTest` + 191 `EmbeddingTest` + 190 `Test Project EMB3`).

**Out of scope**
- #95 (server-side `max_tokens` output cap) — tracked separately.
- Any change to the embedding model or chunking algorithm.
- Backend chunk-cache storage layout (already `projectId`-scoped and verified).

## 2. Root-cause analysis (verified on disk)

The leak was **runtime front-end state**, not disk contamination.

- Leaking chat: `.chat_sessions/session_1789910567298.json`
  ("How do the documents in this project differ?"),
  `projectId = project_1789910130524933_2f6d37` (name `EmbeddingNegTest`,
  created 2026-09-20). That project dir contains **only**
  `FSSOnline as is state.txt` + `FAS Cloud Services Overview.txt`.
- `eOffer Data Dictionary.xlsx` lives in a **different** project *also* named
  `EmbeddingNegTest`: `project_1789778243766721_30a89f` (created 2026-09-18),
  attached as a **per-chat upload** in `session_1789778537756.json`
  (turn 0 note: `Files: eOffer Data Dictionary.xlsx - dataDictionary.csv`).
- `grep` confirms **no eOffer text exists** under
  `.chunk_cache/projects/project_1789910130524933_2f6d37/`.
- Token accounting on the leaking chat: turn 1 = 8,219 input tokens (≈ the two
  legit files); turn 3 = 15,934 — a ~7,700-token jump matching eOffer's
  32,704 chars ÷ 4 ≈ 8,176 tokens.

**Mechanism.** Retrieval has **no notion of the active project**:

- `getRelevantChunks()` (`frontend/app.js` ~L2591) defaults to
  `[...fileChunks, ...projectChunks]` — it trusts whatever is in those two
  module-global arrays.
- `prepareContextMessages()` (~L3260) injects context whenever
  `fileChunks.length + projectChunks.length > 0`, again with no `projectId`
  check.
- Per-chat `fileChunks`/`uploadedFiles` are cleared at the **end** of
  `sendMessage` (L3573) and on new-chat (L3988), but **`openProject()`
  (L1425), `startNewProjectChat()` (L1447), and `restoreSession()` (~L2044)
  do NOT clear `fileChunks`/`uploadedFiles`**. `openProject`/`restoreSession`
  reload `projectChunks` but leave stale per-chat chunks resident.
- Two projects sharing the display name `EmbeddingNegTest` made the
  cross-contamination easy to trigger and hard to notice.

Net: chunks from a previously-open project/chat survived in module state and
were merged into the next chat's retrieval pool.

## 3. Root-cause summary (duplicate-name factor)

Selection is already `projectId`-keyed in the DOM (`openProject(item.dataset.id)`,
L1609), so duplicate display names do **not** by themselves misroute a click.
The duplicate name only masked the leak during manual QA. The fix must not rely
on name uniqueness; it must key isolation on `projectId`.

## 4. User story & acceptance criteria

As a user working across multiple projects, I want each chat's document context
to be strictly limited to its own project, so that no other project's documents
ever leak into my prompts or the model's answers.

- [ ] **AC-1 (isolation):** A chat whose session `projectId = P` retrieves
  chunks only from project *P*'s shared files plus files attached to that chat.
  No chunk tagged with a different `projectId` is ever selected or injected.
- [ ] **AC-2 (projectId-keyed, name-immune):** Isolation holds even when two
  projects share an identical display name; selection and scoping use
  `projectId`, never the name.
- [ ] **AC-3 (clear on switch):** `projectChunks`, `fileChunks`, and
  `uploadedFiles` are provably empty immediately after `openProject()`,
  `startNewProjectChat()`, `restoreSession()`, new-chat, and project move-out
  (before any new load for the target project runs).
- [ ] **AC-4 (defense in depth):** Even if a stale chunk from another project
  is present in a module array, retrieval drops it because it does not match
  the active `projectId` (a chunk with no `projectId` is treated as per-chat
  and allowed only for the current chat).
- [ ] **AC-5 (regression):** A test reconstructs the observed scenario
  (open project 30a89f with an eOffer per-chat upload → open project 2f6d37 →
  ask a question) and asserts eOffer chunks are NOT in the retrieval result.
- [ ] **AC-6 (backend scoping re-verified):** `/chunk-cache?projectId=` read and
  list operations remain confined to the requested project's cache dir
  (existing guard `_resolve_chunk_cache_dir` + `_safe_project_id`).
- [ ] **AC-7 (safe purge):** A documented, dry-run-first procedure removes the
  orphaned Sept-13 test projects without touching real projects, and is
  reversible until confirmed.

## 5. Affected files

- `frontend/app.js`
  - `getRelevantChunks()` (~L2591) — accept/derive an `activeProjectId` and
    filter candidate chunks so only chunks matching the active project (or
    unscoped per-chat chunks belonging to the current chat) survive.
  - `prepareContextMessages()` (~L3260) — pass the active `projectId` into
    retrieval; gate injection on the filtered set, not raw array lengths.
  - `loadProjectChunks()` (~L435) — tag each loaded chunk with its
    `projectId` (source of truth for AC-4).
  - `openProject()` (L1425), `startNewProjectChat()` (L1447),
    `restoreSession()` (~L2044), move-out handler (~L1770), delete handler
    (~L1861) — clear `fileChunks`/`uploadedFiles`/`projectChunks` on switch
    (AC-3). Prefer a single `resetChatContextState()` helper reused by all.
- `frontend/tests/js/project-context-isolation.test.mjs` (new) — AC-1..AC-5.
- `backend/tests/python/test_server_branches.py` — assert `/chunk-cache`
  list/read stay project-scoped (AC-6) if not already covered.
- `scripts/purge-orphan-test-projects.sh` (new) — dry-run-first purge tool
  (AC-7), git-ignored data dirs only.
- `docs/USER_GUIDE.md`, `CHANGELOG.md`, `backlog.md`,
  `Cline/scrum/product-backlog.md` — docs + lifecycle.

## 6. Technical approach

**Primary — hard-scope retrieval by `projectId`:**
1. In `loadProjectChunks(projectId)`, stamp every chunk object with
   `projectId` before pushing into `projectChunks`.
2. Add a module accessor for the active chat's project (the session's
   `projectId`, i.e. `currentProjectId` at compose time).
3. In `getRelevantChunks()`, before ranking, filter the candidate pool:
   keep a chunk iff `chunk.projectId === activeProjectId`
   **or** `chunk.projectId` is absent (a genuine per-chat upload for the
   current chat). Drop everything else. Leakage becomes impossible even if
   clear-on-switch regresses.
4. `prepareContextMessages()` computes the filtered set once and only injects
   when it is non-empty.

**Secondary — clear-on-switch invariant:**
Introduce `resetChatContextState()` that empties `fileChunks`,
`uploadedFiles`, `pendingImages`, and `projectChunks`, then refreshes the
attachment tray. Call it at the top of `openProject`, `startNewProjectChat`,
`restoreSession`, the new-chat handler, and move-out — *before* loading the
target project's chunks.

Conventions honored: no new runtime deps (vanilla JS + Python stdlib);
`/chunk-cache` keeps its path-traversal guard; no CSS change (no `?v=` bump);
backend bind/config untouched.

## 7. Test plan

| Test | File | Description |
|------|------|-------------|
| AC-1/AC-4 filter | frontend/tests/js/project-context-isolation.test.mjs | `getRelevantChunks` drops chunks whose `projectId` ≠ active |
| AC-2 name-immune | same | two projects same name, different ids → no cross-pull |
| AC-3 clear-on-switch | same | after each switch entry point, arrays are empty |
| AC-5 regression | same | reconstruct eOffer scenario → eOffer chunk absent |
| AC-6 backend scope | backend/tests/python/test_server_branches.py | `/chunk-cache?projectId=` list/read confined to project dir |

Run: `./run-tests.sh --coverage` (server.py ≥ 90%, JS branch ≥ 70%).

## 8. Docs to update
- [ ] CHANGELOG.md — bugfix entry (project RAG isolation).
- [ ] docs/USER_GUIDE.md — note that project chats are context-isolated.
- [ ] README.md — only if purge script needs documenting.
- [ ] backlog.md — #94 `[~]` → `[x]` on completion; scrum mirror synced.

## 9. Risks / edge cases
- Legacy `projectChunks`/cache entries lack a `projectId` field — migration:
  stamp on load; treat missing-`projectId` project chunks conservatively
  (injected only when their source project is the active one at load time).
- Genuine per-chat uploads inside a project: per-chat chunks have no
  `projectId` and must remain available for that chat only; clear-on-switch
  (AC-3) removes them when leaving the chat, so AC-4's "absent ⇒ allowed" is
  safe.
- Purge script must operate on git-ignored data dirs only and never delete a
  project referenced by a real (non-test) session.

## 10. Review checklist (Reviewer role)
- [ ] Implementation matches spec sections 5–7
- [ ] `./run-tests.sh --coverage` passes (gates met)
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (section 8)
- [ ] Memory note written
- [ ] Regression test (AC-5) present and green

