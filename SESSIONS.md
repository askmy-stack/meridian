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

---

## Session 10 — 2026-06-14
**Duration:** ~2h
**Phase:** SCRI honesty — Chunk 3 (architecture + UX completion)

### Built
- **Batch demo path:** `docs/ARCHITECTURE_DEMO.md`, `scripts/pipeline_batch.py`
- **Multi-index SCRI:** `pillar_scores` on explanation API + SuppliersView pillar mini-bars
- **Feature layers:** NOAA weather + OpenSanctions stub in `feature_builder` + provenance
- **Copilot grounding:** graph facts, disclaimer banner, uncertainty fallback
- **GraphHealthView:** `/ops/graph-health` dashboard (geo, events, tier-2, model status)
- **Digest honesty:** `narrative_type: template` + Dashboard label
- PR #11 `feat/flaw-fixes-chunk3`

### State at end
- 24/24 flaws addressed (3 partial: live AIS, deploy execution, demo GIF recording)
- Unit tests + frontend build pass without Neo4j

### Decisions made
- Pillar scores are weighted feature sums — not separate ML models
- Batch pipeline reuses seed/score scripts — no Kafka shortcut into graph_loader

### Blockers
- None for Chunk 3 merge

### Next session starts with
1. Merge PRs #9–#11 (chunk1 → chunk2 → chunk3)
2. Optional: live deploy per DEPLOY_QUICKSTART.md
3. Record demo GIF

[OWNER NOTES]
-

---
## Session 11 — 2026-06-14
**Duration:** ~2h
**Phase:** Portfolio demo ready — data credibility + Makefile + docs

### Built
- **Labels:** `data/disruption_labels.csv` expanded to 50+ rows (Suez, Fukushima, Taiwan earthquake, Red Sea, COVID, Ukraine, etc.)
- **Makefile:** `portfolio-ready`, `fetch-wgi`, `seed-erp`, `pipeline-batch`, `check-deploy`
- **ERP demo:** expanded `data/sample_erp_tiers.csv` (22 tier edges)
- **Scripts:** `record_demo.sh`, `check_deploy_config.sh`
- **Docs:** README hero + quick start, `docs/DEMO.md` (GraphHealth, pillars, batch), DEPLOY_QUICKSTART env fix
- **Frontend:** `VITE_API_URL` alias in client; `.env.example` production notes
- PR #13 `feat/portfolio-demo-ready`

### State at end
- Unit tests + frontend build pass without Neo4j
- `make portfolio-ready` trains model + fetches WGI; Neo4j steps skip gracefully if down
- Demo GIF still placeholder until `bash scripts/record_demo.sh`
- Deploy config validated; execution deferred (no secrets)

### Decisions made
- `portfolio-ready` uses `-` prefix on Neo4j steps so WGI + train succeed offline
- SCRI honesty thesis front-and-center in README hero

### Blockers
- None for merge; live deploy requires owner credentials

### Next session starts with
1. Record `docs/assets/meridian-demo.gif`
2. Execute Railway + Vercel deploy per DEPLOY_QUICKSTART.md
3. Cron daily `export_graph_snapshots.py` for TGN manifest readiness

[OWNER NOTES]
-

---

## Session 12 — 2026-06-14
**Duration:** ~2h
**Phase:** Phase A — Real data foundation

### Built
- **TimescaleDB:** `scripts/init_timescale.sql`, hypertables `supplier_score_history` + `event_signal_history`, `src/storage/timescale_writer.py`
- **Hooks:** `score_suppliers.py` + `graph_loader.py` append history; graceful skip when TimescaleDB down
- **Link confidence:** `:AFFECTS` edges get `link_method`, `confidence`, `linked_at` (geospatial, country_match, demo_seed, manual)
- **Rescore:** `scripts/rescore_on_events.py`, `make rescore-recent`
- **Labels v2:** optional `delay_days`, `volume_impact_pct` on `disruption_labels.csv` + `load_disruption_label_rows()`
- **WGI:** provenance logging on every feature build; cache-hit unit test
- **Docs:** `docs/REAL_DATA_PHASE_A.md`; graph health `avg_link_confidence`
- PR #14 `feat/phase-a-real-data`

### State at end
- Unit tests pass without Neo4j or TimescaleDB
- TimescaleDB init runs on fresh `docker compose up` volume
- Label corpus still ~83 rows — 500-row target documented for Phase B

### Decisions made
- TimescaleDB optional (TIMESCALE_URL) — demo never hard-depends on it
- Batch rescore via script; Kafka trigger deferred to Phase B
- Fuzzy NER links use `link_method=manual`

### Blockers
- None for merge

### Next session starts with
1. Phase B: Kafka rescore consumer + risk timeline API
2. Expand labels toward 500 rows with verified impact fields
3. Merge PR #13 then #14

[OWNER NOTES]
-

---

## Session 13 — 2026-06-14
**Duration:** ~3h
**Phase:** Phase B — Intelligence layer

### Built
- **Qdrant RAG:** `src/rag/` (qdrant_client, embedder hash/MiniLM fallback, collections, copilot_service)
- **Index script:** `scripts/index_rag_corpus.py`, `make index-rag`
- **Grounded copilot:** RAG retrieval + citations[], `LLM_PROVIDER=stub|ollama|openai`, D-006 risk-score refusal
- **Event classifier:** `src/intelligence/event_classifier.py` — structured JSON, optional graph_loader hook
- **Conformal SCRI:** `src/intelligence/conformal.py` → `score_interval` on supplier explanation API
- **Changepoint:** `src/intelligence/changepoint.py` CUSUM + `/intelligence/suppliers/{id}/weak-signals`
- **Frontend:** CopilotView citations + disclaimer; SuppliersView interval band
- **Docs:** `docs/REAL_DATA_PHASE_B.md`; link from Phase A
- PR #15 `feat/phase-b-rag-intelligence`

### State at end
- Unit tests pass without Qdrant, Ollama, or Neo4j
- Demo works with hash embedder and stub LLM
- sentence-transformers optional via `requirements-dev.txt`

### Decisions made
- Hash embedder default for CI; MiniLM opt-in
- Conformal calibration from disruption_labels.csv holdout
- ENABLE_LLM_CLASSIFIER=false by default

### Blockers
- None

### Next session starts with
1. Phase C: Kafka rescore consumer + risk timeline API
2. Expand labels toward 500 rows
3. Merge PR #14 then #15

[OWNER NOTES]
-

---

## Session 14 — 2026-06-14
**Duration:** ~4h
**Phase:** Phase C — Predictive & causal research layer

### Built
- **TGN v1:** `scripts/train_tgn_v1.py` (GRU on snapshot sequences), extended `prepare_tgn_training.py` with graph edge counts, `TGNForecaster` checkpoint loading
- **HMM regime:** `src/intelligence/hmm_regime.py` — 3-state regional stress; APIs `/intelligence/regions/{id}/regime`, `/analytics/regime-summary`; map regime badge
- **DoWhy scale:** bootstrap correlation CI when n&lt;30; `scripts/collect_causal_pairs.py`; `make collect-causal-pairs`
- **Alternatives:** `src/intelligence/graph_embeddings.py` Node2Vec stub; `GET /suppliers/{id}/alternatives`; EntityDrawer section
- **Backtest:** `scripts/backtest_scri.py` → `data/backtest/latest.json`; `GET /analytics/backtest-summary`; GraphHealthView KPI card
- **Docs:** `docs/REAL_DATA_PHASE_C.md`, updated `TGN_RESEARCH.md`, `CAUSAL_SCOPE.md`
- PR #16 `feat/phase-c-predictive`

### State at end
- Unit tests pass without Neo4j, GPU, or trained checkpoint
- `hmmlearn` added to `requirements.txt` (lightweight)
- Frontend build passes with regime badge + alternatives + backtest card

### Decisions made
- v1 TGN = CPU GRU on snapshot sequences (no torch_geometric for v1)
- HMM synthetic fallback when Neo4j event rates empty
- Graph embeddings = deterministic hash walk stub until Node2Vec wired

### Blockers
- None for merge

### Next session starts with
1. Merge PR #15 then #16
2. Daily snapshot cron + first real `train-tgn` run after 7 days data
3. Expand disruption labels toward 500 rows

[OWNER NOTES]
-
