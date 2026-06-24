---
alwaysApply: true
---

# Role: Infrastructure as Code (declarative, reproducible environments)

The way USAi Chat is configured, built, run, and deployed must be **code** —
declarative, version-controlled, and reproducible — never a list of manual steps a
human must remember. See `docs/principles.md` §3.

## Principles

- **Declarative environment.** The runtime is described by the `Dockerfile` +
  `docker-compose.yml`; `docker compose up` (or `make docker-up`) is the
  reproducible bootstrap. The container's runtime surface stays minimal (Python
  stdlib + `python-dotenv`) — Docker is dev/deploy tooling, not a runtime dep.
- **Config is code.** Configuration comes from environment variables read in
  `load_config()`; **`.env.example` is the declarative contract** that documents
  every variable. Secrets live only in the git-ignored `.env`, injected at run time
  via `env_file` — **never baked into an image** or committed.
- **No hardcoded environment.** Hosts, ports, paths, and URLs come from
  config/env, not literals in source. The bind address honors `HOST`/`PORT`
  (`resolve_bind_address`) with safe local defaults (`127.0.0.1:8000`).
- **One set of commands everywhere.** The `Makefile` targets (`run`, `test`,
  `coverage`, `scan`, `check`, `docker-up`) are the single entry points used both
  locally and in CI, so "works on my machine" and "works in CI" stay identical.
- **Least privilege.** The container runs as a non-root user and only copies the
  files the app needs.

## When you change infra/config, you MUST

1. **Keep `.env.example` in sync.** If `load_config()` reads a new variable,
   document it in `.env.example` — the `tests/python/test_env_example_sync.py`
   drift guard enforces this; don't weaken it to hide drift.
2. **Keep Docker/compose/Makefile/CI aligned.** A new run/setup/deploy step must be
   expressed as a target/stage, not just prose. Update the `Dockerfile` `COPY` list
   if the app gains a file it needs at runtime.
3. **Never put secrets in infra.** No secret in a `Dockerfile` layer, build arg,
   compose literal, or committed file.
4. **Add/adjust tests** for config-resolution logic (e.g. `resolve_bind_address`)
   and run the IaC drift guard.

The `iac-review` check verifies this role.
