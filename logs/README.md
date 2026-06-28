# logs/ — Server Log Files

This directory holds **timestamped server log files** written by `server.py`.

## File naming convention

```
YYYY-MM-DD-HHMMSS-server.jsonl
```

One file is created per server run (the timestamp is captured at startup).
Each line is a JSON object matching the internal log entry shape:

```json
{"timestamp": "2026-06-27T14:30:00.123456", "level": "info", "component": "memory", "message": "search \"foo\" → 2 hit(s)", "details": {}}
```

## Enabling log persistence

By default, nothing is written here — log persistence is **opt-in**.

To enable it, set in your `.env`:

```
PERSIST_LOGS=true
LOG_FILE_MAX=20    # max number of session log files to keep (oldest deleted)
```

Restart the server for the settings to take effect.

## Rotation

The server automatically prunes the oldest `*.jsonl` files whenever the number of
session files would exceed `LOG_FILE_MAX` (default 20). The current session's file
is never pruned.

## Git tracking

- `logs/.gitkeep` and `logs/README.md` are **tracked** in git.
- `logs/*.jsonl` and `logs/*.log` are **git-ignored** (runtime state).

## Security

Log messages never contain API keys, Bearer tokens, or vault contents.
The `server.py` `add_log()` call-sites are audited to enforce this.
