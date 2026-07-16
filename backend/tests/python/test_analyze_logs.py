"""
tests/python/test_analyze_logs.py
Tests for scripts/analyze_logs.py (RAIL Log Analysis — backlog #52).

Each test exercises analyze() directly by importing the module, using
tempfile for isolated log directories. No network calls; no external deps.

TDD order (RAIL): written BEFORE the module exists (Red), then
analyze_logs.py is implemented to make them pass (Green).
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRIPT_PATH = os.path.join(REPO_ROOT, "scripts", "analyze_logs.py")


def _load_module():
    """Dynamically import scripts/analyze_logs.py by file path."""
    spec = importlib.util.spec_from_file_location("analyze_logs", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_jsonl(path, entries):
    """Write a list of dicts as JSONL to the given Path."""
    with open(path, "w") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


class TestAnalyzeLogs(unittest.TestCase):

    def test_al1_empty_dir(self):
        """AL-1: analyze() on an empty dir returns has_errors=False, files_read=0."""
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            result = mod.analyze(Path(tmp))
        self.assertFalse(result["has_errors"])
        self.assertEqual(result["files_read"], 0)
        self.assertEqual(result["total_entries"], 0)

    def test_al2_all_info(self):
        """AL-2: All info-level entries → has_errors=False, by_level error==0."""
        mod = _load_module()
        entries = [
            {"timestamp": "2026-06-28T01:00:00", "level": "info",
             "component": "proxy", "message": "Request proxied"},
            {"timestamp": "2026-06-28T01:00:01", "level": "info",
             "component": "memory", "message": "Memory saved"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(Path(tmp) / "session.jsonl", entries)
            result = mod.analyze(Path(tmp))
        self.assertFalse(result["has_errors"])
        self.assertEqual(result["by_level"].get("error", 0), 0)
        self.assertEqual(result["total_entries"], 2)

    def test_al3_one_error(self):
        """AL-3: A single error entry → has_errors=True."""
        mod = _load_module()
        entries = [
            {"timestamp": "2026-06-28T01:00:00", "level": "error",
             "component": "proxy", "message": "Upstream unreachable"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(Path(tmp) / "session.jsonl", entries)
            result = mod.analyze(Path(tmp))
        self.assertTrue(result["has_errors"])
        self.assertEqual(result["by_level"].get("error", 0), 1)

    def test_al4_multiple_errors_same_component(self):
        """AL-4: Multiple errors from same component → top_errors[0]['count'] >= 2."""
        mod = _load_module()
        entries = [
            {"timestamp": "2026-06-28T01:00:00", "level": "error",
             "component": "proxy", "message": "Upstream unreachable"},
            {"timestamp": "2026-06-28T01:00:01", "level": "error",
             "component": "proxy", "message": "Upstream unreachable"},
            {"timestamp": "2026-06-28T01:00:02", "level": "error",
             "component": "proxy", "message": "Upstream unreachable"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(Path(tmp) / "session.jsonl", entries)
            result = mod.analyze(Path(tmp))
        self.assertTrue(result["has_errors"])
        self.assertGreater(len(result["top_errors"]), 0)
        self.assertGreaterEqual(result["top_errors"][0]["count"], 2)

    def test_al5_latency_outlier_present(self):
        """AL-5: A fetch entry with latency_ms > 2000 appears in latency_outliers."""
        mod = _load_module()
        entries = [
            {"timestamp": "2026-06-28T09:12:44", "level": "info",
             "component": "fetch", "message": "Response received",
             "details": {"latency_ms": 3421, "url": "/api/v1/chat"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(Path(tmp) / "session.jsonl", entries)
            result = mod.analyze(Path(tmp))
        self.assertEqual(len(result["latency_outliers"]), 1)
        self.assertEqual(result["latency_outliers"][0]["latency_ms"], 3421)

    def test_al6_latency_no_outlier(self):
        """AL-6: A fetch entry with latency_ms <= 2000 does NOT appear in latency_outliers."""
        mod = _load_module()
        entries = [
            {"timestamp": "2026-06-28T09:12:44", "level": "info",
             "component": "fetch", "message": "Response received",
             "details": {"latency_ms": 1800, "url": "/api/v1/chat"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(Path(tmp) / "session.jsonl", entries)
            result = mod.analyze(Path(tmp))
        self.assertEqual(len(result["latency_outliers"]), 0)

    def test_al7_secret_scrubbed(self):
        """AL-7: sk- prefix in message is replaced with [REDACTED] in top_errors."""
        mod = _load_module()
        secret_msg = "Token sk-abc123 rejected by upstream"
        entries = [
            {"timestamp": "2026-06-28T01:00:00", "level": "error",
             "component": "proxy", "message": secret_msg},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(Path(tmp) / "session.jsonl", entries)
            result = mod.analyze(Path(tmp))
        self.assertTrue(result["has_errors"])
        for err in result["top_errors"]:
            self.assertNotIn("sk-abc123", err["message"],
                             "Raw secret must not appear in top_errors")
            self.assertIn("[REDACTED]", err["message"])

    def test_al8_malformed_json_skipped(self):
        """AL-8: A malformed JSONL line is skipped; remaining valid lines are parsed."""
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "session.jsonl"
            with open(log_file, "w") as fh:
                fh.write("this is not valid JSON\n")
                fh.write(json.dumps({
                    "timestamp": "2026-06-28T01:00:00", "level": "info",
                    "component": "server", "message": "Server started"
                }) + "\n")
            result = mod.analyze(Path(tmp))
        self.assertEqual(result["total_entries"], 1)
        self.assertFalse(result["has_errors"])


if __name__ == "__main__":
    unittest.main()
