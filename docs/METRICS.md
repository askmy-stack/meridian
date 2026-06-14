# Meridian Metrics Methodology

Meridian exposes **SCRI** — the **Supply Chain Risk Index** — a normalized 0–100 score for supplier-level geopolitical and operational exposure. Every dashboard percentage maps to this framework.

---

## SCRI (Supply Chain Risk Index)

**Definition:** Probability-style index that a supplier will experience a material disruption (≥7-day delay or ≥15% volume impact) within the next 30 days, given current open signals and network position.

**Output range:** `0.0 – 1.0` (UI displays as **0–100%**)

**Model:** XGBoost binary classifier trained on supplier feature vectors, with **mandatory SHAP attribution** per [DECISIONS.md D-003](../DECISIONS.md).

### Composite intuition (pre-model feature design)

SCRI features are grouped into five pillars aligned with supply-chain risk literature:

| Pillar | Feature(s) in code | Interpretation | Primary references |
|--------|-------------------|----------------|-------------------|
| **Geographic exposure** | `conflict_proximity_score` | Severity of conflict/news events linked to supplier geography | [GDELT Goldstein scale](https://www.gdeltproject.org/data/documentation/GDELT-Event_Codebook-V2.0.pdf) (event intensity −10 to +10, normalized) |
| **Governance / stability** | `political_stability_index` | Inverse political risk by country (demo uses WGI-inspired proxies) | [World Bank WGI — Political Stability](https://databank.worldbank.org/source/worldwide-governance-indicators) |
| **Network fragility** | `single_source_flag`, `dependency_depth`, `alternative_sources_count` | Concentration and substitutability | Wagner & Bode (2006), *Analyzing the vulnerability of supply chains* |
| **Operational stress** | `port_congestion_score`, `weather_risk_score` | Chokepoint / port pressure from AIS + weather layers | UNCTAD chokepoint literature; NOAA alerts |
| **Event load** | `recent_events_count`, `critical_events_count` | 30-day signal density from graph-linked `:Event` nodes | ACLED + GDELT event streams |

### Risk categories (display bands)

| SCRI (0–1) | Category | Action tier |
|------------|----------|-------------|
| 0.00 – 0.24 | NONE / LOW | Monitor |
| 0.25 – 0.49 | MEDIUM | Review quarterly |
| 0.50 – 0.74 | HIGH | Activate contingency |
| 0.75 – 1.00 | CRITICAL | Executive escalation |

Bands follow common enterprise TPRM practice (similar to Resilience360 / Everstream tiering) and are **calibrated on demo seed data** — production deployments should recalibrate on labeled disruption outcomes.

---

## Explainability (SHAP)

Every supplier score returned by `/suppliers/{id}/explanation` includes SHAP feature contributions.

**Reference:** Lundberg & Lee (2017), *A Unified Approach to Interpreting Model Predictions* — [NeurIPS paper](https://arxiv.org/abs/1705.07874)

Meridian uses `shap.TreeExplainer` on the XGBoost model. Top factors are sorted by absolute SHAP value for CFO-readable narratives.

---

## Simulation metrics

### Propagation impact

**BFS engine** (`src/simulation/propagation.py`) walks Neo4j relationships (`AFFECTS`, `SHIPS_VIA`, `PASSES_THROUGH`, `SUPPLIES`) with hop-decay. Reported **affected entity count** and **max depth** are graph-derived, not synthetic.

### Monte Carlo financial exposure

**Iterations:** Minimum **1,000** runs ([DECISIONS.md D-010](../DECISIONS.md), [AGENTS.md](../AGENTS.md)).

**Outputs:**

| Metric | Meaning |
|--------|---------|
| `expected_delay_days` | Mean simulated delay across iterations |
| `p90_delay_days` | 90th percentile delay (tail risk) |
| `expected_cost_usd` | Mean financial impact draw |
| `probability_disruption` | Share of runs exceeding disruption threshold |

Distribution assumptions (log-normal delay, uniform cost multipliers) are documented in `src/simulation/monte_carlo.py` and should be replaced with empirically fitted distributions in production.

---

## Causal claims (DoWhy — research track)

**Policy ([D-005](../DECISIONS.md)):** User-facing language that asserts **causation** (e.g. “Red Sea conflict **causes** your delay”) requires DoWhy identification + refutation tests.

Correlational signals (event severity ↔ supplier score) are labeled **association only** until causal pipeline passes.

**Reference:** Sharma & Kiciman (2020), [DoWhy Python library](https://www.pywhy.org/dowhy/)

---

## Forecasting (TGN — research track)

7 / 14 / 30-day **risk trajectory** (not replacement for SCRI point score) uses temporal graph methods per [D-004](../DECISIONS.md).

**Reference:** Rossi et al., *Temporal Graph Networks* — [PyTorch Geometric Temporal](https://pytorch-geometric-temporal.readthedocs.io/)

---

## Multi-index SCRI decomposition (API stub)

`/suppliers/{id}/explanation` returns `pillar_scores` — **weighted sums of existing feature groups**, not separate ML models:

| Pillar | Features combined |
|--------|-------------------|
| `geographic` | `conflict_proximity_score`, inverse `political_stability_index` |
| `operational` | `port_congestion_score`, `weather_risk_score` (NOAA demo match) |
| `network` | `single_source_flag`, `dependency_depth` |
| `event_load` | `recent_events_count`, `critical_events_count` |

UI shows four mini-bars under the main SCRI on **Suppliers** view. Values are 0–1 (displayed as 0–100%).

Sanctions exposure feeds `conflict_proximity_score` via OpenSanctions demo stub; provenance field `sanctions_exposure` documents the source.

---

## Weekly digest narrative

`POST /intelligence/weekly-digest` sets `narrative_type: "template"`. The narrative is rule-generated — not LLM-verified.

---

## Data freshness KPIs

| Dashboard label | Source | Definition |
|-----------------|--------|------------|
| **Suppliers tracked** | Neo4j | Count of `:Supplier` nodes |
| **Active events** | Neo4j `:Event` | Events with `ingested_at` in last 7 days |
| **Critical risks** | SCRI | Suppliers with `risk_category = CRITICAL` |
| **Peak SCRI** | SCRI | Highest supplier score in current digest |

---

## Changelog

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-06-12 | Initial SCRI documentation for portfolio demo |
