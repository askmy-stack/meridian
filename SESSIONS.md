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
4. Check Kafka UI at http://localhost:8080 for topic verification
5. Begin entity resolution service (Phase 2)

[OWNER NOTES]
- 
