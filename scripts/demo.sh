#!/usr/bin/env bash
# One-command Meridian demo bootstrap (local development).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Meridian demo setup"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — set NEO4J_PASSWORD=meridian_password to match docker-compose"
fi

echo "==> Starting infrastructure (Neo4j on 7475/7688 — avoids Cortex port conflicts)"
docker compose up -d neo4j zookeeper
sleep 12

set -a
# shellcheck disable=SC1091
source .env
set +a

echo "==> Validating environment"
python3 scripts/validate_env.py --env-file .env || true

echo "==> Seeding Neo4j demo data"
python3 -m src.seeding.ports_chokepoints
python3 scripts/seed_suppliers.py --file data/sample_suppliers.csv
python3 scripts/seed_demo_scenarios.py

echo "==> Running unit tests (no Neo4j required)"
python3 -m pytest tests/unit/ -m "not neo4j_required" -q

echo ""
echo "Demo stack is ready."
echo "  API:      uvicorn src.api.main:app --reload --port 8002"
echo "  Frontend: cd frontend && npm install && npm run dev"
echo "  URLs:     http://localhost:5173  |  http://localhost:8002/docs"
echo ""
echo "Optional: python3 -m src.producers gdelt  # ingest live GDELT events"
