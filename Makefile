# USAi Chat — one-word entry points (Infrastructure as Code).
#
# WHY: docs/principles.md §3 — the same declarative commands work locally and in CI,
# so nobody has to remember multi-step incantations. `make` is dev tooling; it ships
# nothing into the app.
#
# Common targets:
#   make help        list targets
#   make setup       create the venv + install runtime dep (+ dev-only tooling)
#   make run         start the server locally (venv Python, so dotenv loads)
#   make test        run the zero-dep test suite
#   make coverage    run tests with coverage gates
#   make scan        run the DevSecOps security scan (lenient — skips missing tools)
#   make scan-strict run the security scan in --strict mode (fails if a scanner is missing)
#   make check       full QA gate: tests+coverage + strict security scan (RAIL Step 4)
#   make docker-up   build + start via docker compose (reproducible bootstrap)
#   make docker-down stop the compose stack
#   make stop        free port 8000

PY := .venv/bin/python
PORT ?= 8000

.DEFAULT_GOAL := help
.PHONY: help setup run stop test coverage scan check docker-up docker-down clean hooks

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv + install runtime dep and dev-only tooling (coverage/security)
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	# Dev-only tooling (NEVER added to requirements.txt — ships nothing in the app).
	$(PY) -m pip install coverage bandit pip-audit

run: ## Start the server locally (uses the venv so python-dotenv loads)
	$(PY) server.py

stop: ## Free the app port
	-lsof -ti:$(PORT) | xargs kill 2>/dev/null || true

test: ## Run syntax gates + JS + Python tests (zero deps)
	./run-tests.sh

coverage: ## Run tests with coverage gates enforced
	./run-tests.sh --coverage

scan: ## Run the DevSecOps security scan (gitleaks + bandit + pip-audit) — lenient (skips missing tools)
	./scripts/security-scan.sh

scan-strict: ## Run the DevSecOps scan in --strict mode (fails if any scanner is missing)
	./scripts/security-scan.sh --strict

check: coverage scan-strict ## Full QA gate (RAIL Step 4): tests+coverage then strict security scan
	@echo "✓ make check complete — tests, coverage, and security scan passed"

docker-up: ## Build + start via docker compose (declarative, reproducible)
	docker compose up --build

docker-down: ## Stop the docker compose stack
	docker compose down

clean: ## Remove dev-only coverage artifacts
	rm -rf .coverage .coverage.* htmlcov coverage.xml

hooks: ## Install git hooks (symlinks .git/hooks/pre-commit → scripts/pre-commit.sh)
	@mkdir -p .git/hooks
	@ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✓ pre-commit hook installed (.git/hooks/pre-commit → scripts/pre-commit.sh)"

