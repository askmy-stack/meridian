# DECISIONS.md — Decision Log + Agent Instructions

> Two purposes:
> 1. **Abhinaysai:** Add instructions here to redirect the agent's work. Agent reads this every session.
> 2. **Agent:** Log every significant architectural or product decision here with rationale.

---

## HOW TO ADD INSTRUCTIONS (for Abhinaysai)

Add a block at the top of the `ACTIVE INSTRUCTIONS` section:

```
### [DATE] — [Your instruction]
Priority: HIGH / MEDIUM / LOW
Status: OPEN
Detail: [What you want done, as specific as possible]
```

Agent will pick up OPEN instructions at next session start, execute, then mark `Status: DONE`.

---

## ACTIVE INSTRUCTIONS

### 2026-05-09 — Build Phase 1: Kafka ingestion pipeline
Priority: HIGH
Status: OPEN
Detail:
- Write docker-compose.yml with Kafka, Zookeeper, Neo4j, PostgreSQL, TimescaleDB, Qdrant
- Write GDELT Kafka producer (Python) — no API key needed, start here
- Write ACLED Kafka producer (Python) — requires free API key
- Write AIS Kafka producer (Python) — AISHub free tier
- All producers: structured JSON output, schema validated with Pydantic
- Topic naming convention: `meridian.{source}.{event_type}` e.g. `meridian.gdelt.conflict`
- Log every event to structlog before publishing to Kafka
- Write pytest unit tests for each producer (mock Kafka, real schema validation)

---

## DECISION LOG

Decisions are immutable once logged. To reverse a decision, add a new entry marked `[REVERSAL]` with rationale.

---

### D-001 — 2026-05-09 — Kafka as single event bus
**Status:** Active
**Decision:** All inter-service communication goes through Kafka. No synchronous HTTP between pipeline services.
**Rationale:** Supply chain signals are high-volume, time-series, and need replay capability (for backtesting simulations against historical disruptions). Kafka gives decoupling, persistence, and replay. HTTP would create tight coupling and lose the ability to reprocess historical events.
**Alternatives considered:** RabbitMQ (no replay), Redis Pub/Sub (no persistence), direct HTTP (no decoupling)
**Owner:** Abhinaysai

---

### D-002 — 2026-05-09 — Neo4j as knowledge graph
**Status:** Active
**Decision:** All relationship data lives in Neo4j. No relationship logic in application code or relational DB.
**Rationale:** Supply chain risk is fundamentally a graph problem — multi-hop dependency tracing (Supplier → Port → Chokepoint → Route → SKU) is a native graph query, not a JOIN chain. Cypher queries are more readable and maintainable than recursive SQL for this use case.
**Alternatives considered:** PostgreSQL with recursive CTEs (possible but painful), Amazon Neptune (cost), TigerGraph (complexity)
**Owner:** Abhinaysai

---

### D-003 — 2026-05-09 — XGBoost + SHAP for risk scoring (not deep learning)
**Status:** Active
**Decision:** Risk scores computed by XGBoost. Every score ships with SHAP explanation. No neural network for the primary risk score.
**Rationale:** Procurement teams won't act on scores they can't explain to their CFO. SHAP on XGBoost gives per-feature attribution that's business-legible ("score elevated because: Taiwan Strait military activity +0.34, single-source dependency +0.28"). Deep learning scores would require additional explanation layer and add complexity without accuracy gain for tabular risk features.
**Alternatives considered:** Neural network (less explainable), LLM scoring (hallucination risk — LLM classifies events only, never scores risk), pure rules (doesn't generalize)
**Owner:** Abhinaysai

---

### D-004 — 2026-05-09 — TGN (Temporal Graph Network) as forecasting core
**Status:** Active
**Decision:** 7/14/30-day risk forecasting uses TGN trained on historical disruption events.
**Rationale:** Standard GNNs ignore time — supply chain risk is inherently temporal (a 3-day-old conflict behaves differently than a 3-week-old one). TGN handles dynamic graphs with temporal features natively. This is the primary ML moat — no production supply chain tool uses TGNs publicly.
**Alternatives considered:** Static GNN (ignores time), LSTM on tabular features (ignores graph structure), ARIMA (ignores graph relationships)
**Implementation note:** Use PyTorch Geometric Temporal library. Train on: COVID 2020, Suez 2021, Red Sea 2023 disruption events mapped to real supply chain impact metrics.
**Owner:** Abhinaysai

---

### D-005 — 2026-05-09 — DoWhy for all causal claims
**Status:** Active
**Decision:** Any statement of causation in Meridian must go through DoWhy causal inference. Correlation ≠ causation in the codebase.
**Rationale:** One false positive alert that procurement acts on and finds wrong destroys trust in the entire system permanently. Causal inference distinguishes "Red Sea conflict CAUSES shipping delays" from "Red Sea conflict and delays share a common cause (US election cycle)." This is the difference between a useful system and a noise generator.
**Alternatives considered:** Granger causality (weaker), pure correlation (insufficient), manual analyst review (doesn't scale)
**Owner:** Abhinaysai

---

### D-006 — 2026-05-09 — Local LLM for dev, GPT-4o for production event classification
**Status:** Active
**Decision:** Development uses Ollama + Gemma 4 E4B (local WSL2). Production event classification uses GPT-4o API with structured output (function calling).
**Rationale:** LLM is used only for event classification (structured JSON extraction from news text) — not for risk scoring. This is a bounded, testable task. GPT-4o function calling gives reliable structured output. Local LLM for dev avoids API costs during iteration.
**Cost control:** Cache LLM outputs for identical news text. Batch classification — don't call API per-event in real-time, batch every 60 seconds.
**Owner:** Abhinaysai

---

### D-007 — 2026-05-09 — Free data sources only for MVP
**Status:** Active
**Decision:** MVP uses only free-tier data sources. No paid APIs until open-source launch validates demand.
**Rationale:** Portfolio project — cost must be near-zero. GDELT, ACLED (free academic), AISHub (free tier), NOAA, NASA FIRMS collectively cover all signal categories needed for MVP.
**Paid sources to consider post-launch:** Refinitiv (financial), Spire (AIS premium), Predata (political risk) — evaluate based on user demand after launch.
**Owner:** Abhinaysai

---

### D-008 — 2026-05-09 — Docker Compose local, Terraform + AWS ECS production
**Status:** Active
**Decision:** Local development via Docker Compose. Production via Terraform-provisioned AWS ECS (Fargate).
**Rationale:** Matches existing skill set (Jio Platforms Terraform + Kubernetes experience). ECS Fargate avoids Kubernetes management overhead for initial deployment. One-command local setup maximizes contributor onboarding for open-source.
**Migration path:** Docker Compose → ECS → EKS if scale demands Kubernetes
**Owner:** Abhinaysai

---

### D-009 — 2026-05-09 — Apache 2.0 license
**Status:** Active
**Decision:** Apache 2.0 for open-source release.
**Rationale:** Permissive — allows commercial use, which maximizes adoption and potential enterprise contributors. More permissive than GPL (which would scare enterprise users). Standard for ML/data infrastructure open-source projects (Airflow, Kafka, Spark all Apache 2.0).
**Owner:** Abhinaysai

---

### D-010 — 2026-05-09 — Monte Carlo minimum 1000 iterations per simulation
**Status:** Active
**Decision:** Disruption simulator runs minimum 1000 Monte Carlo iterations. Never output point estimates.
**Rationale:** Supply chain decisions involve millions of dollars. Point estimates are false precision. Probability distributions with confidence intervals give decision-makers the uncertainty context they need. 1000 iterations gives stable distribution at acceptable compute cost.
**Owner:** Abhinaysai

---

## PENDING DECISIONS (need resolution before build)

| # | Decision needed | Options | Deadline |
|---|---|---|---|
| P-001 | Graph schema versioning — how to handle schema migrations in Neo4j | Liquigraph / manual Cypher migration scripts / versioned snapshots | Before Phase 2 |
| P-002 | Multi-tenant vs. single-tenant for open-source version | Single tenant (simpler) / multi-tenant with org isolation | Before Phase 5 |
| P-003 | Supplier data input format | CSV upload / API / manual form / all three | Before Phase 2 |
| P-004 | Alert deduplication strategy | Time-window dedup / content hash / severity threshold | Before Phase 4 |
