# Spec: Composer Attachment Tray (#80)

**Status:** Done
**Created:** 2026-09-18
**Author:** Cline

## 1. Goal & scope

Replace the invisible, destructive, sidebar-buried file-attachment UX with a
coherent **composer attachment tray** that is always visible, additive, and
persists attachment provenance alongside the message turn.

### Root-cause audit

1. **Hidden indicator.** `#uploadedFilesDisplay` is inside the collapsed sidebar
   "File Uploads" `<details>` panel — the user never sees it.
2. **Destructive re-upload.** `handleFileUpload` opens with
   `fileChunks.length = 0; uploadedFiles.length = 0` — every new attach wipes
   the previous files.
3. **Disappears after send.** `persistExchange` does NOT save `uploadedFiles` /
   `fileChunks`. On restore the assistant note lies ("Files: report.pdf") but
   the chunks are gone.
4. **No per-file removal** — only a bulk "Clear" button.
5. **PDF/DOCX locked out.** `#fileUpload accept=` omits `.pdf`/`.docx`;
   `extractTextServerSide` exists but is not wired into the composer path.

**Out of scope:** full chunk re-hydration on session restore (RAG concern,
tracked separately). Acceptance bar = provenance display only.

## 2. User story & acceptance criteria

As a user I want to attach files to my message, see them clearly next to the
composer, remove individual files, and see a record of which files were attached
to each turn when I restore a chat.

- [x] **AT-1** After attaching, a chip per file appears in the **composer tray**
  (above the composer, not in the sidebar).
- [x] **AT-2** Attaching a second file **adds** a chip — the first is kept.
- [x] **AT-3** Clicking ✕ on a chip removes only that file's chunks.
- [x] **AT-4** The 📎 button accepts `.pdf`/`.docx`; they route through
  `extractTextServerSide`.
- [x] **AT-5** After send, the tray clears.
- [x] **AT-6** Restored turn note shows `Files: <names>` for that message.
- [x] **AT-7** `#uploadedFilesDisplay` sidebar div is retired.
- [x] **AT-8** Cache controls (Chunk size, Top chunks, Save/Restore) are kept.
- [x] **AT-9** All existing JS tests pass; new AT-JS-* tests green.

## 3. Affected files

- `frontend/app.js` — additive upload, per-chip remove, `extractTextServerSide`
  routing, `persistExchange` attachment record, `showAttachmentTray()`,
  `removeAttachedFile()`, retire `showUploadedFilesDisplay` body
- `frontend/index.html` — add `#composerAttachments` tray div; update
  `#fileUpload accept=`; remove `#uploadedFilesDisplay` div; bump `?v=31`
- `frontend/styles.css` — `.composer-attachments`, `.file-chip` styles; v31
- `frontend/tests/js/app.test.mjs` — AT-JS-1…AT-JS-8 tests

## 4. Technical approach

### 4a. Attachment record on turn

`persistExchange` adds to user turn:
```js
attachments: uploadedFiles.map(name => ({ name }))
```
`appendMessage` gains an `attachments` param; renders a
`<span class="turn-attachments">📄 name1, name2</span>` when non-empty.

### 4b. Tray component

New `#composerAttachments` div above `#pendingImages` in `.input-wrapper`.
`showAttachmentTray()` renders chips; each chip has a `.file-chip-remove`
button wired to `removeAttachedFile(index)`.

### 4c. Additive upload

Remove destructive `fileChunks.length = 0; uploadedFiles.length = 0` from top
of `handleFileUpload`. Skip filenames already in `uploadedFiles` (de-dupe).

### 4d. Per-file removal

```js
function removeAttachedFile(index) {
  const name = uploadedFiles[index];
  uploadedFiles.splice(index, 1);
  for (let i = fileChunks.length - 1; i >= 0; i--) {
    if (fileChunks[i].fileName === name) fileChunks.splice(i, 1);
  }
  showAttachmentTray();
}
```

### 4e. Clear tray after send

At end of `persistExchange`: `clearUploadedFiles(); showAttachmentTray();`

### 4f. PDF/DOCX routing in composer

Add `.pdf,.docx` to `#fileUpload accept=`. In the text-file loop:
```js
const ext = file.name.toLowerCase().split('.').pop();
if (ext === 'pdf' || ext === 'docx') {
  const { text, filename } = await extractTextServerSide(file);
} else {
  text = await file.text();
}
```

`extractTextServerSide(file, fetchFn = loggedFetch)` is the single shared helper
(POST multipart to `/extract-text`, unwrap `{error}` on failure, return
`{ text, filename }` with the `.txt`-rewritten chunk key). `uploadProjectFile`
and the `_handleFileUploadTest` shim call the same helper — see §5 AT-JS-9…11.

### 4g. Retire uploadedFilesDisplay

Redirect `showUploadedFilesDisplay` to call `showAttachmentTray()` so any
existing callers keep working. Remove `#uploadedFilesDisplay` from `index.html`.

## 5. Test plan

| ID | File | Description |
|----|------|-------------|
| AT-JS-1 | app.test.mjs | Two uploads → both names in `uploadedFiles` |
| AT-JS-2 | app.test.mjs | Same filename twice → de-duped (one entry) |
| AT-JS-3 | app.test.mjs | `removeAttachedFile(0)` removes name + its chunks |
| AT-JS-4 | app.test.mjs | `.pdf` routes to `extractTextServerSide` |
| AT-JS-5 | app.test.mjs | `.docx` routes to `extractTextServerSide` |
| AT-JS-6 | app.test.mjs | `.txt` still uses `file.text()` (regression) |
| AT-JS-7 | app.test.mjs | `persistExchange` stores `attachments` array on user turn |
| AT-JS-8 | app.test.mjs | After `persistExchange`, `uploadedFiles` is empty |
| AT-JS-9 | app.test.mjs | `extractTextServerSide` rewrites only the last extension to `.txt` |
| AT-JS-10 | app.test.mjs | `extractTextServerSide` surfaces the backend `{error}` message |
| AT-JS-11 | app.test.mjs | `extractTextServerSide` degrades to a generic message on a non-JSON error body |

> **Post-sprint addition:** AT-JS-9…11 were added when the three duplicated
> copies of the PDF/DOCX extraction logic were collapsed into a single
> `extractTextServerSide(file, fetchFn)` helper. The `_handleFileUploadTest` shim
> had drifted from production (it threw a generic `'extract failed'` instead of
> the backend's message), so AT-JS-4/5 were passing against a shim that no longer
> matched `handleFileUpload`. The shim now calls the real helper.

## 6. Docs to update

- [x] CHANGELOG.md
- [x] docs/USER_GUIDE.md — update "Uploading files" section
- [x] backlog.md — #80 lifecycle
- [x] Cline/scrum/product-backlog.md

## 7. Risks / edge cases

- `saveChunkCache` POST is per-filename keyed (idempotent) — additive re-save safe.
- `clearUploadedFiles` in New Chat handler: add `showAttachmentTray()` call.
- Cache-restore path calls `showUploadedFilesDisplay` → redirected to tray.

**Known limitation (accepted, documented):** `restoreFromCache(filename)` still
clears `fileChunks`/`uploadedFiles` before loading, so restoring from the cached-files
panel is **not** additive (unlike the 📎 attach path). The tray reflects the truth
either way, so it is not user-confusing, but it is inconsistent with AT-2. Noted in
`docs/USER_GUIDE.md` §7 (provenance-only note) and left as-is — a future item can make
restore additive if needed.

## 8. Review checklist

- [x] Implementation matches spec sections 3–5
- [x] `./run-tests.sh --coverage` passes
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated (section 6)
- [x] Memory note written
