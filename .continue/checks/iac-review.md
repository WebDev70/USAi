---
name: Infrastructure as Code Review
description: Environment/config changes stay declarative, reproducible, and drift-free (no manual-only steps)
---

Review this change for **Infrastructure as Code** quality, per `docs/principles.md`
§3. The goal: running and configuring the app is **declarative and reproducible**,
never a list of manual steps a human must remember. Apply this when the change
touches `Dockerfile`, `docker-compose.yml`, `Makefile`, `.env.example`, CI
(`.github/workflows/*`), `server.py` bind/config handling, or run scripts. If the
change touches none of those, pass.

Flag as **failing** if any of these are true:

- **Config drift.** `load_config()` in `server.py` reads a new environment variable
  but `.env.example` was not updated to document it (the
  `tests/python/test_env_example_sync.py` guard should also catch this — it must
  not be weakened to hide drift).
- **Hardcoded environment values.** A host, port, path, URL, or credential that
  should come from config/env was hardcoded into source (e.g. binding a literal
  address instead of honoring `HOST`/`PORT`).
- **Secrets baked into infra.** The `Dockerfile`/compose copies `.env` into the
  image or bakes a secret into a layer/arg, instead of injecting it at run time via
  `env_file`/`--env-file`. Secrets must never live in an image or in git.
- **Non-reproducible / manual-only step introduced.** A required setup/run/deploy
  action was added that exists only as prose instructions with no
  `Makefile`/compose/script target to perform it deterministically.
- **Container runs as root**, or binds/exposes more broadly than intended without
  reason (the local default must stay `127.0.0.1`; `0.0.0.0` is only for the
  container via `HOST`).
- **CI / IaC divergence.** The `Makefile`/scripts and the CI workflow drifted apart
  so they no longer run the same commands (the "works locally, breaks in CI" trap).

If environment and configuration remain declarative, documented, reproducible, and
secret-free, pass the check.
