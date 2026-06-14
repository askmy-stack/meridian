# Meridian

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/askmy-stack/meridian/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/askmy-stack/meridian/actions/workflows/ci-cd.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Supply Chain Risk Intelligence (SCRI)** — geopolitical signals, a Neo4j knowledge graph, explainable risk scores, and disruption simulation.

> Every major supply chain disruption of the last 20 years was visible in open signals weeks before impact. Meridian connects GDELT, conflict, shipping, and weather data to **your** suppliers with honest calibration labels — band-first SCRI display, not false precision.

<p align="center">
  <a href="docs/DEMO.md">
    <img src="docs/assets/meridian-demo.gif" alt="Meridian demo walkthrough" width="920"
         onerror="this.onerror=null;this.src='docs/assets/meridian-hero.svg'" />
  </a>
  <br />
  <sub>Record GIF: <code>bash scripts/record_demo.sh</code> · <a href="docs/DEMO.md">2-min demo script</a> · placeholder until recorded</sub>
</p>

**Repository:** [github.com/askmy-stack/meridian](https://github.com/askmy-stack/meridian)

---

## At a glance

| Surface | What you get |
|---------|----------------|
| [**Command Center**](docs/DEMO.md) | KPIs, ModelStatusBanner, weekly digest, markdown export |
| [**Risk map**](docs/DEMO.md) | MapLibre globe — conflict zones, trade routes, NOAA weather, sanctions |
| [**Simulator**](docs/DEMO.md) | Six presets · BFS propagation · Monte Carlo p10/p50/p90 bands |
| [**Copilot**](docs/DEMO.md) | Graph-grounded Q&A with uncertainty fallback |
| [**Graph health**](docs/DEMO.md) | Tier-2 coverage, completeness score, model calibration |
| [**Alerts**](docs/DEMO.md) | Tiered feed, causal association badges, map deep links |

📖 [**Quickstart**](docs/QUICKSTART.md) · 🎬 [**Demo script**](docs/DEMO.md) · ⚠️ [**Limitations**](docs/LIMITATIONS.md) · 🚀 [**Deploy**](docs/DEPLOY_QUICKSTART.md)

---

## Quick start (portfolio demo)

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11 or 3.12 |
| Docker | Latest (Neo4j) |
| Node.js | 20+ (frontend) |

```bash
git clone https://github.com/askmy-stack/meridian.git
cd meridian
cp .env.example .env
# NEO4J_URI=bolt://localhost:7688  (host port from docker-compose.yml)

docker compose up -d neo4j
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a

make portfolio-ready   # WGI fetch → train model → seed → score → export
```

**Terminal 1 — API**

```bash
make dev               # uvicorn on :8002
```

**Terminal 2 — Frontend**

```bash
make dev-frontend      # Vite on :5173
```

Open **http://localhost:5173**

| URL | Service |
|-----|---------|
| http://localhost:5173 | Dashboard |
| http://localhost:8002/docs | API |
| http://localhost:7475 | Neo4j Browser |

### ERP tier-N demo (optional)

```bash
make seed-all
python scripts/ingest_erp_csv.py data/sample_erp_tiers.csv
# or: make seed-erp
```

### Batch pipeline (no Kafka)

Laptop-friendly refresh without streaming infra:

```bash
make pipeline-batch    # demo scenarios + rescore suppliers
```

See [`docs/ARCHITECTURE_DEMO.md`](docs/ARCHITECTURE_DEMO.md).

### One-shot bootstrap

```bash
make demo              # scripts/demo.sh — infra + seed + unit tests
make check-deploy      # validate Vercel/Railway config files
```

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

## Live ingestion (optional)

```bash
docker compose up -d kafka zookeeper
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
| Frontend | React 18, Vite, MapLibre, Recharts |
| CI | GitHub Actions (Neo4j + pytest + frontend build) |

---

## Project layout

```
meridian/
├── src/                    # producers, consumers, api, graph, simulation
├── frontend/               # React dashboard (11 routes)
├── scripts/                # portfolio-ready, train, seed, pipeline_batch
├── data/                   # disruption_labels.csv, sample ERP tiers, WGI cache
├── tests/                  # pytest (unit + integration)
└── docs/                   # DEMO, LIMITATIONS, DEPLOY_QUICKSTART
```

---

## Data sources (free tier)

| Source | Signal |
|--------|--------|
| [GDELT](https://www.gdeltproject.org/) | Global news events |
| [ACLED](https://acleddata.com/) | Armed conflict (academic key) |
| [AISHub](https://www.aishub.net/) | Vessel tracking |
| World Bank WGI | Political stability (`make fetch-wgi`) |
| NOAA / NASA FIRMS | Weather & disasters |
| OpenSanctions | Sanctions entities |

Training labels: `data/disruption_labels.csv` — 50+ public disruption case studies (Suez 2021, Fukushima, Taiwan earthquake, Red Sea, COVID lockdowns, etc.)

---

Good first issues: [labels/good first issue](https://github.com/askmy-stack/meridian/labels/good%20first%20issue)

---

## License

[Apache 2.0](LICENSE) — use it, fork it, build on it.
