# Spec: More File Types (PDF/DOCX)

**Status:** In Progress
**Created:** 2026-06-25
**Author:** Cline
**Backlog item:** #8

## 1. Goal & scope

Add PDF and DOCX upload support so users can upload these document types and have their text content chunked, embedded, and retrieved through the existing RAG pipeline.

**In scope:**
- Server-side text extraction for `.pdf` (via `pypdf`) and `.docx` (via stdlib `zipfile`/XML).
- New `POST /extract-text` endpoint.
- Frontend routing in `handleFileUpload` for PDF/DOCX files.
- `has_pdf` flag in `/config`.
- Scanned/image-only PDF graceful degradation (warning, not error).

**Out of scope:**
- PPTX, XLS, ODT, or other office formats.
- OCR for scanned PDFs.
- Per-page citation or page-number metadata in chunks.

## 2. User story & acceptance criteria

*As a USAi user, I want to upload PDF and DOCX files so that their text content is chunked and used for RAG retrieval, just like plain text files.*

- [x] AC-1: Uploading a `.pdf` file with extractable text produces chunks that appear in `fileChunks` and are retrieved by `getRelevantChunks`.
- [x] AC-2: Uploading a `.docx` file produces chunks from the document body text.
- [x] AC-3: Uploading a scanned/image-only PDF shows a non-fatal warning in the status bar; the upload completes without crashing.
- [x] AC-4: Uploading a file with an unsupported extension (not `.pdf`/`.docx`/plain-text/image) still works exactly as before.
- [x] AC-5: `/config` returns `has_pdf: true` when `pypdf` is installed; `false` otherwise.
- [x] AC-6: `./run-tests.sh --coverage` passes all coverage gates.
- [x] AC-7: `./scripts/security-scan.sh` exits 0.

## 3. Affected files

- `server.py` — new `_post_extract_text` method + helper functions + `/config` `has_pdf` flag
- `requirements.txt` — add `pypdf==6.14.2` with sha256 hash
- `app.js` — `handleFileUpload` branching for PDF/DOCX; new `extractTextServerSide` helper
- `index.html` — extend `accept=` on `#fileUpload`
- `tests/python/test_server.py` — new `TestExtractText` class (13 tests)
- `tests/js/app.test.mjs` — 6 new tests for `extractTextServerSide`
- `CHANGELOG.md` — entry for #8
- `docs/USER_GUIDE.md` — document PDF/DOCX support + scanned PDF note
- `backlog.md` — mark #8 done

## 4. Technical approach

**Backend (`server.py`):**

1. `_try_import_pypdf()` — module-level, tries `import pypdf`, returns module or `None`. Enables graceful degradation and mocking in tests.
2. `_extract_docx_text(data: bytes) -> str` — opens bytes as `zipfile.ZipFile`, reads `word/document.xml`, collects all `<w:t>` text elements. Raises `ValueError` for non-zip or missing document.xml.
3. `_extract_pdf_text(data: bytes) -> tuple[str, str|None]` — opens with `pypdf.PdfReader(io.BytesIO(data))`, joins `page.extract_text()` for all pages. Returns `(text, None)` on success, `("", warning_string)` when no text found (scanned PDF).
4. `_post_extract_text(self)` — validates JSON body `{filename, data}`, enforces 50 MB Content-Length cap (413), validates Base64 decode, routes by extension, returns `{ok, text, warning}`. Returns 415 for unsupported extension; 400 for missing pypdf when PDF requested.
5. Register `'/extract-text': self._post_extract_text` in `do_POST` routes.
6. Add `'has_pdf': _try_import_pypdf() is not None` to `_get_config` return dict.
7. New stdlib imports: `import base64`, `import io`, `import zipfile`, `import xml.etree.ElementTree as ET`.

**Frontend (`app.js`):**
- `extractTextServerSide(file)` — reads `file` as ArrayBuffer, base64-encodes, POSTs to `/extract-text`, returns `{text, warning}`.
- In `handleFileUpload` text-files loop: detect `.pdf`/`.docx` by `file.name.toLowerCase()`, call `extractTextServerSide` instead of `file.text()`. Non-null warning is appended to responseLog.
- Export `extractTextServerSide` at bottom of file.

**Conventions:** path-traversal guard not needed (filename only used for extension detection); SSRF guard not needed (no upstream URL involved). 50 MB cap mirrors the embeddings endpoint's 10 MB cap scaled up for documents.

## 5. Test plan

| Test | File | Description |
|------|------|-------------|
| test_docx_extraction_valid | test_server.py | Builds minimal in-memory DOCX zip; asserts text contains expected words |
| test_docx_extraction_invalid_zip | test_server.py | b"not a zip" → ValueError |
| test_docx_extraction_missing_document_xml | test_server.py | Valid zip without word/document.xml → ValueError |
| test_pdf_extraction_valid | test_server.py | skipIf pypdf missing; tiny PDF → text extracted, warning None |
| test_pdf_extraction_no_text_returns_warning | test_server.py | PDF with no text layer → warning non-null, text empty |
| test_pdf_extraction_invalid_bytes | test_server.py | b"not a pdf" → Exception raised |
| test_post_extract_text_docx | test_server.py | HTTP POST valid Base64 DOCX → 200 ok:true non-empty text |
| test_post_extract_text_pdf_missing_dep | test_server.py | Mock _try_import_pypdf→None; POST .pdf → 400 "pypdf not installed" |
| test_post_extract_text_unsupported_extension | test_server.py | POST .xyz → 415 |
| test_post_extract_text_payload_too_large | test_server.py | Content-Length > 50MB → 413 |
| test_post_extract_text_invalid_base64 | test_server.py | data="!!!bad" → 400 |
| test_config_has_pdf_true | test_server.py | Mock pypdf importable → has_pdf true |
| test_config_has_pdf_false | test_server.py | Mock pypdf missing → has_pdf false |
| JS-PDF-1 | app.test.mjs | extractTextServerSide POSTs to /extract-text with correct body shape |
| JS-PDF-2 | app.test.mjs | Returns {text, warning} from response |
| JS-PDF-3 | app.test.mjs | Throws on HTTP error |
| JS-PDF-4 | app.test.mjs | handleFileUpload routes .pdf to extractTextServerSide |
| JS-PDF-5 | app.test.mjs | handleFileUpload routes .docx to extractTextServerSide |
| JS-PDF-6 | app.test.mjs | .txt files still use file.text() (not extractTextServerSide) |

## 6. Docs to update

- [x] CHANGELOG.md
- [x] docs/USER_GUIDE.md (user-facing: PDF/DOCX upload support + scanned PDF note)
- [ ] README.md — no setup/config changes needed (pypdf is in requirements.txt which users already install)
- [x] backlog.md (mark #8 done)

## 7. Risks / edge cases

- **Password-protected PDFs:** `pypdf` raises an exception; `_post_extract_text` catches and returns 400 with "Could not extract text: …".
- **Corrupted DOCX:** `zipfile.BadZipFile` raised; caught and returned as 400.
- **Very large PDFs:** 50 MB Content-Length guard prevents memory exhaustion.
- **pypdf not installed (fresh clone):** `has_pdf: false` in `/config`; `/extract-text` returns 400 with clear message; PDF/DOCX files in `handleFileUpload` will show the error in `responseLog` but not crash.
- **DOCX with tracked changes / revision history:** Only final `<w:t>` elements are extracted (no revision tracking).

## 8. Review checklist (filled by Reviewer role)

- [ ] Implementation matches spec sections 3–5
- [ ] `./run-tests.sh --coverage` passes
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (section 6)
- [ ] Memory note written
