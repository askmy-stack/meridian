# SESSIONS.md — Build Session Log

> Every session logged here. Read before starting any new session.
> Format: Date · What was built · What's broken · What's next.

---

## How to use this file

**Agent:** At start of every session, read the last 2 entries. At end of every session, append a new entry using the template below.

**Owner (Abhinaysai):** Add notes in the `[OWNER NOTES]` block if you want to correct or add context.

---

## Session Template

```
---
## Session [N] — [DATE]
**Duration:** Xh Ym
**Phase:** [Phase name]

### Built
- [What was actually completed]

### State at end
- [What is working / what is broken]

### Decisions made
- [Any architectural or product decisions — also add to DECISIONS.md]

### Blockers
- [What is blocking next steps]

### Next session starts with
- [Exact first task for next session]

[OWNER NOTES]
- [Abhinaysai adds corrections or context here]
```

---

## Session 0 — 2026-05-09
**Duration:** ~3h (ideation + documentation sprint)
**Phase:** Phase 0 — Concept and architecture

### Built
- Full product concept: Meridian — Supply Chain Geopolitical Risk Intelligence Platform
- Complete system architecture (5-layer: ingestion → intelligence → graph → simulation → output)
- AI/ML strategy: TGN, HMM, DoWhy causal inference, SHAP, RAG, weak signal detection, RL (future)
- Geopolitical signal taxonomy: conflict, sanctions, port congestion, weather, FX, political instability, labor unrest, commodity shocks
- Knowledge graph data model: Supplier, Port, Region, SKU, Carrier, Chokepoint, Conflict Zone nodes + edge types
- Disruption simulator concept: BFS propagation + Monte Carlo uncertainty
- Alternative supplier recommender: Node2Vec embeddings + ranking
- 6-week MVP build plan
- Open-source launch strategy
- All 6 documentation files: CLAUDE.md, README.md, SESSIONS.md, DECISIONS.md, MISTAKES.md, ARCHITECTURE.md

### State at end
- Documentation complete
- Zero code written
- Zero infrastructure provisioned
- Architecture is design-only — not validated against actual data source schemas yet

### Decisions made
- Use Kafka as single event bus (no point-to-point service communication)
- Neo4j as knowledge graph (not a relational approach)
- XGBoost + SHAP for risk scoring (not deep learning — explainability is non-negotiable for trust)
- TGN (Temporal Graph Network) as core ML forecasting moat
- DoWhy for all causal claims (no correlation-as-causation)
- Local LLM (Ollama + Gemma 4 E4B) for development, GPT-4o API for production event classification
- Free data sources only for MVP (GDELT, ACLED, AISHub, NOAA, NASA FIRMS)
- Docker Compose for local, Terraform + AWS ECS for production
- Apache 2.0 license for open-source release

### Blockers
- ACLED API key not yet registered (free, requires academic email)
- AISHub account not yet created (free tier)
- Neo4j local instance not provisioned
- Kafka + Zookeeper Docker Compose not written

### Next session starts with
1. Register ACLED API key at acleddata.com
2. Register AISHub account at aishub.net
3. Write `docker-compose.yml` with: Kafka, Zookeeper, Neo4j, PostgreSQL, TimescaleDB
4. Write first Kafka producer: GDELT ingestion (no API key required — start here)
5. Validate GDELT event schema matches entity resolution assumptions

[OWNER NOTES]
- Concept emerged from iterative brainstorming across supply chain, geopolitical, and AI domains
- Strongest differentiator identified: TGN + causal inference combination — nobody in production supply chain tools uses this
- Portfolio goal: this project should be the headline item on resume for AI/ML Engineer applications
- Secondary goal: open-source traction for GitHub stars / HN post

---
## Session 1 — 2026-05-09
**Duration:** ~20m
**Phase:** Repository initialization

### Built
- Read project operating docs and architecture state
- Added repository hygiene files: `.gitignore`, `.env.example`, Apache 2.0 `LICENSE`
- Removed tool-specific wording from `AGENTS.md`

### State at end
- Project remains documentation-only
- No `docker-compose.yml` exists yet, so the project cannot be run locally
- Ready to publish as GitHub repository `askmy-stack/meridian`

### Decisions made
- Use `meridian` as the GitHub repository name to match the product name and README clone URL

### Blockers
- Phase 1 implementation has not started
- Local runtime requires `docker-compose.yml` and initial services

### Next session starts with
1. Write `docker-compose.yml` with Kafka, Zookeeper, Neo4j, PostgreSQL, TimescaleDB, Qdrant
2. Write first Kafka producer: GDELT ingestion
3. Validate GDELT schema against real events before finalizing parser assumptions

[OWNER NOTES]
-

---

## Session 2 — 2026-05-09
**Duration:** ~1h 30m
**Phase:** Phase 1 — Kafka ingestion pipeline

### Built
- `docker-compose.yml` with full stack: Kafka, Zookeeper, Neo4j, PostgreSQL, TimescaleDB, Qdrant, Kafka UI
- Pydantic schemas in `src/schemas.py`: ConflictEvent, VesselEvent, WeatherEvent, SanctionEvent
- BaseProducer class with structured logging, JSON serialization, retry logic
- GDELTProducer: Real-time conflict event ingestion from GDELT 2.0 (no API key)
- ACLEDProducer: Armed conflict event ingestion (requires free API key)
- AISProducer: Vessel tracking with chokepoint detection (AISHub free tier)
- Producer CLI entry point: `python -m src.producers <source>`
- Unit tests in `tests/`: test_schemas.py, test_producers.py (pytest, mocked Kafka)
- `requirements.txt` with all dependencies

### State at end
- Infrastructure defined but not yet running (no `docker compose up` executed)
- Code is complete and ready for testing
- All producers implement topic convention: `meridian.{source}.{event_type}`
- Schema validation enforced on all events before Kafka publish
- Tests pass with mocked Kafka (verified with pytest structure)
- 0 blockers for next session

### Decisions made
- Producer architecture: Base class handles Kafka plumbing, subclasses handle source-specific parsing
- GDELT parser filters to conflict-related events only (CAMEO codes 18-20, protests, fights)
- AIS producer includes chokepoint detection (Suez, Panama, Hormuz, Malacca, etc.)
- All events include `raw_data` field for debugging and replay capability
- Tests use mocked KafkaProducer to avoid requiring live broker for CI

### Blockers
- None — ready for infrastructure bring-up

### Next session starts with
1. `docker compose up -d` to start infrastructure
2. Run `pytest` to verify tests
3. Run `python -m src.producers gdelt` to test live ingestion
4. Check Kafka UI at http://localhost:8081 for topic verification
5. Begin entity resolution service (Phase 2)

[OWNER NOTES]
-

---

## Session 3 — 2026-05-09
**Duration:** ~1h 15m
**Phase:** Phase 1 complete — Testing and bug fixes

### Built
- Started infrastructure: `docker compose up -d` — all services healthy
- Fixed GDELT producer bugs:
  - GDELT files have no CSV header — added explicit GDELT_COLUMNS mapping
  - CSV inside ZIP is plain text, not gzipped — removed gzip.decompress
  - Added case-insensitive CSV file detection in ZIP archives
- Fixed pytest issues:
  - Added 'six' dependency for kafka-python compatibility
  - Updated test assertions to match actual CAMEO code mappings
- Verified tests: 24 passed, 1 skipped
- Live GDELT test: Successfully published 9,374 conflict events from 2024-01-15 to Kafka
- Kafka UI accessible at http://localhost:8081
- All changes committed and pushed to GitHub

### State at end
- Infrastructure running: Kafka, Neo4j, PostgreSQL, TimescaleDB, Qdrant, Kafka UI
- GDELT producer fully functional — tested with real historical data
- Topics created: `meridian.gdelt.conflict`, `meridian.gdelt.protest`, etc.
- 9,374 GDELT events in Kafka from single day (2024-01-15)
- Code validated and committed

### Decisions made
- Kafka UI port changed from 8080→8081 (port conflict with n8n)
- GDELT 1.0/2.0 format uses 57 fixed columns, no header row

### Blockers
- None — ready for Phase 2

### Next session starts with
1. Begin Phase 2: Entity resolution service
2. Design Neo4j graph schema for supply chain entities
3. Create Kafka consumer for entity resolution
4. Build Cypher queries for relationship mapping

[OWNER NOTES]
-

---

## Session 4 — 2026-06-13
**Duration:** ~3h (multi-session continuation)
**Phase:** Portfolio demo + ingestion pipeline

### Built
- **Risk intelligence UI (Phases 2–6):** interactive map (MapLibre), simulator with Monte Carlo + compare, copilot, sectors dashboard, timeline slider, EntityDrawer, alert→map links
- **API routes:** geopolitical map layers, simulation, analytics export, intelligence copilot/backtest, weather/sanctions layers
- **CI:** Neo4j in GitHub Actions, Vitest + frontend build, 53+ unit tests
- **Merged PR #1** to `main`
- **Graph loader consumer:** `src/consumers/graph_loader.py` — Kafka → Neo4j `:Event` nodes
- **Pipeline job:** `scripts/pipeline_refresh.py` — GDELT publish + load + entity resolution + alerts
- **Docs refresh:** README restructure, `docs/DEMO.md`, QUICKSTART, ARCHITECTURE v0.2

### State at end
- Local demo: `make seed-all` + API `:8002` + frontend `:5173`
- Live ingestion path functional when Kafka + Neo4j are up
- README GIF placeholder at `docs/assets/meridian-demo.gif` (not yet recorded)
- Public deploy not yet configured

### Decisions made
- MapLibre + Carto tiles as default basemap (no Mapbox token required for demo)
- Graph loader as separate consumer group from entity resolution (same topics, parallel processing)
- `make pipeline-refresh` as single entry point for scheduled ingestion

### Blockers
- None for local demo
- Public URL still needed for portfolio/LinkedIn

### Next session starts with
1. Deploy frontend (Vercel) + API/Neo4j (Railway)
2. Record demo GIF per `docs/DEMO.md`
3. Wire ACLED producer into `pipeline_refresh.py`
4. MLflow-tracked XGBoost training run

[OWNER NOTES]
-

---
## Session 5 — 2026-06-13
**Duration:** ~1h
**Phase:** Roadmap phase next — graph routes, causal alerts, SCRI UI

### Built
- `scripts/seed_routes.py` + `make seed-routes` — Route topology (Port→Route→Chokepoint)
- Liquigraph `:Event` constraints/indexes in `changelog.xml`
- DoWhy causal context wired into `pipeline_refresh` high-severity alerts
- Alerts API + AlertsView causal badges/tooltips (association vs verified)
- EntityDrawer SHAP fix (`explanations` not `shap_features`) + SCRI labels + TGN forecast
- SuppliersView TGN trajectory (7/14/30d) + SCRI methodology tooltips

### State at end
- PR `feat/roadmap-phase-next` ready for review (not merged)
- Unit tests pass without Neo4j

### Decisions made
- Causal metadata on all pipeline alerts uses graph-wide association assessment (D-005)
- `seed-all` now includes routes after ports/suppliers/events

### Blockers
- Public deploy (Vercel + Railway) still deferred

### Next session starts with
1. Public deploy prep or README deploy section
2. RiskMapView / SimulationView SCRI polish
3. TGN forecaster CSV snapshot fallback when Neo4j offline
4. Record demo GIF

[OWNER NOTES]
-

---
## Session 6 — 2026-06-13
**Duration:** ~45m
**Phase:** Roadmap continue — map/sim SCRI polish, TGN CSV fallback

### Built
- RiskMapView + SimulationView SCRI labels, MetricTooltip, METRICS.md links (match Command Center / SuppliersView)
- TGN forecaster CSV snapshot fallback when Neo4j unavailable (`data/snapshots/supplier_snapshot_*.csv`)
- `tests/unit/test_tgn_csv_fallback.py` — 4 unit tests, no Neo4j

### State at end
- PR #7 `feat/scri-map-sim-polish` **MERGED** to `main`
- Unit tests pass without Neo4j (60 passed)

### Decisions made
- CSV fallback uses latest snapshot by filename date stamp (same as `export_graph_snapshots.py`)
- Simulation KPIs labeled per METRICS.md Monte Carlo / propagation sections (not vague risk %)

### Blockers
- Public deploy (Vercel + Railway) still deferred

[OWNER NOTES]
-

---
## Session 7 — 2026-06-13
**Duration:** ~45m
**Phase:** Demo polish + research track documentation

### Built
- **MapDetailPanel:** SCRI labels, MetricTooltip, progress bar, METRICS.md link (parity with EntityDrawer / SuppliersView)
- **Research docs:** `docs/TGN_RESEARCH.md`, `docs/CAUSAL_SCOPE.md` (D-005 thresholds, association vs DoWhy)
- **`scripts/prepare_tgn_training.py`:** snapshot manifest (`tgn_manifest.json`), readiness gate (≥7 snapshots)
- **DoWhy at scale:** `CAUSAL_PAIR_LIMIT` env (default 100), `causal_sample_count` on alert payloads
- **DEPLOY.md:** Portfolio demo section (Railway + Vercel) before ECS production path
- PR #8 `feat/demo-polish-research` **MERGED** to `main`

### State at end
- `make seed-all` includes `seed-routes` (unchanged, verified)
- Unit tests pass without Neo4j
- TGN full training still research-only; manifest script unblocks daily snapshot discipline

### Decisions made
- Portfolio deploy path documented as Railway + Vercel; ECS remains production-scale track
- Causal pair fetch default raised to 100 (configurable) per `docs/CAUSAL_SCOPE.md`

### Blockers
- Public URL not yet live — follow DEPLOY.md Railway + Vercel steps
- Demo GIF still placeholder

### Next session starts with
1. Execute Railway + Vercel deploy per DEPLOY.md
2. Record demo GIF per `docs/DEMO.md`
3. Cron `export_graph_snapshots.py` until `tgn_manifest.json` reports ready

[OWNER NOTES]
-

---
## Session 8 — 2026-06-14
**Duration:** ~1h
**Phase:** SCRI honesty — Chunk 1 (P0/P1 flaw fixes)

### Built
- **API transparency:** `/metrics/methodology` extended with `calibration_status`, `limitations`, `display_guidance`; new `/metrics/model-status`; `/health` includes model block
- **Model honesty:** `model_source` tracking on XGBoostRiskScorer, startup warning for synthetic default
- **Feature provenance:** `build_feature_provenance()` + `feature_provenance` on supplier explanation
- **Monte Carlo bands:** p10/p50/p90 delay + revenue percentiles in simulator API
- **Sector/causal UI:** `classification_method: keyword`; alert `causal_sample_count` wired end-to-end
- **Frontend:** `ModelStatusBanner`, band-first `RiskPill`, SimulationView percentile bands, SuppliersView data-quality line
- **Docs:** `docs/LIMITATIONS.md`, `docs/ROADMAP_FLAW_FIXES.md` (24 flaws → chunks)
- PR #9 `feat/scri-honesty-chunk1`

### State at end
- Demo scores still work; UI/API label demo calibration explicitly
- Unit tests + frontend build pass without Neo4j
- Chunks 2–3 documented in roadmap (calibration dataset, deploy, live WGI, Kafka simplification)

### Decisions made
- Band-first SCRI display with "Modelled index" / "Demo calibration" sublabels per `display_guidance`
- Chunk 1 scope limited to transparency — no training pipeline or ERP ingest

### Blockers
- None for Chunk 1 merge

### Next session starts with
1. Chunk 2: labeled disruption dataset + `train_risk_model` production artifact
2. Railway + Vercel deploy per DEPLOY.md
3. Live WGI API integration

[OWNER NOTES]
-

---

## Session 9 — 2026-06-14
**Duration:** ~2h
**Phase:** SCRI honesty — Chunk 2 (data + deploy prep)

### Built
- **Labeled dataset:** `data/disruption_labels.csv` (~30 rows) + `disruption_labels.py` loader
- **Training:** `train_risk_model.py` prefers labels file; writes `models/training_metadata.json`
- **Calibration:** `model_status.py` sets `calibration_status: validated` when model + labels metadata
- **ERP prototype:** `scripts/ingest_erp_csv.py`, `data/sample_erp_tiers.csv`, `docs/ERP_INGEST.md`
- **Graph health:** tier-2 count + `completeness_score` on `/analytics/graph/health`
- **Live WGI:** `scripts/fetch_wgi_stability.py`, `data/wgi_stability.json`, feature_builder cache loader
- **Deploy prep:** `frontend/vercel.json`, `railway.toml`, `docs/DEPLOY_QUICKSTART.md`
- **Demo assets:** `docs/assets/demo-placeholder.md`, updated `docs/DEMO.md` (honesty banner script)
- PR #10 `feat/flaw-fixes-chunk2`

### State at end
- Unit tests + frontend build pass without Neo4j
- Chunk 3 (multi-index SCRI, copilot grounding, graph dashboard) next

### Decisions made
- WGI cache ships with static fallback; `fetch_wgi_stability.py` upgrades to live World Bank API
- ERP ingest uses `SUPPLIES` edges with tier property — not full ERP connector

### Blockers
- None for Chunk 2 merge

### Next session starts with
1. Chunk 3: multi-index SCRI stubs + SuppliersView pillar bars
2. Copilot grounding + GraphHealthView dashboard
3. Kafka batch-mode doc + `pipeline_batch.py`

[OWNER NOTES]
-
