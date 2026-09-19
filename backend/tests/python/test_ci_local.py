"""
backend/tests/python/test_ci_local.py
Tests for the `run-tests.sh --ci-python` local CI-simulation flag (backlog #16).

The GitHub Actions `python` job installs NO npm packages, so a Python test that
accidentally depends on something inside node_modules passes locally and fails in
CI. `--ci-python` closes that gap: it temporarily hides node_modules and skips the
JS suites, reproducing the CI Python job on a developer machine.

HERMETIC BY DESIGN — why a temp tree instead of running run-tests.sh in place:
    run-tests.sh runs `unittest discover` over backend/tests/python, which is where
    THIS file lives. Invoking the real script from here would re-discover this file
    and fork another run-tests.sh, recursing until the machine is saturated and
    a minimal throw-away tree (copied script + stub frontend + stub backend) and
    runs the script there. Same isolation approach as _make_jsdom_free_tree in
    test_scripts.py.

Guard-rails covered:
  T-16a  node_modules is genuinely absent while the Python suite runs
  T-16b  a failing Python test still propagates a non-zero exit code
  T-16c  node_modules is restored afterwards — including when the suite fails
  T-16d  the JS suites are skipped, unknown flags are rejected, and the parser
         handles every argument (not just $1)
"""
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RUN_TESTS = os.path.join(REPO_ROOT, "run-tests.sh")

# Probe that PASSES only when node_modules is absent from the script's own root.
# run-tests.sh does `cd "$(dirname "$0")"`, so a relative check is the same check
# the script's hide/restore logic operates on.
PROBE_ASSERTS_HIDDEN = '''\
import os
import unittest


class ProbeNodeModulesHidden(unittest.TestCase):
    def test_node_modules_absent(self):
        self.assertFalse(os.path.exists("node_modules"))
'''

PROBE_ALWAYS_FAILS = '''\
import unittest


class ProbeAlwaysFails(unittest.TestCase):
    def test_always_fails(self):
        self.fail("deliberate failure - exit-code propagation probe")
'''


class _CiPythonHarness(unittest.TestCase):
    """Builds a disposable repo containing run-tests.sh and one probe test."""

    def _make_tree(self, probe_source, with_node_modules=True):
        tmp = tempfile.mkdtemp(prefix="usai-ci-local-")
        self.addCleanup(shutil.rmtree, tmp, True)

        script = os.path.join(tmp, "run-tests.sh")
        shutil.copy(RUN_TESTS, script)
        os.chmod(script, 0o755)

        # A stub frontend keeps the child run hermetic and fast: the real app.js
        # (~193 KB) and its suites are irrelevant to what --ci-python does, and
        # running them would couple these tests to unrelated JS failures.
        js_dir = os.path.join(tmp, "frontend", "tests", "js")
        os.makedirs(js_dir)
        with open(os.path.join(tmp, "frontend", "app.js"), "w") as fh:
            fh.write("// stub app.js so the `node --check` syntax gate has a target\n")
        with open(os.path.join(js_dir, "stub.test.mjs"), "w") as fh:
            fh.write(
                "import { test } from 'node:test';\n"
                "test('stub js test', () => {});\n"
            )

        # `py_compile backend/*.py` needs at least one module; a stub keeps the
        # real backend (and this test file) out of the child run entirely.
        probe_dir = os.path.join(tmp, "backend", "tests", "python")
        os.makedirs(probe_dir)
        with open(os.path.join(tmp, "backend", "stub.py"), "w") as fh:
            fh.write("# stub module so the py_compile syntax gate has a target\n")
        with open(os.path.join(probe_dir, "test_probe.py"), "w") as fh:
            fh.write(probe_source)

        if with_node_modules:
            # Deliberately NO jsdom subdirectory: run-tests.sh skips the behavior
            # suite when node_modules/jsdom is absent, so the negative-control test
            # fails on the probe (node_modules visible) rather than on a missing
            # jsdom import — the failure reason must be the one under test.
            # A marker file lets us prove the SAME directory came back, rather than
            # an empty one the script happened to recreate.
            os.makedirs(os.path.join(tmp, "node_modules"))
            with open(os.path.join(tmp, "node_modules", "marker.txt"), "w") as fh:
                fh.write("original")

        return tmp

    def _run(self, tree, *args):
        return subprocess.run(
            [os.path.join(tree, "run-tests.sh"), *args],
            capture_output=True,
            text=True,
            cwd=tree,
        )

    def _assert_restored(self, tree, context):
        """node_modules is back (with its marker) and no staging dir remains."""
        marker = os.path.join(tree, "node_modules", "marker.txt")
        self.assertTrue(
            os.path.isfile(marker),
            msg=f"node_modules was not restored after {context}",
        )
        with open(marker) as fh:
            self.assertEqual(fh.read(), "original", f"wrong node_modules restored ({context})")
        leftovers = [n for n in os.listdir(tree) if n.startswith(".tmp_node_modules_")]
        self.assertEqual(leftovers, [], msg=f"staging dir left behind after {context}")


class TestCiPythonHidesNodeModules(_CiPythonHarness):
    """T-16a — node_modules is genuinely hidden while the Python suite runs."""

    def test_python_suite_sees_no_node_modules(self):
        tree = self._make_tree(PROBE_ASSERTS_HIDDEN)
        result = self._run(tree, "--ci-python")
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "--ci-python should hide node_modules so the probe passes "
                f"(exit {result.returncode})\n{result.stdout}\n{result.stderr}"
            ),
        )

    def test_without_the_flag_node_modules_is_visible(self):
        """
        Negative control: the same probe must FAIL without --ci-python. Without
        this, T-16a would still pass if the hide logic were deleted on a machine
        that simply has no node_modules.
        """
        tree = self._make_tree(PROBE_ASSERTS_HIDDEN)
        result = self._run(tree)
        self.assertNotEqual(
            result.returncode,
            0,
            msg="probe passed without --ci-python — node_modules was not visible",
        )


class TestCiPythonRestoresNodeModules(_CiPythonHarness):
    """T-16c — the EXIT trap restores node_modules on success AND on failure."""

    def test_restored_after_successful_run(self):
        tree = self._make_tree(PROBE_ASSERTS_HIDDEN)
        result = self._run(tree, "--ci-python")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self._assert_restored(tree, "a successful run")

    def test_restored_after_failed_run(self):
        tree = self._make_tree(PROBE_ALWAYS_FAILS)
        result = self._run(tree, "--ci-python")
        self.assertNotEqual(result.returncode, 0)
        self._assert_restored(tree, "a failing run")


class TestCiPythonExitCode(_CiPythonHarness):
    """T-16b — a failing test is never masked by the hide/restore wrapper."""

    def test_failing_test_propagates_nonzero_exit(self):
        tree = self._make_tree(PROBE_ALWAYS_FAILS)
        result = self._run(tree, "--ci-python")
        self.assertNotEqual(
            result.returncode,
            0,
            msg=(
                "--ci-python reported success despite a failing test\n"
                f"{result.stdout}\n{result.stderr}"
            ),
        )

    def test_success_banner_absent_on_failure(self):
        """The all-clear banner must not print when the suite failed."""
        tree = self._make_tree(PROBE_ALWAYS_FAILS)
        result = self._run(tree, "--ci-python")
        self.assertNotIn("All checks passed", result.stdout + result.stderr)


class TestCiPythonArgParsing(_CiPythonHarness):
    """T-16d — flag parsing covers every argument and rejects typos."""

    def test_unknown_flag_is_rejected(self):
        """A typo'd flag must fail loudly instead of silently running defaults."""
        tree = self._make_tree(PROBE_ASSERTS_HIDDEN)
        result = self._run(tree, "--ci-pythn")
        self.assertNotEqual(result.returncode, 0, msg="unknown flag was accepted")
        self.assertIn("unknown option", (result.stdout + result.stderr).lower())

    def test_js_suites_are_skipped(self):
        """The skip banner proves the JS work was bypassed, not merely passing."""
        tree = self._make_tree(PROBE_ASSERTS_HIDDEN)
        result = self._run(tree, "--ci-python")
        self.assertIn("skipped (--ci-python)", result.stdout + result.stderr)

    def test_flag_is_honoured_when_not_first_argument(self):
        """
        Guards the original `[ "${1:-}" = ... ]` bug class: --ci-python must work
        in any position, so `--coverage --ci-python` cannot silently run the JS
        gate against a hidden node_modules.
        """
        tree = self._make_tree(PROBE_ASSERTS_HIDDEN)
        result = self._run(tree, "--coverage", "--ci-python")
        combined = result.stdout + result.stderr
        self.assertIn(
            "skipped (--ci-python)",
            combined,
            msg=f"--ci-python ignored in second position\n{combined}",
        )


if __name__ == "__main__":
    unittest.main()
