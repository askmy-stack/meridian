# Quickstart — your first event through Meridian (5 minutes)

This walks you from a clean checkout to seeing a GDELT conflict event land in
Kafka, load into Neo4j, and appear on the dashboard.

## 0. Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11 or 3.12 (3.13 not supported yet) |
| Docker | latest |
| Node.js | 20+ |

## 1. Clone and configure

```bash
git clone https://github.com/askmy-stack/meridian.git
cd meridian
cp .env.example .env
python scripts/validate_env.py --env-file .env
```

Set `NEO4J_URI=bolt://localhost:7688` (docker-compose maps bolt to **7688** on the host).

## 2. Boot infrastructure

```bash
docker compose up -d neo4j kafka zookeeper
```

| URL | Service |
|-----|---------|
| http://localhost:7475 | Neo4j Browser (`neo4j` / password from `.env`) |
| http://localhost:8081 | Kafka UI |

## 3. Install deps and test

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make test-unit
```

## 4. Seed the knowledge graph

```bash
set -a && source .env && set +a
make seed-all
```

Loads ports, chokepoints, 30 suppliers, and 8 demo geopolitical events.

## 5. Live pipeline (GDELT → Kafka → Neo4j)

```bash
python -m src.producers gdelt          # publish to meridian.gdelt.*
make load-graph                        # upsert :Event nodes
# or full job:
make pipeline-refresh                  # publish + load + entity links + alerts
```

Verify in Kafka UI → topic `meridian.gdelt.conflict`.

## 6. Start API + frontend

```bash
# Terminal 1
uvicorn src.api.main:app --reload --port 8002

# Terminal 2
cd frontend && cp .env.example .env.local && npm install && npm run dev
```

Visit http://localhost:5173

**Demo flow** ([full script](./DEMO.md)):

1. **Command Center** — digest + export
2. **Simulator** — Red Sea scenario + map overlay
3. **Risk Map** — conflict zones, weather/sanctions toggles
4. **Copilot** — natural-language scenario hint
5. **Alerts** — emit test alert → view on map

## API smoke test

```bash
curl http://localhost:8002/health
curl http://localhost:8002/geopolitical/conflict-zones
curl -X POST http://localhost:8002/alerts/test
curl http://localhost:8002/alerts
```

## Common gotchas

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: structlog` on `make seed-all` | Use venv/conda Python with `pip install -r requirements.txt` |
| Neo4j connection refused | `docker compose up -d neo4j`; use port **7688** in `.env` |
| Map shows no tiles | MapLibre works without token; optional `VITE_MAPBOX_TOKEN` in `.env.local` |
| Kafka UI empty | Wait 30s after `docker compose up`; run `make ingest-gdelt` |

## What's next?

* [DEMO.md](./DEMO.md) — 2–3 minute recording script
* [ARCHITECTURE.md](../ARCHITECTURE.md) — system design
* [AGENTS.md](../AGENTS.md) — contributor rules
