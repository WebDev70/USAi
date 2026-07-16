# Spec: Referenced-Path Existence Guard (#59)

**Status:** Done
**Created:** 2026-07-15
**Author:** Cline

## 1. Goal & scope

Add **Guard 4** to `scripts/doc-consistency-check.sh`: parse every `.md` file in
`.clinerules/` and `docs/tooling/`, extract every `backend/…`, `frontend/…`, and
`scripts/…` path reference, and assert that each referenced file (or directory)
actually exists under `$REPO_ROOT`.

**Why:** Future directory reorganisations can silently break workflow docs (just as
the test-path reorg in #56 did). Guard 4 auto-detects broken references so the
`cli-check.sh --review` gate and pre-commit hook catch them immediately.

**Out of scope:**
- Checking references in files outside `.clinerules/` and `docs/tooling/`
- Checking `http://` / `https://` URLs
- Checking wikilinks or Obsidian vault paths

## 2. User story & acceptance criteria

As a developer editing workflow docs, I want a machine check that tells me when I
reference a `backend/`, `frontend/`, or `scripts/` path that doesn't exist, so
that broken doc references are caught before they mislead future contributors.

- [x] **AC-2a — Fail on missing referenced path:** `doc-consistency-check.sh` exits
  non-zero when a `.md` file in `.clinerules/` or `docs/tooling/` contains a
  `backend/…`, `frontend/…`, or `scripts/…` path that does not exist under
  `$REPO_ROOT`.
- [x] **AC-2b — Pass when all referenced paths exist:** exits 0 when every
  `backend/…`, `frontend/…`, `scripts/…` reference in those files resolves to a
  real file or directory.
- [x] **AC-2c — Ignore code-block context consistently:** paths inside fenced code
  blocks (` ``` `) are still checked — they are often example commands that should
  remain valid. Only paths explicitly prefixed by a `` ` `` (inline code) or
  appearing as bare tokens in the prose are extracted; the regex pattern handles
  both.
- [x] **AC-2d — No false positives on glob patterns:** path tokens containing `*`
  or `$` (shell globs and variables) are skipped — they cannot be resolved to a
  specific file.

## 3. Affected files

- `scripts/doc-consistency-check.sh` — append Guard 4 block before the final
  result section
- `backend/tests/python/test_scripts.py` — add `TestRefPathExistenceGuard` class
  (T-14a/b/c) after `TestMandatoryGateGuard`
- `docs/specs/ref-path-existence-guard.md` — this file
- `CHANGELOG.md` — add entry under `[Unreleased]`
- `backlog.md` — flip item #59 `[~]` → `[x]`

## 4. Technical approach

### Regex pattern

Extract path tokens matching:

```
(backend|frontend|scripts)/[A-Za-z0-9_./-]+
```

- Must start at a word boundary or after a non-alphanumeric character (space,
  backtick, `(`, `"`, `'`, newline)
- Must NOT contain `*` or `$` (skip globs / shell variables)
- Bash 3.2-compatible: use `grep -Eo` with a POSIX ERE pattern

### Guard 4 block structure (appended before `# Final result`)

```bash
# ---------------------------------------------------------------------------
# Guard 4 — Referenced-path existence guard (AC-2, item #59)
# ...
# ---------------------------------------------------------------------------
echo "--- Guard 4: Referenced-path existence check ---"

REF_SCAN_DIRS=(".clinerules" "docs/tooling")
REF_PATH_PATTERN='(backend|frontend|scripts)/[A-Za-z0-9_./-]+'

for scan_dir in "${REF_SCAN_DIRS[@]}"; do
    abs_scan="$REPO_ROOT/$scan_dir"
    [ -d "$abs_scan" ] || continue
    while IFS= read -r abs_file; do
        rel_file="${abs_file#$REPO_ROOT/}"
        # Extract all path tokens matching the pattern
        while IFS= read -r token; do
            [ -z "$token" ] && continue
            # Skip tokens with shell glob/variable characters
            case "$token" in *\** | *\$*) continue ;; esac
            # Strip trailing punctuation (., ), ', ")
            token="${token%%[.,)\'\"]*}"
            [ -z "$token" ] && continue
            target="$REPO_ROOT/$token"
            if [ ! -e "$target" ]; then
                OFFENDERS="${OFFENDERS}\n  ✕  Missing path '${token}' referenced in '${rel_file}'"
                ERRORS=$((ERRORS + 1))
            fi
        done < <(grep -Eo "$REF_PATH_PATTERN" "$abs_file" 2>/dev/null || true)
    done < <(find "$abs_scan" -name "*.md" -type f 2>/dev/null)
done
```

### Conventions
- Bash 3.2-compatible: no `mapfile`, no `declare -A`
- Follows the same `REPO_ROOT`-relative layout as Guards 1–3
- `OFFENDERS` and `ERRORS` accumulate across all guards (shared variables)

## 5. Test plan

| ID | Class | Description |
|----|-------|-------------|
| T-14a | `TestRefPathExistenceGuard` | Missing `backend/` path → exit non-zero |
| T-14b | `TestRefPathExistenceGuard` | All referenced paths exist → exit 0 |
| T-14c | `TestRefPathExistenceGuard` | Glob tokens (`backend/tests/*.py`) skipped → exit 0 |

Tests use the existing `_setup_drift_tree` / `_run_doc_consistency` helpers.
Each test creates a real file/dir under the temp tree so `os.path.exists` resolves.

## 6. Docs to update

- [x] `CHANGELOG.md` — entry in `[Unreleased]`
- [ ] `docs/USER_GUIDE.md` — not user-facing, no change needed
- [ ] `README.md` — no setup/config change needed
- [x] `backlog.md` — mark item #59 done
- [x] `Cline/scrum/product-backlog.md` — move to Completed table

## 7. Risks / edge cases

- **Deeply-nested paths in prose:** e.g. `backend/tests/python/test_server.py` → the
  regex is greedy and will capture the full path, which is the desired behaviour.
- **Relative path fragments not starting at root:** e.g. `tests/python/` (without
  `backend/`) — these are NOT matched by Guard 4 (they fall under Guard 1's stale-path
  check). Guards are complementary, not overlapping.
- **Symlinks:** `[ -e "$target" ]` follows symlinks — symlinked paths are treated as
  existing. Acceptable for our use case.
- **`docs/tooling/` `.md` files themselves:** they are scanned but their own references
  (`docs/tooling/cline.md`) start with `docs/` not `backend/`/`frontend/`/`scripts/`,
  so no false positives.

## 8. Review checklist (filled by Reviewer role)

- [ ] Implementation matches spec sections 3–5
- [ ] `./run-tests.sh --coverage` passes both coverage gates
- [ ] `./scripts/security-scan.sh` clean
- [ ] Docs updated (section 6)
- [ ] Memory note written
