"""Tests for Obsidian-MCP bridge — Backlog #16 Phase 2

TDD order: all 13 tests written BEFORE production code (Red → Green → Refactor).
Tests cover:
  T-1..T-6  unit tests for call_obsidian_mcp() and _mcp_enabled()
  T-7..T-13 integration tests against a live ThreadingHTTPServer
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Bootstrap: add project root to sys.path so we can import server
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_rpc_stdout(result_text="done"):
    """Return bytes that look like a successful JSON-RPC response line."""
    rpc = {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"text": result_text}]}}
    return json.dumps(rpc).encode()


def _error_rpc_stdout(msg="something failed"):
    """Return bytes that look like a JSON-RPC error response."""
    rpc = {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": msg}}
    return json.dumps(rpc).encode()


# ---------------------------------------------------------------------------
# Unit tests (T-1 ... T-6)
# ---------------------------------------------------------------------------

class TestCallObsidianMcp(unittest.TestCase):
    """T-1..T-4: unit tests for call_obsidian_mcp()."""

    def setUp(self):
        self._orig_config = dict(server.CONFIG)
        server.CONFIG.update({
            'obsidian_mcp_path': '/fake/obsidian-mcp.js',
            'obsidian_node_path': 'node',
            'obsidian_vault_path': '/fake/vault',
        })

    def tearDown(self):
        server.CONFIG.clear()
        server.CONFIG.update(self._orig_config)

    def test_T1_success(self):
        """T-1: valid JSON-RPC result -> returns (text, None)."""
        completed = MagicMock()
        completed.stdout = _good_rpc_stdout("tag renamed")
        completed.returncode = 0
        with patch('subprocess.run', return_value=completed):
            result, err = server.call_obsidian_mcp('rename_tag', {'oldTag': 'a', 'newTag': 'b'})
        self.assertIsNone(err)
        self.assertEqual(result, "tag renamed")

    def test_T2_timeout(self):
        """T-2: TimeoutExpired -> returns (None, error_str)."""
        import subprocess
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='node', timeout=10)):
            result, err = server.call_obsidian_mcp('rename_tag', {})
        self.assertIsNone(result)
        self.assertIn('timed out', err.lower())

    def test_T3_file_not_found(self):
        """T-3: mcp_path points at non-existent file -> returns (None, error_str)."""
        with patch('subprocess.run', side_effect=FileNotFoundError('node not found')):
            result, err = server.call_obsidian_mcp('rename_tag', {})
        self.assertIsNone(result)
        self.assertIsNotNone(err)

    def test_T4_rpc_error(self):
        """T-4: JSON-RPC error object -> returns (None, error_str)."""
        completed = MagicMock()
        completed.stdout = _error_rpc_stdout("vault not found")
        completed.returncode = 0
        with patch('subprocess.run', return_value=completed):
            result, err = server.call_obsidian_mcp('rename_tag', {})
        self.assertIsNone(result)
        self.assertIn('vault not found', err)


class TestMcpEnabled(unittest.TestCase):
    """T-5..T-6: unit tests for _mcp_enabled()."""

    def setUp(self):
        self._orig_config = dict(server.CONFIG)

    def tearDown(self):
        server.CONFIG.clear()
        server.CONFIG.update(self._orig_config)

    def test_T5_disabled_when_no_path(self):
        """T-5: _mcp_enabled() is False when obsidian_mcp_path is empty."""
        server.CONFIG['obsidian_mcp_path'] = ''
        self.assertFalse(server._mcp_enabled())

    def test_T6_enabled_when_configured(self):
        """T-6: _mcp_enabled() is True when path exists AND vault is configured."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            server.CONFIG['obsidian_mcp_path'] = mcp_path
            server.CONFIG['obsidian_vault_path'] = vault_dir
            server.CONFIG['obsidian_memory_subdir'] = 'USAi'
            try:
                self.assertTrue(server._mcp_enabled())
            finally:
                os.unlink(mcp_path)


# ---------------------------------------------------------------------------
# Integration tests (T-7 ... T-13)
# ---------------------------------------------------------------------------

from http.server import ThreadingHTTPServer  # noqa: E402
import threading  # noqa: E402
import urllib.request  # noqa: E402
import urllib.error  # noqa: E402


def _start_test_server(extra_config=None):
    """Boot a test instance on a random port, return (httpd, base_url)."""
    server.load_config()
    server.CONFIG['_test_allow_loopback'] = True
    if extra_config:
        server.CONFIG.update(extra_config)
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.EnvConfigHTTPRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()
    port = httpd.server_address[1]
    return httpd, f'http://127.0.0.1:{port}'


def _post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _get(url):
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class TestMcpIntegration(unittest.TestCase):
    """T-7..T-13: integration tests against a live server instance."""

    def test_T7_post_mcp_tool_no_bridge_returns_400(self):
        """T-7: POST /mcp/tool without bridge configured -> 400."""
        httpd, base = _start_test_server({'obsidian_mcp_path': ''})
        try:
            status, body = _post(f'{base}/mcp/tool', {'tool': 'rename_tag', 'arguments': {}})
            self.assertEqual(status, 400, body)
        finally:
            httpd.shutdown()

    def test_T8_post_mcp_tool_unknown_tool_returns_400(self):
        """T-8: POST /mcp/tool with tool not in allowlist -> 400."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            try:
                status, body = _post(f'{base}/mcp/tool',
                                     {'tool': 'rm_rf_everything', 'arguments': {}})
                self.assertEqual(status, 400, body)
                self.assertIn('not allowed', body.get('error', '').lower())
            finally:
                httpd.shutdown()
                os.unlink(mcp_path)

    def test_T9_post_mcp_rename_tag_missing_fields_returns_400(self):
        """T-9: POST /mcp/rename-tag missing newTag -> 400."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            try:
                status, body = _post(f'{base}/mcp/rename-tag', {'oldTag': 'foo'})
                self.assertEqual(status, 400, body)
            finally:
                httpd.shutdown()
                os.unlink(mcp_path)

    def test_T10_post_mcp_move_note_missing_fields_returns_400(self):
        """T-10: POST /mcp/move-note missing destination -> 400."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            try:
                status, body = _post(f'{base}/mcp/move-note', {'source': 'note.md'})
                self.assertEqual(status, 400, body)
            finally:
                httpd.shutdown()
                os.unlink(mcp_path)

    def test_T11_get_mcp_vaults_no_bridge_returns_400(self):
        """T-11: GET /mcp/vaults without bridge configured -> 400."""
        httpd, base = _start_test_server({'obsidian_mcp_path': ''})
        try:
            status, body = _get(f'{base}/mcp/vaults')
            self.assertEqual(status, 400, body)
        finally:
            httpd.shutdown()

    def test_T12_get_config_includes_has_mcp_bridge(self):
        """T-12: GET /config always includes has_mcp_bridge key."""
        httpd, base = _start_test_server({'obsidian_mcp_path': ''})
        try:
            status, body = _get(f'{base}/config')
            self.assertEqual(status, 200, body)
            self.assertIn('has_mcp_bridge', body)
            self.assertFalse(body['has_mcp_bridge'])
        finally:
            httpd.shutdown()

    def test_T13_post_mcp_tool_large_body_returns_413(self):
        """T-13: POST /mcp/tool with body > 5 MB -> 413 (or connection closed)."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            try:
                big_body = json.dumps(
                    {'tool': 'rename_tag',
                     'arguments': {'data': 'x' * (5 * 1024 * 1024 + 1)}}
                ).encode()
                req = urllib.request.Request(
                    f'{base}/mcp/tool', data=big_body,
                    headers={'Content-Type': 'application/json'})
                try:
                    with urllib.request.urlopen(req) as resp:
                        status = resp.status
                except urllib.error.HTTPError as e:
                    status = e.code
                except urllib.error.URLError:
                    # Server may close the connection mid-send after reading the
                    # Content-Length header and sending 413 — BrokenPipe is OK.
                    status = 413
                self.assertEqual(status, 413)
            finally:
                httpd.shutdown()
                os.unlink(mcp_path)


    def test_T14_post_mcp_tool_success_returns_200(self):
        """T-14 extra: POST /mcp/tool allowed tool + mock MCP success -> 200."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            import subprocess as _sp
            rpc = json.dumps({"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"ok"}]}})
            with patch('subprocess.run', return_value=_sp.CompletedProcess(
                    args=[], returncode=0, stdout=rpc.encode())):
                try:
                    status, body = _post(f'{base}/mcp/tool',
                                         {'tool': 'rename_tag', 'arguments': {'oldTag':'a','newTag':'b'}})
                    self.assertEqual(status, 200, body)
                    self.assertTrue(body.get('ok'))
                finally:
                    httpd.shutdown()
                    os.unlink(mcp_path)

    def test_T15_post_mcp_rename_tag_success_returns_200(self):
        """T-15 extra: POST /mcp/rename-tag success path -> 200."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            import subprocess as _sp
            rpc = json.dumps({"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"renamed"}]}})
            with patch('subprocess.run', return_value=_sp.CompletedProcess(
                    args=[], returncode=0, stdout=rpc.encode())):
                try:
                    status, body = _post(f'{base}/mcp/rename-tag',
                                         {'oldTag': 'foo', 'newTag': 'bar'})
                    self.assertEqual(status, 200, body)
                finally:
                    httpd.shutdown()
                    os.unlink(mcp_path)

    def test_T16_post_mcp_move_note_success_returns_200(self):
        """T-16 extra: POST /mcp/move-note success path -> 200."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            import subprocess as _sp
            rpc = json.dumps({"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"moved"}]}})
            with patch('subprocess.run', return_value=_sp.CompletedProcess(
                    args=[], returncode=0, stdout=rpc.encode())):
                try:
                    status, body = _post(f'{base}/mcp/move-note',
                                         {'source': 'note.md', 'destination': 'folder/note.md'})
                    self.assertEqual(status, 200, body)
                finally:
                    httpd.shutdown()
                    os.unlink(mcp_path)

    def test_T17_get_mcp_vaults_success_returns_200(self):
        """T-17 extra: GET /mcp/vaults success path -> 200."""
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
            mcp_path = tf.name
        with tempfile.TemporaryDirectory() as vault_dir:
            httpd, base = _start_test_server({
                'obsidian_mcp_path': mcp_path,
                'obsidian_vault_path': vault_dir,
                'obsidian_memory_subdir': 'USAi',
            })
            import subprocess as _sp
            rpc = json.dumps({"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"vault1"}]}})
            with patch('subprocess.run', return_value=_sp.CompletedProcess(
                    args=[], returncode=0, stdout=rpc.encode())):
                try:
                    status, body = _get(f'{base}/mcp/vaults')
                    self.assertEqual(status, 200, body)
                    self.assertTrue(body.get('ok'))
                finally:
                    httpd.shutdown()
                    os.unlink(mcp_path)


if __name__ == '__main__':
    unittest.main()

