# AGENTS.md — Agent Operating Instructions for Meridian

> This file is the **primary instruction set** for any AI agent working on Meridian.
> Read this before touching any file, writing any code, or making any architectural decision.
> Update this file when operating rules change.

---

## What is Meridian

Meridian is an open-source **Supply Chain Geopolitical Risk Intelligence Platform**.

It ingests real-time signals (conflict data, AIS vessel tracking, weather, financial indicators, news) and maps them through a knowledge graph to predict disruptions to specific suppliers, routes, and SKUs — before they happen.

**Thesis:** Every major supply chain disruption of the last 20 years was visible in signals weeks before impact. Meridian connects those signals in real-time.

---

## Owner

**Abhinaysai Kamineni**
MS Data Science, George Washington University (May 2026)
Arlington, VA | kamineniabhinaysai@gmail.com
GitHub: github.com/askmy-stack
LinkedIn: linkedin.com/in/abhinaysai-kamineni

**Job search context:** This project is a portfolio centerpiece targeting AI/ML Engineer and Data Engineering roles at Series B+ companies ($150K+). Every build decision should maximize both technical depth and recruiter legibility.

---

## Agent Operating Rules

### Before every session
1. Read `SESSIONS.md` — understand what was built last, what's in-progress
2. Read `DECISIONS.md` — check for new instructions or priority changes
3. Read `MISTAKES.md` — don't repeat known errors
4. Check `ARCHITECTURE.md` — understand current system state before proposing changes

### Code standards
- Python 3.11+
- Type hints on all functions
- Docstrings on all classes and public methods
- No hardcoded credentials — use `.env` + `python-dotenv`
- All services containerized — `Dockerfile` per service, `docker-compose.yml` at root
- Tests in `/tests/` — pytest, minimum unit tests for all ML components
- Logging via `structlog` — structured JSON logs, never `print()`

### Architecture rules
- Kafka is the single event bus — nothing communicates point-to-point at scale
- Neo4j is the source of truth for relationships — no relationship logic in application code
- All ML models tracked in MLflow — no untracked experiments
- Risk scores always include SHAP explanation — no black-box outputs to users
- Monte Carlo simulations run minimum 1000 iterations — never point estimates

### What NOT to do
- Do not hardcode scenario templates — scenarios are LLM-generated + user-defined
- Do not use correlation as causation — DoWhy for all causal claims
- Do not build UI before core pipeline works — data first, always
- Do not use synchronous HTTP calls between services — Kafka or async
- Do not expose raw LLM output as risk scores — LLM classifies events, XGBoost scores risk

### Response style
- No filler words
- No lengthy preambles
- Execution-first: write code, then explain if needed
- When stuck: state the blocker clearly, propose 2 options, ask for decision
- Always reference `DECISIONS.md` before proposing architectural changes

---

## Current Phase

**Phase:** Pre-build — documentation and architecture finalization
**Next milestone:** MVP data ingestion pipeline (Kafka + GDELT + AIS)
**Target:** Working demo in 6 weeks

---

## Key Constraints

| Constraint | Detail |
|---|---|
| Hardware | HP ZBook 15 G5 — 48GB RAM, NVIDIA Quadro P2000 4GB VRAM |
| Local LLM | Ollama + Gemma 4 E4B (WSL2, ~10GB RAM, 8-12 tok/s) |
| Cloud budget | Minimize — use free tiers (GDELT, AIS public, NOAA, ACLED) |
| Timeline | 6-week MVP, open-source launch by end of week 7 |
| Portfolio goal | GitHub repo must be demo-able in under 5 minutes |

---

## Free Data Sources (confirmed available)

| Source | Data | API/Access |
|---|---|---|
| GDELT Project | Global news events, conflict | gdeltproject.org — free, no key |
| ACLED | Armed conflict events, locations | acleddata.com — free academic key |
| AIS (AISHub) | Vessel positions, port calls | aishub.net — free tier |
| NOAA | Weather, climate alerts | api.weather.gov — free, no key |
| NASA FIRMS | Fire, flood, disaster events | firms.modaps.eosdis.nasa.gov — free |
| OpenSanctions | Sanctions lists, entities | opensanctions.org — free |
| World Bank | Country risk indicators | api.worldbank.org — free |
| UN Comtrade | Trade flow data | comtradeapi.un.org — free tier |

---

## Glossary

| Term | Definition |
|---|---|
| Chokepoint | Geographic bottleneck in global shipping (Suez, Strait of Hormuz, etc.) |
| SCRI | Supply Chain Risk Intelligence — internal acronym for Meridian |
| TGN | Temporal Graph Network — core ML model for risk prediction |
| BFS | Breadth-First Search — used for disruption propagation through graph |
| SHAP | SHapley Additive exPlanations — explainability layer on risk scores |
| AIS | Automatic Identification System — vessel tracking transponder data |
| ACLED | Armed Conflict Location & Event Data — conflict event database |
| GDELT | Global Database of Events, Language, and Tone — news event database |
