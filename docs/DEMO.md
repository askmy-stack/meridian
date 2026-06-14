# Demo walkthrough (~2 minutes)

Use this script for Loom recordings, recruiter calls, and README GIF capture.
Align narration with **SCRI honesty banners** (ModelStatusBanner, band-first RiskPill, feature provenance).

## Prerequisites

```bash
docker compose up -d neo4j
cp .env.example .env   # NEO4J_URI=bolt://localhost:7688
set -a && source .env && set +a

make portfolio-ready     # WGI + train + seed + score (Neo4j steps skip if down)
make dev                 # API :8002
make dev-frontend        # UI :5173
```

Open **http://localhost:5173**

Record GIF: `bash scripts/record_demo.sh` → `docs/assets/meridian-demo.gif`

---

## Scene 1 — Honest Command Center (25s)

**Route:** `/` (Command Center)

1. Land on dashboard — note **ModelStatusBanner** at top (demo vs validated calibration)
2. KPI cards: suppliers tracked, critical risks, active events — hover for **band-first** tooltips (LOW/MEDIUM/HIGH/CRITICAL before %)
3. Weekly digest panel — label shows `narrative_type: template` (not LLM-verified prose)
4. Click **Export digest** — markdown executive brief downloads
5. Narration: SCRI is a **modelled index** with honest calibration — not actuarial probability until labeled retrain

---

## Scene 2 — Red Sea scenario (35s)

**Route:** `/simulate` (Simulator)

1. Select **Red Sea / Bab-el-Mandeb Disruption** preset
2. Click **Run scenario**
3. Highlight:
   - Suppliers affected (BFS graph propagation)
   - **p10 / p50 / p90** delay bands — Monte Carlo, not point estimates
   - Revenue impact bands if shown
   - Mitigation playbook bullets
4. Scroll to **Propagation on map** — epicenter + affected supplier markers

Optional: **Compare scenarios** — Red Sea vs Suez side-by-side.

---

## Scene 3 — World map + provenance (30s)

**Route:** `/map` (Risk Map)

1. Toggle layers: conflict zones, trade routes, active events
2. Enable **Weather (NOAA)** and **Sanctions** supplemental layers
3. Click a high-risk supplier marker → **Entity drawer**
4. Point out **feature provenance** line (live vs static/stub features)
5. Mention labeled training data in `data/disruption_labels.csv` when discussing risk scores

---

## Scene 4 — Copilot, sectors, suppliers (25s)

**Routes:** `/copilot`, `/sectors`, `/suppliers`

1. **Copilot** — ask: *"What happens if Red Sea shipping is disrupted?"*
   - Show disclaimer banner and graph-grounded facts
   - Click through to suggested simulator preset
2. **Sectors** — hover classification tooltip (`classification_method: keyword`, not ML taxonomy)
3. **Suppliers** — open SHAP explanation with calibration sublabel and **pillar mini-bars** (geo/ops/fin stubs)

---

## Scene 5 — Graph health + alerts (25s)

**Routes:** `/ops/graph-health`, `/alerts`

1. **Graph Health** — completeness score, tier-2 supplier count, geo/event coverage
2. Model status block mirrors Command Center banner
3. **Alerts** — tier badges, causal **association** label + sample count (not verified causation)

---

## Scene 6 — Live pipeline (optional, 20s)

**Without Kafka (laptop demo):**

```bash
make pipeline-batch
```

**With Kafka:**

```bash
make pipeline-refresh
```

Explain: GDELT → Kafka → Neo4j graph loader → entity resolution → Slack-ready alerts.
Batch mode re-scores suppliers without streaming — see `docs/ARCHITECTURE_DEMO.md`.

---

## Recording tips

- Resolution: 1920×1080, dark browser theme matches UI
- Script: `bash scripts/record_demo.sh` (ffmpeg + palette GIF conversion)
- Target: `docs/assets/meridian-demo.gif` (≤ 15 MB, ~12–15 fps)
- Narration hook: *"Every major disruption was visible in signals weeks early — Meridian connects them to your suppliers with honest calibration labels."*

See also: [`docs/assets/demo-placeholder.md`](assets/demo-placeholder.md)
