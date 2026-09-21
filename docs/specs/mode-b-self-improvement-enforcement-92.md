# Spec: Enforce Mode B Self-Improvement in Session Notes

**Status:** Done
**Type:** chore
**Created:** 2026-09-21
**Author:** Cline / user
**Prior context:** Sprint-19 governance report ADVISORY-03 (SPMS-5) filed this as #92.
Of 5 recent session notes examined, **0** recorded a Mode B outcome. Mode B is the
proactive/efficiency-driven track of `govern.md` SPMS-5: every session note must contain
either a workflow-improvement proposal *or* an explicit "no improvement found" statement.
Related memory notes:
[[2026-09-19-180404-sprint-19-governance-audit]],
[[2026-09-20-203500-backlog-grooming-post-sprint-21]].

---

## 1. Goal & scope

### Goal
Make a missing Mode B outcome **structurally impossible to skip** without triggering a
visible pipeline failure. Four enforcement points:

1. **Template enforcement** — add a required `## Mode B self-improvement` section to the
   session-note template in `build.md §3a` and `loop.md` Step 5.
2. **`/review` gate** — add a Mode B row to `review.md §6d` Documentation gate.
3. **`/govern` gate** — update `govern.md` SPMS-5 to reference `scripts/mode-b-check.sh`.
4. **Scripts guard + hermetic test** — new `scripts/mode-b-check.sh` + new
   `backend/tests/python/test_mode_b_check.py` (5 tests, G-4 redaction included).

### Out of scope
- No change to `server.py`, `app.js`, `styles.css`, `index.html`.
- No sprint-template change (Mode B applies to per-session memory notes only).
- `mode-b-check.sh` is NOT wired into `run-tests.sh` or CI — vault unavailable there.
  Invoked from `/review` and `/govern` only (same as `backlog-90-reconciliation-check.sh`).

---

## 2. User story & acceptance criteria

**As a** Cline developer running the RAIL pipeline,
**I want** every completed session note to include a Mode B self-improvement outcome,
**so that** process-improvement opportunities are never silently skipped.

- **AC-1:** `build.md §3a` template contains `## Mode B self-improvement` section.
- **AC-2:** `loop.md` Step 5 template + Done criteria contain the same section + checkbox.
- **AC-3:** `review.md §6d` has Mode B documentation-gate row → GAP if absent.
- **AC-4:** `govern.md` SPMS-5 references `scripts/mode-b-check.sh` with exit-code semantics.
- **AC-5:** Guard exits 0 (present), 1 (absent), 0+skip (vault unset/missing).
- **AC-6:** Guard accepts optional path arg; defaults to newest `*.md` by mtime.
- **AC-7 (G-4 redaction):** Guard never echoes note contents; reports `path:line_number [REDACTED]`.
- **AC-8 (hermetic tests):** T-1…T-5 in `test_mode_b_check.py` (described in §5).
- **AC-9 (gates clean):** `run-tests.sh --coverage`, `security-scan.sh`, `doc-consistency-check.sh`, `quality-gate.sh` all exit 0.

---

## 3. Affected files

| File | Change |
|------|--------|
| `.clinerules/workflows/build.md` | §3a template: add `## Mode B self-improvement` stanza |
| `.clinerules/workflows/loop.md` | Step 5 template + Done criteria: add stanza + checkbox |
| `.clinerules/workflows/review.md` | §6d: add Mode B row |
| `.clinerules/workflows/govern.md` | SPMS-5 proactive track: reference `scripts/mode-b-check.sh` |
| `scripts/mode-b-check.sh` | **New** — bash guard, exits 0/1, redacts, skips when vault unset |
| `backend/tests/python/test_mode_b_check.py` | **New** — 5 hermetic tests (T-1 … T-5) |
| `CHANGELOG.md` | `[Unreleased] › Changed` entry |
| `backlog.md` | #92 `[~]` → `[x]` with Done date + outcome + spec link (loop close) |

---

## 4. Technical approach

### 4a. Template edits (build.md §3a and loop.md Step 5)

In `build.md §3a`, after the YAML frontmatter block, add the following required section
to the prose description of what the note must contain:

```markdown
## Mode B self-improvement

*(Required — fill in before closing this session.)*

Proactive process-improvement scan: review the workflow used this session and record
**one** of the following:

- **Proposal:** `<title> — <one-sentence description>` (add to `backlog.md` if actionable)
- **No improvement found:** "no improvement found — <date> — <brief reason>"

Leave nothing blank. A missing section is flagged as a GAP by `/review §6d`
and `scripts/mode-b-check.sh`.
```

`loop.md` Step 5 gets the same block. The Done-criteria list gets:

```
- [ ] Mode B self-improvement section recorded in session note (proposal or "no improvement found")
```

### 4b. Review gate (review.md §6d)

New row immediately after the AGENTS.md / CONTINUE.md row:

```markdown
- [ ] **Mode B self-improvement** — session note has a `## Mode B self-improvement`
  heading with a non-empty body → else emit
  `GAP [process]: session note missing Mode B self-improvement section.`
```

### 4c. Govern gate (govern.md SPMS-5)

Replace the second bullet of the Mode B paragraph with:

```markdown
- **Proactive/efficiency-driven track (Mode B):** Run the deterministic check:
  ```bash
  scripts/mode-b-check.sh          # checks newest Cline/memories/*.md
  scripts/mode-b-check.sh <path>   # or a specific note
  ```
  - Exit 0 → Mode B recorded ✓
  - Exit 1 → Mode B missing → ADVISORY (first occurrence) / BLOCKING (2+ audits)
  - Exit 0 + "SKIP" → vault unavailable, do not flag
```

### 4d. scripts/mode-b-check.sh

```
Usage: scripts/mode-b-check.sh [<note-path>]
Exit: 0 = present or skip; 1 = section absent
```

- **Skip:** `OBSIDIAN_VAULT_PATH` unset or `Cline/memories/` absent → exit 0 with message.
- **SKIP_MODE_B=1** → exit 0 (matches `SKIP_GITLEAKS` pattern in `security-scan.sh`).
- **Target:** optional path arg; else newest `*.md` by `ls -t | head -1`.
- **Detection:** `grep -in "^## Mode B" "$TARGET"` — case-insensitive, heading-anchored.
- **Redaction (G-4):** diagnostic output is `path:line_number [REDACTED]` — never the
  matched line text.

### 4e. Shift-left governance check (§4b)

| Check | Result |
|-------|--------|
| G-1 AC testability | ✅ All 9 ACs verified by tests or file inspection |
| G-2 Scope / value | ✅ ADVISORY-03 real finding; fix is minimal |
| G-3 Dependency coherence | ✅ No new runtime deps; bash+coreutils always available |
| G-4 Grep-based security spec | ✅ APPLIES — redaction AC-7 + hermetic T-4 present |

---

## 5. Test plan

| # | Description | Setup | Expected |
|---|-------------|-------|----------|
| T-1 | Note with `## Mode B self-improvement` + proposal body | tmp note | exit 0 |
| T-2 | Note with `## Mode B self-improvement` + "no improvement found" | tmp note | exit 0 |
| T-3 | Note missing Mode B section entirely | tmp note (other content only) | exit ≠ 0 |
| T-4 **(G-4)** | Missing Mode B + planted `FAKE_SECRET_abc123` token | tmp note | exit ≠ 0 **AND** token absent from stdout+stderr |
| T-5 | `OBSIDIAN_VAULT_PATH` unset | env var removed | exit 0, "skip" in stdout |

All tests use `subprocess.run` on the real `scripts/mode-b-check.sh` with a `tempfile`
directory as vault root — zero network, zero real vault contact.

---

## 6. Docs to update

- [ ] `CHANGELOG.md` — add entry under `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — not user-facing → N/A
- [ ] `README.md` — no env/config change → N/A
- [ ] `AGENTS.md` / `CONTINUE.md` — no conventions changed → N/A
- [ ] `backlog.md` — mark #92 done at loop close

---

## 7. Risks & edge cases

| Risk | Mitigation |
|------|-----------|
| `ls -t` portability | macOS + Linux both support it; note in script header |
| Vault path with spaces | Quote all variables throughout |
| `OBSIDIAN_VAULT_PATH` set but `Cline/memories/` absent | Script checks both; exits 0 with skip |
| `doc-consistency-check.sh` ref-path check before script exists | Script created same turn as workflow edits |

---

## 8. Review checklist (filled by `/review`)

- [x] Implementation matches spec §3–5 exactly
- [x] `./run-tests.sh --coverage` passes (server.py ≥ 90%, JS branch ≥ 70%)
- [x] `./scripts/security-scan.sh` clean
- [x] Docs updated per §6
- [x] Acceptance criteria AC-1…AC-9 all verified
- [x] Memory note written to `Cline/memories/`

## Spec changelog

| Date | Section | Amendment | Reason |
|------|---------|-----------|--------|

