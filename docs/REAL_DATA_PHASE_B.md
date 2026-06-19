# Phase B — Intelligence Layer

Meridian Phase B adds Qdrant RAG grounding, structured event classification, conformal SCRI intervals, and lightweight changepoint weak-signal detection — all without requiring Qdrant or Ollama for the demo path.

**Prerequisite:** [Phase A — Real Data Foundation](REAL_DATA_PHASE_A.md) · **Next:** [Phase C — Predictive & Causal Research](REAL_DATA_PHASE_C.md)

## Architecture

```mermaid
flowchart LR
    subgraph rag [RAG]
        QD[Qdrant]
        EM[Embedder hash / MiniLM]
        IX[index_rag_corpus.py]
        KI[rag_indexer Kafka consumer]
        GC[index_graph_communities.py]
    end
    subgraph intel [Intelligence]
        EC[event_classifier.py]
        CF[conformal.py]
        CP[changepoint CUSUM]
        COP[copilot_service.py]
    end
    subgraph graph [Neo4j]
        E[Event]
        S[Supplier]
    end
    IX --> EM --> QD
    KI --> EM --> QD
    GC --> EM --> QD
    COP --> QD
    COP --> S
    GL[graph_loader] --> EC
    GL --> KI
    SS[score_suppliers] --> CF
    SS --> IX
    CF --> API["/suppliers/{id}/explanation"]
    CP --> API2["/intelligence/suppliers/{id}/weak-signals"]
    COP --> API3["/intelligence/copilot"]
    DIG[weekly digest] --> QD
```

**D-006 enforced:** LLM classifies events and composes grounded prose only — never outputs `risk_score` or SCRI percentages unless those values exist in Neo4j context.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant HTTP endpoint |
| `RAG_EMBED_MODE` | *(unset)* | Set to `hash` for deterministic test embeddings |
| `RAG_EMBED_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model when installed |
| `LLM_PROVIDER` | `stub` | `stub` \| `ollama` \| `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama API |
| `OLLAMA_MODEL` | `gemma2:2b` | Ollama model name |
| `OPENAI_API_KEY` | *(unset)* | Required when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `ENABLE_LLM_CLASSIFIER` | `false` | Hook classifier in GDELT graph_loader path |
| `RAG_INDEXER_MAX_IDLE_ROUNDS` | `3` | Idle polls before rag-indexer exits |

Optional embeddings: `pip install -r requirements-dev.txt` (sentence-transformers).

## Make targets

```bash
make index-rag                  # Neo4j + scenarios + backtests + docs → Qdrant
make index-graph-communities    # Supplier graph communities (GraphRAG)
make rag-indexer                # Stream Kafka events → Qdrant (PIPELINE_MAX_MESSAGES)
```

Graceful skip when Qdrant is down — logs `qdrant_index_skipped`, exit 0.

## Qdrant collections

| Collection | Source | Indexed by |
|------------|--------|------------|
| `meridian_events` | Neo4j Event nodes + Kafka stream | `index_rag_corpus.py`, `rag_indexer` |
| `meridian_suppliers` | Neo4j Supplier nodes | `index_rag_corpus.py`, `score_suppliers` re-index |
| `meridian_methodology` | `docs/METRICS.md`, `LIMITATIONS.md`, `CAUSAL_SCOPE.md` | `index_rag_corpus.py` |
| `meridian_scenarios` | `DEMO_SCENARIOS` simulation presets | `index_rag_corpus.py` |
| `meridian_backtests` | `BACKTEST_SCENARIOS` case studies | `index_rag_corpus.py` |
| `meridian_graph_communities` | Neo4j supplier subgraph clusters | `index_graph_communities.py` |

## Components

### Qdrant RAG (`src/rag/`)

| Module | Role |
|--------|------|
| `qdrant_client.py` | Connect + health probe |
| `embedder.py` | MiniLM or hash fallback (384-dim) |
| `collections.py` | Collections + `search_routed()` keyword routing |
| `indexing.py` | Reusable corpus indexing helpers |
| `context_budget.py` | Dedupe citations, cap ~4000 chars |
| `llm_compose.py` | Shared LLM synthesis (copilot + digest) |
| `copilot_service.py` | Routed retrieval + question-aware Neo4j facts |

### Kafka RAG indexer (`src/consumers/rag_indexer.py`)

Subscribes to `GRAPH_LOADER_TOPICS` (GDELT + ACLED conflict streams). On each message: embed event text → `upsert_documents(meridian_events)`. Logs `rag_index_event`. Graceful skip when Qdrant unavailable.

Run locally: `make rag-indexer` or `python -m src.consumers rag-indexer`. Optional `rag-indexer` service in `docker-compose.yml`.

### GraphRAG communities (`scripts/index_graph_communities.py`)

Fetches supplier subgraph from Neo4j, detects communities (NetworkX Louvain when available, else `country_iso` clusters), writes deterministic summaries to `meridian_graph_communities`. Copilot searches this collection when questions mention region/sector/cluster keywords.

### Event classifier (`src/intelligence/event_classifier.py`)

Rule-based default → `{event_type, severity_proxy, locations[], entities[]}`. Optional LLM when `ENABLE_LLM_CLASSIFIER=true`.

### Conformal SCRI (`src/intelligence/conformal.py`)

Split conformal on `data/disruption_labels.csv` holdout → `score_interval: {lower, upper, coverage, method}` on supplier explanation API.

### Changepoint weak signals (`src/intelligence/changepoint.py`)

CUSUM on daily event rate per supplier. Exposed at `GET /intelligence/suppliers/{id}/weak-signals`.

## API changes

| Endpoint | Change |
|----------|--------|
| `POST /intelligence/copilot` | Routed retrieval, richer graph context, `citations_count`/`retrieval_ms` in logs |
| `POST /intelligence/weekly-digest` | + `citations[]`, `narrative_type` (`template` \| `rag`) |
| `GET /suppliers/{id}/explanation` | + `related_corpus[]` (citations only, no new scores) |
| `GET /intelligence/suppliers/{id}/weak-signals` | CUSUM + weak-signal detector |

## Local verification

```bash
make up                  # includes Qdrant on :6333
make index-rag           # optional — graceful skip if Qdrant down
make index-graph-communities
RAG_EMBED_MODE=hash LLM_PROVIDER=stub python3 -m pytest tests/unit/test_phase_b.py tests/unit/test_rag_extended.py -v
python3 -m pytest tests/unit/ -m "not neo4j_required" -q
```

## Phase C pointer

Phase C (planned): Kafka rescore consumer, risk timeline API from TimescaleDB, expanded label corpus (500 rows), and production LLM batch classification pipeline.

See `DECISIONS.md` D-006 and `SESSIONS.md` Session 13.
