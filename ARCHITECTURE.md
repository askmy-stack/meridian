# ARCHITECTURE.md — System Architecture Specification

> Living document. Update on every architectural change.
> Version history at bottom. Never delete old versions — mark as deprecated.

---

## Current Version: v0.2 — Portfolio demo + live ingestion
**Status:** Shipped — React dashboard, FastAPI, Neo4j graph, GDELT pipeline, CI
**Date:** 2026-06-13
**Author:** Abhinaysai Kamineni

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: SIGNAL INGESTION                                           │
│  GDELT · AIS (vessel) · ACLED (conflict) · NOAA · NASA FIRMS        │
│  World Bank · OpenSanctions · UN Comtrade · FX feeds                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Kafka topics
┌──────────────────────────────▼──────────────────────────────────────┐
│  LAYER 2: INTELLIGENCE ENGINE                                        │
│  Entity Resolution (spaCy NER)                                       │
│  Event Classifier (BERT fine-tuned on ACLED event types)            │
│  Risk Scorer (XGBoost + SHAP)                                        │
│  Weak Signal Detector (Isolation Forest + LSTM autoencoder)         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  LAYER 3: KNOWLEDGE GRAPH — Neo4j                                    │
│  Node types: Supplier, Port, Region, SKU, Carrier,                  │
│              Chokepoint, Conflict Zone, Route                        │
│  Edge types: sources-from, ships-via, located-in,                   │
│              blocked-by, depends-on, substitutable-with,            │
│              threatens, detected-by, operates-on                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  LAYER 4: SIMULATION + FORECASTING                                   │
│  Disruption Simulator (BFS propagation + Monte Carlo ≥1000 iters)   │
│  TGN Forecaster (7/14/30-day risk — PyTorch Geometric Temporal)     │
│  HMM Regime Detector (stable / escalation / crisis)                 │
│  Causal Inference Engine (DoWhy + EconML)                           │
│  Alternative Supplier Recommender (Node2Vec + ranking)              │
│  Counterfactual Analyzer (DoWhy on historical snapshots)            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  LAYER 5: OUTPUT                                                     │
│  React + Mapbox GL dashboard (live risk map)                        │
│  Slack alerts (tiered severity: INFO / WARNING / CRITICAL)          │
│  REST API (FastAPI + JWT)                                            │
│  Weekly digest (LLM-generated narrative — RAG over incident history)│
│  SHAP explanation per risk score                                     │
└─────────────────────────────────────────────────────────────────────┘

CROSS-CUTTING:
  Storage:       PostgreSQL (entities) · TimescaleDB (time-series) · Qdrant (vectors)
  Observability: Prometheus + Grafana
  ML Tracking:   MLflow
  IaC:           Docker Compose (local) → Terraform + AWS ECS (production)
```

---

## Service Breakdown

### 1. Ingestion Services (Layer 1)

| Service | Source | Kafka Topic | Update Frequency | Auth |
|---|---|---|---|---|
| `gdelt-producer` | GDELT 2.0 GKG | `meridian.news.events` | Every 15 min | None |
| `acled-producer` | ACLED API | `meridian.conflict.events` | Daily | API key |
| `ais-producer` | AISHub | `meridian.vessel.positions` | Real-time / 5min | Account |
| `noaa-producer` | NOAA API | `meridian.weather.alerts` | Hourly | None |
| `nasa-producer` | NASA FIRMS | `meridian.disaster.events` | Daily | Token |
| `sanctions-producer` | OpenSanctions | `meridian.sanctions.updates` | Daily | None |
| `worldbank-producer` | World Bank API | `meridian.country.indicators` | Weekly | None |
| `fx-producer` | ExchangeRate API | `meridian.fx.ticks` | Hourly | Free key |

**Kafka topic naming convention:** `meridian.{domain}.{event_type}`

**All producers output:**
```json
{
  "source": "gdelt",
  "event_id": "uuid4",
  "timestamp": "ISO8601",
  "schema_version": "1.0",
  "payload": { ... source-specific fields ... },
  "ingested_at": "ISO8601"
}
```

---

### 2. Intelligence Engine (Layer 2)

#### 2a. Entity Resolution
**Purpose:** Maps free-text news mentions ("Foxconn's Zhengzhou plant") to canonical supplier nodes in Neo4j.

**Stack:** spaCy en_core_web_lg + custom NER trained on supply chain entity types
**Input:** Raw news text from `meridian.news.events`
**Output:** Enriched event with `resolved_entities: [{ entity_id, entity_type, confidence }]`
**Fallback:** Fuzzy string match against known supplier list if NER confidence < 0.7

#### 2b. Event Classifier
**Purpose:** Converts unstructured news/conflict events into structured risk taxonomy.

**Stack:** BERT (bert-base-uncased) fine-tuned on ACLED event type labels
**Classes:** conflict_escalation, sanctions_announcement, port_congestion, labor_unrest, natural_disaster, political_instability, infrastructure_failure, pandemic_signal
**Output:**
```json
{
  "event_type": "conflict_escalation",
  "severity": 0.87,
  "affected_regions": ["YEM", "SAU"],
  "affected_chokepoints": ["Bab-el-Mandeb"],
  "estimated_duration_days": 14,
  "confidence": 0.79
}
```
**Note:** LLM (GPT-4o function calling) used for production — BERT fine-tune for cost efficiency at scale.

#### 2c. Risk Scorer
**Purpose:** Computes supplier-level risk score with SHAP attribution.

**Stack:** XGBoost + SHAP
**Features:**
- Conflict proximity score (distance from supplier to active conflict zones)
- Chokepoint dependency count (how many critical chokepoints supplier routes use)
- Geographic concentration index (Herfindahl index on sourcing geography)
- Financial health signals (credit default swap spreads, earnings revisions)
- Single-source dependency flag
- Historical disruption frequency (supplier-specific)
- Weather/disaster proximity score
- Sanctions exposure score

**Output:**
```json
{
  "supplier_id": "tsmc-taiwan-001",
  "risk_score": 0.91,
  "risk_level": "CRITICAL",
  "shap_explanation": [
    { "feature": "taiwan_strait_conflict_proximity", "contribution": +0.34 },
    { "feature": "single_source_dependency", "contribution": +0.28 },
    { "feature": "fx_volatility_twd_usd", "contribution": +0.18 },
    { "feature": "financial_health_score", "contribution": -0.09 }
  ],
  "scored_at": "ISO8601"
}
```

#### 2d. Weak Signal Detector
**Purpose:** Detect pre-crisis anomalies 2-4 weeks before mainstream signals.

**Stack:** Isolation Forest (static anomaly) + LSTM Autoencoder (temporal anomaly)
**Signals monitored:** Wikipedia edit frequency on conflict articles, social media volume by language/region, satellite imagery change delta (NASA FIRMS), shipping booking cancellation rate
**Output:** Anomaly score per region per 7-day rolling window

---

### 3. Knowledge Graph (Layer 3)

#### Neo4j Schema v0.1

**Node types and properties:**

```cypher
// Supplier
(:Supplier {
  id: String,           // UUID
  name: String,
  country_iso: String,
  region: String,
  tier: Integer,        // 1 = direct, 2 = supplier's supplier, 3 = tier 3
  industry: String,
  annual_revenue_usd: Float,
  employee_count: Integer,
  risk_score: Float,    // Updated by risk scorer
  last_scored_at: DateTime
})

// Port
(:Port {
  id: String,
  name: String,
  locode: String,       // UN/LOCODE standard
  country_iso: String,
  latitude: Float,
  longitude: Float,
  throughput_teu_annual: Integer,
  congestion_score: Float
})

// Chokepoint
(:Chokepoint {
  id: String,
  name: String,         // "Strait of Hormuz", "Suez Canal", etc.
  latitude: Float,
  longitude: Float,
  daily_vessel_count: Integer,
  annual_trade_value_usd: Float,
  current_risk_score: Float
})

// Route
(:Route {
  id: String,
  name: String,
  origin_region: String,
  destination_region: String,
  avg_transit_days: Integer,
  avg_cost_per_container_usd: Float
})

// Region
(:Region {
  id: String,
  name: String,
  country_iso: String,
  stability_index: Float,    // From World Bank governance indicators
  conflict_active: Boolean,
  sanctions_active: Boolean
})

// Conflict Zone
(:ConflictZone {
  id: String,
  name: String,
  acled_event_id: String,
  conflict_type: String,
  severity: Float,
  started_date: Date,
  latitude: Float,
  longitude: Float,
  radius_km: Integer,
  status: String        // active / resolved / escalating
})

// SKU
(:SKU {
  id: String,
  name: String,
  hs_code: String,
  category: String,
  owner_org: String,
  critical_flag: Boolean
})

// Carrier
(:Carrier {
  id: String,
  name: String,
  country_iso: String,
  fleet_size: Integer,
  market_share_pct: Float
})
```

**Edge types:**

```cypher
// Supplier relationships
(:Supplier)-[:SUPPLIES {tier: Int, annual_value_usd: Float}]->(:Supplier)
(:Supplier)-[:MANUFACTURES {sku_count: Int}]->(:SKU)
(:Supplier)-[:LOCATED_IN]->(:Region)
(:Supplier)-[:SHIPS_VIA {primary: Boolean, volume_pct: Float}]->(:Port)

// Route relationships
(:Port)-[:ON_ROUTE]->(:Route)
(:Route)-[:PASSES_THROUGH]->(:Chokepoint)
(:Carrier)-[:OPERATES_ON]->(:Route)

// Risk relationships
(:ConflictZone)-[:THREATENS {proximity_km: Float}]->(:Chokepoint)
(:ConflictZone)-[:AFFECTS]->(:Region)
(:ConflictZone)-[:DETECTED_BY {source: String, confidence: Float}]->(:NewsEvent)

// Substitution relationships
(:Supplier)-[:SUBSTITUTABLE_WITH {
  lead_time_delta_days: Int,
  cost_delta_pct: Float,
  qualification_required: Boolean
}]->(:Supplier)
```

**Key queries:**

```cypher
// Find all SKUs affected if a chokepoint closes
MATCH (c:Chokepoint {name: "Taiwan Strait"})
MATCH (c)<-[:PASSES_THROUGH]-(:Route)<-[:ON_ROUTE]-(:Port)<-[:SHIPS_VIA]-(s:Supplier)
MATCH (s)-[:MANUFACTURES]->(sku:SKU)
RETURN sku.name, s.name, s.risk_score
ORDER BY s.risk_score DESC

// Find alternative suppliers for a given supplier
MATCH (s:Supplier {id: "tsmc-taiwan-001"})-[:SUBSTITUTABLE_WITH]->(alt:Supplier)
WHERE alt.risk_score < s.risk_score
RETURN alt.name, alt.country_iso, alt.risk_score,
       (s)-[:SUBSTITUTABLE_WITH]->(alt).lead_time_delta_days AS lead_time_impact
ORDER BY alt.risk_score ASC

// Propagate conflict risk upstream
MATCH (conflict:ConflictZone {status: "active"})
MATCH (conflict)-[:THREATENS]->(chokepoint:Chokepoint)
MATCH (chokepoint)<-[:PASSES_THROUGH*1..3]-(:Route)<-[:ON_ROUTE]-(:Port)<-[:SHIPS_VIA]-(supplier:Supplier)
RETURN conflict.name, chokepoint.name, supplier.name, supplier.risk_score
```

---

### 4. Simulation Engine (Layer 4)

#### 4a. Disruption Simulator

**Algorithm:**
1. Receive scenario definition (e.g., `{ event: "chokepoint_closure", target: "Taiwan Strait", duration_days: 30 }`)
2. Run BFS from affected chokepoint through graph: Chokepoint → Routes → Ports → Suppliers → SKUs
3. For each affected node, sample impact distribution (delay days, cost premium, shortage probability)
4. Monte Carlo: repeat 1000+ times with sampled parameters
5. Aggregate: return P10/P50/P90 estimates per affected SKU

**Output:**
```json
{
  "scenario": "Taiwan Strait closure — 30 days",
  "total_skus_affected": 847,
  "critical_path_components": 23,
  "p50_estimated_impact_usd": 340000000,
  "p90_estimated_impact_usd": 580000000,
  "p50_recovery_weeks": 14,
  "alternative_routes": [
    { "route": "Cape of Good Hope", "additional_days": 21, "cost_premium_pct": 34 }
  ],
  "alternative_suppliers": [ ... ],
  "simulation_iterations": 1000,
  "run_at": "ISO8601"
}
```

#### 4b. TGN Forecaster (Phase 6)
**Model:** Temporal Graph Network (PyTorch Geometric Temporal)
**Input:** Graph snapshot sequence + event timeline
**Output:** Risk score per node at T+7, T+14, T+30
**Training data:** Historical disruption events (COVID 2020, Suez 2021, Red Sea 2023)

#### 4c. HMM Regime Detector (Phase 6)
**States:** stable, escalating, crisis
**Observation variables:** conflict_event_rate, vessel_dwell_time_delta, sanctions_count_rolling_7d, fx_volatility_index
**Output:** Current regime + transition probability matrix

#### 4d. Causal Inference Engine (Phase 6)
**Stack:** DoWhy + EconML
**Use cases:**
- Distinguish causal from correlated risk signals
- Counterfactual: "What if we had dual-sourced Taiwan in 2022?"
- Treatment effect estimation: "What does adding an alternative supplier reduce risk by?"

---

### 5. Output Layer (Layer 5)

#### REST API (FastAPI)
**Endpoints:**
```
GET  /api/v1/suppliers                    # List suppliers with risk scores
GET  /api/v1/suppliers/{id}/risk          # Risk score + SHAP for one supplier
GET  /api/v1/suppliers/{id}/alternatives  # Alternative supplier recommendations
GET  /api/v1/simulate                     # Run disruption scenario
GET  /api/v1/chokepoints                  # All chokepoints with current risk
GET  /api/v1/alerts                       # Active alerts (paginated)
GET  /api/v1/graph/impact/{event_id}      # Graph propagation for a specific event
POST /api/v1/suppliers/upload             # Bulk upload supplier list (CSV)
```

#### Alert Tiers
```
INFO:     Risk score 0.40–0.59 — monitor, no action required
WARNING:  Risk score 0.60–0.79 — review sourcing, prepare contingency
CRITICAL: Risk score 0.80–1.00 — immediate procurement action required
```

#### Dashboard (React + Mapbox GL)
- Live world map: suppliers colored by risk score
- Chokepoint overlays: active conflict zones, vessel congestion heat map
- Supplier drill-down: click supplier → risk score + SHAP + alternatives
- Scenario simulator: UI to define and run disruption scenarios
- Alert feed: real-time alert list with acknowledge/dismiss

---

## Storage Architecture

| Store | Technology | Data | Retention |
|---|---|---|---|
| Entities | PostgreSQL 15 | Suppliers, SKUs, carriers, org data | Permanent |
| Time-series | TimescaleDB | Risk scores, vessel positions, conflict events | 5 years |
| Vectors | Qdrant | News embeddings for semantic search | 2 years |
| Graph | Neo4j 5 | Knowledge graph — all relationship data | Permanent |
| ML artifacts | MLflow + S3 | Model weights, experiment tracking | Permanent |
| Cache | Redis | API response cache, session data | 24h TTL |

---

## Infrastructure

### Local (Docker Compose)
```yaml
Services:
  - zookeeper
  - kafka (single broker)
  - neo4j
  - postgres
  - timescaledb
  - qdrant
  - redis
  - mlflow
  - prometheus
  - grafana
  - api (FastAPI)
  - frontend (React dev server)
  
Ports exposed:
  - 7474: Neo4j browser
  - 9092: Kafka
  - 8000: FastAPI
  - 3000: React
  - 9090: Prometheus
  - 3001: Grafana
  - 5432: PostgreSQL
  - 6333: Qdrant
```

### Production (Terraform + AWS)
```
ECS Fargate tasks: ingestion services (1 per source), API, intelligence engine
RDS PostgreSQL: managed, Multi-AZ
Amazon MSK: managed Kafka
Neo4j AuraDB: managed Neo4j (or self-hosted on EC2)
S3: MLflow artifact store, static frontend
CloudFront: frontend CDN
ALB: load balancer for API
Route53: DNS
CloudWatch: logs (in addition to Prometheus/Grafana)
```

---

## ML Model Registry

| Model | Version | Framework | Status | Tracked In |
|---|---|---|---|---|
| Event Classifier (BERT) | v0.1 | HuggingFace Transformers | Design only | MLflow |
| Risk Scorer (XGBoost) | v0.1 | XGBoost + SHAP | Design only | MLflow |
| TGN Forecaster | v0.1 | PyTorch Geometric Temporal | Design only | MLflow |
| HMM Regime Detector | v0.1 | hmmlearn | Design only | MLflow |
| Weak Signal (LSTM AE) | v0.1 | PyTorch | Design only | MLflow |
| Node2Vec Embeddings | v0.1 | PyTorch Geometric | Design only | MLflow |

---

## Build Phases

| Phase | Scope | Status | Notes |
|---|---|---|---|
| Phase 0 | Architecture + documentation | ✅ Complete | 2026-05-09 |
| Phase 1 | Kafka + ingestion producers (GDELT, AIS, ACLED) | ✅ Complete | Producers + graph loader consumer |
| Phase 2 | Neo4j graph + geopolitical map API | ✅ Complete | Map, timeline, conflict zones |
| Phase 3 | Risk scoring + SHAP | ⚠️ Partial | Heuristic/demo scores; MLflow training next |
| Phase 4 | Simulator + product UX | ✅ Complete | Compare, sectors, copilot, EntityDrawer |
| Phase 5 | React dashboard + CI | ✅ Complete | Vitest, Playwright scaffold, Neo4j in CI |
| Phase 6 | Advanced ML (TGN, HMM, DoWhy) | 🔬 Research | Stubs only |
| Phase 7 | Public deploy + OSS launch | 🔄 Next | Live URL, demo GIF, HN |

### Live pipeline (Phase 1 extension)

```
GDELTProducer  →  meridian.gdelt.*  →  GraphLoaderConsumer  →  :Event nodes
                                   →  EntityResolutionConsumer  →  (:Event)-[:AFFECTS]->(:Supplier)
scripts/pipeline_refresh.py  →  optional Slack alerts for high-severity ingested events
```

---

## Version History

| Version | Date | Changes |
|---|---|---|
| v0.1 | 2026-05-09 | Initial architecture design — Session 0 |
| v0.2 | 2026-06-13 | Portfolio demo UI, GDELT graph loader pipeline, CI with Neo4j |

---

## Deprecated Versions

*None yet.*
