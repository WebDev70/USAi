# Spec: QA Review — USAi Testing Strategy

**Status:** Done  
**Created:** 2026-06-24  
**Author:** Cline  
**Type:** docs / chore

---

## 1. Goal & scope

A quality-assurance review of the *entire* USAi testing strategy — not a feature,
but a structured audit that:

1. Inventories what is tested today and how well.
2. Identifies gaps, fragile mechanics, and improvement opportunities.
3. Prioritises findings by impact and produces an actionable output:
   - This document (the durable record).
   - A companion spec `docs/specs/frontend-behavior-tests.md` (Option C — the
     highest-value gap: a dev-only jsdom layer so real frontend user-flows can be
     exercised).
   - New backlog items (backlog #36–#39) for each remaining priority.

**Out of scope for this pass:** implementing any new tests beyond the spec.

---

## 2. Test-stack inventory

### 2a. What exists

| Layer | Tooling | Threshold / gate |
|-------|---------|-----------------|
| **Syntax** | `node --check app.js`, `python -m py_compile server.py` | Fail-fast; run on every `./run-tests.sh` |
| **JS unit (pure helpers)** | `node --test` (`node:test` + `node:assert`) | No min; always run |
| **JS coverage gate** | `node tests/js-coverage.mjs` — parses Node built-in `--experimental-test-coverage` report | Branch ≥ **70%** on `app.js` (of exported helpers only) |
| **Python unit + HTTP integration** | `unittest` against a real `ThreadingHTTPServer` on an ephemeral port | Always run |
| **Python coverage gate** | `coverage.py --branch` | Line ≥ **90%**, Branch ≥ **80%** (`server.py`) |
| **Ratchet guard** | `scripts/ratchet-check.sh` + `.coverage-thresholds` | Prevents gates being silently lowered |
| **Dev-script tests** | `tests/python/test_scripts.py` — tests the tooling scripts themselves | Included in Python run |
| **Security scan** | `scripts/security-scan.sh` (gitleaks + bandit + pip-audit + memory-note secret scan) | Deterministic; run in CI `security` job |
| **CI** | `.github/workflows/tests.yml` — JS job (Node 22), Python job (3.9 + 3.11), Security job | All three run on every push/PR |

### 2b. Backend use-case → test traceability

| Use case / behaviour | Test file | Test name(s) |
|----------------------|-----------|-------------|
| Proxy — inject server API key when client sends none | `test_server_proxy.py` | `test_proxy_injects_server_api_key_when_client_sends_none` |
| Proxy — forward client auth when provided | `test_server_proxy.py` | `test_proxy_forwards_client_auth_when_provided` |
| Proxy — 502 on unreachable upstream | `test_server_proxy.py` | `test_proxy_502_on_unreachable_upstream` |
| Proxy — relay upstream error status | `test_server_proxy.py` | `test_proxy_relays_upstream_error_status` |
| Proxy — 503 when base_url missing | `test_server_proxy.py` | `test_proxy_503_when_base_url_missing` |
| Proxy — SSE streaming relayed | `test_server_proxy.py` | `test_streaming_response_is_relayed` |
| Proxy — incremental streaming (first chunk before last) | `test_server_proxy.py` | `test_first_chunk_arrives_before_last` |
| `/config` — returns non-secret fields + flags | `test_server_http.py`, `test_server_branches.py` | `test_config_*` |
| `/config` — never leaks secrets | `test_server_http.py` | `test_config_never_leaks_secrets` |
| Memory — save/list/read/search lifecycle | `test_server_http.py` | `test_save_then_list_read_and_search` |
| Memory — auto-tag, accept string tags | `test_server_http.py` | `test_save_accepts_tags_as_string_and_auto_tags` |
| Memory — untitled fallback | `test_server_http.py` | `test_save_untitled_when_title_missing` |
| Memory — path traversal rejected | `test_server_http.py` | `test_read_rejects_path_traversal` |
| Memory — oversized payload rejected | `test_server_http.py` | `test_save_rejects_oversized_payload` |
| Memory — missing query → 400 | `test_server_http.py` | `test_search_missing_query_is_400` |
| Memory — disabled without vault → 400 | `test_server_branches.py` | `test_memory_endpoints_400_without_vault` |
| Sessions — save/list/delete roundtrip | `test_server_http.py` | `test_session_save_list_delete_roundtrip` |
| Sessions — auto-generate ID | `test_server_http.py` | `test_session_save_generates_id_when_omitted` |
| Sessions — unknown session → 404 | `test_server_http.py` | `test_get_unknown_session_is_404` |
| Chat history — empty→save→new-session archives | `test_server_branches.py` | `test_chat_history_empty_then_save_then_new_session_archives` |
| Chunk cache — roundtrip + traversal-safe | `test_server_http.py` | `test_chunk_cache_roundtrip_and_traversal_safe` |
| Chunk cache — 404 unknown | `test_server_branches.py` | `test_get_unknown_chunk_cache_is_404` |
| Logs — post / clear | `test_server_branches.py` | `test_log_post_and_clear` |
| Logs — malformed body → 400 | `test_server_branches.py` | `test_malformed_log_body_is_400` |
| Logs — oversized body → 413 | `test_server_http.py` | `test_log_entry_too_large_is_rejected` |
| Context7 — success | `test_server_proxy.py` | `test_context7_success_wraps_upstream_data` |
| Context7 — 400 when unconfigured | `test_server_branches.py` | `test_context7_400_when_unconfigured` |
| Context7 — relay upstream error | `test_server_proxy.py` | `test_context7_relays_upstream_error` |
| Context7 — 502 unreachable | `test_server_proxy.py` | `test_context7_502_on_unreachable_upstream` |
| Unknown route → 404 | `test_server_http.py` | `test_unknown_post_route_is_404`, `test_unknown_delete_route_is_404` |
| Malformed JSON body → 400 | `test_server_branches.py` | `test_*_malformed_json_is_400` |
| `_slugify`, `_resolve_memory_file`, `get_memory_dir` guards | `test_server.py` | multiple |
| `add_log` rotation | `test_server.py` | `test_rotates_at_max_logs` |
| `load_config` defaults | `test_server.py` | `test_reads_env_and_applies_defaults` |

### 2c. Frontend use-case → test traceability

| Use case | Exported helper tested? | Test coverage |
|----------|------------------------|--------------|
| `escapeHtml` XSS prevention | ✅ | `app.test.mjs` |
| `renderMarkdown` (bold, code, fenced blocks, XSS-safe, null-safe) | ✅ | `app.test.mjs` |
| `extractJson` (plain, fenced, fallback) | ✅ | `app.test.mjs` |
| `extractBalanced` JSON extraction | ✅ | `app.test.mjs` |
| `formatUsage` token display | ✅ | `app.test.mjs` |
| `getExcludedParams` / `MODEL_PARAM_EXCLUSIONS` | ✅ | `app.test.mjs` |
| `buildResponseFormat` (JSON mode) | ✅ | `app.test.mjs` |
| `safeTrim` | ✅ | `app.test.mjs` |
| `enforceStrictSchema` | ✅ | `app.test.mjs` |
| `scoreChunkByKeywords` / `chunkText` (RAG helpers) | ✅ | `app.test.mjs` |
| `normalizeAssistantText` | ✅ | `app.test.mjs` |
| Sidebar collapse/expand + localStorage persistence (`applySidebarCollapsed`, `_testToggle`, `_testInit`) | ✅ | `app.test.mjs` |
| **Send message / chat request flow** (`sendMessage`) | ❌ | Not tested |
| **Non-streaming API call** (`callChatApi`) | ❌ | Not tested |
| **Streaming API call with SSE delta relay** (`streamChatApi`) | ❌ | Not tested |
| **Tool calling loop** (`runWithTools`) | ❌ | Not tested |
| **Chat history restore / session switch** (`loadChatHistory`, `showSessionsList`) | ❌ | Not tested |
| **Session archival on new-chat** (`archiveCurrentSession`) | ❌ | Not tested |
| **Markdown rendering + bubble append** (`appendMessage`) | ❌ | Not tested |
| **Copy button wiring** | ❌ | Not tested |
| **Edit & resend / regenerate** | ❌ | Not tested |
| **Save-to-memory button** (`saveMemory`) | ❌ | Not tested |
| **Settings save/restore** (`saveSettings`, `restoreSettings`) | ❌ | Not tested |
| **Error display in chat** | ❌ | Not tested |
| **Stop / cancel (AbortController)** | ❌ | Not tested |
| **File upload + RAG chunking pipeline** | ❌ | Not tested |
| **Auto-recall memory injection** | ❌ | Not tested |

---

## 3. Findings (prioritised)

### 🔴 P1 — No frontend behavior tests

**Finding:** The 16 untested frontend use cases in §2c all require DOM/`fetch`/
`localStorage` context that only exists in the browser. `node --test` skips the
entire orchestration layer of `app.js` because it cannot import `document` or
`window`. A regression in `sendMessage`, streaming rendering, session switching, or
the tool loop silently passes all gates.

**Impact:** High — this is where most user-visible bugs live.

**Recommendation:** Add a dev-only jsdom-based test layer (see
`docs/specs/frontend-behavior-tests.md` for the full proposal).

---

### 🟡 P2 — SSRF guard on proxy target has no dedicated unit test

**Finding:** `is_safe_upstream_url()` is mentioned in documentation and referenced
by `nosec B310` suppressions in `server.py`, but no test file exercises it directly
(searching `tests/python/**` for `is_safe_upstream_url` returns zero hits in
invocations). The proxy tests use a real stub server — they test the happy path and
HTTP-error relay but **do not** call the guard with file://, gopher://, 169.254.x.x
(IMDS), ::1, or other SSRF inputs.

**Impact:** Medium — the guard exists but is untested. A refactor could break it
silently.

**Recommendation:** Add a `TestIsSafeUpstreamUrl` unit test class with:
- `http://` and `https://` → safe.
- `file://`, `gopher://`, `ftp://` → rejected.
- `http://169.254.169.254` (AWS IMDS), `http://127.0.0.1`, `http://[::1]` → rejected.
- Hostname that resolves to a loopback → rejected (if the guard checks post-DNS).

Track as **backlog #36**.

---

### 🟡 P3 — JS ratchet sentinel is not wired (committed minimum substituted)

**Finding:** `run-tests.sh` (line 88) reads `JS_BRANCH_LIVE="${JS_BRANCH_PCT:-$JS_MIN}"`.
`JS_BRANCH_PCT` is never exported by `tests/js-coverage.mjs` (no sentinel file
written), so the ratchet always compares the committed threshold against itself —
the JS branch ratchet effectively never fires.

**Impact:** Medium — the JS coverage threshold can decay without the ratchet
catching it; only the gate in `js-coverage.mjs` itself stops it, but only at the
hard floor, not the actual current high-water mark.

**Recommendation:** Have `tests/js-coverage.mjs` write the measured branch %
to a sentinel file (e.g., `/tmp/usai-js-branch-pct`) and have `run-tests.sh`
read it. This closes the ratchet loop for JS.

Track as **backlog #37**.

---

### 🟡 P4 — Proxy negative/adversarial cases are incomplete

**Finding:** The proxy test suite covers key injection, auth passthrough, error
relay, 502/503, SSE streaming, and incremental delivery. Missing:

- **Malformed upstream JSON** in a non-streaming response (what does the proxy
  return? 200 with bad body? 502?).
- **Header passthrough/stripping** — does the proxy forward `Content-Type`
  correctly? Does it strip hop-by-hop headers?
- **Oversized streamed body** — does the relay eventually close or exhaust memory?
- **Timeout vs. connection-refused distinction** — currently both map to 502;
  verifying the two code paths are separate.

**Impact:** Medium — these are real-world failure modes in a deployed proxy.

**Recommendation:** Add a `ProxyAdversarialTests` class covering the above.

Track as **backlog #38**.

---

### 🟡 P5 — CI Python job runs `coverage run` but not `run-tests.sh --coverage`

**Finding:** `tests.yml` runs:
```bash
python -m coverage run -m unittest discover ...
python -m coverage report -m
```
This exercises the `.coveragerc` `fail_under=88` (combined) safety net but does
**not** run the branch-coverage gate (`run-tests.sh --coverage` which enforces the
separate 80% branch threshold via JSON extraction). The branch threshold is only
enforced locally.

**Impact:** Low-medium — branch coverage regression would pass CI but fail locally.

**Recommendation:** Change the CI python step to call `./run-tests.sh --coverage`
directly (or extract the branch-gate logic into a standalone script callable from
CI). Alternatively, add a dedicated branch-gate step.

Track as **backlog #39**.

---

### 🟢 P6 — Streaming tests use raw sockets + timing assertions (flake risk)

**Finding:** `ProxyIncrementalStreamingTests.test_first_chunk_arrives_before_last`
uses `time.time()` to assert that the first chunk arrives before the last. While
thoughtfully written, timing-based assertions are inherently flaky on heavily loaded
CI runners.

**Recommendation:** Document the retry tolerance or convert to a structural
assertion (e.g., assert first chunk arrives within N seconds of response start,
not that it arrives before the last byte).

---

### 🟢 P7 — `coverage.py` is an unpinned dev dependency

**Finding:** `requirements.txt` pins `python-dotenv` (with hash). `coverage.py` is
installed ad-hoc (`pip install coverage`) in both `run-tests.sh` and CI, with no
pinned version. A `coverage.py` major version bump could change report format or
JSON schema.

**Recommendation:** Add a `requirements-dev.txt` (or `pyproject.toml` dev group)
pinning `coverage`, `bandit`, `pip-audit` with hashes. Consistent with the IaC
principle.

---

### 🟢 P8 — No mutation testing

**Finding:** 90% line / 80% branch coverage is strong but measures *execution*, not
*assertion quality*. Mutation testing (e.g., `mutmut` on `server.py`) validates
that the tests actually *catch* bugs, not just run code.

**Recommendation:** Run `mutmut` as an occasional local audit (not gated — too slow
for CI). Candidate target: the security-critical functions (`_resolve_memory_file`,
`get_memory_dir`, future `is_safe_upstream_url` unit tests).

---

## 4. Summary scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Backend API coverage (use cases)** | ⭐⭐⭐⭐⭐ | All major endpoints + edge cases covered |
| **Security invariants (server-side)** | ⭐⭐⭐⭐ | Traversal, secret-leak, oversize covered; SSRF unit test missing (P2) |
| **Frontend pure helpers** | ⭐⭐⭐⭐ | All 13 exported helpers covered; branch ≥ 70% gated |
| **Frontend behavior / UI flows** | ⭐ | ~0 coverage — entire orchestration layer untested (P1) |
| **Coverage gate rigor** | ⭐⭐⭐⭐ | Ratchet exists; JS sentinel not wired (P3) |
| **CI alignment** | ⭐⭐⭐ | Security + line coverage in CI; branch gate local-only (P5) |
| **Test tooling hygiene** | ⭐⭐⭐ | Dev deps unpinned (P7); streaming tests timing-dependent (P6) |

---

## 5. Action items → backlog

| # | Finding | Priority | Backlog ID |
|---|---------|----------|-----------|
| P1 | Frontend behavior tests (jsdom) | High | Spec: `frontend-behavior-tests.md`; backlog item TBD |
| P2 | SSRF guard unit tests | Medium | #36 |
| P3 | Wire JS ratchet sentinel | Medium | #37 |
| P4 | Proxy adversarial cases | Medium | #38 |
| P5 | CI branch-coverage gate | Low-Med | #39 |
| P6 | Streaming test flake hardening | Low | (note in test file) |
| P7 | Pin dev dependencies | Low | (part of #39 or separate) |
| P8 | Mutation testing audit | Low | (periodic / manual) |

---

## 6. Related documents

- `docs/rail-pipeline.md` — canonical RAIL concept + testing strategy
- `docs/specs/frontend-behavior-tests.md` — Option C spec (jsdom frontend tests)
- `docs/ARCHITECTURE.md` — backend + frontend component map
- `backlog.md` — items #36–#39 added per this review
- `.coveragerc`, `.coverage-thresholds`, `run-tests.sh`, `tests/js-coverage.mjs`
