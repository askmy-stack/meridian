# Deploy Quickstart — Railway + Vercel

Portfolio demo path for Meridian (Flaw #17). Config-only — run deploy when credentials are ready.

## Architecture

| Service | Platform | Root / build |
|---------|----------|--------------|
| React frontend | **Vercel** | `frontend/` → `npm run build` → `dist/` |
| FastAPI API | **Railway** | Repo root → `Dockerfile` |
| Neo4j | **Neo4j Aura Free** or Railway plugin | Bolt URI on API service |

---

## 1. Neo4j (Aura Free)

1. Create a free instance at [neo4j.com/cloud/aura-free](https://neo4j.com/cloud/platform/aura-graph-database/).
2. Copy `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

Seed remotely (from your laptop):

```bash
export NEO4J_URI="neo4j+s://xxxx.databases.neo4j.io"
export NEO4J_USER=neo4j
export NEO4J_PASSWORD="your-password"
make seed-all
python scripts/ingest_erp_csv.py   # optional tier-2 edges
```

---

## 2. Railway — API

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Root directory: repository root (uses `railway.toml` + `Dockerfile`).
3. Set environment variables:

| Variable | Example |
|----------|---------|
| `NEO4J_URI` | `neo4j+s://…` |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | *(secret)* |
| `JWT_SECRET_KEY` | random 32+ char string |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |

4. Generate domain → note API URL, e.g. `https://meridian-api-production.up.railway.app`.
5. Verify: `curl https://YOUR-API/health`

Optional: upload trained model artifact to Railway volume or bake into image after `python scripts/train_risk_model.py`.

---

## 3. Vercel — Frontend

1. [vercel.com](https://vercel.com) → **Add New Project** → import GitHub repo.
2. **Root Directory:** `frontend`
3. Framework preset: **Vite**
4. Environment variable:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://YOUR-API.up.railway.app` |

5. Deploy. `frontend/vercel.json` handles SPA rewrites.

Verify: open Vercel URL → Command Center loads KPIs (API online badge green).

---

## 4. Post-deploy checklist

- [ ] `/health` returns `neo4j: ok`
- [ ] `/metrics/model-status` shows expected calibration banner
- [ ] Risk map loads supplier markers
- [ ] Run simulator preset (Red Sea)
- [ ] Record demo GIF per `docs/assets/demo-placeholder.md`

---

## Cost estimate

Vercel Hobby + Railway Starter + Aura Free ≈ **$0–20/mo**. See `DEPLOY.md` for AWS ECS production path.
