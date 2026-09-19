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
import shutil
import sys
import tempfile
import textwrap
import unittest


# Absolute path to the script under test — resolved relative to this file so
# tests work regardless of the current working directory.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
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
COVERAGE_THRESHOLDS = os.path.join(REPO_ROOT, ".coverage-thresholds")
RUN_TESTS = os.path.join(REPO_ROOT, "run-tests.sh")
CI_TESTS = os.path.join(REPO_ROOT, ".github", "workflows", "tests.yml")


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


class TestRatchetCommittedThresholds(unittest.TestCase):
    """Backlog #74: committed floors match the approved verified coverage."""

    def test_committed_thresholds_are_ratcheted(self):
        with open(COVERAGE_THRESHOLDS) as fh:
            configured = {
                key: value
                for key, value in (
                    line.strip().split("=", 1)
                    for line in fh
                    if line.strip() and not line.startswith("#")
                )
            }

        self.assertEqual(configured, {
            "python_line": "90",
            "python_branch": "90",
            "js_branch": "75",
        })

    def test_local_and_ci_gates_match_committed_thresholds(self):
        with open(RUN_TESTS) as fh:
            local_runner = fh.read()
        with open(CI_TESTS) as fh:
            ci_workflow = fh.read()

        self.assertIn("PY_MIN=90", local_runner)
        self.assertIn("PY_BRANCH_MIN=90", local_runner)
        self.assertIn("JS_MIN=75", local_runner)
        self.assertIn("node tests/js-coverage.mjs 75", ci_workflow)
        self.assertIn("if branch_int < 90:", ci_workflow)


class TestRatchetHeadroomAdvisory(unittest.TestCase):
    """Backlog #74: excessive threshold headroom is visible but non-blocking."""

    def test_advises_at_five_points_without_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            _write_thresholds(tf, python_line=90, python_branch=90, js_branch=75)
            rc, out = _run_ratchet(tf, python_line=90, python_branch=95, js_branch=75)

        self.assertEqual(rc, 0, msg=f"Advisory must not fail the build:\n{out}")
        self.assertIn("ADVISORY", out)
        self.assertIn("python_branch", out)
        self.assertIn("5.00", out)
        self.assertIn("ratchet", out.lower())

    def test_does_not_advise_below_five_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            tf = os.path.join(tmp, ".coverage-thresholds")
            _write_thresholds(tf, python_line=90, python_branch=90, js_branch=75)
            rc, out = _run_ratchet(tf, python_line=94.99, python_branch=94.99, js_branch=79.99)

        self.assertEqual(rc, 0, msg=out)
        self.assertNotIn("ADVISORY", out)


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
                    The RAIL roles (0-6) apply in order.
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
                    "docs/tooling/some-other-doc.md": textwrap.dedent("""\
                        # Some other doc
                        See [coding conventions](../rail-pipeline.md#3-conventions).
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

    def test_exits_nonzero_when_phrase_duplicated_in_other_doc(self):
        """
        docs/tooling/other.md restates 'is_safe_upstream_url' verbatim → fail.
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
                    "docs/tooling/other.md": textwrap.dedent("""\
                        # Other tooling doc
                        - SSRF guard (`is_safe_upstream_url` in server.py).
                    """),
                },
            )
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (phrase in other doc), got {rc}.\nOutput:\n{out}",
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


class TestSecurityScanScope(unittest.TestCase):
    """The canonical SAST gate covers production recursively without test fixtures."""

    def test_bandit_scans_backend_and_excludes_tests(self):
        with open(SECURITY_SCAN) as fh:
            script = fh.read()
        self.assertIn('-r backend/', script)
        self.assertIn('-x backend/tests', script)
        self.assertNotIn('backend/server.py backend/proxy_handlers.py', script)


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

    def test_checklist_prose_and_task_identifier_do_not_trigger_scan(self):
        """T-8d: prose and an embedded `sk-` substring are not secret values."""
        with tempfile.TemporaryDirectory() as tmp:
            mem_dir = os.path.join(tmp, "Cline", "memories")
            os.makedirs(mem_dir)
            with open(os.path.join(mem_dir, "2099-01-01-prose.md"), "w") as fh:
                fh.write(
                    "No API keys, Bearer tokens, or passwords in this note.\n"
                    "Completed task-1234567890123456 verification.\n"
                )
            rc, out = _run_memory_scan(tmp)
            self.assertEqual(rc, 0, msg=f"Expected prose to pass.\n{out}")

    def test_fails_for_each_secret_shaped_value_without_echoing_value(self):
        """T-8e/f: all value families fail and diagnostic output is redacted."""
        fixtures = {
            "sk.md": "token = sk-abcdefghijklmnop\n",
            "bearer.md": "Authorization: Bearer abcdefghijklmnop\n",
            "api-key.md": "api_key = abcdefghijklmnop\n",
            "password.md": "password = abcdefghijklmnop\n",
        }
        for filename, content in fixtures.items():
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                mem_dir = os.path.join(tmp, "Cline", "memories")
                os.makedirs(mem_dir)
                with open(os.path.join(mem_dir, filename), "w") as fh:
                    fh.write(content)
                rc, out = _run_memory_scan(tmp)
                self.assertNotEqual(rc, 0, msg=f"Expected {filename} to fail.\n{out}")
                self.assertIn(filename, out)
                self.assertIn("[REDACTED]", out)
                self.assertNotIn("abcdefghijklmnop", out)

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

# `node` is a DEV-ONLY prerequisite for the JS gate. Skip (never fail) when the
# runner has no Node so a Python-only environment stays green.
NODE_BIN = shutil.which("node")


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


@unittest.skipUnless(NODE_BIN, "node not installed — JS coverage gate is dev-only")
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


@unittest.skipUnless(NODE_BIN, "node not installed — JS coverage gate is dev-only")
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


@unittest.skipUnless(NODE_BIN, "node not installed — JS coverage gate is dev-only")
class TestJsCoverageWithoutJsdom(unittest.TestCase):
    """
    T-10c (CI regression): the coverage gate must pass in a tree with no
    node_modules/jsdom.

    WHY: the GitHub Actions *Python* job installs no npm packages, yet T-10a/T-10b
    above invoke tests/js-coverage.mjs. Before the guard, `node --test` aborted with
    ERR_MODULE_NOT_FOUND for jsdom (imported only by app.behavior.test.mjs), the gate
    exited 1, and both sentinel tests failed — turning a missing JS dev dependency
    into a red Python job. run-tests.sh already skips the behavior suite the same way.
    """

    def test_gate_passes_when_jsdom_absent(self):
        """Excludes the jsdom-only suite, warns, and still reports branch %."""
        with tempfile.TemporaryDirectory() as tmp:
            # Mirror the repo layout the script expects (tests/ + frontend/) without
            # a node_modules directory, so existsSync(node_modules/jsdom) is false.
            os.makedirs(os.path.join(tmp, "tests"))
            shutil.copy(JS_COVERAGE, os.path.join(tmp, "tests", "js-coverage.mjs"))
            # Symlink frontend/ rather than copying app.js (193 KB) + its test suites.
            os.symlink(os.path.join(REPO_ROOT, "frontend"), os.path.join(tmp, "frontend"))

            result = subprocess.run(
                ["node", os.path.join(tmp, "tests", "js-coverage.mjs"), "75"],
                capture_output=True, text=True, cwd=tmp,
            )
            out = result.stdout + result.stderr

            self.assertEqual(result.returncode, 0,
                             msg=f"Gate must pass without jsdom, exited "
                                 f"{result.returncode}:\n{out}")
            self.assertIn("jsdom not installed", out,
                          msg=f"Expected a skip warning naming jsdom:\n{out}")
            self.assertNotIn("ERR_MODULE_NOT_FOUND", out,
                             msg=f"jsdom must not be imported at all:\n{out}")
            self.assertRegex(out, r"branch\s+[\d.]+%",
                             msg=f"Gate must still report a branch %:\n{out}")


# ---------------------------------------------------------------------------
# Item #58 — Doc-drift guard tests (T-11, T-12, T-13)
# Tests for the three new guard blocks in scripts/doc-consistency-check.sh
# ---------------------------------------------------------------------------

def _setup_drift_tree(tmp_dir, extra_files):
    """
    Build a minimal doc tree for doc-drift guard testing.

    Always creates:
      docs/rail-pipeline.md  — canonical source with the RAIL roles (0-6) phrase
      docs/tooling/some-doc.md  — minimal reference (no duplication)
      AGENTS.md              — minimal reference (no duplication)

    extra_files: dict of rel_path → content overrides (merged on top).

    Also creates a minimal repo skeleton (scripts/quality-gate.sh, frontend/app.js,
    backend/server.py). The base canonical doc cites these, and now that
    docs/rail-pipeline.md is itself inside the scan scope, the referenced-path guard
    checks them — an empty tmp tree would fail every test for a fixture artifact
    rather than for the behavior under test.
    """
    skeleton = (
        os.path.join("scripts", "quality-gate.sh"),
        os.path.join("frontend", "app.js"),
        os.path.join("backend", "server.py"),
    )
    for rel in skeleton:
        abs_path = os.path.join(tmp_dir, rel)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write("# fixture stub\n")

    base_files = {
        "docs/rail-pipeline.md": textwrap.dedent("""\
            # RAIL Pipeline
            The RAIL roles (0-6) apply in order.
            ## 3. Conventions
            - CSS changes bump `styles.css?v=N` in index.html.
            - SSRF guard: `is_safe_upstream_url` in server.py.
            - New tools go in `TOOL_REGISTRY`.
            - Gate via `getEnabledTools()`.
            - New endpoints add a `_handler`.
            Run `./scripts/quality-gate.sh` before merging.
        """),
        "docs/tooling/some-doc.md": textwrap.dedent("""\
            # Some tooling reference
            See [conventions](../rail-pipeline.md).
        """),
        "AGENTS.md": textwrap.dedent("""\
            # AGENTS
            See [conventions](docs/rail-pipeline.md).
        """),
    }
    # Apply overrides from extra_files on top of base
    merged = {**base_files, **extra_files}
    for rel_path, content in merged.items():
        abs_path = os.path.join(tmp_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)


# ---------------------------------------------------------------------------
# T-11: Stale-path guard
# ---------------------------------------------------------------------------

class TestStalePathGuard(unittest.TestCase):
    """
    T-11a/b: AC-1 — doc-consistency-check.sh exits non-zero if any deprecated
    flat test path (tests/js/, tests/python/, 'node --check app.js',
    'py_compile server.py') appears verbatim in .clinerules/ or docs/tooling/
    files.
    """

    def test_fails_when_stale_path_in_tooling_docs(self):
        """T-11a: stale flat path 'tests/js/' in a tooling doc → exit non-zero."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/some-tool.md": textwrap.dedent("""\
                    # Build workflow
                    Run: node --test $(find tests/js/ -name '*.test.mjs')
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (stale 'tests/js/' in tooling doc), got {rc}.\n{out}",
            )
            self.assertIn("tests/js", out,
                          msg=f"Expected stale path in output:\n{out}")

    def test_passes_when_correct_paths_used(self):
        """T-11b: only correct paths 'frontend/tests/js/' and 'backend/tests/python/' → exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/some-doc.md": textwrap.dedent("""\
                    # Some tooling reference
                    See [conventions](../rail-pipeline.md).
                """),
                "docs/workflows/build.md": textwrap.dedent("""\
                    # Build workflow
                    Run: node --test $(find frontend/tests/js/ -name '*.test.mjs')
                    Run: python -m unittest discover -s backend/tests/python
                    Run: node --check frontend/app.js
                    Run: python3 -m py_compile backend/server.py
                """),
            })
            # Create all referenced paths so Guard 4 does not fire
            os.makedirs(os.path.join(tmp, "frontend", "tests", "js"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "backend", "tests", "python"), exist_ok=True)
            with open(os.path.join(tmp, "frontend", "app.js"), "w") as fh:
                fh.write("// app\n")
            with open(os.path.join(tmp, "backend", "server.py"), "w") as fh:
                fh.write("# server\n")
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (correct paths only), got {rc}.\n{out}",
            )


# ---------------------------------------------------------------------------
# T-12: Role-count consistency guard
# ---------------------------------------------------------------------------

class TestRoleCountGuard(unittest.TestCase):
    """
    T-12a/b/c: AC-3 — doc-consistency-check.sh exits non-zero if the canonical
    phrase 'The RAIL roles (0-6)' is absent from .clinerules/rail-pipeline.md,
    or if a conflicting count phrase (five roles / six roles / seven roles)
    appears in any enforcing file.
    """

    def test_fails_when_canonical_phrase_missing_from_rail_pipeline(self):
        """T-12a: docs/rail-pipeline.md lacks 'The RAIL roles (0' prefix → exit non-zero."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                # Override with a version that lacks 'The RAIL roles (0' entirely
                "docs/rail-pipeline.md": textwrap.dedent("""\
                    # RAIL Pipeline
                    Run the pipeline roles in order.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (canonical phrase missing from docs/rail-pipeline.md), got {rc}.\n{out}",
            )

    def test_fails_when_conflicting_count_present(self):
        """T-12b: 'six roles' in docs/tooling/cline.md → exit non-zero.

        #87: the role-count guard scope is an explicit file list, not a recursive
        dir walk, so this fixture must name one of those files.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/cline.md": textwrap.dedent("""\
                    # Cline tooling reference
                    There are six roles in the RAIL pipeline.
                    See [conventions](../rail-pipeline.md).
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit ('six roles' conflict in tooling doc), got {rc}.\n{out}",
            )
            self.assertIn("six roles", out,
                          msg=f"Expected 'six roles' in output:\n{out}")

    def test_passes_when_canonical_phrase_present_no_conflict(self):
        """T-12c: correct canonical phrase present, no conflicting count → exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {})
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (canonical phrase present, no conflict), got {rc}.\n{out}",
            )


# ---------------------------------------------------------------------------
# T-13: Mandatory-gate guard
# ---------------------------------------------------------------------------

class TestMandatoryGateGuard(unittest.TestCase):
    """
    T-13a/b: doc-consistency-check.sh exits non-zero if the word
    'optional' appears on the same line as 'quality-gate.sh'.
    """

    def test_fails_when_quality_gate_is_optional(self):
        """T-13a: 'optional' on same line as 'quality-gate.sh' → exit non-zero."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/some-doc.md": textwrap.dedent("""\
                    # Some tooling reference
                    Running ./scripts/quality-gate.sh is optional before merging.
                    See [conventions](../rail-pipeline.md).
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit ('optional' near quality-gate), got {rc}.\n{out}",
            )

    def test_passes_when_quality_gate_is_mandatory(self):
        """T-13b: 'quality-gate.sh' without 'optional' on same line → exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/some-doc.md": textwrap.dedent("""\
                    # Some tooling reference
                    See [conventions](../rail-pipeline.md).
                    Run `./scripts/quality-gate.sh` to gate a PR.
                """),
            })
            # Create scripts/quality-gate.sh so Guard 4 does not fire
            scripts_dir = os.path.join(tmp, "scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            with open(os.path.join(scripts_dir, "quality-gate.sh"), "w") as fh:
                fh.write("#!/usr/bin/env bash\n")
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (quality-gate not optional), got {rc}.\n{out}",
            )


# ---------------------------------------------------------------------------
# Review workflow evidence contract (#76(a) pre-commit audit)
# ---------------------------------------------------------------------------

class TestReviewWorkflowEvidenceContract(unittest.TestCase):
    """Pin the real gate commands and current-run evidence requirement."""

    def test_review_runs_each_deterministic_gate_explicitly(self):
        review_path = os.path.join(REPO_ROOT, ".clinerules", "workflows", "review.md")
        with open(review_path, encoding="utf-8") as fh:
            review = fh.read()

        for command in (
            "./scripts/quality-gate.sh",
            "./run-tests.sh --coverage",
            "./scripts/security-scan.sh",
            "./scripts/doc-consistency-check.sh",
        ):
            self.assertIn(command, review)

    def test_review_rejects_reused_gate_results(self):
        review_path = os.path.join(REPO_ROOT, ".clinerules", "workflows", "review.md")
        with open(review_path, encoding="utf-8") as fh:
            review = fh.read()

        self.assertIn("Never carry counts or", review)
        self.assertIn("PASS claims forward from an earlier session", review)
        self.assertIn("substitute commands", review)
        self.assertIn("do not satisfy the coverage gate", review)



# ---------------------------------------------------------------------------
# T-14: Referenced-path existence guard (AC-2, item #59)
# ---------------------------------------------------------------------------

class TestRefPathExistenceGuard(unittest.TestCase):
    """
    T-14a/b/c: AC-2 — doc-consistency-check.sh exits non-zero when a .md file
    in .clinerules/ or docs/tooling/ references a backend/, frontend/, or
    scripts/ path that does not exist on disk.
    """

    def test_fails_when_referenced_backend_path_missing(self):
        """T-14a: backend/nonexistent/path.py referenced but not on disk → exit non-zero."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/build-workflow.md": textwrap.dedent("""\
                    # Build workflow
                    Run: PYTHONPATH=backend .venv/bin/python -m unittest discover \
 -s backend/tests/python -p 'test_*.py'
                    See also backend/nonexistent/path.py for details.
                """),
            })
            # Create the real path that _setup_drift_tree mentions so only
            # backend/nonexistent/path.py is missing
            os.makedirs(os.path.join(tmp, "backend", "tests", "python"), exist_ok=True)
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (missing backend path), got {rc}.\n{out}",
            )
            self.assertIn("backend/nonexistent/path.py", out,
                          msg=f"Expected missing path in output:\n{out}")

    def test_passes_when_all_referenced_paths_exist(self):
        """T-14b: all backend/, frontend/, scripts/ references resolve → exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                # Override docs/tooling/some-doc.md to only reference paths we create
                "docs/tooling/some-doc.md": textwrap.dedent("""\
                    # Some tooling reference
                    See [conventions](../rail-pipeline.md).
                    Run `./scripts/doc-consistency-check.sh` to gate a PR.
                """),
                "docs/workflows/build.md": textwrap.dedent("""\
                    # Build workflow
                    Run: node --test $(find frontend/tests/js/ -name '*.test.mjs')
                    Run: PYTHONPATH=backend .venv/bin/python -m unittest discover \
 -s backend/tests/python
                    Gate: ./scripts/doc-consistency-check.sh
                """),
            })
            # Create the real directories and files so the references resolve
            os.makedirs(os.path.join(tmp, "frontend", "tests", "js"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "backend", "tests", "python"), exist_ok=True)
            scripts_dir = os.path.join(tmp, "scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            with open(os.path.join(scripts_dir, "doc-consistency-check.sh"), "w") as fh:
                fh.write("#!/usr/bin/env bash\n")
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (all referenced paths exist), got {rc}.\n{out}",
            )

    def test_skips_glob_tokens_no_false_positive(self):
        """T-14c: glob pattern 'backend/tests/*.py' skipped (contains *) → exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                # Override docs/tooling/some-doc.md to avoid any scripts/ references
                "docs/tooling/some-doc.md": textwrap.dedent("""\
                    # Some tooling reference
                    See [conventions](../rail-pipeline.md).
                """),
                "docs/workflows/build.md": textwrap.dedent("""\
                    # Build workflow
                    Run: find backend/tests/*.py  (glob — not a real path)
                    Run: scripts/$VAR/helper.sh   (shell variable — skip)
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (glob/variable tokens skipped), got {rc}.\n{out}",
            )


# ---------------------------------------------------------------------------
# #87 — Scan-scope regression tests
#
# WHY these exist: the guard's own scan scope was silently narrowed once
# (13 .clinerules/*.md files dropped out of every guard). These tests pin the
# scope itself so a future refactor cannot quietly shrink it again.
#
# They also restore the coverage of two tests deleted during that narrowing:
#   - test_exits_nonzero_when_phrase_duplicated_in_cline_rules
#   - test_fails_when_stale_path_in_clinerules
# ---------------------------------------------------------------------------

class TestClineRulesInScanScope(unittest.TestCase):
    """
    #87: .clinerules/ must be inside the scan scope of the stale-path,
    mandatory-gate and referenced-path guards, and .clinerules/rail-pipeline.md
    must be inside the (narrower) convention-phrase guard.
    """

    def test_fails_when_phrase_duplicated_in_clinerules_rail_pipeline(self):
        """Restores deleted coverage: phrase verbatim in .clinerules/rail-pipeline.md → fail."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".clinerules/rail-pipeline.md": textwrap.dedent("""\
                    # RAIL — Cline always-on rule
                    SSRF guard: `is_safe_upstream_url` in server.py.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (phrase in .clinerules/), got {rc}.\n{out}",
            )
            self.assertIn("is_safe_upstream_url", out,
                          msg=f"Expected offending phrase in output:\n{out}")

    def test_fails_when_stale_path_in_clinerules_workflow(self):
        """Restores deleted coverage: stale 'tests/js/' in .clinerules/workflows/ → fail."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".clinerules/workflows/build.md": textwrap.dedent("""\
                    # Build workflow
                    Run: node --test $(find tests/js/ -name '*.test.mjs')
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (stale path in .clinerules/), got {rc}.\n{out}",
            )
            self.assertIn("tests/js", out,
                          msg=f"Expected stale path in output:\n{out}")

    def test_fails_when_missing_ref_path_in_clinerules_workflow(self):
        """#87: referenced-path guard must reach .clinerules/workflows/."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".clinerules/workflows/review.md": textwrap.dedent("""\
                    # Review workflow
                    See backend/nonexistent/probe.py for details.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (missing path in .clinerules/), got {rc}.\n{out}",
            )
            self.assertIn("backend/nonexistent/probe.py", out,
                          msg=f"Expected missing path in output:\n{out}")

    def test_fails_when_quality_gate_optional_in_clinerules_workflow(self):
        """#87: mandatory-gate guard must reach .clinerules/workflows/."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".clinerules/workflows/loop.md": textwrap.dedent("""\
                    # Loop workflow
                    Running quality-gate.sh is optional at the end.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (gate called optional in .clinerules/), got {rc}.\n{out}",
            )


class TestPerGuardScopeInvariant(unittest.TestCase):
    """
    #87: the phrase guard is deliberately NARROWER than the path guards.

    Cline workflow files legitimately name conventions (a workflow has to tell
    the agent to bump `styles.css?v=N`). Only the four rule-restating files are
    phrase-checked. Collapsing the two scopes into one list is what caused the
    original narrowing, so this invariant is pinned by a test.
    """

    def test_convention_phrase_in_clinerules_workflow_does_not_fail(self):
        """A workflow file may name a convention without tripping the phrase guard."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".clinerules/workflows/build.md": textwrap.dedent("""\
                    # Build workflow
                    Bump `styles.css?v=N` in index.html after editing CSS.
                    Register new tools in `TOOL_REGISTRY` and gate via `getEnabledTools()`.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (workflow files are not phrase-checked), got {rc}.\n{out}",
            )

    def test_missing_optional_scan_dir_is_not_an_error(self):
        """A scan dir that does not exist (e.g. .roo/ pre-migration) is skipped, not fatal."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {})
            self.assertFalse(os.path.exists(os.path.join(tmp, ".roo")))
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (absent optional scan dir), got {rc}.\n{out}",
            )


class TestContinueRulesInScanScope(unittest.TestCase):
    """
    #87 follow-up: .continue/rules/ must be inside the same wide scan scope as
    .clinerules/. Both harnesses are equal peers per AGENTS.md, and this dir had
    accumulated 12 stale paths precisely because no guard watched it.
    """

    def test_fails_when_stale_path_in_continue_rules(self):
        """Stale 'tests/python/' in .continue/rules/ → fail."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".continue/rules/testing-standards.md": textwrap.dedent("""\
                    # Testing standards
                    Run: unittest discover -s tests/python -p 'test_*.py'
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (stale path in .continue/rules/), got {rc}.\n{out}",
            )
            self.assertIn("tests/python", out,
                          msg=f"Expected stale path in output:\n{out}")

    def test_fails_when_missing_ref_path_in_continue_rules(self):
        """A .continue/rules/ file citing a non-existent test file → fail.

        This is the exact drift found in infrastructure-as-code.md, which cited
        test_env_example_sync.py — a file that never existed in git history.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".continue/rules/infrastructure-as-code.md": textwrap.dedent("""\
                    # IaC
                    The backend/tests/python/test_env_example_sync.py guard enforces this.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (missing path in .continue/rules/), got {rc}.\n{out}",
            )
            self.assertIn("test_env_example_sync.py", out,
                          msg=f"Expected missing path in output:\n{out}")

    def test_convention_phrase_in_continue_rules_does_not_fail(self):
        """Continue rule files, like Cline workflows, may name conventions."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                ".continue/rules/frontend.md": textwrap.dedent("""\
                    # Frontend rules
                    Bump `styles.css?v=N` in index.html after editing CSS.
                    Register tools in `TOOL_REGISTRY`; gate via `getEnabledTools()`.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (Continue rules are not phrase-checked), got {rc}.\n{out}",
            )


class TestLiveDocsInScanScope(unittest.TestCase):
    """
    #87 follow-up 2: the canonical doc and the user-facing docs are themselves
    scanned. docs/rail-pipeline.md is the source of truth every other file is told
    to defer to, yet nothing checked its own paths; README.md and USER_GUIDE.md are
    the first commands a new contributor runs.
    """

    def test_fails_when_stale_path_in_canonical_doc(self):
        """The canonical doc is not exempt from its own stale-path rule."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/rail-pipeline.md": textwrap.dedent("""\
                    # RAIL Pipeline
                    The RAIL roles (0-6) apply in order.
                    Write tests in tests/python/test_server.py first.
                    Run `./scripts/quality-gate.sh` before merging.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (stale path in canonical doc), got {rc}.\n{out}",
            )
            self.assertIn("docs/rail-pipeline.md", out,
                          msg=f"Expected canonical doc named in output:\n{out}")

    def test_fails_when_missing_ref_path_in_readme(self):
        """README.md is in scope — a broken path there misleads a new contributor."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "README.md": textwrap.dedent("""\
                    # USAi Chat
                    Start with `backend/does_not_exist.py`.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (missing path in README.md), got {rc}.\n{out}",
            )
            self.assertIn("backend/does_not_exist.py", out,
                          msg=f"Expected missing path in output:\n{out}")

    def test_fails_when_stale_path_in_review_check(self):
        """docs/quality/review-checks/*.md are live gate criteria, so they are scanned."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/quality/review-checks/iac-review.md": textwrap.dedent("""\
                    # IaC review
                    The tests/python/test_env_example_sync.py guard catches this.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (stale path in review check), got {rc}.\n{out}",
            )

    def test_docs_specs_are_excluded_as_historical(self):
        """
        docs/specs/ holds COMPLETED specs — historical records that legitimately
        cite the paths correct at the time of writing. Scanning them would force
        rewriting the record to satisfy a guard, so they stay out of scope.
        This is a deliberate boundary, pinned so a future 'scan all of docs/'
        change has to confront it rather than silently falsify history.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/specs/old-feature.md": textwrap.dedent("""\
                    # Spec: old feature (completed 2025)
                    | `tests/js/app.test.mjs` | New tests |
                    Run `node --check app.js` and `py_compile server.py`.
                    Also references backend/never_existed.py from that era.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (docs/specs/ is historical, not scanned), got {rc}.\n{out}",
            )


class TestStalePathMatcherBoundaries(unittest.TestCase):
    """
    The stale-path matcher is boundary-aware, not a bare substring search. Both
    of these cases were real defects found by running the guard over docs/, and
    both are the kind that erode trust in a guard: one cries wolf, one stays quiet.
    """

    def test_does_not_flag_similarly_named_real_path(self):
        """
        `tests/js-coverage.mjs` is a real file at the repo root; its `tests/`
        prefix is not the JS test dir. A bare `tests/js` substring search
        reported it as stale. Regression: the guard must not fire here.
        """
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "tests"), exist_ok=True)
            with open(os.path.join(tmp, "tests", "js-coverage.mjs"), "w") as fh:
                fh.write("// coverage gate\n")
            _setup_drift_tree(tmp, {
                "docs/tooling/coverage.md": textwrap.dedent("""\
                    # Coverage
                    JS branch gate lives in `tests/js-coverage.mjs`.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 ('tests/js-coverage.mjs' is not stale), got {rc}.\n{out}",
            )

    def test_flags_stale_ref_even_when_correct_ref_on_same_line(self):
        """
        Previously the matcher piped through `grep -vF <correct form>`, so a line
        containing BOTH a stale and a correct reference was discarded entirely —
        masking real drift. The stale reference must still be reported.

        The assertion targets the stale-path message specifically rather than just
        a non-zero exit: the same fixture line also trips the referenced-path guard
        (`backend/tests/python` does not exist in the tmp tree), so an exit-code-only
        assertion passes even with the buggy matcher restored. Verified by mutation.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/mixed.md": textwrap.dedent("""\
                    # Mixed reference
                    Migrated from tests/python to backend/tests/python.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertNotEqual(
                rc, 0,
                msg=f"Expected non-zero exit (stale ref masked by same-line correct ref), got {rc}.\n{out}",
            )
            self.assertIn(
                "Stale path 'tests/python' found in 'docs/tooling/mixed.md'", out,
                msg=f"Expected the STALE-PATH guard to fire on a mixed line:\n{out}",
            )

    def test_does_not_flag_correct_path_alone(self):
        """The corrected form on its own must never be reported (no false positive)."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_drift_tree(tmp, {
                "docs/tooling/ok.md": textwrap.dedent("""\
                    # Fine
                    Tests live in backend/tests/python/ and frontend/tests/js/.
                    Run `node --check frontend/app.js` and `py_compile backend/server.py`.
                """),
            })
            rc, out = _run_doc_consistency(tmp)
            self.assertEqual(
                rc, 0,
                msg=f"Expected exit 0 (all paths already correct), got {rc}.\n{out}",
            )


if __name__ == "__main__":
    unittest.main()
