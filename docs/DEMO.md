# Demo walkthrough (~2 minutes)

Use this script for Loom recordings, recruiter calls, and README GIF capture.
Align narration with **SCRI honesty banners** (ModelStatusBanner, band-first RiskPill, feature provenance).

## Prerequisites

```bash
docker compose up -d neo4j kafka zookeeper
cp .env.example .env   # NEO4J_URI=bolt://localhost:7688
set -a && source .env && set +a
PY=/opt/anaconda3/bin/python make seed-all   # or your venv python
PY=/opt/anaconda3/bin/python uvicorn src.api.main:app --reload --port 8002
cd frontend && npm run dev
```

Open **http://localhost:5173**

---

## Scene 1 — Honest Command Center (30s)

1. Land on **Command Center** (`/`)
2. Point out **ModelStatusBanner** — demo vs validated calibration label
3. KPI cards: suppliers tracked, critical risks, active events (band-first tooltips)
4. Click **Export digest** — markdown executive brief downloads
5. Mention: SCRI is a **modelled index** with band-first display — not actuarial probability until labeled retrain

---

## Scene 2 — Red Sea scenario (45s)

1. Go to **Simulator** (`/simulate`)
2. Select **Red Sea / Bab-el-Mandeb Disruption**
3. Click **Run scenario**
4. Highlight:
   - Suppliers affected (BFS propagation)
   - **p10 / p50 / p90** delay bands (Monte Carlo — not point estimates)
   - Mitigation playbook bullets
5. Scroll to **Propagation on map** — epicenter + affected suppliers

Optional: **Compare scenarios** — Red Sea vs Suez side-by-side.

---

## Scene 3 — World map + provenance (45s)

1. Open **Risk Map** (`/map`)
2. Toggle layers: conflict zones, trade routes, active events
3. Enable **Weather (NOAA)** and **Sanctions** supplemental layers
4. Click a high-risk supplier marker → **Entity drawer**
5. Note **feature provenance** line (live vs static features)

---

## Scene 4 — Copilot + sectors (30s)

1. **Copilot** (`/copilot`) — ask: *"What happens if Red Sea shipping is disrupted?"*
2. Click through to suggested simulator preset
3. **Sectors** (`/sectors`) — keyword classification tooltip (not ML taxonomy)
4. **Suppliers** — SHAP explanation with calibration sublabel

---

## Scene 5 — Live pipeline (optional, 30s)

With Kafka running:

```bash
make pipeline-refresh
```

Explain: GDELT → Kafka → Neo4j graph loader → entity resolution → Slack-ready alerts.
For portfolio demos without Kafka, see `docs/ARCHITECTURE_DEMO.md` (batch mode).

---

## Recording tips

- Resolution: 1920×1080, dark browser theme matches UI
- Save GIF per `docs/assets/demo-placeholder.md` → `docs/assets/meridian-demo.gif`
- Narration hook: *"Every major disruption was visible in signals weeks early — Meridian connects them to your suppliers with honest calibration labels."*
