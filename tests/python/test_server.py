"""Starter unit tests for pure / security-critical helpers in server.py.

Run from the project root with:
    .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'

Uses the stdlib `unittest` framework only — no third-party test runner, per the
project's zero-new-dependency philosophy. These tests import server.py directly;
importing it must NOT start the HTTP server (it doesn't — `run()` is guarded by
`if __name__ == '__main__'`).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Make the project root importable so `import server` works regardless of CWD.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402


class GetMemoryDirTests(unittest.TestCase):
    """get_memory_dir() must resolve <vault>/<subdir>/memories and refuse to
    escape the vault (path-traversal guard). It reads the module-level CONFIG, so
    each test sets CONFIG explicitly and restores it afterward."""

    def setUp(self):
        self._saved_config = dict(server.CONFIG)

    def tearDown(self):
        server.CONFIG = self._saved_config

    def test_returns_none_when_no_vault_configured(self):
        server.CONFIG = {'obsidian_vault_path': '', 'obsidian_memory_subdir': 'USAi'}
        self.assertIsNone(server.get_memory_dir())

    def test_returns_none_when_vault_path_does_not_exist(self):
        server.CONFIG = {
            'obsidian_vault_path': '/no/such/vault/hopefully-12345',
            'obsidian_memory_subdir': 'USAi',
        }
        self.assertIsNone(server.get_memory_dir())

    def test_resolves_subdir_memories_inside_vault(self):
        with tempfile.TemporaryDirectory() as vault:
            server.CONFIG = {
                'obsidian_vault_path': vault,
                'obsidian_memory_subdir': 'USAi',
            }
            result = server.get_memory_dir()
            self.assertIsNotNone(result)
            expected = (Path(vault).resolve() / 'USAi' / 'memories').resolve()
            self.assertEqual(result, expected)
            # The resolved dir must live inside the vault (no traversal escape).
            self.assertEqual(result.relative_to(Path(vault).resolve()),
                             Path('USAi') / 'memories')

    def test_rejects_path_traversal_in_subdir(self):
        """A subdir containing '..' must not let the memory dir escape the vault."""
        with tempfile.TemporaryDirectory() as vault:
            server.CONFIG = {
                'obsidian_vault_path': vault,
                'obsidian_memory_subdir': '../../etc',
            }
            # The guard should return None because the resolved path is outside
            # the vault.
            self.assertIsNone(server.get_memory_dir())


class SlugifyTests(unittest.TestCase):
    """_slugify() turns titles into filesystem-safe slugs."""

    def test_basic_slug(self):
        self.assertEqual(server._slugify('Hello, World!'), 'hello-world')

    def test_collapses_and_trims_separators(self):
        self.assertEqual(server._slugify('  Multiple   spaces & symbols!! '),
                         'multiple-spaces-symbols')

    def test_empty_falls_back_to_memory(self):
        self.assertEqual(server._slugify(''), 'memory')
        self.assertEqual(server._slugify('!!!'), 'memory')

    def test_respects_max_len(self):
        slug = server._slugify('a' * 200, max_len=10)
        self.assertLessEqual(len(slug), 10)


if __name__ == '__main__':
    unittest.main()
