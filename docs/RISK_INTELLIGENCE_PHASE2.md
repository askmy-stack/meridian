# Risk Intelligence — Phase 2 Report

**Date:** 2026-06-12  
**Scope:** UX/UI audit, interactive world map, geopolitical expansion, simulation enhancements, tests, production-readiness.

---

## 1. UX/UI Improvement Summary

### Strengths (post Phase 2)
- Dark command-center design system with sidebar navigation and live Neo4j health
- Map-driven narrative: conflict zones → events → trade routes → entity risk
- Drill-down panel answers **what / where / why / who / impact**
- Timeline view for non-technical stakeholders
- Simulation results include mitigation playbook + map overlay

### Improvements delivered
| Area | Change |
|------|--------|
| Information hierarchy | Map page restructured: hero → layer toggles → map + detail panel → KPI strip |
| Navigation | Added **Timeline** route (`/timeline`) |
| Data visualization | Multi-layer Mapbox map (zones, routes, events, entities) + SVG fallback |
| User flows | Map ↔ Simulate cross-links; entity list click → map selection |
| Accessibility | `aria-pressed`, `aria-busy`, `role="alert"`, `role="list"` on timeline |
| Mobile | Responsive grid (`xl:col-span-2`), collapsible sidebar (existing) |
| Empty/error states | DemoBanner, seed instructions, API error banners |
| Edge cases | No Mapbox token → SVG world map; no XGBoost → heuristic SHAP |

### Remaining UX gaps (Phase 3)
- Map click → supplier SHAP side panel (deep link to `/suppliers`)
- Real-time SSE/WebSocket map updates
- Keyboard navigation for map features
- Playwright E2E for map + simulation flows

---

## 2. Interactive World Map

**Frontend:** `frontend/src/components/map/InteractiveWorldMap.jsx`  
**API:** `GET /geopolitical/map-layers`

| Layer | Source | Interaction |
|-------|--------|-------------|
| Conflict zones | Static reference + GeoJSON polygons | Click → zone summary |
| Trade routes | Neo4j `SHIPS_VIA`, `PASSES_THROUGH` | Color by route risk |
| Active events | Neo4j `Event` nodes with lat/lon | Click → event + supplier |
| Entities | Suppliers / ports / chokepoints | Size/color by risk score |
| Simulation overlay | Post-run affected suppliers | Rose markers on epicenter |

---

## 3. Geopolitical Dataset Expansion

**Seed script:** `scripts/seed_demo_scenarios.py` — **8 events** including:
- Russia–Ukraine armed conflict
- US–Iran / Hormuz energy security
- China–US trade restrictions
- Semiconductor allocation risk
- Red Sea, Taiwan Strait, Suez (existing)

**Reference zones:** `src/geopolitical/conflict_zones.py` — 6 operational areas with sectors and summaries.

**Simulation presets:** 6 scenarios in `src/api/routes/simulation.py` with mitigations and regions.

---

## 4. Scenario Simulation Enhancements

`POST /simulation/scenarios/{id}/run` now returns:
- `impact_summary` — headline, revenue at risk, probabilities
- `mitigations` — actionable playbook bullets
- `map_overlay` — epicenter + affected supplier GeoJSON

---

## 5. Additional Views

| View | Route | Status |
|------|-------|--------|
| Global risk map | `/map` | Enhanced |
| Timeline | `/timeline` | **New** |
| Supply graph | `/network` | Existing |
| Command center | `/` | Existing (digest + charts) |
| Simulator | `/simulate` | Enhanced with map |

---

## 6. Test Coverage

| File | Coverage |
|------|----------|
| `tests/unit/test_geopolitical_routes.py` | Conflict zones, map-layers, events*, routes*, timeline* |
| `tests/unit/test_conflict_zones.py` | Static zone data + GeoJSON |
| `tests/unit/test_risk_map.py` | Risk map API + port score fix |
| `tests/unit/test_simulation_route.py` | 6 scenarios + mitigations |

\* `neo4j_required` marker — run with seeded Neo4j.

### Recommended E2E (not yet automated)
1. Load `/map` → toggle layers → click zone → detail panel populates
2. Run Taiwan scenario → map overlay shows affected suppliers
3. Timeline lists ≥8 events after `make seed-demo`

---

## 7. Production-Readiness Assessment

| Pillar | Score | Notes |
|--------|-------|-------|
| Demo / portfolio | **A** | 5-min walkthrough with map + simulate + timeline |
| Data pipeline | **C** | Kafka producers exist; not wired to map/API |
| Auth / security | **C+** | JWT on writes; read routes open for demo |
| ML / explainability | **B-** | Heuristic SHAP fallback works; XGBoost optional |
| Testing | **B** | 38+ unit tests; no frontend E2E yet |
| Ops / deploy | **B-** | Docker Neo4j on isolated ports; Railway-ready API |

**Verdict:** Phase 2 delivers a **credible map-driven risk intelligence demo**. Phase 3 should focus on live ingestion, persistent alerts, and E2E tests.

---

## Quick start

```bash
docker compose up -d neo4j
set -a && source .env && set +a
make seed-all
uvicorn src.api.main:app --reload --port 8002
cd frontend && npm run dev
```

Open http://localhost:5173/map

Optional: `VITE_MAPBOX_TOKEN` in `frontend/.env.local` for full Mapbox tiles.
