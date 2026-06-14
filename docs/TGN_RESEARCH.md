# TGN Research Track — Temporal Graph Networks for Supply Chain Risk

> **Status:** Research / MVP stub · **Decision:** [D-004](../DECISIONS.md)

## Why TGN for supply chain risk

Standard graph neural networks treat the supply chain as a static snapshot. Supply chain risk is **inherently temporal**:

- A conflict in week 1 behaves differently from the same conflict in week 4 (escalation, rerouting, inventory buffers).
- Disruption propagates through **time-stamped edges** (vessel delays, port closures, supplier tier changes).
- **Temporal Graph Networks (TGN)** maintain a memory module and timestamped message passing — the right fit for “what happens next on this evolving graph?”

Meridian’s portfolio thesis: **TGN + DoWhy + SHAP** is a combination no production supply chain tool ships publicly. TGN is the forecasting moat; XGBoost + SHAP remains the explainable point-score (SCRI).

## Current MVP behavior

| Layer | Implementation | Notes |
|-------|----------------|-------|
| Point risk (SCRI) | XGBoost + SHAP | Production path for alerts and map |
| Trajectory (7/14/30d) | `TGNForecaster` stub | Falls back to LSTM in `weak_signal_detector` |
| History without Neo4j | CSV snapshot fallback | `data/snapshots/supplier_snapshot_YYYYMMDD.csv` |
| Training | Not run | `TGNForecaster.train()` logs requirements and returns `False` |

**API:** `GET /intelligence/suppliers/{id}/forecast` returns `model: "lstm_fallback"` until a trained TGN checkpoint exists.

**Daily snapshots:** `scripts/export_graph_snapshots.py` exports supplier rows (risk_score, event counts, max severity) for offline training prep.

**Readiness check:** `scripts/prepare_tgn_training.py` scans snapshots and writes `data/snapshots/tgn_manifest.json` (`ready_for_training: true` when ≥7 daily files exist).

## Path to full training

### 1. Collect temporal data (30+ days recommended)

```bash
# Daily cron or post-pipeline hook
python scripts/export_graph_snapshots.py
python scripts/prepare_tgn_training.py
```

Target: **30+ daily snapshots**, 100+ suppliers per snapshot, 1000+ labeled event outcomes (see `TGNForecaster._log_training_requirements()`).

### 2. Prepare dataset

- Extend `prepare_tgn_training.py` (future) to emit PyG Temporal `TemporalData` objects: nodes, edges, timestamps, labels.
- Align snapshot dates with Kafka event timelines and Neo4j `:Event` resolution outcomes.

### 3. Train with PyTorch Geometric Temporal

Dependencies (not in MVP `requirements.txt`):

```
torch>=2.1
torch_geometric>=2.4
torch_geometric_temporal>=0.54
```

Training sketch (stub — not wired in CI):

1. Load snapshot sequence from manifest.
2. Build TGN (2–3 layers, link prediction + node classification).
3. Train on held-out **time** split (last 7 days validation).
4. Log to MLflow; export weights to `models/tgn/`.
5. Set `TGNForecaster(model_path=...)` in API.

### 4. Hardware (local dev per AGENTS.md)

| Resource | Meridian dev machine | Full TGN training |
|----------|----------------------|-------------------|
| GPU | NVIDIA Quadro P2000 **4GB VRAM** | Minimum **8GB VRAM** recommended for TGN |
| RAM | 48GB | 32GB+ |
| Training time | N/A (stub) | 2–3 days GPU for production-quality model |

**Practical path on P2000:** use snapshots + smaller subgraph batches, gradient checkpointing, or cloud GPU (HF Jobs / single A10) for the actual training run; keep inference on CPU or small GPU.

## Related files

| File | Role |
|------|------|
| `src/forecasting/tgn_forecaster.py` | Stub + LSTM + CSV fallback |
| `scripts/export_graph_snapshots.py` | Daily Neo4j → CSV export |
| `scripts/prepare_tgn_training.py` | Manifest + readiness gate |
| `docs/METRICS.md#forecasting-tgn--research-track` | User-facing metric definitions |
| `tests/unit/test_tgn_csv_fallback.py` | CSV fallback tests (no Neo4j) |

## Success criteria (research track)

- [ ] ≥30 daily snapshots in `data/snapshots/`
- [ ] `tgn_manifest.json` reports `ready_for_training: true`
- [ ] MLflow run with validation AUC / MAE on 7-day horizon
- [ ] API returns `model: "tgn"` for at least demo suppliers
- [ ] Forecast explanations include graph attention weights (not LSTM trend only)
