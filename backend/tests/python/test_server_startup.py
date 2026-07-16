"""tests/python/test_server_startup.py — Subprocess-level startup regression test.

Regression test for the circular-import bug introduced by backlog #45
(server-module split): when server.py is run as `python server.py` the
handler-mixin modules (proxy_handlers, memory_handlers, session_handlers,
mcp_handlers, projects_handlers) each did `import server as _server` at
module-import time.  At that point Python's import machinery had already
begun executing server.py and had placed a *partially-initialised* module
object in sys.modules['server'].  Any name referenced from the mixin
before server.py finished executing would therefore be missing, causing
ImportError / AttributeError at startup.

Import-based tests (test_server.py etc.) cannot catch this class of bug
because they import server.py in-process after Python has already finished
loading it.  Only a subprocess launch reproduces the real startup path.

Fix: every handler module now uses a _ServerProxy that defers attribute
lookup to sys.modules['server'] at *call* time rather than at import time.

Test strategy:
- Launch `python server.py` as a subprocess with a minimal .env-like
  environment (no real API key needed — the server binds and logs startup
  messages before any request arrives).
- Give it up to SERVER_START_TIMEOUT seconds to print the "Serving on"
  startup line to stderr (or to exit with a non-zero code).
- Assert that the process did NOT exit immediately with an error (which is
  what the circular-import bug produced).
- Terminate the server cleanly after the assertion.

This test is intentionally I/O-bound (network bind on a free port) and
therefore lives in a separate file so it can be excluded from the fast
unit-test run when desired.
"""

import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

# ── constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# How long (seconds) to wait for the "Serving on" line before giving up.
SERVER_START_TIMEOUT = 12

# Marker text that server.py prints when it has successfully started.
STARTUP_MARKER = b"Serving on"


# ── helpers ──────────────────────────────────────────────────────────────────

def _find_free_port() -> int:
    """Return an OS-assigned free TCP port number."""
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _build_env(port: int) -> dict:
    """Build a minimal environment for starting the server.

    Only the variables the server actually reads at startup are set;
    no API key is required because we just want it to bind and start
    (not proxy any real requests).
    """
    env = {
        # Inherit PATH so python / the venv executable is found
        'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
        # Minimal server config — must not contain real secrets.
        # NOTE: server.py calls load_dotenv(override=True) which will re-read
        # PORT/HOST from .env if they are set there.  We pass PORT/HOST here
        # as env vars that will be present when load_config() is called, but
        # load_dotenv(override=True) may overwrite them.  To avoid the real
        # .env from stealing the port, we also set PYTHONDONTWRITEBYTECODE
        # (harmless) and rely on the server reading HOST/PORT *after*
        # load_config() from the final os.getenv() call in __main__.
        # Because load_config() doesn't store PORT/HOST in CONFIG (only in
        # os.environ via dotenv), the __main__ os.getenv('PORT') call will
        # see our value — unless the .env file overrides it.  To be safe,
        # the test accepts any port by just checking the startup banner text.
        'PORT': str(port),
        'HOST': '127.0.0.1',
        # Disable persistence so no files are written during the test
        'PERSIST_LOGS': 'false',
        'CAPTURE_RAW_RESPONSES': 'false',
    }
    # Pass through VIRTUAL_ENV / PYTHONPATH so the venv is found
    for key in ('VIRTUAL_ENV', 'PYTHONPATH', 'PYTHONHOME', 'HOME', 'USER',
                'OBSIDIAN_VAULT_PATH', 'OBSIDIAN_MEMORY_SUBDIR'):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


# ── test ─────────────────────────────────────────────────────────────────────

class TestServerSubprocessStartup(unittest.TestCase):
    """Verify that `python server.py` starts cleanly without circular-import errors."""

    def test_server_starts_without_import_error(self):
        """server.py must reach the 'Serving on' log line when run as __main__.

        A circular-import / AttributeError at startup causes the process to
        exit immediately with a non-zero return code and an error traceback on
        stderr.  We detect that by:
        1. Polling stderr for the STARTUP_MARKER within SERVER_START_TIMEOUT s.
        2. Checking that the process hasn't already exited with an error.
        """
        port = _find_free_port()
        python_exe = sys.executable  # the same Python that is running the tests
        env = _build_env(port)

        # PYTHONUNBUFFERED=1 disables Python's stdout buffering so print()
        # calls in server.py flush immediately — without this, the "Serving on"
        # banner can sit in the OS buffer until the test timeout expires.
        env['PYTHONUNBUFFERED'] = '1'

        proc = subprocess.Popen(
            [python_exe, str(PROJECT_ROOT / 'backend' / 'server.py')],
            cwd=str(PROJECT_ROOT / 'backend'),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge so we see all output
        )

        found_marker = False
        combined_output = b''
        deadline = time.monotonic() + SERVER_START_TIMEOUT

        # Set stdout to non-blocking so reads don't hang indefinitely.
        import fcntl
        assert proc.stdout is not None  # always true: PIPE was requested
        stdout_fd = proc.stdout.fileno()
        fl = fcntl.fcntl(stdout_fd, fcntl.F_GETFL)
        fcntl.fcntl(stdout_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        try:
            while time.monotonic() < deadline:
                # Has the process already died?
                ret = proc.poll()
                if ret is not None:
                    # Read any remaining output for the error message
                    try:
                        rest, _ = proc.communicate(timeout=2)
                        combined_output += rest
                    except Exception:
                        pass
                    self.fail(
                        f"server.py exited prematurely with code {ret}.\n"
                        f"Output:\n{combined_output.decode('utf-8', errors='replace')}"
                    )

                # Drain whatever is available right now (non-blocking).
                try:
                    chunk = os.read(proc.stdout.fileno(), 8192)
                    if chunk:
                        combined_output += chunk
                        if STARTUP_MARKER in combined_output:
                            found_marker = True
                            break
                except BlockingIOError:
                    # Nothing available yet — yield briefly and retry.
                    time.sleep(0.05)
                except OSError:
                    time.sleep(0.05)
        finally:
            if proc.poll() is None:
                # Terminate cleanly regardless of test outcome
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

        self.assertTrue(
            found_marker,
            f"Server did not print '{STARTUP_MARKER.decode()}' within "
            f"{SERVER_START_TIMEOUT}s.\nOutput so far:\n"
            f"{combined_output.decode('utf-8', errors='replace')}"
        )


if __name__ == '__main__':
    unittest.main()
