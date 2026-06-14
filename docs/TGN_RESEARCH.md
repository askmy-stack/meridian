# TGN Research Track — Temporal Graph Networks for Supply Chain Risk

> **Status:** Research / v1 GRU trained on snapshots · **Decision:** [D-004](../DECISIONS.md)

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
| Trajectory (7/14/30d) | `TGNForecaster` v1 GRU | Falls back to LSTM when no checkpoint |
| History without Neo4j | CSV snapshot fallback | `data/snapshots/supplier_snapshot_YYYYMMDD.csv` |
| Training v1 | `scripts/train_tgn_v1.py` | PyTorch GRU on score sequences (CPU-friendly) |

**API:** `GET /intelligence/forecast/{id}` returns `model: "tgn"` when `models/tgn_v1.pt` exists, else `lstm_fallback`.

**Daily snapshots:** `scripts/export_graph_snapshots.py` exports supplier rows (risk_score, event counts, max severity) for offline training prep.

**Readiness check:** `scripts/prepare_tgn_training.py` scans snapshots, writes `data/snapshots/tgn_manifest.json` (`ready_for_training: true` when ≥7 daily files exist), and includes optional Neo4j edge counts.

## v1 training steps (GRU research track)

### 1. Collect snapshots (≥7 days minimum, 30+ recommended)

```bash
# Daily cron or post-pipeline hook
python scripts/export_graph_snapshots.py
python scripts/prepare_tgn_training.py
```

Manifest fields: `snapshot_count`, `graph_edges.affects_edges`, `ready_for_training`.

### 2. Train GRU v1

```bash
make train-tgn
# or: python scripts/train_tgn_v1.py
```

- Builds `(seq_len=7 → next score)` pairs per supplier from ordered snapshots
- Trains tiny GRU (PyTorch) or Ridge fallback (sklearn) on CPU
- Saves checkpoint to `models/tgn_v1.pt` (gitignored)
- Logs metrics to MLflow experiment `tgn_v1_research`; tags `research_stub` when insufficient data

### 3. Wire inference

`TGNForecaster` auto-loads `TGN_MODEL_PATH` (default `models/tgn_v1.pt`) at init. No code changes needed after training.

```bash
curl "localhost:8002/intelligence/forecast/taiwan-semiconductor-corp?horizon_days=14"
```

### 4. Path to full PyG Temporal TGN

Dependencies (not in MVP `requirements.txt` — see `requirements-dev.txt` / cloud GPU):

```
torch>=2.1
torch_geometric>=2.4
torch_geometric_temporal>=0.54
```

Full training sketch:

1. Extend manifest → PyG `TemporalData` (nodes, edges, timestamps, labels).
2. Train TGN (2–3 layers, link prediction + node classification).
3. Held-out **time** split (last 7 days validation).
4. Export weights; set `TGN_MODEL_PATH`.

## Hardware (local dev per AGENTS.md)

| Resource | Meridian dev machine | Full TGN training |
|----------|----------------------|-------------------|
| GPU | NVIDIA Quadro P2000 **4GB VRAM** | Minimum **8GB VRAM** recommended for TGN |
| RAM | 48GB | 32GB+ |
| v1 GRU training | CPU, seconds–minutes | N/A |
| Full TGN | N/A (stub path) | 2–3 days GPU |

**Practical path on P2000:** v1 GRU for portfolio demo; cloud GPU (HF Jobs / A10) for full TGN; keep inference on CPU.

## Related files

| File | Role |
|------|------|
| `src/forecasting/tgn_forecaster.py` | GRU v1 load + LSTM + CSV fallback |
| `scripts/export_graph_snapshots.py` | Daily Neo4j → CSV export |
| `scripts/prepare_tgn_training.py` | Manifest + edge counts + readiness gate |
| `scripts/train_tgn_v1.py` | GRU v1 training + MLflow |
| `docs/REAL_DATA_PHASE_C.md` | Phase C architecture |
| `tests/unit/test_tgn_csv_fallback.py` | CSV fallback tests |
| `tests/unit/test_train_tgn_v1.py` | Synthetic training path |

## Success criteria (research track)

- [x] ≥7 daily snapshots → `ready_for_training: true`
- [x] MLflow run or `research_stub` tag when data insufficient
- [x] API returns `model: "tgn"` when checkpoint loaded
- [ ] ≥30 daily snapshots for production-quality GRU
- [ ] Full PyG TGN with graph attention explanations
- [ ] Validation MAE on 7-day horizon logged to MLflow
