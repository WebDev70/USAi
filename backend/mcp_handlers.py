"""mcp_handlers.py — Obsidian-MCP bridge handler mixin.

Contains McpHandlersMixin with all /mcp/* endpoint methods extracted
from EnvConfigHTTPRequestHandler (server.py backlog #45 module split).

This module is intentionally isolated as the future home for multi-server
MCP connectors (backlog #57).

Import strategy: server-module names are imported at the top of this file.
In server.py the mixin imports are placed AFTER all module-level constants
and functions are defined (just before the class declaration), so all
referenced names are already bound in the partial server module when Python
processes these imports — no circular-import issue arises.
"""

import json
import sys


class _ServerProxy:
    """Lazy proxy to the 'server' module — breaks the circular import at script startup.

    See proxy_handlers.py for the full explanation.
    """
    def __getattr__(self, name):
        mod = sys.modules.get('server') or sys.modules.get('__main__')
        return getattr(mod, name)


_server = _ServerProxy()


class McpHandlersMixin:
    """Mixin providing /mcp/* handler methods for EnvConfigHTTPRequestHandler.

    Methods rely on self being an HTTPRequestHandler instance with:
      - self.headers, self.rfile, self.wfile (from BaseHTTPRequestHandler)
      - self._json_response() (defined in EnvConfigHTTPRequestHandler)
    """

    # ── Obsidian-MCP bridge handlers (#16 Phase 2) ────────────────────────────

    def _read_mcp_body(self):
        """Read and parse the JSON request body for MCP endpoints.

        Enforces a 5 MB body limit (returns None and sends 413 on oversize).
        Returns the parsed dict, or None if the read/parse fails (response already sent).
        """
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 5 * 1024 * 1024:
            self._json_response(413, {'error': 'Payload too large'})
            return None
        try:
            body = self.rfile.read(content_length).decode('utf-8')
            return json.loads(body)
        except Exception as exc:
            self._json_response(400, {'error': str(exc)})
            return None

    def _post_mcp_tool(self):
        """POST /mcp/tool — generic allowlisted obsidian-mcp tool call.

        Body: { "tool": "<tool_name>", "arguments": { ... } }
        Returns: { "ok": true, "result": "..." }  or  { "error": "..." }
        """
        if not _server._mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        data = self._read_mcp_body()
        if data is None:
            return
        tool = (data.get('tool') or '').strip()
        if tool not in _server.MCP_TOOL_ALLOWLIST:
            self._json_response(400, {'error': f'Tool "{tool}" not allowed'})
            return
        arguments = data.get('arguments') or {}
        result, err = _server.call_obsidian_mcp(tool, arguments)
        if err is not None:
            self._json_response(502, {'error': err})
            return
        _server.add_log('info', 'mcp', f'tool "{tool}" succeeded')
        self._json_response(200, {'ok': True, 'result': result})

    def _post_mcp_rename_tag(self):
        """POST /mcp/rename-tag — convenience endpoint for rename_tag.

        Body: { "oldTag": "foo", "newTag": "bar" }
        """
        if not _server._mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        data = self._read_mcp_body()
        if data is None:
            return
        old_tag = (data.get('oldTag') or '').strip()
        new_tag = (data.get('newTag') or '').strip()
        if not old_tag or not new_tag:
            self._json_response(400, {'error': 'oldTag and newTag are required'})
            return
        result, err = _server.call_obsidian_mcp('rename_tag', {'oldTag': old_tag, 'newTag': new_tag})
        if err is not None:
            self._json_response(502, {'error': err})
            return
        _server.add_log('info', 'mcp', f'rename_tag "{old_tag}" -> "{new_tag}"')
        self._json_response(200, {'ok': True, 'result': result})

    def _post_mcp_move_note(self):
        """POST /mcp/move-note — convenience endpoint for move_note.

        Body: { "source": "note.md", "destination": "folder/note.md" }
        """
        if not _server._mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        data = self._read_mcp_body()
        if data is None:
            return
        source = (data.get('source') or '').strip()
        destination = (data.get('destination') or '').strip()
        if not source or not destination:
            self._json_response(400, {'error': 'source and destination are required'})
            return
        result, err = _server.call_obsidian_mcp('move_note', {'source': source, 'destination': destination})
        if err is not None:
            self._json_response(502, {'error': err})
            return
        _server.add_log('info', 'mcp', f'move_note "{source}" -> "{destination}"')
        self._json_response(200, {'ok': True, 'result': result})

    def _get_mcp_vaults(self):
        """GET /mcp/vaults — list available Obsidian vaults via obsidian-mcp."""
        if not _server._mcp_enabled():
            self._json_response(400, {'error': 'MCP bridge not configured'})
            return
        result, err = _server.call_obsidian_mcp('list_available_vaults', {})
        if err is not None:
            self._json_response(502, {'error': err})
            return
        _server.add_log('info', 'mcp', 'list_available_vaults succeeded')
        self._json_response(200, {'ok': True, 'result': result})
