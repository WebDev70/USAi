#!/usr/bin/env python3
"""
scripts/analyze_logs.py
RAIL Log Analyzer — stdlib-only (json, pathlib, sys, collections, re).

Reads *.jsonl files from a log directory and emits a structured summary:
- total entries and breakdown by level / component
- top-3 most frequent error messages (scrubbed for secrets)
- fetch entries with latency_ms > 2000ms
- exit 1 if any error entries found, exit 0 otherwise

Usage (direct):
    python3 scripts/analyze_logs.py [log-dir]  # default: logs/

Called by:
    scripts/analyze-logs.sh  (shell wrapper for CI / RAIL gates)
"""
import collections
import json
import re
import sys
from pathlib import Path

# Patterns that indicate sensitive data — replace with [REDACTED] in all output.
_SENSITIVE = re.compile(r'sk-|Bearer |api_key=|password=', re.IGNORECASE)

# Latency threshold: fetch entries above this are reported as outliers.
LATENCY_THRESHOLD_MS = 2000

# Per-file line cap — avoids loading huge logs entirely into memory.
MAX_LINES_PER_FILE = 5000


def scrub(text: str) -> str:
    """Replace sensitive patterns with [REDACTED] in the given string."""
    return _SENSITIVE.sub('[REDACTED]', text)


def analyze(log_dir: Path) -> dict:
    """
    Analyze all *.jsonl files in log_dir (non-recursive, capped at
    MAX_LINES_PER_FILE lines per file).

    Returns a dict with keys:
        files_read       int
        total_entries    int
        by_level         dict[str, int]
        by_component     dict[str, int]
        top_errors       list of {component, message, count}  — up to 3, scrubbed
        latency_outliers list of {url, latency_ms, timestamp}
        has_errors       bool
    """
    by_level: dict = collections.defaultdict(int)
    by_component: dict = collections.defaultdict(int)
    error_counts: dict = collections.Counter()
    latency_outliers: list = []
    files_read = 0
    total_entries = 0

    for jsonl_file in sorted(log_dir.glob("*.jsonl")):
        files_read += 1
        with open(jsonl_file, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, raw in enumerate(fh, start=1):
                if line_no > MAX_LINES_PER_FILE:
                    break
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    # Malformed line — skip silently (never raise).
                    continue

                total_entries += 1
                level = str(entry.get("level", "unknown")).lower()
                component = str(entry.get("component", "unknown"))
                message = str(entry.get("message", ""))
                details = entry.get("details") or {}
                timestamp = str(entry.get("timestamp", ""))

                by_level[level] += 1
                by_component[component] += 1

                if level == "error":
                    error_counts[(component, scrub(message))] += 1

                if isinstance(details, dict):
                    latency_ms = details.get("latency_ms")
                    if latency_ms is not None:
                        try:
                            latency_ms = int(latency_ms)
                        except (TypeError, ValueError):
                            latency_ms = None
                    if latency_ms is not None and latency_ms > LATENCY_THRESHOLD_MS:
                        url = scrub(str(details.get("url", "")))
                        latency_outliers.append({
                            "url": url,
                            "latency_ms": latency_ms,
                            "timestamp": timestamp,
                        })

    top_errors = []
    for (comp, msg), count in error_counts.most_common(3):
        top_errors.append({"component": comp, "message": msg, "count": count})

    has_errors = by_level.get("error", 0) > 0

    return {
        "files_read": files_read,
        "total_entries": total_entries,
        "by_level": dict(by_level),
        "by_component": dict(by_component),
        "top_errors": top_errors,
        "latency_outliers": latency_outliers,
        "has_errors": has_errors,
    }


def _format_report(result: dict, log_dir: Path) -> str:
    """Format the analyze() result as a human-readable text block."""
    lines = ["=== RAIL Log Analysis ==="]

    if result["files_read"] == 0:
        lines.append(
            f"No log files found in '{log_dir}' — PERSIST_LOGS may be disabled."
        )
        return "\n".join(lines)

    lines.append(
        f"Files read    : {result['files_read']:<6} "
        f"Total entries : {result['total_entries']}"
    )

    level_str = "  ".join(
        f"{k}={v}" for k, v in sorted(result["by_level"].items())
    )
    lines.append(f"By level      : {level_str}")

    comp_items = sorted(result["by_component"].items(), key=lambda x: -x[1])
    comp_str = "  ".join(f"{k}={v}" for k, v in comp_items[:8])
    if len(comp_items) > 8:
        comp_str += "  ..."
    lines.append(f"By component  : {comp_str}")

    if result["top_errors"]:
        lines.append("Top errors (up to 3):")
        for err in result["top_errors"]:
            lines.append(
                f"  [{err['component']}] {err['message']}  (\u00d7{err['count']})"
            )

    if result["latency_outliers"]:
        lines.append(f"Latency outliers (>{LATENCY_THRESHOLD_MS}ms):")
        for o in result["latency_outliers"]:
            lines.append(
                f"  {o['url']}  {o['latency_ms']}ms  {o['timestamp']}"
            )

    exit_code = 1 if result["has_errors"] else 0
    lines.append(
        f"Exit code: {exit_code}  "
        f"({'errors found' if result['has_errors'] else 'no errors'})"
    )
    return "\n".join(lines)


def main(argv=None):
    """
    CLI: analyze_logs.py [log-dir]
    Prints the report to stdout and exits 1 if errors found, 0 otherwise.
    """
    if argv is None:
        argv = sys.argv[1:]

    log_dir = Path(argv[0]) if argv else Path("logs")

    result = analyze(log_dir)
    print(_format_report(result, log_dir))
    sys.exit(1 if result["has_errors"] else 0)


if __name__ == "__main__":
    main()
