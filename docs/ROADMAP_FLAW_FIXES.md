# Flaw → Fix Roadmap — Meridian SCRI Honesty Program

Maps 24 critique flaws to remediation chunks. **Chunk 1 (this PR)** covers P0/P1 transparency; Chunks 2–3 cover data, calibration, and architecture.

| # | Flaw | Solution | Status |
|---|------|----------|--------|
| 1 | No labeled disruption dataset | Build historical disruption labels + training CSV; MLflow tracked retrain | **done** (chunk2) |
| 2 | SCRI presented as precise probability | Band-first UI, "modelled index" sublabels, `display_guidance` API | **done** (chunk1) |
| 3 | Multi-index SCRI (geo/ops/fin) overstated | `pillar_scores` API stub + SuppliersView mini-bars | **done** (chunk3) |
| 4 | Causal language on correlates | Association-only badge + sample count on alerts | **done** (chunk1) |
| 5 | DoWhy not at production scale | `CAUSAL_PAIR_LIMIT`, `docs/CAUSAL_SCOPE.md` | **done** (session 7) |
| 6 | Methodology hidden from UI | `/metrics/methodology` + MetricTooltip limitations | **done** (chunk1) |
| 7 | Stub features invisible | `feature_provenance` on explanation endpoint | **done** (chunk1) |
| 8 | Weather/financial features fake | Provenance flags + LIMITATIONS.md Layer B | **done** (chunk1) |
| 9 | Sector taxonomy implied ML | `classification_method: keyword` + SectorsView tooltip | **done** (chunk1) |
| 10 | Monte Carlo point estimates | p10/p50/p90 delay + revenue bands in API/UI | **done** (chunk1) |
| 11 | TGN forecast oversold | "Research track · LSTM fallback" badge | **done** (chunk1) |
| 12 | ERP / tier-N not disclosed | LIMITATIONS.md + ERP CSV ingest prototype | **done** (chunk2) |
| 13 | Graph completeness unknown | Graph health endpoint + GraphHealthView dashboard | **done** (chunk3) |
| 14 | Untrained model silent default | `/health` + `/metrics/model-status`, startup warning, banners | **done** (chunk1) |
| 15 | Kafka complexity vs demo | `docs/ARCHITECTURE_DEMO.md` + `pipeline_batch.py` | **done** (chunk3) |
| 16 | SHAP without calibrated model | Demo calibration banner + model_source | **done** (chunk1) |
| 17 | Public deploy not live | Railway + Vercel config + DEPLOY_QUICKSTART.md | **done** (chunk2 config) |
| 18 | Risk % over band in lists | RiskPill band-first + sublabel | **done** (chunk1) |
| 19 | Live WGI not integrated | Cached WGI fetch script + feature_builder loader | **done** (chunk2) |
| 20 | AIS / sanctions layers thin | NOAA weather + sanctions stub in feature_builder | **partial** (chunk3 — demo stub, not live AIS) |
| 21 | Demo GIF missing | Record per docs/DEMO.md + demo-placeholder.md | **done** (chunk2 placeholder) |
| 22 | Weekly digest LLM unverified | `narrative_type: template` in API + Dashboard label | **done** (chunk3) |
| 23 | Copilot answers unconstrained | Graph-grounded copilot + disclaimer + I-don't-know fallback | **done** (chunk3) |
| 24 | No single limitations doc | `docs/LIMITATIONS.md` | **done** (chunk1) |

## Chunk 2 (PR #10 — done)

- `data/disruption_labels.csv` + label-aware `train_risk_model.py`
- `calibration_status: validated` when model + labels metadata present
- ERP CSV ingest (`scripts/ingest_erp_csv.py`) + graph health tier/completeness
- Live WGI cache (`scripts/fetch_wgi_stability.py`, `data/wgi_stability.json`)
- `frontend/vercel.json`, `railway.toml`, `docs/DEPLOY_QUICKSTART.md`
- Demo GIF instructions (`docs/assets/demo-placeholder.md`)

## Chunk 3 (PR #11 — done)

- `docs/ARCHITECTURE_DEMO.md` + `scripts/pipeline_batch.py` (PIPELINE_MODE=batch)
- `pillar_scores` on explanation API + SuppliersView mini-bars
- NOAA weather + sanctions stub wired into feature_builder + provenance
- Copilot grounding (`grounded`, `disclaimer`, graph facts, uncertainty fallback)
- `GraphHealthView` at `/ops/graph-health`
- Digest `narrative_type: template` + Dashboard label

## Remaining partial items

- **Flaw #20:** Live AIS ingest into SCRI features (demo stub only)
- **Flaw #17:** Actual Railway/Vercel deploy execution (config shipped — run `vercel link` + `railway up` per DEPLOY_QUICKSTART)
- **Flaw #21:** Record `meridian-demo.gif` (script shipped: `scripts/record_demo.sh`; placeholder hero until recorded)

## Session 11 (PR #13 — portfolio demo ready)

- `data/disruption_labels.csv` expanded to 50+ public case-study rows
- `make portfolio-ready`, `fetch-wgi`, `seed-erp`, `pipeline-batch`, `check-deploy`
- README portfolio polish + updated `docs/DEMO.md` (GraphHealth, pillars, batch path)
- `scripts/record_demo.sh`, `scripts/check_deploy_config.sh`
- `frontend/.env.example` + `VITE_API_URL` alias in API client

## Chunk 1 deliverables (PR #9)

- API: `calibration_status`, `limitations`, `display_guidance`, `model-status`, health model block
- API: Monte Carlo p10/p50/p90, sector `classification_method`, alert `causal_sample_count`
- API: `feature_provenance` on supplier explanation
- UI: `ModelStatusBanner`, RiskPill band-first, SimulationView bands, AlertsView sample count
- Docs: `LIMITATIONS.md`, this roadmap
