# Quickstart — your first event through Meridian (5 minutes)

This walks you from a clean checkout to seeing a real GDELT conflict event
land in Kafka and propagate through the platform.

## 0. Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11 or 3.12 (3.13 not supported yet) |
| Docker | latest |
| Node.js | 20+ (only if you want the UI) |

## 1. Clone and configure

```bash
git clone https://github.com/askmy-stack/meridian.git
cd meridian
cp .env.example .env
python scripts/validate_env.py --env-file .env
```

The validator will tell you which optional API keys you're missing (you can
ignore those for the quickstart — GDELT and NOAA are public and need no key).

## 2. Boot the infrastructure

```bash
docker compose up -d
```

This starts Kafka, Zookeeper, Neo4j, Postgres, TimescaleDB, Qdrant, and the
Kafka UI. Give it ~30 seconds.

Sanity check:

```bash
open http://localhost:7474        # Neo4j browser (neo4j / meridian_password)
open http://localhost:8081        # Kafka UI
```

## 3. Install Python deps and run tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make test-unit                    # ~5 seconds, no infra required
```

If unit tests pass, the codebase imports cleanly on your machine.

## 4. Send a real GDELT event through Kafka

```bash
python -m src.producers gdelt
```

You should see structured JSON logs like:

```json
{"event": "gdelt_event_published", "event_id": "12345...", "country": "TW"}
```

Open the Kafka UI (`http://localhost:8081`) and inspect the
`meridian.gdelt.conflict` topic — the event should be there.

## 5. Seed the knowledge graph (one command)

```bash
make demo    # compose up + seed ports, suppliers, and demo disruption events
# or step by step:
make seed-all
```

This loads major ports and chokepoints into Neo4j. Open the Neo4j browser and
run:

```cypher
MATCH (p:Port)-[:PASSES_THROUGH]->(c:Chokepoint) RETURN p, c LIMIT 25
```

You should see the supply-chain network graph.

## 6. Boot the API

```bash
uvicorn src.api.main:app --reload
```

Try a few endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/alerts
curl -X POST http://localhost:8000/alerts/test
curl http://localhost:8000/alerts            # the test alert is now in history
```

## 7. (Optional) Boot the dashboard

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Visit http://localhost:5173. Demo flow:

1. **Dashboard** — weekly digest after `make seed-all`
2. **Map** — geospatial risk (add `VITE_MAPBOX_TOKEN` for interactive tiles)
3. **Suppliers** — click a supplier for SHAP explanations
4. **Simulate** — run Red Sea / Taiwan / Suez preset scenarios
5. **Alerts** — use **Emit test alert** button

## What's next?

* Read [`ARCHITECTURE.md`](../ARCHITECTURE.md) for the system design.
* Read [`AGENTS.md`](../AGENTS.md) for the operating rules.
* Pick a `good first issue` from
  [GitHub](https://github.com/askmy-stack/meridian/labels/good%20first%20issue).

## Common gotchas

| Symptom | Fix |
|---------|-----|
| `pandas` build failure on `pip install` | Use Python 3.11 or 3.12, not 3.13 |
| Kafka UI shows zero brokers | Wait 30s; `docker compose restart kafka` if persistent |
| Neo4j `Unauthorized` | Default password is `meridian_password` — set `NEO4J_PASSWORD` in `.env` |
| `/auth/login` always 401 | Set `MERIDIAN_ADMIN_USERNAME` / `MERIDIAN_ADMIN_PASSWORD` in `.env` |
| CORS errors in browser | Set `CORS_ALLOWED_ORIGINS` in `.env` to include your frontend URL |
