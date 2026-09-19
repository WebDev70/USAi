
import os
import subprocess
import tempfile
import textwrap
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
QUALITY_GATE_SCRIPT = os.path.join(REPO_ROOT, "scripts", "quality-gate.sh")

class TestNeutralQualityInfra(unittest.TestCase):
    def test_review_checks_dir_exists(self):
        """T-M1a: The neutral review criteria directory docs/quality/review-checks/ must exist."""
        checks_dir = os.path.join(REPO_ROOT, "docs", "quality", "review-checks")
        self.assertTrue(os.path.isdir(checks_dir), f"Directory not found: {checks_dir}")

    def test_review_checks_manifest_exists(self):
        """T-M1b: The manifest docs/quality/review-checks/README.md must exist."""
        manifest_path = os.path.join(REPO_ROOT, "docs", "quality", "review-checks", "README.md")
        self.assertTrue(os.path.isfile(manifest_path), f"File not found: {manifest_path}")

class TestQualityGateScript(unittest.TestCase):
    """Tests for the scripts/quality-gate.sh script."""

    def test_quality_gate_fails_on_missing_check(self):
        """T-M2a: quality-gate.sh must fail if a check file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a manifest pointing to a non-existent check.
            manifest_content = "1. `non-existent-check.md`"
            manifest_path = os.path.join(tmpdir, "README.md")
            with open(manifest_path, "w") as f:
                f.write(manifest_content)

            # The script should fail because the check file doesn't exist.
            # We pass the directory containing the manifest to the script.
            result = subprocess.run(
                [QUALITY_GATE_SCRIPT, tmpdir],
                capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0,
                f"quality-gate.sh should have failed due to missing check, but it passed. Stderr: {result.stderr}")
            self.assertIn("ERROR: Quality check file not found", result.stderr, f"Expected error message not found in stderr. Stderr: {result.stderr}")

    def test_quality_gate_fails_on_empty_check(self):
        """T-M2b: quality-gate.sh must fail if a check file is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an empty check file.
            empty_check_path = os.path.join(tmpdir, "empty-check.md")
            open(empty_check_path, "a").close()

            # Create a manifest pointing to the empty check.
            manifest_content = "1. `empty-check.md`"
            manifest_path = os.path.join(tmpdir, "README.md")
            with open(manifest_path, "w") as f:
                f.write(manifest_content)

            # The script should fail because the check file is empty.
            result = subprocess.run(
                [QUALITY_GATE_SCRIPT, tmpdir],
                capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0,
                f"quality-gate.sh should have failed due to empty check, but it passed. Stderr: {result.stderr}")
            self.assertIn("ERROR: Quality check file is empty", result.stderr, f"Expected error message not found in stderr. Stderr: {result.stderr}")
