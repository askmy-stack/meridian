.PHONY: help dev up down test test-unit test-integration lint format seed validate-env clean demo \
	fetch-wgi portfolio-ready seed-erp pipeline-batch check-deploy rescore-recent

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
	uvicorn src.api.main:app --reload --port 8002

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

seed-demo:  ## Seed demo disruption events for digest/alerts narrative
	$(PY) scripts/seed_demo_scenarios.py

seed-routes:  ## Seed Route topology (Port→Route→Chokepoint)
	$(PY) scripts/seed_routes.py

seed-all: seed seed-suppliers seed-demo seed-routes  ## Seed all demo data (ports + suppliers + events + routes)

ingest-gdelt:  ## Publish latest GDELT conflict events to Kafka
	$(PY) -m src.producers gdelt

ingest-acled:  ## Publish ACLED conflict events to Kafka (requires API key)
	$(PY) -m src.producers acled

ingest-ais:  ## Publish AISHub chokepoint vessel events to Kafka
	$(PY) -m src.producers ais

load-graph:  ## Consume Kafka events into Neo4j (set PIPELINE_MAX_MESSAGES)
	$(PY) -m src.consumers graph-loader --max-messages $(or $(PIPELINE_MAX_MESSAGES),500)

load-vessels:  ## Consume AIS events into Neo4j Vessel nodes
	$(PY) -m src.consumers vessel-loader --max-messages $(or $(PIPELINE_MAX_MESSAGES),500)

pipeline-refresh:  ## GDELT + ACLED + AIS → Kafka → Neo4j → entity links → alerts
	$(PY) scripts/pipeline_refresh.py

train-risk:  ## Train XGBoost risk model with MLflow tracking
	MLFLOW_TRACKING_URI=file:./mlruns $(PY) scripts/train_risk_model.py

score-suppliers:  ## Score all suppliers and write risk_score to Neo4j
	$(PY) scripts/score_suppliers.py

rescore-recent:  ## Rescore suppliers with new :AFFECTS links (RESCORE_LOOKBACK_HOURS=24)
	$(PY) scripts/rescore_on_events.py

index-rag:  ## Index Neo4j events + METRICS.md + suppliers into Qdrant
	$(PY) scripts/index_rag_corpus.py

export-snapshots:  ## Export supplier graph snapshot CSV for TGN training
	$(PY) scripts/export_graph_snapshots.py

fetch-wgi:  ## Fetch World Bank WGI stability scores → data/wgi_stability.json
	$(PY) scripts/fetch_wgi_stability.py

seed-erp:  ## Ingest tier-N supplier edges from sample ERP CSV
	$(PY) scripts/ingest_erp_csv.py data/sample_erp_tiers.csv

pipeline-batch:  ## Refresh demo data without Kafka (PIPELINE_MODE=batch)
	PIPELINE_MODE=batch $(PY) scripts/pipeline_batch.py

portfolio-ready:  ## Full portfolio bootstrap: WGI → train → seed → score → export
	@echo "=== portfolio-ready: sequential demo bootstrap ==="
	@echo "Step 1/5 fetch-wgi"
	@$(MAKE) fetch-wgi
	@echo "Step 2/5 train-risk"
	@$(MAKE) train-risk
	@echo "Step 3/5 seed-all (requires Neo4j — skip if unavailable)"
	-@$(MAKE) seed-all
	@echo "Step 4/5 score-suppliers (requires Neo4j — skip if unavailable)"
	-@$(MAKE) score-suppliers
	@echo "Step 5/5 export-snapshots (requires Neo4j — skip if unavailable)"
	-@$(MAKE) export-snapshots
	@echo "portfolio-ready complete — see README Quick start"

check-deploy:  ## Validate deploy config files exist
	bash scripts/check_deploy_config.sh

demo:  ## Bootstrap infra, seed data, and run unit tests for portfolio demo
	bash scripts/demo.sh

validate-env:  ## Validate required env vars
	$(PY) scripts/validate_env.py --env-file .env

## --- Housekeeping ---

clean:  ## Remove pycache, build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -prune -exec rm -rf {} +
	find . -type d -name '.ruff_cache' -prune -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -prune -exec rm -rf {} +
	rm -f test_results.html
