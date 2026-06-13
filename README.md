# Meridian

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/askmy-stack/meridian/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/askmy-stack/meridian/actions/workflows/ci-cd.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Geopolitical supply chain risk intelligence — live signals, a Neo4j knowledge graph, explainable risk scores, and disruption simulation.**

> Map conflict, shipping, and weather signals to **your** suppliers before they hit production.

<p align="center">
  <a href="docs/DEMO.md">
    <img src="docs/assets/meridian-hero.svg" alt="Meridian — supply chain risk map, simulator, and copilot" width="920" />
  </a>
  <br />
  <sub>Record a walkthrough GIF → <code>docs/assets/meridian-demo.gif</code> · <a href="docs/DEMO.md">demo script</a></sub>
</p>

**Repository:** [github.com/askmy-stack/meridian](https://github.com/askmy-stack/meridian)

---

## At a glance

| Surface | What you get |
|---------|----------------|
| [**Command Center**](docs/DEMO.md) | KPIs, weekly digest, markdown export |
| [**Risk map**](docs/DEMO.md) | MapLibre globe — conflict zones, trade routes, events, NOAA weather, sanctions |
| [**Simulator**](docs/DEMO.md) | Six geopolitical presets · BFS propagation · 1,000-run Monte Carlo · side-by-side compare |
| [**Copilot**](docs/DEMO.md) | Natural language → scenario + supplier context |
| [**Sectors**](docs/DEMO.md) | Semiconductor, energy, automotive, shipping roll-ups |
| [**Alerts**](docs/DEMO.md) | Tiered feed, test emit, map deep links, persistent history |
| [**Pipeline**](docs/QUICKSTART.md#5-live-pipeline-gdelt--kafka--neo4j) | GDELT → Kafka → Neo4j → entity links → alerts |

📖 [**Quickstart (5 min)**](docs/QUICKSTART.md) · 🎬 [**Demo script (2–3 min)**](docs/DEMO.md) · 🤝 [**Contributing**](CONTRIBUTING.md)

---

## Why Meridian

Major disruptions — Suez, Red Sea, Taiwan Strait, Ukraine — showed up first in **open signals** (GDELT, AIS, ACLED), not in quarterly supplier reviews.

Meridian connects those signals to suppliers, ports, and chokepoints in Neo4j, scores exposure with explainable ML, and lets you **simulate** impact before it lands on the P&L.

---

## Architecture

```
 GDELT · ACLED · AIS              React app (Vite + MapLibre)
        │                                    ▲
        ▼                                    │
     Kafka ──► Graph loader ──► Neo4j ◄──── FastAPI
        │            │            ▲
        └──► Entity resolution ─────┘
                         │
              XGBoost + SHAP · Monte Carlo · Slack alerts
```

Details: [ARCHITECTURE.md](ARCHITECTURE.md) · Decisions: [DECISIONS.md](DECISIONS.md)

---

## Quickstart

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11 or 3.12 |
| Docker | Latest |
| Node.js | 20+ (frontend) |

### Run locally

```bash
git clone https://github.com/askmy-stack/meridian.git
cd meridian
cp .env.example .env

# Neo4j bolt is on host port 7688 (see docker-compose.yml)
# NEO4J_URI=bolt://localhost:7688

docker compose up -d neo4j kafka zookeeper

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a

make seed-all
# If `python3` lacks deps: PY=/path/to/venv/bin/python make seed-all

# Terminal 1
uvicorn src.api.main:app --reload --port 8002

# Terminal 2
cd frontend && npm install && npm run dev
```

| URL | Service |
|-----|---------|
| http://localhost:5173 | Dashboard |
| http://localhost:8002/docs | API |
| http://localhost:7475 | Neo4j Browser |
| http://localhost:8081 | Kafka UI |

One-shot bootstrap: `make demo` ([`scripts/demo.sh`](scripts/demo.sh))

### Live ingestion

```bash
make ingest-gdelt          # GDELT → meridian.gdelt.* topics
make load-graph            # Kafka → Neo4j :Event nodes
make pipeline-refresh      # publish + load + entity resolution + alerts
```

Topic convention: `meridian.{source}.{event_type}`

---

## Tech stack

| Layer | Stack |
|-------|--------|
| Streaming | Apache Kafka |
| Graph | Neo4j 5 |
| API | FastAPI, JWT, structlog |
| ML | XGBoost, SHAP, MLflow-tracked training |
| Frontend | React 18, Vite, MapLibre / optional Mapbox, Recharts |
| CI | GitHub Actions (Neo4j + pytest + frontend build) |

---

## Project layout

```
meridian/
├── src/
│   ├── producers/          # GDELT, ACLED, AIS → Kafka
│   ├── consumers/          # Graph loader, entity resolution
│   ├── api/                # FastAPI (map, sim, copilot, alerts, analytics)
│   ├── graph/              # Neo4j client
│   ├── simulation/         # BFS + Monte Carlo
│   ├── geopolitical/       # Conflict zones, supplemental layers
│   └── alerting/           # Slack + file-backed persistence
├── frontend/               # React dashboard (9 routes)
├── scripts/                # Seeds, pipeline_refresh.py, demo.sh
├── tests/                  # pytest (unit + integration)
└── docs/                   # QUICKSTART, DEMO, assets
```

---

## Data sources (free tier)

| Source | Signal |
|--------|--------|
| [GDELT](https://www.gdeltproject.org/) | Global news events |
| [ACLED](https://acleddata.com/) | Armed conflict (academic key) |
| [AISHub](https://www.aishub.net/) | Vessel tracking |
| NOAA / NASA FIRMS | Weather & disasters |
| OpenSanctions | Sanctions entities |

---

## Roadmap

| Milestone | Status |
|-----------|--------|
| Portfolio demo (map, simulator, copilot, CI) | ✅ Shipped |
| GDELT → Kafka → Neo4j pipeline | ✅ Shipped |
| Public deploy (Vercel + Railway) | 🔜 Next |
| MLflow-tracked XGBoost training | ✅ Shipped |
| ACLED + AIS in `pipeline_refresh` | ✅ Shipped |
| TGN + DoWhy causal layer | 🟡 MVP shipped (forecast API, DoWhy wrapper, BFS Monte Carlo); full TGN training still research |

Good first issues: [labels/good first issue](https://github.com/askmy-stack/meridian/labels/good%20first%20issue)

---

## Author

**Abhinaysai Kamineni** — MS Data Science, George Washington University  

[GitHub](https://github.com/askmy-stack) · [LinkedIn](https://linkedin.com/in/abhinaysai-kamineni)

---

## License

[Apache 2.0](LICENSE) — use it, fork it, build on it.
