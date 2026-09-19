"""
backend/tests/python/test_env_example_sync.py
Config-as-code drift guard (IaC principle — docs/principles.md §3).

`.env.example` is the **declarative contract** that documents every environment
variable the server reads. If `server.py` starts reading a new variable and
`.env.example` is not updated, a deployer has no way to discover the knob — the
config stops being self-describing. This test fails on that drift.

WHY THIS FILE EXISTS: four live policy documents (`docs/rail-pipeline.md` x3,
`docs/principles.md`, and `docs/quality/review-checks/iac-review.md`) asserted that
this guard enforces `.env.example` sync. It had never existed in git history — the
docs described a control that was never implemented, so `iac-review.md` was telling
reviewers not to "weaken" a test that could not be weakened because it was absent.
The invariant itself was sound and already held (23 vars read, 23 documented), so
the guard was written rather than the four docs downgraded.

Env vars are discovered by walking the AST for `os.getenv(...)` calls rather than
by importing and calling `load_config()`: AST inspection needs no `.env`, starts no
server, and also catches reads outside `load_config()` (e.g. the `HOST`/`PORT`
lookups in the `__main__` bind block).
"""
import ast
import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SERVER_PY = os.path.join(REPO_ROOT, "backend", "server.py")
ENV_EXAMPLE = os.path.join(REPO_ROOT, ".env.example")

# Documented as `NAME=` or commented-out `# NAME=` (a commented default is still
# documentation — it shows the deployer the variable exists and its shape).
ENV_KEY_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=")


def _env_vars_read_by_server():
    """Return the set of env var names passed as a literal first arg to os.getenv."""
    with open(SERVER_PY, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=SERVER_PY)

    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match `os.getenv(...)` and a bare `getenv(...)` if ever imported directly.
        is_getenv = (
            isinstance(func, ast.Attribute) and func.attr == "getenv"
        ) or (
            isinstance(func, ast.Name) and func.id == "getenv"
        )
        if not is_getenv or not node.args:
            continue
        first = node.args[0]
        # Only literal names are checkable; a computed name can't be verified here.
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            names.add(first.value)
    return names


def _env_vars_documented():
    """Return the set of env var names documented in .env.example."""
    documented = set()
    with open(ENV_EXAMPLE, "r", encoding="utf-8") as fh:
        for line in fh:
            match = ENV_KEY_RE.match(line)
            if match:
                documented.add(match.group(1))
    return documented


class EnvExampleSyncTests(unittest.TestCase):
    """Every env var server.py reads must be documented in .env.example."""

    def test_env_example_exists(self):
        """The declarative config contract must be present and committed."""
        self.assertTrue(
            os.path.isfile(ENV_EXAMPLE),
            f".env.example is the IaC config contract and must exist: {ENV_EXAMPLE}",
        )

    def test_extractor_finds_known_vars(self):
        """Sanity-check the AST extractor itself, so a silent parse failure cannot
        make this guard vacuously pass (an empty set would satisfy the subset
        assertion below)."""
        read = _env_vars_read_by_server()
        for expected in ("API_KEY", "BASE_URL", "HOST", "PORT"):
            self.assertIn(
                expected, read,
                msg=f"AST extractor failed to find {expected} in server.py — "
                    "the extractor is broken, not the config.",
            )

    def test_documented_parser_finds_known_keys(self):
        """Sanity-check the .env.example parser for the same reason."""
        documented = _env_vars_documented()
        for expected in ("API_KEY", "BASE_URL"):
            self.assertIn(
                expected, documented,
                msg=f"Parser failed to find {expected} in .env.example — "
                    "the parser is broken, not the config.",
            )

    def test_every_env_var_read_is_documented(self):
        """The actual drift guard: no undocumented env var may be read."""
        read = _env_vars_read_by_server()
        documented = _env_vars_documented()
        undocumented = sorted(read - documented)
        self.assertEqual(
            undocumented, [],
            msg=(
                "server.py reads env var(s) that .env.example does not document: "
                f"{undocumented}. Add them to .env.example (a commented `# NAME=` "
                "line counts) so the config contract stays self-describing."
            ),
        )


if __name__ == "__main__":
    unittest.main()
