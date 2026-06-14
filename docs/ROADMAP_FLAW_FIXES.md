# Flaw → Fix Roadmap — Meridian SCRI Honesty Program

Maps 24 critique flaws to remediation chunks. **Chunk 1 (this PR)** covers P0/P1 transparency; Chunks 2–3 cover data, calibration, and architecture.

| # | Flaw | Solution | Status |
|---|------|----------|--------|
| 1 | No labeled disruption dataset | Build historical disruption labels + training CSV; MLflow tracked retrain | **chunk2** |
| 2 | SCRI presented as precise probability | Band-first UI, "modelled index" sublabels, `display_guidance` API | **done** (chunk1) |
| 3 | Multi-index SCRI (geo/ops/fin) overstated | Document single composite; optional API stub fields later | **chunk3** |
| 4 | Causal language on correlates | Association-only badge + sample count on alerts | **done** (chunk1) |
| 5 | DoWhy not at production scale | `CAUSAL_PAIR_LIMIT`, `docs/CAUSAL_SCOPE.md` | **done** (session 7) |
| 6 | Methodology hidden from UI | `/metrics/methodology` + MetricTooltip limitations | **done** (chunk1) |
| 7 | Stub features invisible | `feature_provenance` on explanation endpoint | **done** (chunk1) |
| 8 | Weather/financial features fake | Provenance flags + LIMITATIONS.md Layer B | **done** (chunk1) |
| 9 | Sector taxonomy implied ML | `classification_method: keyword` + SectorsView tooltip | **done** (chunk1) |
| 10 | Monte Carlo point estimates | p10/p50/p90 delay + revenue bands in API/UI | **done** (chunk1) |
| 11 | TGN forecast oversold | "Research track · LSTM fallback" badge | **done** (chunk1) |
| 12 | ERP / tier-N not disclosed | LIMITATIONS.md + roadmap chunk2 | **chunk2** |
| 13 | Graph completeness unknown | `feature_provenance` live count; graph health endpoint exists | **partial** (chunk1) |
| 14 | Untrained model silent default | `/health` + `/metrics/model-status`, startup warning, banners | **done** (chunk1) |
| 15 | Kafka complexity vs demo | Document simplified deploy path | **chunk3** |
| 16 | SHAP without calibrated model | Demo calibration banner + model_source | **done** (chunk1) |
| 17 | Public deploy not live | Railway + Vercel per DEPLOY.md | **chunk2** |
| 18 | Risk % over band in lists | RiskPill band-first + sublabel | **done** (chunk1) |
| 19 | Live WGI not integrated | Static table documented; live API fetch | **chunk2** |
| 20 | AIS / sanctions layers thin | Layer provenance + ingest roadmap | **chunk3** |
| 21 | Demo GIF missing | Record per docs/DEMO.md | **chunk2** |
| 22 | Weekly digest LLM unverified | Label as template narrative in METRICS | **chunk3** |
| 23 | Copilot answers unconstrained | Grounding + disclaimer in CopilotView | **chunk3** |
| 24 | No single limitations doc | `docs/LIMITATIONS.md` | **done** (chunk1) |

## Chunk 2 (planned)

- Labeled disruption dataset + `scripts/train_risk_model.py` production artifact
- ERP CSV ingest prototype / tier-2 edges
- Live World Bank WGI pull (cached)
- Railway + Vercel deploy execution
- Demo GIF

## Chunk 3 (planned)

- Kafka topology simplification doc / optional single-process mode
- Multi-index SCRI API stubs (geo / ops / fin decomposition)
- AIS + sanctions live layers in feature builder
- Copilot grounding hardening
- Full graph completeness dashboard

## Chunk 1 deliverables (PR #9)

- API: `calibration_status`, `limitations`, `display_guidance`, `model-status`, health model block
- API: Monte Carlo p10/p50/p90, sector `classification_method`, alert `causal_sample_count`
- API: `feature_provenance` on supplier explanation
- UI: `ModelStatusBanner`, RiskPill band-first, SimulationView bands, AlertsView sample count
- Docs: `LIMITATIONS.md`, this roadmap
