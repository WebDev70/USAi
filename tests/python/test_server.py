"""Starter unit tests for pure / security-critical helpers in server.py.

Run from the project root with:
    .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'

Uses the stdlib `unittest` framework only — no third-party test runner, per the
project's zero-new-dependency philosophy. These tests import server.py directly;
importing it must NOT start the HTTP server (it doesn't — `run()` is guarded by
`if __name__ == '__main__'`).
"""

import json
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
        self._saved_config = dict(server.CONFIG)
        self._saved_logs_dir = server.LOGS_DIR
        self._saved_stamp = server._LOG_SESSION_STAMP
        server.server_logs.clear()

    def tearDown(self):
        server.server_logs.clear()
        server.server_logs.extend(self._saved_logs)
        server.MAX_LOGS = self._saved_max
        server.CONFIG = self._saved_config
        server.LOGS_DIR = self._saved_logs_dir
        server._LOG_SESSION_STAMP = self._saved_stamp

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

    # ── PL-1: persist enabled — writes valid JSON line ───────────────────────
    def test_persist_log_writes_jsonl_when_enabled(self):
        """PL-1: _persist_log writes a valid JSON line to logs/ when PERSIST_LOGS=true."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server.LOGS_DIR = Path(tmpdir)
            server._LOG_SESSION_STAMP = '2026-06-27-143000'
            server.CONFIG = dict(server.CONFIG)
            server.CONFIG['persist_logs'] = True
            server.CONFIG['log_file_max'] = 20
            entry = {
                'timestamp': '2026-06-27T14:30:00',
                'level': 'info',
                'component': 'test',
                'message': 'PL-1 test',
                'details': {},
            }
            server._persist_log(entry)
            log_file = Path(tmpdir) / '2026-06-27-143000-server.jsonl'
            self.assertTrue(log_file.exists(), 'JSONL file should be created')
            line = log_file.read_text(encoding='utf-8').strip()
            parsed = json.loads(line)
            self.assertEqual(parsed['message'], 'PL-1 test')
            self.assertEqual(parsed['level'], 'info')
            self.assertEqual(parsed['component'], 'test')

    # ── PL-2: persist disabled — no file written ─────────────────────────────
    def test_persist_log_noop_when_disabled(self):
        """PL-2: _persist_log is a no-op when PERSIST_LOGS is false (default)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server.LOGS_DIR = Path(tmpdir)
            server._LOG_SESSION_STAMP = '2026-06-27-143001'
            server.CONFIG = dict(server.CONFIG)
            server.CONFIG['persist_logs'] = False
            entry = {
                'timestamp': '2026-06-27T14:30:01',
                'level': 'info', 'component': 'test',
                'message': 'PL-2 test', 'details': {},
            }
            server._persist_log(entry)
            log_file = Path(tmpdir) / '2026-06-27-143001-server.jsonl'
            self.assertFalse(log_file.exists(), 'No file should be created when persist_logs is off')

    # ── PL-3: write failure swallowed — add_log never raises ─────────────────
    def test_persist_log_failure_is_swallowed(self):
        """PL-3: A write failure (bad path) is swallowed; add_log() must not raise."""
        # Point LOGS_DIR at a non-existent deep path so open() will fail.
        server.LOGS_DIR = Path('/nonexistent/path/that/does/not/exist')
        server._LOG_SESSION_STAMP = '2026-06-27-143002'
        server.CONFIG = dict(server.CONFIG)
        server.CONFIG['persist_logs'] = True
        server.CONFIG['log_file_max'] = 20
        # Must not raise — failure is always swallowed.
        try:
            server.add_log('info', 'test', 'PL-3 write failure test')
        except Exception as exc:
            self.fail(f'add_log raised unexpectedly: {exc}')

    # ── PL-4: rotation — oldest file pruned when at cap ──────────────────────
    def test_log_file_rotation(self):
        """PL-4: Oldest *.jsonl files are pruned when the count reaches log_file_max."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server.LOGS_DIR = Path(tmpdir)
            server.CONFIG = dict(server.CONFIG)
            server.CONFIG['persist_logs'] = True
            server.CONFIG['log_file_max'] = 3
            # Create 3 existing "old" session files.
            for i in range(3):
                old_file = Path(tmpdir) / f'2026-06-2{i}-090000-server.jsonl'
                old_file.write_text('{"msg": "old"}\n', encoding='utf-8')
            # Now write a new session — rotation should prune oldest.
            server._LOG_SESSION_STAMP = '2026-06-27-143003'
            entry = {
                'timestamp': '2026-06-27T14:30:03',
                'level': 'info', 'component': 'test',
                'message': 'PL-4 rotation test', 'details': {},
            }
            server._persist_log(entry)
            remaining = list(Path(tmpdir).glob('*.jsonl'))
            # cap=3, 3 old + 1 new = 4 total; oldest should be pruned to stay at ≤ cap
            self.assertLessEqual(len(remaining), 3,
                                 f'Expected ≤3 files after rotation, got {len(remaining)}: {remaining}')
            # The new session file must be present.
            new_file = Path(tmpdir) / '2026-06-27-143003-server.jsonl'
            self.assertIn(new_file, remaining, 'Current session file must survive rotation')


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
        # MCP bridge keys added in Sprint 09 (#16 Ph2) — verify defaults are loaded
        self.assertEqual(server.CONFIG['obsidian_mcp_path'], '')
        self.assertEqual(server.CONFIG['obsidian_node_path'], 'node')
        # Auto model router tier overrides (#19 fix) — verify defaults are loaded
        # (empty strings so TIER_MAP falls back to its hardcoded verified ids)
        self.assertEqual(server.CONFIG['tier_high_model'],   '')
        self.assertEqual(server.CONFIG['tier_medium_model'], '')
        self.assertEqual(server.CONFIG['tier_low_model'],    '')


class IsSafeUpstreamUrlTests(unittest.TestCase):
    """is_safe_upstream_url() must accept only http/https URLs pointing at
    non-private, non-loopback, non-link-local hosts.

    Security invariants verified here:
    - Only http:// and https:// schemes are allowed.
    - Private / loopback / link-local IP addresses are rejected (SSRF guard).
    - Hostnames 'localhost' and variants that resolve to loopback are rejected.
    - Empty / malformed / non-string inputs are rejected.
    """

    def _safe(self, url):
        """Assert that the URL is accepted (returns True)."""
        result = server.is_safe_upstream_url(url)
        self.assertTrue(result, f"Expected {url!r} to be SAFE but got {result!r}")

    def _unsafe(self, url):
        """Assert that the URL is rejected (returns False)."""
        result = server.is_safe_upstream_url(url)
        self.assertFalse(result, f"Expected {url!r} to be REJECTED but got {result!r}")

    # --- Safe inputs ---

    def test_http_public_url_is_safe(self):
        self._safe('http://api.openai.com/v1/chat/completions')

    def test_https_public_url_is_safe(self):
        self._safe('https://api.anthropic.com/v1/messages')

    def test_https_url_with_port_is_safe(self):
        self._safe('https://my-gateway.example.com:8443/api')

    # --- Scheme rejections ---

    def test_file_scheme_is_rejected(self):
        self._unsafe('file:///etc/passwd')

    def test_gopher_scheme_is_rejected(self):
        self._unsafe('gopher://evil.example.com')

    def test_ftp_scheme_is_rejected(self):
        self._unsafe('ftp://files.example.com')

    def test_empty_string_is_rejected(self):
        self._unsafe('')

    def test_none_is_rejected(self):
        self._unsafe(None)

    def test_relative_url_is_rejected(self):
        self._unsafe('/api/v1/chat')

    # --- SSRF / private IP rejections ---

    def test_aws_imds_ipv4_is_rejected(self):
        self._unsafe('http://169.254.169.254/latest/meta-data/')

    def test_loopback_ipv4_is_rejected(self):
        self._unsafe('http://127.0.0.1/api')

    def test_loopback_ipv6_is_rejected(self):
        self._unsafe('http://[::1]/api')

    def test_private_rfc1918_10_x_is_rejected(self):
        self._unsafe('http://10.0.0.1/internal')

    def test_private_rfc1918_192_168_is_rejected(self):
        self._unsafe('http://192.168.1.100/internal')

    def test_private_rfc1918_172_16_is_rejected(self):
        self._unsafe('http://172.16.0.1/internal')

    def test_localhost_hostname_is_rejected(self):
        self._unsafe('http://localhost/api')

    def test_localhost_https_is_rejected(self):
        self._unsafe('https://localhost:8080/api')


if __name__ == '__main__':
    unittest.main()
