# Meridian — Known Limitations & Honest Scope

Meridian is a **portfolio-grade demo** of supply chain geopolitical risk intelligence. This document states what the platform does and does not claim, aligned with critique layers A/B/C.

## Layer A — Product claims (what we show users)

| Claim | Reality in MVP |
|-------|----------------|
| SCRI is a calibrated disruption probability | **Modelled index** on 0–1 scale; bands (LOW→CRITICAL) are actionable tiers, not validated actuarial probabilities |
| XGBoost + SHAP explanations | Model runs; SHAP when library available; **default model may be synthetic-trained** until `models/risk_scorer.xgb` or MLflow artifact is deployed |
| Real-time risk alerts | In-memory alert buffer + optional Slack; not a 24/7 SOC pipeline |
| Monte Carlo simulation | ≥1,000 iterations; outputs **p10/p50/p90 bands**, not single point estimates |
| Causal impact on alerts | DoWhy when sample size permits; otherwise **association only** with explicit badge |

## Layer B — Data & features (what feeds the model)

| Signal | Status |
|--------|--------|
| GDELT / ACLED events → graph | Demo ingest path; not continuous production Kafka at scale |
| Conflict proximity, recent events | **Live** from Neo4j when seeded |
| Political stability (WGI) | **Cached World Bank WGI** via `make fetch-wgi`; static fallback when cache missing |
| Weather risk | **Default 0** — NOAA layer stub, not in SCRI features yet |
| Port congestion | **Partial** — derived from graph chokepoint vessel counts |
| Financial health, market volatility | **Heuristic defaults**, not ERP or market feeds |
| Sector dashboards | **Keyword classification** on supplier name/industry |
| Tier-N supply chain depth | **Not ingested** — single-hop graph demo |

## Layer C — Research / future track

| Capability | Status |
|------------|--------|
| TGN temporal forecasting | Research track; **LSTM fallback** when TGN weights unavailable |
| Labeled disruption dataset for calibration | Not built — see `docs/ROADMAP_FLAW_FIXES.md` Chunk 2 |
| ERP / tier-N graph expansion | Chunk 2+ |
| Live WGI at scale (auto-refresh) / sanctions / AIS | WGI cached on demand; continuous ingest deferred |
| Kafka-only microservice topology simplification | Documented, not refactored in Chunk 1 |

## How to read SCRI in the UI

1. Prefer **band labels** (CRITICAL, HIGH, …) over precise percentages.
2. Look for **"Modelled index"** or **"Demo calibration"** sublabels when `calibration_status` is `demo`.
3. Check **feature provenance** on supplier explanations (`X/13 features from live graph`).
4. Treat simulation outputs as **ranges** (p10–p90 delay days), not forecasts of record.

## API transparency endpoints

- `GET /metrics/methodology` — definitions, limitations, display guidance
- `GET /metrics/model-status` — model source, training status
- `GET /health` — includes `model` block when extended in Chunk 1

See also: `docs/METRICS.md`, `docs/CAUSAL_SCOPE.md`, `DECISIONS.md` (D-003, D-005).
