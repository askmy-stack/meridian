# Phase A — Real Data Foundation

Meridian Phase A adds durable time-series history, richer event→supplier link metadata, and batch rescore triggers without requiring Kafka in the demo path.

## Architecture

```mermaid
flowchart LR
    subgraph ingest [Ingestion]
        GDELT[GDELT / ACLED]
        GL[graph_loader]
    end
    subgraph graph [Neo4j]
        E[Event]
        S[Supplier]
        E -->|AFFECTS link_method confidence linked_at| S
    end
    subgraph score [Scoring]
        SS[score_suppliers.py]
        RS[rescore_on_events.py]
        XGB[XGBoost + SHAP]
    end
    subgraph ts [TimescaleDB]
        SSH[supplier_score_history]
        ESH[event_signal_history]
    end
    GDELT --> GL --> E
    GL --> E
    SS --> XGB --> S
    SS --> SSH
    RS --> SSH
    GL --> ESH
```

**LLM does not score risk** — XGBoost produces scores; TimescaleDB stores history only.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TIMESCALE_URL` | Optional | Full DSN, e.g. `postgresql://meridian:pass@localhost:5433/meridian_timeseries` |
| `TIMESCALE_HOST` | Optional | Host when URL not set (default `localhost`) |
| `TIMESCALE_PORT` | Optional | Port (default `5433`) |
| `TIMESCALE_DB` | Optional | Database name (default `meridian_timeseries`) |
| `RESCORE_LOOKBACK_HOURS` | Optional | Window for `make rescore-recent` (default `24`) |

When TimescaleDB is down or unset, scripts log `timescale_history_skipped` and continue — same graceful pattern as Neo4j in unit tests.

## Database init

Hypertables are created on first `docker compose up` via:

`scripts/init_timescale.sql` → mounted to `docker-entrypoint-initdb.d/`

**Tables:**

- `supplier_score_history` — `supplier_id`, `risk_score`, `risk_category`, `model_version`, `feature_snapshot` (JSONB), `scored_at`
- `event_signal_history` — `event_id`, `severity`, `source`, `linked_supplier_count`, `ingested_at`

## Make targets

| Target | Purpose |
|--------|---------|
| `make up` | Starts TimescaleDB with init script |
| `make fetch-wgi` | Refresh `data/wgi_stability.json` (included in `portfolio-ready`) |
| `make score-suppliers` | Score all suppliers → Neo4j + TimescaleDB history |
| `make rescore-recent` | Rescore suppliers with new `:AFFECTS` in last N hours |
| `make load-graph` | Kafka → Neo4j + geospatial/country links + event batch log |

## Event → supplier link methods

`:AFFECTS` edges carry:

| Property | Description |
|----------|-------------|
| `link_method` | `geospatial`, `country_match`, `demo_seed`, or `manual` |
| `confidence` | 0–1 match strength |
| `linked_at` | When the edge was created |

Exposed on `GET /analytics/graph/health` as `avg_link_confidence`.

## Label schema v2 (foundation)

`data/disruption_labels.csv` adds optional columns:

- `delay_days` — estimated delivery delay
- `volume_impact_pct` — estimated volume impact

Loader: `load_disruption_label_rows()` in `src/intelligence/disruption_labels.py` (backward compatible with training via `load_disruption_labels()`).

**Target for Phase B:** expand to **500+ labeled rows** with verified `delay_days` / `volume_impact_pct` from public case studies and ERP backtests.

## Path to Phase B

1. Kafka consumer triggers `rescore_on_events` on `meridian.scoring.rescore` topic
2. Continuous WGI refresh cron + staleness alerts
3. Full label corpus (500 rows) + retrain with impact-weighted features
4. TimescaleDB-backed risk timeline API for frontend sparklines

## Local verification

```bash
make up
make fetch-wgi
make seed-all          # requires Neo4j
make score-suppliers   # writes Neo4j + TimescaleDB if up
make rescore-recent
python3 -m pytest tests/unit/ -m "not neo4j_required" -q
```
