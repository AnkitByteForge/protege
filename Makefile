.PHONY: help dev api web db-up db-down db-migrate observability test test-e2e lint typecheck format eval clean

.DEFAULT_GOAL := help
UV := uv run
API_PORT ?= 8300
WEB_PORT ?= 3101

# mypy needs the src dirs as explicit package bases to resolve the shared
# `protege.*` namespace packages (separator is platform-specific).
ifeq ($(OS),Windows_NT)
MYPYPATH := services/session/src;packages/contracts/src;tools/authoring/src
else
MYPYPATH := services/session/src:packages/contracts/src:tools/authoring/src
endif

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

dev: ## Start the full local stack: Postgres + migrations + API + web (Ctrl+C stops api/web)
	@test -f .env || cp .env.example .env
	$(MAKE) db-up
	$(MAKE) db-migrate
	$(MAKE) -j2 api web

api: ## Run the FastAPI dev server on :$(API_PORT)
	$(UV) uvicorn protege.session_service.app:app --reload --port $(API_PORT)

web: ## Run the Next.js dev server on :$(WEB_PORT)
	cd apps/web && npm run dev -- --port $(WEB_PORT)

db-up: ## Start Postgres 17 + pgvector (docker compose)
	docker compose up -d --wait db

db-down: ## Stop and remove containers
	docker compose down

db-migrate: ## Apply Alembic migrations (baseline at P0)
	$(UV) alembic -c services/session/alembic.ini upgrade head

observability: ## Start Langfuse (compose profile "observability") on :3200
	docker compose --profile observability up -d langfuse-db langfuse

test: ## Run backend unit tests (pytest)
	$(UV) pytest

test-e2e: ## Run the Playwright smoke test (builds and starts the web app)
	cd apps/web && npx playwright test

lint: ## Ruff (lint + format check) + ESLint + Prettier check
	$(UV) ruff check .
	$(UV) ruff format --check .
	cd apps/web && npm run lint && npm run format:check

typecheck: ## mypy (strict) + tsc --noEmit
	MYPYPATH="$(MYPYPATH)" $(UV) mypy
	cd apps/web && npm run typecheck

format: ## Auto-format Python (ruff) and web (prettier)
	$(UV) ruff format .
	$(UV) ruff check --fix .
	cd apps/web && npm run format

eval: ## Run the evaluation harness (lands in P24; intentional no-op at P0)
	@echo "evals/ is intentionally empty at P0 - the harness arrives in P24 (roadmap). Nothing to evaluate yet."

clean: ## Remove local caches and build artifacts
	docker compose down --remove-orphans || true
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache apps/web/.next apps/web/test-results apps/web/playwright-report
