"""
tests/python/test_dev_deps.py
Tests for scripts/dev-deps-check.sh (RAIL QA Hardening — dev-dep drift gap).

Each test runs dev-deps-check.sh via subprocess against a temporary
requirements-dev.txt fixture, keeping tests fully hermetic.

TDD order (RAIL): these tests are written BEFORE the script exists (Red),
then dev-deps-check.sh is implemented to make them pass (Green).

Exit-code contract for dev-deps-check.sh:
  0 — all installed tool versions match the pins in requirements-dev.txt
  1 — at least one installed version differs from the pin
  2 — usage error: missing pin file, or a checked package not found in pin file
"""
import os
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEV_DEPS_CHECK = os.path.join(REPO_ROOT, "scripts", "dev-deps-check.sh")


def _write_req_dev(path, entries):
    """
    Write a requirements-dev.txt at *path* with the given entries.
    entries: list of (package_spec, hash) tuples, e.g.
             [("coverage==7.10.7", "sha256:abc123")]
    If hash is None the line is written without a hash (for error-path tests).
    """
    with open(path, "w") as fh:
        fh.write("# Dev/CI-only tooling — test fixture\n")
        for pkg, sha in entries:
            if sha:
                fh.write(f"{pkg} \\\n    --hash={sha}\n")
            else:
                fh.write(f"{pkg}\n")


def _run_check(req_file, python_exe=None, extra_env=None):
    """
    Run dev-deps-check.sh with REQUIREMENTS_DEV_TXT pointing at *req_file*
    and optionally a custom PYTHON_EXE or extra environment variables.
    Returns (returncode, stdout+stderr).

    extra_env: dict of additional env vars to pass to the script (e.g.
               {"CHECKED_PACKAGES_OVERRIDE": "coverage bandit"}).
    """
    env = {**os.environ, "REQUIREMENTS_DEV_TXT": req_file}
    if python_exe:
        env["PYTHON_EXE"] = python_exe
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["bash", DEV_DEPS_CHECK],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )
    return result.returncode, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# T-1: exits 0 when all installed versions match pin file
# ---------------------------------------------------------------------------

class TestDevDepsCheckPass(unittest.TestCase):
    """T-1: dev-deps-check.sh exits 0 when all tool versions match the pins."""

    def test_exits_0_on_matching_versions(self):
        """
        Write a pin file with the exact versions actually installed in the venv;
        the script must exit 0 (all match).
        """
        venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python")
        if not os.path.isfile(venv_py):
            self.skipTest(".venv not present — run `make setup` first")

        # Discover what is actually installed so the pin matches exactly.
        import subprocess as sp
        def installed_version(pkg):
            r = sp.run([venv_py, "-m", "pip", "show", pkg],
                       capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
            return None

        cov_ver = installed_version("coverage")
        ban_ver = installed_version("bandit")
        if cov_ver is None or ban_ver is None:
            self.skipTest("coverage or bandit not installed in .venv")

        import subprocess as sp2
        def installed_version2(pkg):
            r = sp2.run([venv_py, "-m", "pip", "show", pkg],
                        capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
            return None

        pip_audit_ver = installed_version2("pip-audit")
        if pip_audit_ver is None:
            self.skipTest("pip-audit not installed in .venv")

        with tempfile.TemporaryDirectory() as tmp:
            req = os.path.join(tmp, "requirements-dev.txt")
            _write_req_dev(req, [
                (f"coverage=={cov_ver}", "sha256:dummy"),
                (f"bandit=={ban_ver}", "sha256:dummy"),
                (f"pip-audit=={pip_audit_ver}", "sha256:dummy"),
            ])
            # Limit checked packages to only the three we pinned above — avoids
            # exit 2 from mutmut being in the default list but absent from the
            # fixture pin file (mutmut is not required to be installed).
            rc, out = _run_check(
                req,
                python_exe=venv_py,
                extra_env={"CHECKED_PACKAGES_OVERRIDE": "coverage bandit pip-audit"},
            )
            self.assertEqual(rc, 0, msg=f"Expected exit 0, got {rc}.\n{out}")
            self.assertIn("✓", out, msg=f"Expected ✓ in output:\n{out}")


# ---------------------------------------------------------------------------
# T-2: exits 1 when an installed version mismatches pin
# ---------------------------------------------------------------------------

class TestDevDepsCheckMismatch(unittest.TestCase):
    """T-2: dev-deps-check.sh exits 1 when a pinned version != installed."""

    def test_exits_1_on_version_mismatch(self):
        venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python")
        if not os.path.isfile(venv_py):
            self.skipTest(".venv not present")

        # Get actual installed versions of bandit and pip-audit so those pins
        # match and only coverage is wrong — ensuring we get exit 1, not exit 2.
        def _ver(pkg):
            r = subprocess.run([venv_py, "-m", "pip", "show", pkg],
                               capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
            return None

        ban_ver = _ver("bandit")
        pip_audit_ver = _ver("pip-audit")
        if ban_ver is None or pip_audit_ver is None:
            self.skipTest("bandit or pip-audit not installed in .venv")

        with tempfile.TemporaryDirectory() as tmp:
            req = os.path.join(tmp, "requirements-dev.txt")
            # Pin coverage to an obviously wrong version; others match actual.
            # Scope CHECKED_PACKAGES_OVERRIDE to avoid exit 2 from mutmut
            # not being pinned in the fixture file.
            _write_req_dev(req, [
                ("coverage==0.0.0", "sha256:dummy"),
                (f"bandit=={ban_ver}", "sha256:dummy"),
                (f"pip-audit=={pip_audit_ver}", "sha256:dummy"),
            ])
            rc, out = _run_check(
                req,
                python_exe=venv_py,
                extra_env={"CHECKED_PACKAGES_OVERRIDE": "coverage bandit pip-audit"},
            )
            self.assertEqual(rc, 1, msg=f"Expected exit 1 (mismatch), got {rc}.\n{out}")
            self.assertIn("✕", out, msg=f"Expected ✕ in output:\n{out}")


# ---------------------------------------------------------------------------
# T-3: exits 2 when a package is absent from the pin file
# ---------------------------------------------------------------------------

class TestDevDepsCheckMissingPackage(unittest.TestCase):
    """T-3: dev-deps-check.sh exits 2 when a required package has no pin entry."""

    def test_exits_2_on_missing_package_in_pin_file(self):
        venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python")
        if not os.path.isfile(venv_py):
            self.skipTest(".venv not present")

        with tempfile.TemporaryDirectory() as tmp:
            req = os.path.join(tmp, "requirements-dev.txt")
            # Write a pin file that omits bandit entirely
            _write_req_dev(req, [
                ("coverage==7.10.7", "sha256:dummy"),
                # bandit deliberately missing
            ])
            rc, out = _run_check(req, python_exe=venv_py)
            # Script must exit 2: pin not found for a checked package
            self.assertEqual(rc, 2, msg=f"Expected exit 2 (missing package in pin), got {rc}.\n{out}")


# ---------------------------------------------------------------------------
# T-4: exits 2 when requirements-dev.txt is missing
# ---------------------------------------------------------------------------

class TestDevDepsCheckMissingFile(unittest.TestCase):
    """T-4: dev-deps-check.sh exits 2 when requirements-dev.txt doesn't exist."""

    def test_exits_2_on_missing_requirements_dev_txt(self):
        rc, out = _run_check("/nonexistent/requirements-dev.txt")
        self.assertEqual(rc, 2, msg=f"Expected exit 2 (missing file), got {rc}.\n{out}")
        # Output should mention the missing file or a usage/config error
        self.assertTrue(
            "not found" in out.lower() or "no such" in out.lower()
            or "missing" in out.lower() or "error" in out.lower(),
            msg=f"Expected error message in output:\n{out}",
        )


# ---------------------------------------------------------------------------
# T-5: exits 1 when a pinned package is not installed (uninstalled-but-pinned)
# ---------------------------------------------------------------------------

class TestDevDepsCheckPinnedButNotInstalled(unittest.TestCase):
    """T-5: dev-deps-check.sh exits 1 when a package is pinned but not installed."""

    def test_exits_1_on_pinned_but_not_installed(self):
        """
        Write a pin file that includes a fake package 'usai-test-absent-pkg' that
        is obviously not installed anywhere.  The script must exit 1 and print
        'not installed' in its output.

        This covers the gap identified after RAIL QA Hardening closeout:
        `dev-deps-check.sh` silently skips packages in CHECKED_PACKAGES that
        are not installed when the pin IS present.
        """
        venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python")
        if not os.path.isfile(venv_py):
            self.skipTest(".venv not present")

        with tempfile.TemporaryDirectory() as tmp:
            req = os.path.join(tmp, "requirements-dev.txt")
            # Pin a package that cannot be installed (fake name)
            _write_req_dev(req, [
                ("coverage==7.10.7", "sha256:dummy"),
                ("bandit==1.8.6", "sha256:dummy"),
                ("pip-audit==2.9.0", "sha256:dummy"),
                ("usai-test-absent-pkg==0.0.1", "sha256:dummy"),
            ])
            rc, out = _run_check(
                req,
                python_exe=venv_py,
                extra_env={"CHECKED_PACKAGES_OVERRIDE": "coverage bandit pip-audit usai-test-absent-pkg"},
            )
            self.assertEqual(rc, 1, msg=f"Expected exit 1 (pinned but not installed), got {rc}.\n{out}")
            self.assertIn("not installed", out.lower(),
                          msg=f"Expected 'not installed' in output:\n{out}")


if __name__ == "__main__":
    unittest.main()
