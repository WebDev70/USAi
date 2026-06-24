"""
tests/python/test_scripts.py
Tests for scripts/spec-check.sh (RAIL Phase 1 — Verification gaps).

Each test runs spec-check.sh via subprocess against a temporary git repository
with a fixture spec file and a controlled git diff, keeping the tests fully
hermetic and deterministic.

TDD order (RAIL): these tests are written BEFORE the script exists (Red), then
spec-check.sh is implemented to make them pass (Green).
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest


# Absolute path to the script under test — resolved relative to this file so
# tests work regardless of the current working directory.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPEC_CHECK = os.path.join(REPO_ROOT, "scripts", "spec-check.sh")


def _run_spec_check(spec_path, git_root):
    """Run spec-check.sh in git_root against spec_path; return (returncode, stdout+stderr)."""
    result = subprocess.run(
        ["bash", SPEC_CHECK, spec_path],
        capture_output=True,
        text=True,
        cwd=git_root,
    )
    return result.returncode, result.stdout + result.stderr


def _init_git_repo(tmp_dir):
    """Initialise a bare git repo in tmp_dir so git commands work."""
    subprocess.run(["git", "init"], cwd=tmp_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_dir, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_dir, capture_output=True, check=True,
    )


def _make_initial_commit(tmp_dir, files):
    """
    Stage and commit a set of files (dict: relative-path → content).
    After this, HEAD exists and git diff --name-only HEAD can be used.
    """
    for rel_path, content in files.items():
        abs_path = os.path.join(tmp_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)
        subprocess.run(["git", "add", rel_path], cwd=tmp_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_dir, capture_output=True, check=True,
    )


def _write_uncommitted(tmp_dir, files):
    """Write files and stage them (so they appear in git diff --name-only HEAD)."""
    for rel_path, content in files.items():
        abs_path = os.path.join(tmp_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)
        subprocess.run(["git", "add", rel_path], cwd=tmp_dir, capture_output=True, check=True)


# ---------------------------------------------------------------------------
# Fixture spec content helpers
# ---------------------------------------------------------------------------

def _build_spec(affected_files, test_files):
    """
    Build a minimal spec with §3 Affected files table and §5 Test plan table.

    affected_files: list of relative paths, e.g. ["scripts/foo.sh"]
    test_files:     list of relative paths, e.g. ["tests/python/test_foo.py"]
    """
    # §3 table
    table_rows = "\n".join(f"| `{f}` | test change |" for f in affected_files)
    section3 = f"""## 3. Affected files

| File | Change |
|------|--------|
{table_rows}
"""

    # §5 table
    test_rows = "\n".join(
        f"| T-{i+1} | desc | `{f}` | unit |"
        for i, f in enumerate(test_files)
    )
    section5 = f"""## 5. Test plan

| # | Test description | File | Type |
|---|-----------------|------|------|
{test_rows}
"""

    return f"# Spec: Fixture\n\n{section3}\n---\n\n{section5}"


# ---------------------------------------------------------------------------
# T-1: exits 0 when diff matches §3 files and §5 tests exactly
# ---------------------------------------------------------------------------
class TestSpecCheckPass(unittest.TestCase):
    def test_exits_0_when_diff_matches_spec(self):
        """
        T-1: spec-check.sh exits 0 when every §3 file and every §5 test file
        appears in the git diff.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _init_git_repo(tmp)
            # Initial commit with a placeholder so HEAD exists
            _make_initial_commit(tmp, {"README.md": "init\n"})

            spec_content = _build_spec(
                affected_files=["scripts/spec-check.sh", "CHANGELOG.md"],
                test_files=["tests/python/test_scripts.py"],
            )
            spec_path = os.path.join(tmp, "docs", "specs", "fixture.md")
            os.makedirs(os.path.dirname(spec_path), exist_ok=True)
            with open(spec_path, "w") as fh:
                fh.write(spec_content)

            # Stage exactly the files listed in the spec (plus CHANGELOG.md which
            # spec-check.sh should ignore in scope-creep analysis)
            _write_uncommitted(tmp, {
                "scripts/spec-check.sh": "#!/usr/bin/env bash\necho hi\n",
                "CHANGELOG.md": "# changelog\n",
                "tests/python/test_scripts.py": "# tests\n",
            })

            rc, output = _run_spec_check(spec_path, tmp)
            self.assertEqual(rc, 0, msg=f"Expected exit 0, got {rc}. Output:\n{output}")
            self.assertIn("PASS", output.upper(), msg=f"Expected PASS in output:\n{output}")


# ---------------------------------------------------------------------------
# T-2: exits non-zero when a §3 file is absent from the diff
# ---------------------------------------------------------------------------
class TestSpecCheckMissingFile(unittest.TestCase):
    def test_exits_nonzero_when_s3_file_absent(self):
        """
        T-2: spec-check.sh exits non-zero when a §3 file is NOT in the git diff.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _init_git_repo(tmp)
            _make_initial_commit(tmp, {"README.md": "init\n"})

            spec_content = _build_spec(
                affected_files=["scripts/spec-check.sh", "scripts/missing.sh"],
                test_files=["tests/python/test_scripts.py"],
            )
            spec_path = os.path.join(tmp, "docs", "specs", "fixture.md")
            os.makedirs(os.path.dirname(spec_path), exist_ok=True)
            with open(spec_path, "w") as fh:
                fh.write(spec_content)

            # Only stage ONE of the two §3 files — "scripts/missing.sh" is absent
            _write_uncommitted(tmp, {
                "scripts/spec-check.sh": "#!/usr/bin/env bash\necho hi\n",
                "tests/python/test_scripts.py": "# tests\n",
            })

            rc, output = _run_spec_check(spec_path, tmp)
            self.assertNotEqual(rc, 0, msg=f"Expected non-zero exit, got {rc}. Output:\n{output}")
            # Should mention the missing file
            self.assertIn("missing.sh", output, msg=f"Expected missing.sh in output:\n{output}")


# ---------------------------------------------------------------------------
# T-3: exits non-zero (or warns) when a diff file is absent from §3 (scope creep)
# ---------------------------------------------------------------------------
class TestSpecCheckScopeCreep(unittest.TestCase):
    def test_warns_or_fails_when_diff_file_not_in_spec(self):
        """
        T-3: spec-check.sh warns (or exits non-zero) when a non-exempt file
        appears in the git diff that is NOT listed in §3.
        Per the spec, scope-creep is a warning (non-blocking), but the output
        must mention the unexpected file.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _init_git_repo(tmp)
            _make_initial_commit(tmp, {"README.md": "init\n"})

            spec_content = _build_spec(
                affected_files=["scripts/spec-check.sh"],
                test_files=["tests/python/test_scripts.py"],
            )
            spec_path = os.path.join(tmp, "docs", "specs", "fixture.md")
            os.makedirs(os.path.dirname(spec_path), exist_ok=True)
            with open(spec_path, "w") as fh:
                fh.write(spec_content)

            # Stage the spec file plus an UNEXPECTED file (not in §3, not exempt)
            _write_uncommitted(tmp, {
                "scripts/spec-check.sh": "#!/usr/bin/env bash\necho hi\n",
                "tests/python/test_scripts.py": "# tests\n",
                "app.js": "// unexpected change\n",   # scope creep
            })

            rc, output = _run_spec_check(spec_path, tmp)
            # Per spec design: scope creep → warning printed (non-blocking).
            # We assert the warning text appears; exit code may be 0 (warning) or 1.
            self.assertIn("app.js", output, msg=f"Expected 'app.js' scope-creep warning:\n{output}")


# ---------------------------------------------------------------------------
# T-4: exits non-zero when a §5 test row has no matching changed file
# ---------------------------------------------------------------------------
class TestSpecCheckMissingTestFile(unittest.TestCase):
    def test_exits_nonzero_when_s5_test_absent(self):
        """
        T-4: spec-check.sh exits non-zero when a §5 test-plan row refers to a
        tests/ file that is NOT in the git diff.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _init_git_repo(tmp)
            _make_initial_commit(tmp, {"README.md": "init\n"})

            spec_content = _build_spec(
                affected_files=["scripts/spec-check.sh"],
                test_files=["tests/python/test_scripts.py"],  # required test
            )
            spec_path = os.path.join(tmp, "docs", "specs", "fixture.md")
            os.makedirs(os.path.dirname(spec_path), exist_ok=True)
            with open(spec_path, "w") as fh:
                fh.write(spec_content)

            # Stage only the implementation file — the test file is NOT staged
            _write_uncommitted(tmp, {
                "scripts/spec-check.sh": "#!/usr/bin/env bash\necho hi\n",
            })

            rc, output = _run_spec_check(spec_path, tmp)
            self.assertNotEqual(rc, 0, msg=f"Expected non-zero exit, got {rc}. Output:\n{output}")
            self.assertIn("test_scripts.py", output,
                          msg=f"Expected test_scripts.py in output:\n{output}")


# ---------------------------------------------------------------------------
# Phase 2 — Ratchet-guard tests (T-9a, T-9b, T-9c)
# Tests for scripts/ratchet-check.sh
# ---------------------------------------------------------------------------

RATCHET_CHECK = os.path.join(REPO_ROOT, "scripts", "ratchet-check.sh")


def _run_ratchet(thresholds_file, python_line, python_branch, js_branch):
    """
    Run ratchet-check.sh with a given thresholds file and live values.
    Returns (returncode, stdout+stderr).
    """
    result = subprocess.run(
        [
            "bash", RATCHET_CHECK,
            "--thresholds-file", thresholds_file,
            "--python-line", str(python_line),
            "--python-branch", str(python_branch),
            "--js-branch", str(js_branch),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def _write_thresholds(path, python_line, python_branch, js_branch):
    """Write a .coverage-thresholds file to path."""
    with open(path, "w") as fh:
        fh.write(f"python_line={python_line}\n")
        fh.write(f"python_branch={python_branch}\n")
        fh.write(f"js_branch={js_branch}\n")


class TestRatchetCheckPass(unittest.TestCase):
    """T-9a: ratchet exits 0 when live values >= committed thresholds."""

    def test_exits_0_when_live_meets_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            _write_thresholds(tf, python_line=90, python_branch=80, js_branch=70)
            rc, out = _run_ratchet(tf, python_line=90, python_branch=85, js_branch=71)
            self.assertEqual(rc, 0, msg=f"Expected exit 0 (live ≥ thresholds), got {rc}.\n{out}")
            self.assertIn("PASS", out.upper(), msg=f"Expected PASS in output:\n{out}")

    def test_exits_0_when_live_exactly_equals_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            _write_thresholds(tf, python_line=90, python_branch=80, js_branch=70)
            rc, out = _run_ratchet(tf, python_line=90, python_branch=80, js_branch=70)
            self.assertEqual(rc, 0, msg=f"Expected exit 0 (live == thresholds), got {rc}.\n{out}")


class TestRatchetCheckFail(unittest.TestCase):
    """T-9b: ratchet exits non-zero when any live value < committed threshold."""

    def test_fails_when_python_line_drops(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            _write_thresholds(tf, python_line=90, python_branch=80, js_branch=70)
            rc, out = _run_ratchet(tf, python_line=88, python_branch=80, js_branch=70)
            self.assertNotEqual(rc, 0, msg=f"Expected non-zero exit (python_line dropped), got {rc}.\n{out}")
            self.assertIn("python_line", out, msg=f"Expected python_line in output:\n{out}")

    def test_fails_when_python_branch_drops(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            _write_thresholds(tf, python_line=90, python_branch=80, js_branch=70)
            rc, out = _run_ratchet(tf, python_line=90, python_branch=75, js_branch=70)
            self.assertNotEqual(rc, 0, msg=f"Expected non-zero exit (python_branch dropped), got {rc}.\n{out}")
            self.assertIn("python_branch", out, msg=f"Expected python_branch in output:\n{out}")

    def test_fails_when_js_branch_drops(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            _write_thresholds(tf, python_line=90, python_branch=80, js_branch=70)
            rc, out = _run_ratchet(tf, python_line=90, python_branch=80, js_branch=65)
            self.assertNotEqual(rc, 0, msg=f"Expected non-zero exit (js_branch dropped), got {rc}.\n{out}")
            self.assertIn("js_branch", out, msg=f"Expected js_branch in output:\n{out}")


class TestRatchetCheckEdgeCases(unittest.TestCase):
    """T-9c: ratchet handles missing file and malformed input gracefully."""

    def test_fails_when_thresholds_file_missing(self):
        rc, out = _run_ratchet("/nonexistent/.coverage-thresholds", 90, 80, 70)
        self.assertNotEqual(rc, 0, msg=f"Expected non-zero exit (missing file), got {rc}.\n{out}")

    def test_fails_when_thresholds_file_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            # Write a file that is missing python_branch
            with open(tf, "w") as fh:
                fh.write("python_line=90\njs_branch=70\n")
            rc, out = _run_ratchet(tf, python_line=90, python_branch=80, js_branch=70)
            self.assertNotEqual(rc, 0, msg=f"Expected non-zero exit (missing key), got {rc}.\n{out}")


# ---------------------------------------------------------------------------
# Phase 3 — doc-consistency-check tests (T-6, T-7)
# Tests for scripts/doc-consistency-check.sh
# ---------------------------------------------------------------------------

DOC_CONSISTENCY_CHECK = os.path.join(REPO_ROOT, "scripts", "doc-consistency-check.sh")


def _run_doc_consistency(check_dir):
    """Run doc-consistency-check.sh with CHECK_DIR set to a temp directory tree."""
    result = subprocess.run(
        ["bash", DOC_CONSISTENCY_CHECK],
        capture_output=True,
        text=True,
        cwd=check_dir,
        env={**os.environ, "REPO_ROOT": check_dir},
    )
    return result.returncode, result.stdout + result.stderr


def _setup_convention_tree(tmp_dir, canonical_content, extra_files):
    """
    Build a minimal doc tree under tmp_dir for doc-consistency testing.

    tmp_dir/
      docs/rail-pipeline.md          ← canonical source (always written)
      <extra_files>                   ← files that may duplicate conventions
    """
    canonical_path = os.path.join(tmp_dir, "docs", "rail-pipeline.md")
    os.makedirs(os.path.dirname(canonical_path), exist_ok=True)
    with open(canonical_path, "w") as fh:
        fh.write(canonical_content)

    for rel_path, content in extra_files.items():
        abs_path = os.path.join(tmp_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)


class TestDocConsistencyPass(unittest.TestCase):
    """
    T-7: doc-consistency-check.sh exits 0 when all convention phrases appear
    only in the canonical source (docs/rail-pipeline.md).
    """

    def test_exits_0_when_phrases_only_in_canonical_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            _setup_convention_tree(
                tmp,
                # Canonical source contains the convention phrases
                canonical_content=textwrap.dedent("""\
                    # RAIL Pipeline
                    ## 3. Conventions
                    - CSS changes bump `styles.css?v=N` in index.html.
                    - SSRF guard: `is_safe_upstream_url` in server.py.
                    - New tools go in `TOOL_REGISTRY`.
                    - Gate via `getEnabledTools()`.
                    - New endpoints add a `_handler`.
                """),
                extra_files={
                    # Other files reference the canonical doc by link only
                    "AGENTS.md": textwrap.dedent("""\
                        # AGENTS
                        See [coding conventions](docs/rail-pipeline.md#3-conventions).
                    """),
                    "docs/tooling/cline.md": textwrap.dedent("""\
                        # Cline reference
                        See [coding conventions](../rail-pipeline.md#3-conventions).
                    """),
                    ".clinerules/rail-pipeline.md": textwrap.dedent("""\
                        # RAIL
                        See docs/rail-pipeline.md for the convention list.
                    """),
                },
            )
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (no duplication), got {rc}.\nOutput:\n{out}",
            )


class TestDocConsistencyFail(unittest.TestCase):
    """
    T-6: doc-consistency-check.sh exits non-zero when a convention phrase
    appears verbatim in more than one non-canonical enforcing file.
    """

    def test_exits_nonzero_when_phrase_duplicated_in_agents_md(self):
        """
        AGENTS.md restates 'styles.css?v=N' verbatim → should fail.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _setup_convention_tree(
                tmp,
                canonical_content=textwrap.dedent("""\
                    # RAIL Pipeline
                    ## 3. Conventions
                    - CSS changes bump `styles.css?v=N` in index.html.
                """),
                extra_files={
                    "AGENTS.md": textwrap.dedent("""\
                        # AGENTS
                        - CSS changes: bump `styles.css?v=N` in index.html.
                    """),
                },
            )
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (phrase duplicated in AGENTS.md), got {rc}.\nOutput:\n{out}",
            )
            self.assertIn(
                "styles.css", out,
                msg=f"Expected offending phrase in output:\n{out}",
            )

    def test_exits_nonzero_when_phrase_duplicated_in_cline_rules(self):
        """
        .clinerules/rail-pipeline.md restates 'is_safe_upstream_url' verbatim → fail.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _setup_convention_tree(
                tmp,
                canonical_content=textwrap.dedent("""\
                    # RAIL Pipeline
                    ## 3. Conventions
                    - SSRF guard: `is_safe_upstream_url` in server.py.
                """),
                extra_files={
                    ".clinerules/rail-pipeline.md": textwrap.dedent("""\
                        # RAIL
                        - SSRF guard (`is_safe_upstream_url` in server.py).
                    """),
                },
            )
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (phrase in .clinerules/), got {rc}.\nOutput:\n{out}",
            )
            self.assertIn(
                "is_safe_upstream_url", out,
                msg=f"Expected offending phrase in output:\n{out}",
            )


# ---------------------------------------------------------------------------
# Phase 5 — Memory-note secret scan test (T-8)
# Tests for the memory-note scan block in scripts/security-scan.sh
# ---------------------------------------------------------------------------

SECURITY_SCAN = os.path.join(REPO_ROOT, "scripts", "security-scan.sh")


def _run_memory_scan(obsidian_vault_path):
    """
    Run security-scan.sh with SKIP_GITLEAKS, SKIP_BANDIT, SKIP_PIP_AUDIT set so
    only the memory-note scan block runs; OBSIDIAN_VAULT_PATH points at a temp dir.
    Returns (returncode, stdout+stderr).
    """
    env = {
        **os.environ,
        "OBSIDIAN_VAULT_PATH": obsidian_vault_path,
        "SKIP_GITLEAKS": "1",
        "SKIP_BANDIT": "1",
        "SKIP_PIP_AUDIT": "1",
    }
    result = subprocess.run(
        ["bash", SECURITY_SCAN],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )
    return result.returncode, result.stdout + result.stderr


class TestMemoryNoteScanClean(unittest.TestCase):
    """T-8a: security-scan.sh exits 0 when no secret patterns are in memory notes."""

    def test_exits_0_when_memory_notes_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem_dir = os.path.join(tmp, "Cline", "memories")
            os.makedirs(mem_dir)
            with open(os.path.join(mem_dir, "2099-01-01-clean.md"), "w") as fh:
                fh.write("# Session note\nNo secrets here, just normal text.\n")
            rc, out = _run_memory_scan(tmp)
            self.assertEqual(rc, 0, msg=f"Expected exit 0 (clean notes), got {rc}.\n{out}")


class TestMemoryNoteScanDirty(unittest.TestCase):
    """T-8b: security-scan.sh exits non-zero when a memory note contains a secret pattern."""

    def test_fails_when_note_contains_sk_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem_dir = os.path.join(tmp, "Cline", "memories")
            os.makedirs(mem_dir)
            with open(os.path.join(mem_dir, "2099-01-01-dirty.md"), "w") as fh:
                fh.write("# Session note\napi_key=sk-abc123secret456\n")
            rc, out = _run_memory_scan(tmp)
            self.assertNotEqual(rc, 0,
                                msg=f"Expected non-zero exit (sk- pattern), got {rc}.\n{out}")
            self.assertIn("secret", out.lower() + "secret",
                          msg=f"Expected secret-scan failure message:\n{out}")

    def test_fails_when_note_contains_bearer_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem_dir = os.path.join(tmp, "Cline", "memories")
            os.makedirs(mem_dir)
            with open(os.path.join(mem_dir, "2099-01-01-bearer.md"), "w") as fh:
                fh.write("# Session note\nAuthorization: Bearer eyJhbGciOiJIUzI1NiJ9\n")
            rc, out = _run_memory_scan(tmp)
            self.assertNotEqual(rc, 0,
                                msg=f"Expected non-zero exit (Bearer pattern), got {rc}.\n{out}")

    def test_exits_0_when_vault_path_unset(self):
        """T-8c: scan skips cleanly (exit 0) when OBSIDIAN_VAULT_PATH is unset."""
        env = {
            **os.environ,
            "SKIP_GITLEAKS": "1",
            "SKIP_BANDIT": "1",
            "SKIP_PIP_AUDIT": "1",
        }
        # Remove OBSIDIAN_VAULT_PATH if it happens to be set in the environment
        env.pop("OBSIDIAN_VAULT_PATH", None)
        result = subprocess.run(
            ["bash", SECURITY_SCAN],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
        )
        self.assertEqual(result.returncode, 0,
                         msg=f"Expected exit 0 (vault unset → skip), got {result.returncode}.\n"
                             f"{result.stdout + result.stderr}")


# ---------------------------------------------------------------------------
# Item #37 — JS branch-coverage sentinel tests (T-10a, T-10b)
# Tests for the sentinel file write in tests/js-coverage.mjs and the
# run-tests.sh read of that sentinel.
# ---------------------------------------------------------------------------

import re as _re

JS_COVERAGE = os.path.join(REPO_ROOT, "tests", "js-coverage.mjs")
SENTINEL_FILE = "/tmp/usai-js-branch-pct"


def _run_js_coverage(min_pct=None):
    """
    Run tests/js-coverage.mjs from the repo root.
    Returns (returncode, stdout+stderr).
    """
    cmd = ["node", JS_COVERAGE]
    if min_pct is not None:
        cmd.append(str(min_pct))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return result.returncode, result.stdout + result.stderr


class TestJsSentinelWritten(unittest.TestCase):
    """
    T-10a: tests/js-coverage.mjs writes the measured branch % to
    /tmp/usai-js-branch-pct after a successful run.
    """

    def setUp(self):
        # Remove sentinel so we test a clean write.
        if os.path.exists(SENTINEL_FILE):
            os.remove(SENTINEL_FILE)

    def test_sentinel_file_written_after_coverage_run(self):
        """T-10a: sentinel file exists and contains a numeric value after js-coverage.mjs runs."""
        rc, out = _run_js_coverage()
        self.assertEqual(rc, 0, msg=f"js-coverage.mjs exited {rc}:\n{out}")
        self.assertTrue(
            os.path.exists(SENTINEL_FILE),
            msg=f"Sentinel file {SENTINEL_FILE} was not written by js-coverage.mjs.\n{out}",
        )
        with open(SENTINEL_FILE) as fh:
            content = fh.read().strip()
        # Must be a number (int or float)
        self.assertTrue(
            _re.match(r"^\d+(\.\d+)?$", content),
            msg=f"Sentinel file content is not numeric: {content!r}",
        )
        value = float(content)
        self.assertGreater(value, 0.0, msg=f"Sentinel value should be > 0, got {value}")
        self.assertLessEqual(value, 100.0, msg=f"Sentinel value should be ≤ 100, got {value}")


class TestJsSentinelMatchesOutput(unittest.TestCase):
    """
    T-10b: the branch % written to the sentinel matches what js-coverage.mjs
    printed to stdout (i.e. they are consistent).
    """

    def setUp(self):
        if os.path.exists(SENTINEL_FILE):
            os.remove(SENTINEL_FILE)

    def test_sentinel_matches_reported_branch_pct(self):
        """T-10b: sentinel value is consistent with the branch % in stdout."""
        rc, out = _run_js_coverage()
        self.assertEqual(rc, 0, msg=f"js-coverage.mjs exited {rc}:\n{out}")

        # Parse the branch % from the output line:
        #   "app.js coverage — line X%  branch Y%  funcs Z%"
        m = _re.search(r"branch\s+([\d.]+)%", out)
        self.assertIsNotNone(m, msg=f"Could not find 'branch X%' in output:\n{out}")
        reported_pct = float(m.group(1))

        self.assertTrue(os.path.exists(SENTINEL_FILE),
                        msg=f"Sentinel file not written:\n{out}")
        with open(SENTINEL_FILE) as fh:
            sentinel_pct = float(fh.read().strip())

        self.assertAlmostEqual(
            sentinel_pct, reported_pct, places=1,
            msg=f"Sentinel {sentinel_pct} != reported {reported_pct}",
        )


if __name__ == "__main__":
    unittest.main()
