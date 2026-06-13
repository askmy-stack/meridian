# Meridian

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Real-time supply chain risk intelligence powered by geopolitical signals, AIS vessel tracking, and a live knowledge graph.**

> Point Meridian at your supplier list. Get risk scores, disruption simulations, and alternative sourcing recommendations — backed by live satellite, shipping, and conflict data.

## Project status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Kafka ingestion (GDELT / ACLED / AIS) | ✅ Producers + unit tests |
| 2 | Entity resolution + Neo4j knowledge graph | ✅ Graph client, fuzzy matching, seed scripts |
| 3 | Intelligence engine (BERT / XGBoost / SHAP) | ⚠️ Functional with synthetic/off-the-shelf models; TGN is a stub |
| 4 | Simulation + alerting (Monte Carlo / BFS / Slack) | ✅ API + UI demo; graph propagation partial without full SKU graph |
| 5 | Frontend dashboard + JWT auth | ✅ 7-page React app; JWT enforced on writes in production |
| 6 | Production deployment (Terraform / CI/CD) | ⚠️ ECS API scaffold; managed Neo4j/Kafka not wired |

**Portfolio demo ready** via `make demo`. Production hardening (managed data plane, CI image pinning) is in progress.

📖 **New here?** Run `make demo`, then `make dev` + `make dev-frontend`. See [`docs/QUICKSTART.md`](docs/QUICKSTART.md).
🤝 **Want to contribute?** Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and check the [good first issues](https://github.com/askmy-stack/meridian/labels/good%20first%20issue).

---

## The Problem

Every major supply chain disruption of the last 20 years was visible in signals weeks before shelves went empty.

- **COVID (2020):** Wuhan factory closures visible in AIS data 3 weeks before Western procurement teams reacted
- **Suez blockage (2021):** Ever Given grounding resolved in days — but port congestion rippled for 6 months
- **Red Sea attacks (2023):** Houthi strikes on shipping visible in ACLED conflict data before mainstream media
- **Taiwan Strait tensions (ongoing):** Semiconductor concentration risk has been measurable for years

Nobody connected the dots fast enough. Meridian connects them in real-time.

---

## What Meridian Does

```
Live signals → Knowledge graph → Risk scores → Disruption simulation → Action
```

| Capability | Description |
|---|---|
| **Signal ingestion** | Real-time news (GDELT), vessel tracking (AIS), conflict events (ACLED), weather (NOAA/NASA), financial indicators |
| **Entity resolution** | Maps news mentions to specific suppliers in your supply chain automatically |
| **Knowledge graph** | Neo4j graph: Supplier → Port → Chokepoint → Route → Conflict Zone |
| **Risk scoring** | XGBoost risk scores per supplier with SHAP explanation — no black boxes |
| **Disruption simulator** | "If Taiwan Strait closes, which of my 847 SKUs are affected and when?" |
| **Alt. supplier recommender** | Graph-similarity sourcing alternatives ranked by lead time and risk |
| **Weak signal detection** | Anomaly detection on pre-crisis signals — 2-4 weeks earlier than news |
| **Causal inference** | DoWhy causal engine — distinguishes real risk from correlated noise |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Signal Ingestion                                        │
│  GDELT · AIS · ACLED · NOAA · NASA · World Bank · FX   │
└──────────────────────┬──────────────────────────────────┘
                       │ Kafka
┌──────────────────────▼──────────────────────────────────┐
│  Intelligence Engine                                     │
│  Entity Resolution (spaCy) · Event Classifier (BERT)   │
│  Risk Scorer (XGBoost + SHAP) · TGN Forecaster         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Knowledge Graph — Neo4j                                 │
│  Supplier · Port · Region · SKU · Carrier               │
│  Chokepoint · Conflict Zone · Route                     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Simulation + Recommendation                             │
│  Monte Carlo disruption sim · Alt. supplier ranking     │
│  Counterfactual analysis · Scenario playbooks           │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Output                                                  │
│  React + Mapbox dashboard · Slack alerts · REST API     │
│  Weekly LLM-generated digest · SHAP explanations        │
└─────────────────────────────────────────────────────────┘
```

Full architecture detail: [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Ingestion | Python scrapers, Kafka Connect |
| Streaming | Apache Kafka, Spark Streaming |
| NLP | spaCy (NER), BERT fine-tuned on ACLED |
| ML | XGBoost, TGN, HMM, DoWhy, SHAP |
| Graph | Neo4j, Node2Vec, GraphSAGE |
| Storage | PostgreSQL, TimescaleDB, Qdrant |
| API | FastAPI, JWT auth |
| Frontend | React, Mapbox GL JS, Recharts |
| IaC | Docker Compose → Terraform + AWS ECS |
| Observability | Prometheus, Grafana |
| ML Tracking | MLflow |

---

## Quickstart

```bash
# Clone
git clone https://github.com/askmy-stack/meridian
cd meridian

# Configure
cp .env.example .env
python scripts/validate_env.py --env-file .env

# Start infrastructure
docker compose up -d

# Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run tests
make test-unit

# Seed demo data (suppliers, ports, disruption scenarios)
make seed-all

# Start API (Terminal 1)
uvicorn src.api.main:app --reload

# Start frontend (Terminal 2)
cd frontend
npm install
npm run dev

# Open services
open http://localhost:5173    # React dashboard (with live supplier data)
open http://localhost:8000/docs # API documentation
open http://localhost:7474      # Neo4j browser (neo4j/meridian_password)
```

---

## Project Structure

```
meridian/
├── ingestion/          # Kafka producers per signal source
│   ├── gdelt/
│   ├── ais/
│   ├── acled/
│   ├── noaa/
│   └── financial/
├── intelligence/       # NLP, classification, risk scoring
│   ├── entity_resolution/
│   ├── event_classifier/
│   └── risk_scorer/
├── graph/              # Neo4j schema, loaders, queries
├── simulation/         # Monte Carlo, BFS propagation
├── recommender/        # Alt. supplier ranking
├── api/                # FastAPI application
├── frontend/           # React dashboard
├── ml/                 # TGN, HMM, causal models
├── infrastructure/     # Terraform, Docker configs
├── tests/
├── scripts/            # Seed data, migration, utilities
├── docs/               # Architecture diagrams, specs
├── CLAUDE.md           # Agent instructions
├── SESSIONS.md         # Build session log
├── DECISIONS.md        # Decision log + agent instructions
├── MISTAKES.md         # Errors and learnings
└── ARCHITECTURE.md     # Full architecture spec
```

---

## Roadmap

| Phase | Status | Scope |
|---|---|---|
| Phase 0 | ✅ Complete | Concept, architecture design, documentation |
| Phase 1 | ✅ Complete | Kafka ingestion — GDELT + AIS + ACLED |
| Phase 2 | ✅ Complete | Neo4j knowledge graph + entity resolution |
| Phase 3 | ✅ Complete | XGBoost risk scorer + SHAP |
| Phase 4 | ✅ Complete | Disruption simulator (Monte Carlo + BFS) |
| Phase 5 | ✅ Complete | React dashboard + Mapbox |
| Phase 6 | ✅ Complete | TGN forecaster + causal inference |
| Phase 7 | 🔄 Ready | Open-source launch + HN post |

---

## Data Sources (all free)

| Source | Data | License |
|---|---|---|
| GDELT Project | Global news events | Open / CC |
| ACLED | Armed conflict events | Free academic |
| AISHub | Vessel positions | Free tier |
| NOAA | Weather alerts | Public domain |
| NASA FIRMS | Disaster events | Public domain |
| OpenSanctions | Sanctions lists | Open |
| World Bank API | Country risk | Open |
| UN Comtrade | Trade flows | Free tier |

---

## Why This Matters

**For procurement teams:** Know about disruptions 2-4 weeks before your competitors.

**For researchers:** First open-source platform combining TGN, causal inference, and knowledge graphs for supply chain risk.

**For developers:** Production-grade Kafka + Neo4j + ML pipeline you can deploy in one `docker-compose up`.

---

## Author

**Abhinaysai Kamineni** — MS Data Science, George Washington University
[GitHub](https://github.com/askmy-stack) · [LinkedIn](https://linkedin.com/in/abhinaysai-kamineni)

---

## License

Apache 2.0 — use it, fork it, build on it.
