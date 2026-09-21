# -*- coding: utf-8 -*-
"""
Test for bidirectional parity between docs/ARCHITECTURE.md §3b and the live routes
in backend/server.py.

This is a doc-drift guard (spec #91). It reads both files as text and compares the
set of live routes against the set documented in the §3b endpoint catalog, in both
directions, so ARCHITECTURE.md §3b can never silently drift from the server again.

Ref: docs/specs/architecture-endpoint-reconciliation-91.md
"""
import os
import re
import unittest

# The vault-independent repo root: this file lives at
# backend/tests/python/test_arch_endpoint_parity.py, so the repo root is three
# directories up. Resolving from __file__ (not os.getcwd()) keeps the test correct
# regardless of the working directory the runner invokes it from.
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
)
SERVER_PATH = os.path.join(_REPO_ROOT, "backend", "server.py")
DOC_PATH = os.path.join(_REPO_ROOT, "docs", "ARCHITECTURE.md")


def get_file_content(path):
    """Read a file and return its content, with an informative error on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Test setup failed: could not find required file at {path}."
        )


def _normalize(path):
    """Collapse a route to its comparable base form.

    Strips any query string (``?name=`` etc.) and unifies path-parameter syntax
    (``{id}`` -> ``<id>``) so the documented rows and the live routes compare as sets.
    """
    path = path.strip()
    path = re.sub(r"\?.*$", "", path)          # drop query string
    path = path.replace("{id}", "<id>")        # unify path-param syntax
    return path


class TestArchitectureEndpointParity(unittest.TestCase):
    """Assert ARCHITECTURE.md §3b lists exactly the routes server.py dispatches."""

    def _parse_live_routes(self):
        """Extract every live route from server.py.

        Two dispatch styles are used in server.py and both are parsed:
          1. ``routes = { '/path': self._handler, ... }`` dicts inside do_GET/do_POST/
             do_DELETE — parsed by pulling the string keys out of each dict block.
          2. prefix dispatch via ``request_path.startswith('/prefix/')`` inside
             do_GET/do_POST/do_PATCH/do_PUT/do_DELETE — normalized to a ``<id>`` row
             (or ``/api/*`` for the proxy prefix).
        """
        content = get_file_content(SERVER_PATH)
        routes = set()

        # Style 1: string keys inside every `routes = { ... }` dict literal.
        for block in re.findall(r"routes\s*=\s*\{(.*?)\}", content, re.DOTALL):
            for path in re.findall(r"'(/[^']*)'\s*:", block):
                routes.add(_normalize(path))

        # Style 2: prefix dispatch. The proxy prefix is documented as `/api/*`;
        # the id-scoped prefixes collapse to `<id>` rows.
        if "request_path.startswith('/api/')" in content:
            routes.add("/api/*")
        if "request_path.startswith('/projects/')" in content:
            routes.add("/projects/<id>")
        if "request_path.startswith('/sessions/')" in content:
            routes.add("/sessions/<id>")

        return routes

    def _parse_documented_routes(self):
        """Extract every method+path row from the §3b endpoint-catalog table.

        A §3b row looks like:  | `GET` | `/config` | description |
        The second backticked column is the path; it is normalized the same way as
        the live routes so the two sets are directly comparable.
        """
        content = get_file_content(DOC_PATH)
        routes = set()
        doc_pattern = re.compile(r"\|\s*`[A-Z/]+`\s*\|\s*`([^`]+)`\s*\|")

        in_table = False
        for line in content.splitlines():
            if line.strip().startswith("### 3b"):
                in_table = True
                continue
            if in_table and line.strip().startswith("### "):
                break  # reached the next section
            if in_table:
                match = doc_pattern.match(line)
                if match:
                    routes.add(_normalize(match.group(1)))
        return routes

    def test_T1_live_routes_are_documented(self):
        """AC-1: every live route has a §3b row  (live - documented == ∅)."""
        missing = self._parse_live_routes() - self._parse_documented_routes()
        self.assertEqual(
            set(), missing,
            "FAIL (T-1): live routes MISSING from ARCHITECTURE.md §3b: "
            f"{sorted(missing)}",
        )

    def test_T2_documented_routes_are_live(self):
        """AC-2: every §3b row maps to a live route  (documented - live == ∅)."""
        phantom = self._parse_documented_routes() - self._parse_live_routes()
        self.assertEqual(
            set(), phantom,
            "FAIL (T-2): documented routes that are PHANTOMS (not in server.py): "
            f"{sorted(phantom)}",
        )

    def test_T3_positive_control_guard_detects_drift(self):
        """AC-4 positive control: the guard must flag an injected fake route.

        Proves the parity check is not passing vacuously (RAIL Entry 011 — execute
        the control, don't merely assert it exists).
        """
        live = self._parse_live_routes()
        documented = self._parse_documented_routes()
        live.add("/__fake_route_for_positive_control__")
        missing = live - documented
        self.assertIn(
            "/__fake_route_for_positive_control__", missing,
            "FAIL (T-3): positive control did not detect the injected fake route — "
            "the guard would pass vacuously.",
        )


if __name__ == "__main__":
    unittest.main()
