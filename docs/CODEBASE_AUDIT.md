# Meridian Codebase Audit

**Date:** 2026-06-14  
**Scope:** Full repo scan — backend, frontend, tests, scripts, docs  
**Auditor:** Agent session (post Phase C)

---

## Summary counts

| Category | Count | Fixed this session |
|----------|------:|-------------------:|
| Critical bugs | 6 | 6 |
| Medium bugs | 8 | 4 |
| UI/UX improvements | 12 | 4 |
| Functionality gaps | 10 | 1 |
| Technical debt | 9 | 3 |

---

## Critical bugs

### 1. passlib + bcrypt 4.1+ breaks JWT user bootstrap (Python 3.13)
- **Location:** `src/api/auth/jwt.py`, `requirements.txt`
- **Severity:** Critical — API import fails at startup when bootstrap users are configured
- **Symptom:** `ValueError: password cannot be longer than 72 bytes` during passlib bcrypt backend init
- **Fix:** Pin `bcrypt==4.0.1` in `requirements.txt` (passlib 1.7.4 incompatible with bcrypt 4.1+)
- **Status:** Fixed

### 2. JWT user store built at import time
- **Location:** `src/api/auth/jwt.py`
- **Severity:** Critical — pytest collection fails before conftest monkeypatch runs
- **Fix:** Lazy `get_users_db()` initialization
- **Status:** Fixed

### 3. Heavy ML imports at package init block API/tests without torch/xgboost
- **Location:** `src/intelligence/__init__.py`, `src/intelligence/feature_builder.py`
- **Severity:** Critical — importing model_status pulled torch/xgboost transitively
- **Fix:** PEP 562 lazy exports; extracted `FeatureVector` to `feature_vector.py` (no xgboost)
- **Status:** Fixed

### 4. `demo.sh` runs all unit tests including `neo4j_required`
- **Location:** `scripts/demo.sh`
- **Severity:** Critical for portfolio demo — confusing skips/failures when Neo4j not seeded
- **Fix:** `pytest tests/unit/ -m "not neo4j_required" -q`
- **Status:** Fixed

### 5. `test_api.sh` targets wrong API port
- **Location:** `scripts/test_api.sh`
- **Severity:** Critical — smoke checks fail (Makefile uses port **8002**, script used **8000**)
- **Fix:** Default `MERIDIAN_API_URL=http://localhost:8002`
- **Status:** Fixed

### 6. Fuzzy entity matcher cache never invalidated after bulk graph writes
- **Location:** `src/entity_resolution/fuzzy_matcher.py` (method exists); callers missing
- **Severity:** Critical for data integrity — stale supplier name cache after ERP/seed ingest
- **Fix:** Call `get_fuzzy_matcher().invalidate_cache()` in `scripts/ingest_erp_csv.py`, `scripts/seed_suppliers.py`
- **Status:** Fixed

---

## Medium bugs

### 7. Six unit tests skip when Neo4j unreachable
- **Location:** `tests/unit/test_geopolitical_routes.py`, `tests/unit/test_risk_map.py`; `tests/conftest.py`
- **Severity:** Medium — expected; CI runs with Neo4j seeded
- **Fix:** Run `docker compose up -d neo4j && make seed-all` before full suite
- **Status:** Open (by design)

### 8. XGBoost requires libomp on macOS (Python 3.13 local env)
- **Location:** System / `xgboost` wheel
- **Severity:** Medium — blocks API-route tests locally; CI (Python 3.11) unaffected
- **Fix:** `brew install libomp` or Python 3.11 venv per AGENTS.md
- **Status:** Open (environment)

### 9. `seed_suppliers.py` default Neo4j URI uses port 7687
- **Location:** `scripts/seed_suppliers.py`
- **Severity:** Medium — mismatch with docker-compose host port **7688**
- **Suggested fix:** Default to `bolt://localhost:7688`
- **Status:** Fixed

### 10. `LIMITATIONS.md` Layer B still says WGI is static-only
- **Location:** `docs/LIMITATIONS.md`
- **Severity:** Medium — docs drift (live WGI cache shipped in Chunk 2)
- **Status:** Fixed (follow-up session)

### 11. Async TimescaleDB unit test flaky on some asyncio backends
- **Location:** `tests/unit/test_timescale_writer.py::test_write_score_batch_executes`
- **Status:** Passes on Python 3.12; minor AsyncMock warning only

### 12. `requirements.txt` pins `torch==2.1.2` (not installable on Python 3.13)
- **Suggested fix:** Document Python 3.11 requirement; split optional ML requirements
- **Status:** Open

### 13. Auth-enabled demo: write routes return 401 without login
- **Location:** `src/api/deps.py`, `frontend/src/pages/LoginView.jsx`
- **Status:** Open — document in DEMO.md

### 14. Integration tests require running Docker stack
- **Location:** `tests/integration/test_api_endpoints.py`
- **Status:** Open (expected)

---

## UI/UX improvements

| # | Title | Location | Severity | Status |
|---|-------|----------|----------|--------|
| 15 | Dashboard missing API error state | `Dashboard.jsx` | High | Fixed |
| 16 | SuppliersView missing load/explanation errors | `SuppliersView.jsx` | High | Fixed |
| 17 | SimulationView silent simulation failures | `SimulationView.jsx` | High | Fixed |
| 18 | GraphHealthView no error handling | `GraphHealthView.jsx` | Medium | Fixed |
| 19 | CopilotView no persistent error banner | `CopilotView.jsx` | Medium | Fixed |
| 20 | Inconsistent error UI across pages | Timeline/RiskMap/Network | Low | Open |
| 21 | No route-level auth guard | `App.jsx` | Low | Open |
| 22 | Large JS bundles (Mapbox + MapLibre) | `frontend/` | Medium | Open |
| 23 | Demo GIF placeholder | `docs/assets/` | Medium | Open |
| 24 | npm audit vulnerabilities | `frontend/package-lock.json` | Low | Open |
| 25 | Mobile nav a11y (focus trap) | `Layout.jsx` | Low | Open |
| 26 | Shared `ErrorBanner` not used everywhere | various | Low | Partial |

---

## Functionality improvements

| # | Title | Location | Severity | Status |
|---|-------|----------|----------|--------|
| 27 | Live AIS → SCRI features stub | `feature_builder.py` | High | Open |
| 28 | Node2Vec alternatives stub | `graph_embeddings.py` | Medium | Open |
| 29 | TGN needs ≥7 daily snapshots | `prepare_tgn_training.py` | Medium | Open |
| 30 | Labels ~83 rows vs 500 target | `data/disruption_labels.csv` | Medium | Open |
| 31 | Public deploy not executed | `railway.toml`, `vercel.json` | Medium | Open |
| 32 | ACLED not in default pipeline refresh | `pipeline_refresh.py` | Low | Open |
| 33 | Weather features default to 0 | `feature_builder.py` | Medium | Open |
| 34 | Kafka rescore consumer deferred | Phase B roadmap | Low | Open |
| 35 | Weekly digest template-only | intelligence API | Low | Documented |
| 36 | Fuzzy cache invalidation on ingest | seed/ERP scripts | Medium | Fixed |

---

## Technical debt

- Pydantic v2 class `Config` deprecation (`src/schemas.py`)
- tensorflow in requirements (heavy, lightly used)
- `src/api/__init__.py` eager `app` import side effects
- No `make test-unit-fast` for `-m "not neo4j_required"`
- ARCHITECTURE.md Phase 6 status stale (stubs now partially shipped)
- Python 3.13 local venv incomplete vs CI Python 3.11
- starlette/httpx deprecation in TestClient
- Duplicate map rendering libraries
- GDPR N/A for current demo scope (no PII beyond JWT bootstrap users)

---

## Test run results (this session)

| Command | Result |
|---------|--------|
| `pytest tests/unit/test_timescale_writer.py` | **6 passed** (Python 3.12) |
| `pytest` subset (non-API unit tests) | **44 passed** (subagent session; xgboost blocked on 3.13) |
| `npm run build` | Pass |

**Local blockers:** Python 3.13 + missing `libomp` for xgboost API tests; use CI (3.11) or `brew install libomp`.

---

## Fixes implemented this session

| File | Change |
|------|--------|
| `requirements.txt` | Pin `bcrypt==4.0.1` |
| `src/api/auth/jwt.py` | Lazy `get_users_db()` |
| `src/intelligence/__init__.py` | Lazy ML exports |
| `src/intelligence/feature_vector.py` | New — decouple FeatureVector from xgboost |
| `src/intelligence/risk_scorer.py` | Import FeatureVector from feature_vector |
| `src/intelligence/feature_builder.py` | Import FeatureVector from feature_vector |
| `tests/conftest.py` | Module-level test env defaults |
| `tests/unit/test_wgi_loader.py` | Direct feature_builder import |
| `scripts/demo.sh` | Exclude neo4j_required tests |
| `scripts/test_api.sh` | Port 8002 default |
| `scripts/ingest_erp_csv.py` | Invalidate fuzzy matcher cache |
| `scripts/seed_suppliers.py` | Invalidate fuzzy matcher cache |
| `frontend/src/components/ui/ErrorBanner.jsx` | New shared component |
| `frontend/src/pages/Dashboard.jsx` | Error state |
| `frontend/src/pages/SuppliersView.jsx` | Error states |
| `frontend/src/pages/SimulationView.jsx` | Error states |
| `frontend/src/pages/GraphHealthView.jsx` | Error state |
| `Makefile` | `test-unit-fast` target |
| `frontend/src/pages/CopilotView.jsx` | Copilot + backtest error banners (follow-up) |
| `docs/LIMITATIONS.md` | WGI cache wording (follow-up) |

---

## Recommended next PR chunks

1. **UX polish:** MapLibre-only bundle; ErrorBanner on Timeline/RiskMap/Network
2. **Data pipeline:** ACLED in pipeline_refresh, NOAA → SCRI, expand labels
3. **Data pipeline:** ACLED in pipeline_refresh, NOAA → SCRI, expand labels
4. **Deploy:** Railway + Vercel + demo GIF

---

## Blockers

- Local Python 3.13 + missing libomp for xgboost
- Neo4j/Docker for integration tests
- Deploy requires owner cloud credentials
