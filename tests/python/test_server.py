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


class ResolveMemoryFileTests(unittest.TestCase):
    """_resolve_memory_file() confines a user path to the memory folder."""

    def test_resolves_basename_inside_dir(self):
        with tempfile.TemporaryDirectory() as d:
            mem = Path(d)
            out = server._resolve_memory_file(mem, 'note.md')
            self.assertEqual(out, (mem / 'note.md').resolve())

    def test_strips_directory_components_to_basename(self):
        with tempfile.TemporaryDirectory() as d:
            mem = Path(d)
            # Even a traversal attempt is reduced to its basename and stays inside.
            out = server._resolve_memory_file(mem, '../../etc/passwd')
            self.assertEqual(out, (mem / 'passwd').resolve())
            out.relative_to(mem.resolve())  # must not raise

    def test_empty_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(server._resolve_memory_file(Path(d), ''))


class AddLogTests(unittest.TestCase):
    """add_log() appends entries and rotates at MAX_LOGS."""

    def setUp(self):
        self._saved_logs = list(server.server_logs)
        self._saved_max = server.MAX_LOGS
        server.server_logs.clear()

    def tearDown(self):
        server.server_logs.clear()
        server.server_logs.extend(self._saved_logs)
        server.MAX_LOGS = self._saved_max

    def test_appends_entry_with_fields(self):
        server.add_log('info', 'test', 'hello', {'k': 'v'})
        self.assertEqual(len(server.server_logs), 1)
        entry = server.server_logs[0]
        self.assertEqual(entry['level'], 'info')
        self.assertEqual(entry['component'], 'test')
        self.assertEqual(entry['message'], 'hello')
        self.assertEqual(entry['details'], {'k': 'v'})
        self.assertIn('timestamp', entry)

    def test_rotates_at_max_logs(self):
        server.MAX_LOGS = 5
        for i in range(10):
            server.add_log('info', 'test', f'msg {i}')
        self.assertLessEqual(len(server.server_logs), 6)
        # Oldest entries dropped; the latest is retained.
        self.assertEqual(server.server_logs[-1]['message'], 'msg 9')


class LoadConfigTests(unittest.TestCase):
    """load_config() reads env vars into CONFIG with sensible defaults."""

    def setUp(self):
        self._saved_config = dict(server.CONFIG)
        self._saved_env = {k: os.environ.get(k) for k in (
            'API_KEY', 'BASE_URL', 'DEFAULT_MODEL', 'OBSIDIAN_MEMORY_SUBDIR')}

    def tearDown(self):
        server.CONFIG = self._saved_config
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_reads_env_and_applies_defaults(self):
        os.environ['API_KEY'] = 'k123'
        os.environ['BASE_URL'] = 'https://api.example'
        os.environ['DEFAULT_MODEL'] = 'gpt-test'
        os.environ.pop('OBSIDIAN_MEMORY_SUBDIR', None)  # exercise the default
        # Point dotenv at a nonexistent file so it doesn't override our env.
        server.ENV_FILE = Path('/no/such/.env')
        server.load_config()
        self.assertEqual(server.CONFIG['api_key'], 'k123')
        self.assertEqual(server.CONFIG['base_url'], 'https://api.example')
        self.assertEqual(server.CONFIG['default_model'], 'gpt-test')
        self.assertEqual(server.CONFIG['obsidian_memory_subdir'], 'USAi')
        self.assertEqual(server.CONFIG['context7_path'], '/v1/context')


if __name__ == '__main__':
    unittest.main()
