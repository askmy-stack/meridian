# Demo walkthrough (2–3 minutes)

Use this script for Loom recordings, recruiter calls, and README GIF capture.

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

## Scene 1 — Command Center (30s)

1. Land on **Command Center** (`/`)
2. Point out KPI cards: suppliers tracked, critical risks, active events
3. Click **Export digest** — markdown executive brief downloads
4. Mention: scores come from Neo4j graph + XGBoost (SHAP on supplier drill-down)

---

## Scene 2 — Red Sea scenario (45s)

1. Go to **Simulator** (`/simulate`)
2. Select **Red Sea / Bab-el-Mandeb Disruption**
3. Click **Run scenario**
4. Highlight:
   - Suppliers affected (BFS propagation)
   - Disruption probability (1,000-iteration Monte Carlo)
   - Mitigation playbook bullets
5. Scroll to **Propagation on map** — epicenter + affected suppliers

Optional: use **Compare scenarios** — Red Sea vs Suez side-by-side.

---

## Scene 3 — World map (45s)

1. Open **Risk Map** (`/map`)
2. Toggle layers: conflict zones, trade routes, active events
3. Enable **Weather (NOAA)** and **Sanctions** supplemental layers
4. Click a high-risk supplier marker → **Entity drawer** opens
5. Click **View on map** / navigate from **Alerts** via **View on map** deep link

---

## Scene 4 — Copilot + sectors (30s)

1. **Copilot** (`/copilot`) — ask: *"What happens if Red Sea shipping is disrupted?"*
2. Click through to suggested simulator preset
3. **Sectors** (`/sectors`) — semiconductor / shipping exposure aggregates
4. **Timeline** (`/timeline`) — drag 7–90 day window slider

---

## Scene 5 — Live pipeline (optional, 30s)

With Kafka running:

```bash
make pipeline-refresh
```

Explain: GDELT → Kafka → Neo4j graph loader → entity resolution → Slack-ready alerts.

Verify in Kafka UI: http://localhost:8081

---

## Recording tips

- Resolution: 1920×1080, dark IDE/browser theme matches UI
- Save GIF to `docs/assets/meridian-demo.gif` (≤15 MB, ~15 fps)
- Narration hook: *"Every major disruption was visible in signals weeks early — Meridian connects them to your suppliers in real time."*
