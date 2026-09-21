"""
backend/tests/python/test_mode_b_check.py
Tests for scripts/mode-b-check.sh (backlog #92 — Mode B self-improvement enforcement).

WHY hermetic:
    mode-b-check.sh reads from $OBSIDIAN_VAULT_PATH/Cline/memories/. Each test
    builds a throw-away temp directory that serves as the vault root so tests
    never touch the real vault, never need network access, and never require
    any installed tooling beyond bash.

TDD order: these tests are written BEFORE the script exists (Red), then
scripts/mode-b-check.sh is implemented to make them pass (Green).

Guards covered:
  T-1  Note containing ## Mode B self-improvement + proposal body → exit 0
  T-2  Note containing ## Mode B self-improvement + "no improvement found" → exit 0
  T-3  Note missing the Mode B section → exit non-zero
  T-4  (G-4 redaction) Missing Mode B + planted fake token → exit non-zero AND
       token absent from stdout+stderr
  T-5  OBSIDIAN_VAULT_PATH unset → exit 0, stdout contains "skip" (case-insensitive)
"""
import os
import shutil
import subprocess
import tempfile
import unittest

# Absolute path to the script under test — resolved relative to this file so
# tests work regardless of the current working directory.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MODE_B_CHECK = os.path.join(REPO_ROOT, "scripts", "mode-b-check.sh")

# Subdirectory inside the fake vault that the script expects.
MEMORIES_SUBDIR = os.path.join("Cline", "memories")


def _make_fake_vault(tmp_dir):
    """Create the Cline/memories/ sub-tree inside tmp_dir and return its path."""
    mem_dir = os.path.join(tmp_dir, MEMORIES_SUBDIR)
    os.makedirs(mem_dir, exist_ok=True)
    return mem_dir


def _write_note(mem_dir, filename, content):
    """Write a markdown note to mem_dir and return its absolute path."""
    path = os.path.join(mem_dir, filename)
    with open(path, "w") as fh:
        fh.write(content)
    return path


def _run_check(vault_path, note_path=None):
    """
    Run mode-b-check.sh and return (returncode, combined_output).

    vault_path  — value for OBSIDIAN_VAULT_PATH; pass None to leave it unset.
    note_path   — optional explicit path arg passed to the script.
    """
    env = os.environ.copy()
    # Remove the real vault path so it never leaks into hermetic tests.
    env.pop("OBSIDIAN_VAULT_PATH", None)
    if vault_path is not None:
        env["OBSIDIAN_VAULT_PATH"] = vault_path

    cmd = ["bash", MODE_B_CHECK]
    if note_path is not None:
        cmd.append(note_path)

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.returncode, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

class TestModeBCheck(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="usai-mode-b-")
        self.mem_dir = _make_fake_vault(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # T-1: note with ## Mode B self-improvement + proposal body → exit 0
    def test_T1_mode_b_present_with_proposal_exits_zero(self):
        """T-1: A note that has ## Mode B self-improvement and a proposal must exit 0."""
        content = (
            "---\ntitle: Test session note\n---\n\n"
            "## Some earlier section\n\nWork done today.\n\n"
            "## Mode B self-improvement\n\n"
            "- **Proposal:** unify skip helpers -- one-sentence description\n"
        )
        _write_note(self.mem_dir, "2026-09-21-010101-test-note.md", content)
        rc, out = _run_check(self.tmp)
        self.assertEqual(rc, 0, f"Expected exit 0 for Mode B present with proposal.\n{out}")

    # T-2: note with ## Mode B self-improvement + "no improvement found" → exit 0
    def test_T2_mode_b_no_improvement_found_exits_zero(self):
        """T-2: A note with ## Mode B and 'no improvement found' must exit 0."""
        content = (
            "---\ntitle: Test session note\n---\n\n"
            "## Mode B self-improvement\n\n"
            "no improvement found -- 2026-09-21 -- short focused session\n"
        )
        _write_note(self.mem_dir, "2026-09-21-020202-test-note.md", content)
        rc, out = _run_check(self.tmp)
        self.assertEqual(rc, 0, f"Expected exit 0 for Mode B 'no improvement found'.\n{out}")

    # T-3: note missing Mode B section → exit non-zero
    def test_T3_mode_b_absent_exits_nonzero(self):
        """T-3: A note without any ## Mode B heading must exit non-zero."""
        content = (
            "---\ntitle: Test session note\n---\n\n"
            "## Session summary\n\n"
            "Work done today. No Mode B section at all.\n"
        )
        _write_note(self.mem_dir, "2026-09-21-030303-test-note.md", content)
        rc, out = _run_check(self.tmp)
        self.assertNotEqual(rc, 0,
            f"Expected non-zero exit when Mode B section absent.\n{out}")

    # T-4 (G-4): Missing Mode B + planted fake token → exit != 0 AND token absent
    def test_T4_G4_redaction_planted_token_not_in_output(self):
        """T-4 (G-4): Exit non-zero AND planted fake token must never appear in output.

        WHY a fake token: Entry 010 in self-improvement-log shows that a prior
        grep-based check echoed matched line text. This test proves mode-b-check.sh
        never echoes note content -- only path:line_number [REDACTED].
        """
        fake_token = "FAKE_SECRET_TOKEN_abc123xyz"
        content = (
            "---\ntitle: Test note with no Mode B section\n---\n\n"
            f"Some content that happens to contain {fake_token} in it.\n\n"
            "## Regular section\n\nNo Mode B section present.\n"
        )
        _write_note(self.mem_dir, "2026-09-21-040404-test-note.md", content)
        rc, out = _run_check(self.tmp)
        self.assertNotEqual(rc, 0,
            f"Expected non-zero exit when Mode B absent.\n{out}")
        self.assertNotIn(
            fake_token, out,
            f"SECURITY VIOLATION: planted token appeared in script output.\n{out}"
        )

    # T-5: OBSIDIAN_VAULT_PATH unset → exit 0, "skip" in stdout
    def test_T5_unset_vault_path_skips_cleanly(self):
        """T-5: When OBSIDIAN_VAULT_PATH is unset the script must skip (exit 0)."""
        rc, out = _run_check(vault_path=None)
        self.assertEqual(rc, 0,
            f"Expected exit 0 when vault path unset.\n{out}")
        self.assertIn("skip", out.lower(),
            f"Expected 'skip' (case-insensitive) in output when vault path unset.\n{out}")


if __name__ == "__main__":
    unittest.main()
