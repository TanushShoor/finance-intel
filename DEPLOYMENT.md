# Deployment Guide

Ledger is a **stateful single-instance** app. Before choosing a host, understand the three constraints that follow from its design:

1. **One backend process only.** Progress is held in an in-process store (`pipeline/progress.py`) and analysis runs as an in-process `BackgroundTask`. Multiple workers/replicas would not share that state — polling would hit the wrong worker. Run **one** uvicorn worker and scale **vertically** (bigger box), not horizontally.
2. **Persistent disk required.** State lives in a SQLite file (`DB_PATH`) and uploaded files (`UPLOAD_DIR`). These must sit on a persistent volume that survives restarts/redeploys.
3. **Long-running work.** A large 10-K takes minutes (sequential Gemini calls). The host must allow long-lived requests/background work — so **serverless/function platforms are a poor fit for the backend** (they cap execution time and don't keep an instance warm). The **frontend is a static SPA** and deploys anywhere.

> Scaling past one box (multiple replicas, autoscaling) needs Postgres instead of SQLite, object storage instead of local uploads, and a shared progress store (e.g. Redis) + a task queue (e.g. Celery/RQ). That's beyond this guide.

---

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | backend env | **Secret.** Never bake into an image; inject at runtime. |
| `GEMINI_MODEL` | backend env | Defaults to `gemini-2.5-flash`. |
| `DB_PATH` | backend env | SQLite path. Put it on the persistent volume (e.g. `/data/contracts.db`). |
| `UPLOAD_DIR` | backend env | Upload dir on the persistent volume (e.g. `/data/uploads`). |
| `VITE_API_BASE` | frontend **build** arg | Public URL the browser uses to reach the backend. Inlined by Vite at build time, so it must be set when you build the frontend. |

CORS is currently open (`allow_origins=["*"]` in `app/main.py`). For production, restrict it to your frontend origin.

---

## Option A — Docker on a single host (recommended)

This matches the app's stateful single-instance design and is the most predictable. Provided files: `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, and `backend/requirements-prod.txt` (slim — excludes test/fixture tooling and the heavy optional `docling`).

On any box with Docker (a $5–10/mo VM is plenty):

```bash
git clone https://github.com/AJ5831A/finance-intel.git && cd finance-intel

# Browser-facing backend URL. Locally that's localhost; in prod use your domain/IP.
export GEMINI_API_KEY=your-key
export VITE_API_BASE=http://localhost:8000      # e.g. https://api.your-domain.com in prod

docker compose up -d --build
```

- Frontend → `http://localhost:8080`  ·  Backend → `http://localhost:8000`
- State persists in the `ledger-data` named volume (SQLite + uploads).
- The backend image runs `uvicorn ... --workers 1` (see constraint #1).

**For a real domain with TLS:** put a reverse proxy (Caddy or nginx) in front, terminate HTTPS, route `your-domain.com` → frontend `:8080` and `api.your-domain.com` → backend `:8000`, then rebuild the frontend with `VITE_API_BASE=https://api.your-domain.com`. Caddy gives you automatic Let's Encrypt certs with a two-line `Caddyfile`.

To enable scanned-PDF OCR, uncomment `docling` in `backend/requirements-prod.txt` and rebuild (expect a much larger image).

---

## Option B — Managed split (easiest for a demo)

Frontend on a static host, backend on a container PaaS with a disk.

### Frontend → Vercel / Netlify / Cloudflare Pages
- Project root: `frontend/`
- Build command: `npm run build` · Output dir: `dist`
- Env var: `VITE_API_BASE = https://<your-backend-url>`
- (Static SPA — these platforms are ideal here.)

### Backend → Render / Railway / Fly.io
- Deploy `backend/` via its `Dockerfile`.
- **Attach a persistent disk** mounted at `/data` (constraint #2). Note: some free tiers have no persistent disk and/or spin the instance down when idle (which kills in-flight analyses) — use a tier with a disk and always-on instance for reliable demos.
- Set env: `GEMINI_API_KEY`, optionally `GEMINI_MODEL`; the Dockerfile already points `DB_PATH`/`UPLOAD_DIR` at `/data`.
- Keep it to **one instance / one worker**.
- After the backend has a URL, set `VITE_API_BASE` to it on the frontend host and redeploy the frontend.

---

## Without Docker (bare VM)

```bash
# Backend
python3.13 -m venv venv && ./venv/bin/pip install -r backend/requirements-prod.txt
cd backend
GEMINI_API_KEY=your-key DB_PATH=/var/lib/ledger/contracts.db UPLOAD_DIR=/var/lib/ledger/uploads \
  ../venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
# (run under systemd or a process manager so it restarts on boot/crash)

# Frontend (build once, serve the static dist/ with nginx or any static server)
cd frontend && VITE_API_BASE=https://api.your-domain.com npm ci && npm run build
```

---

## Post-deploy checklist

- [ ] `GET /contracts` returns `200` (and `[]` on a fresh DB).
- [ ] `GET /docs` shows the API.
- [ ] Upload a short earnings release → it reaches `done`; metrics/tone/risks/memo populate.
- [ ] `DB_PATH` + `UPLOAD_DIR` are on a volume that survives a restart (re-deploy, confirm the filing list persists).
- [ ] `GEMINI_API_KEY` is set via secrets, not committed (`.env` is git-ignored).
- [ ] CORS restricted to the frontend origin (optional but recommended).
- [ ] Backend runs exactly one worker.
