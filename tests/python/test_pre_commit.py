"""
tests/python/test_pre_commit.py
Regression tests for scripts/pre-commit.sh (Backlog #28).

Each test runs scripts/pre-commit.sh against a temporary git repository using
GIT_DIR / GIT_WORK_TREE env-var overrides that the script already supports, so
no real git state is mutated.

SKIP_GITLEAKS=1 is set in all tests to avoid a hard dependency on the gitleaks
binary in CI environments where it may not be installed.

Exit-code contract for scripts/pre-commit.sh:
  0 — all checks passed
  1 — at least one check failed (syntax error detected)

TDD order (RAIL): tests written first (Red), then Makefile/docs wired (Green).

Test IDs:
  PC-1  Clean staged .py file          → exit 0
  PC-2  Staged .py with syntax error   → exit 1
  PC-3  Staged .js with syntax error   → exit 1
  PC-4  Clean staged .js file          → exit 0
  PC-5  Only .md staged                → exit 0
  PC-6  SKIP_GITLEAKS honoured         → exit 0 (even when gitleaks absent)
"""

import os
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PRE_COMMIT_SH = os.path.join(REPO_ROOT, "scripts", "pre-commit.sh")


def _init_temp_repo(tmp_dir):
    """
    Initialise a minimal git repo in *tmp_dir* so git commands inside the
    hook work (git diff --cached requires a repo).
    Returns (git_dir, work_tree) as strings.
    """
    subprocess.run(["git", "init", tmp_dir], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", tmp_dir, "config", "user.email", "test@example.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", tmp_dir, "config", "user.name", "Test User"],
        check=True, capture_output=True,
    )
    return os.path.join(tmp_dir, ".git"), tmp_dir


def _stage_file(work_tree, filename, content):
    """Write *content* to *work_tree*/<filename> and git-add it."""
    path = os.path.join(work_tree, filename)
    with open(path, "w") as fh:
        fh.write(content)
    subprocess.run(
        ["git", "-C", work_tree, "add", filename],
        check=True, capture_output=True,
    )


def _run_hook(git_dir, work_tree, extra_env=None):
    """
    Run scripts/pre-commit.sh with GIT_DIR / GIT_WORK_TREE overrides and
    SKIP_GITLEAKS=1.  Returns (returncode, combined stdout+stderr).
    """
    env = {
        **os.environ,
        "GIT_DIR": git_dir,
        "GIT_WORK_TREE": work_tree,
        "SKIP_GITLEAKS": "1",
    }
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["bash", PRE_COMMIT_SH],
        capture_output=True, text=True, cwd=REPO_ROOT, env=env,
    )
    return result.returncode, result.stdout + result.stderr


class PreCommitHookTests(unittest.TestCase):
    """Regression suite for scripts/pre-commit.sh exit-code contract."""

    def setUp(self):
        # Each test gets its own isolated git repo in a temp directory so
        # staged files never leak between tests.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.work_tree = self._tmpdir.name
        self.git_dir, _ = _init_temp_repo(self.work_tree)

    def tearDown(self):
        self._tmpdir.cleanup()

    # ------------------------------------------------------------------
    # PC-1: Clean staged .py file → exit 0
    # ------------------------------------------------------------------
    def test_pc1_clean_py_exits_0(self):
        """PC-1: Valid Python syntax in staged .py → hook exits 0."""
        _stage_file(self.work_tree, "good.py", "x = 1\nprint(x)\n")
        rc, out = _run_hook(self.git_dir, self.work_tree)
        self.assertEqual(rc, 0, msg=f"Expected exit 0 for clean .py.\nOutput:\n{out}")

    # ------------------------------------------------------------------
    # PC-2: Staged .py with a syntax error → exit 1
    # ------------------------------------------------------------------
    def test_pc2_bad_py_exits_1(self):
        """PC-2: Python syntax error in staged .py → hook exits 1."""
        # Unclosed parenthesis — guaranteed SyntaxError under py_compile.
        _stage_file(self.work_tree, "bad.py", "def foo(\n    pass\n")
        rc, out = _run_hook(self.git_dir, self.work_tree)
        self.assertEqual(rc, 1, msg=f"Expected exit 1 for bad .py.\nOutput:\n{out}")
        self.assertIn("bad.py", out)

    # ------------------------------------------------------------------
    # PC-3: Staged .js with a syntax error → exit 1
    # ------------------------------------------------------------------
    def test_pc3_bad_js_exits_1(self):
        """PC-3: JS syntax error in staged .js → hook exits 1."""
        # Mismatched braces — guaranteed SyntaxError under node --check.
        _stage_file(self.work_tree, "bad.js", "function foo( { return 1; }")
        rc, out = _run_hook(self.git_dir, self.work_tree)
        self.assertEqual(rc, 1, msg=f"Expected exit 1 for bad .js.\nOutput:\n{out}")
        self.assertIn("bad.js", out)

    # ------------------------------------------------------------------
    # PC-4: Clean staged .js file → exit 0
    # ------------------------------------------------------------------
    def test_pc4_clean_js_exits_0(self):
        """PC-4: Valid JS syntax in staged .js → hook exits 0."""
        _stage_file(self.work_tree, "good.js", "function foo() { return 1; }\n")
        rc, out = _run_hook(self.git_dir, self.work_tree)
        self.assertEqual(rc, 0, msg=f"Expected exit 0 for clean .js.\nOutput:\n{out}")

    # ------------------------------------------------------------------
    # PC-5: Only non-.py/.js files staged → exit 0
    # ------------------------------------------------------------------
    def test_pc5_only_md_staged_exits_0(self):
        """PC-5: Staging only a .md file → hook exits 0 (no syntax check)."""
        _stage_file(self.work_tree, "README.md", "# hello\n")
        rc, out = _run_hook(self.git_dir, self.work_tree)
        self.assertEqual(rc, 0, msg=f"Expected exit 0 when only .md staged.\nOutput:\n{out}")

    # ------------------------------------------------------------------
    # PC-6: SKIP_GITLEAKS is honoured
    # ------------------------------------------------------------------
    def test_pc6_skip_gitleaks_honoured(self):
        """PC-6: SKIP_GITLEAKS=1 skips the gitleaks step; hook still exits 0."""
        _stage_file(self.work_tree, "ok.py", "# nothing suspicious\n")
        rc, out = _run_hook(self.git_dir, self.work_tree, extra_env={"SKIP_GITLEAKS": "1"})
        self.assertEqual(rc, 0, msg=f"Expected exit 0 with SKIP_GITLEAKS=1.\nOutput:\n{out}")
        self.assertIn("SKIP_GITLEAKS", out)


if __name__ == "__main__":
    unittest.main()
