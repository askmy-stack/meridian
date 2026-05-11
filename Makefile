.PHONY: help dev up down test test-unit test-integration lint format seed validate-env clean

PY ?= python3
PIP ?= pip
COMPOSE ?= docker compose

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## --- Local infra ---

up:  ## Start docker compose stack
	$(COMPOSE) up -d
	@echo "Waiting for services..."
	@sleep 5
	@$(MAKE) validate-env

down:  ## Stop docker compose stack
	$(COMPOSE) down

restart: down up  ## Restart stack

logs:  ## Tail compose logs
	$(COMPOSE) logs -f --tail=200

## --- Dev loops ---

dev:  ## Start API (hot reload) — requires `make up` first
	uvicorn src.api.main:app --reload --port 8000

dev-frontend:  ## Start frontend dev server
	cd frontend && npm run dev

## --- Testing ---

test: test-unit test-integration  ## Run all tests

test-unit:  ## Fast unit tests (no services required)
	$(PY) -m pytest tests/unit/ -v

test-integration:  ## Integration tests (requires `make up`)
	$(PY) -m pytest tests/integration/ -v

test-cov:  ## Tests with coverage report
	$(PY) -m pytest tests/ --cov=src --cov-report=term-missing

## --- Quality ---

lint:  ## Lint with ruff + black --check
	ruff check src/ tests/
	black --check src/ tests/

format:  ## Auto-format with black + ruff --fix
	black src/ tests/
	ruff check --fix src/ tests/

typecheck:  ## Run mypy
	mypy src/api src/schemas.py

## --- Data ---

seed:  ## Seed Neo4j with ports / chokepoints
	$(PY) -m src.seeding.ports_chokepoints

seed-suppliers:  ## Seed Neo4j with demo supplier data
	$(PY) scripts/seed_suppliers.py --file data/sample_suppliers.csv

seed-all: seed seed-suppliers  ## Seed all demo data (ports + suppliers)

validate-env:  ## Validate required env vars
	$(PY) scripts/validate_env.py --env-file .env

## --- Housekeeping ---

clean:  ## Remove pycache, build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -prune -exec rm -rf {} +
	find . -type d -name '.ruff_cache' -prune -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -prune -exec rm -rf {} +
	rm -f test_results.html
