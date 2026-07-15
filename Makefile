# Crucible developer commands (thin wrappers; no business logic — plan §3).
# Windows without make: use scripts/check.ps1 or run the uv/docker commands directly.

.PHONY: bootstrap check fmt lint type imports test test-int evals up down migrate lock

bootstrap:            ## Install toolchain deps and git hooks
	uv sync --dev
	uv run pre-commit install

check: ## The one command a fresh clone must pass (Phase 1 DoD)
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run lint-imports
	uv run pytest -m "not integration"
	uv run alembic -c packages/db/alembic.ini upgrade head --sql > /dev/null
	uv run python evals/references/run_all.py > /dev/null
	@echo "ALL CHECKS PASSED"

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .

type:
	uv run mypy

imports:
	uv run lint-imports

test:
	uv run pytest -m "not integration"

test-int:             ## Requires the compose stack (make up)
	uv run pytest -m integration

sandbox-image:        ## Build the hardened sandbox runner image
	docker build -f infra/docker/runner.Dockerfile -t crucible-sandbox-runner:local .

sandbox:              ## Run the sandbox containment canaries (needs the image)
	uv run pytest -m sandbox

evals:                ## Seed-suite reference calculators
	uv run python evals/references/run_all.py

up:                   ## Local stack (add --profile full for web)
	docker compose up -d

down:
	docker compose down

migrate:              ## Explicit migration step — never runs on app startup
	uv run alembic -c packages/db/alembic.ini upgrade head

lock:
	uv lock
