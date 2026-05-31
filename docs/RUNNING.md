# Running MedFabric 3

## Recommended tools

| Layer | Tool | Notes |
| --- | --- | --- |
| Python | [uv](https://docs.astral.sh/uv/) | Replaces pip + venv. `uv sync` handles everything. |
| JavaScript | [Bun](https://bun.sh) | Replaces npm. `bun install` / `bun run dev`. |
| Containers | Docker + Compose v2 | `docker compose` (no hyphen). |
| DB | PostgreSQL 16 via Docker | Never run bare postgres on the host. |

---

## Option A — Production (Docker Compose)

```bash
# 1. Set secrets in backend/.env (create if missing)
#    Required: POSTGRES_PASSWORD, JWT_SECRET_KEY
#    Generate a key: openssl rand -hex 32

# 2. Build and start all services
sudo docker compose -f docker/docker-compose.v3.yaml --env-file backend/.env up --build -d

# Frontend  → http://localhost:3000
# API docs  → http://localhost:8000/api/docs  (if EXPOSE_API_DOCS=true)
```

Tables are created automatically on first startup via `Base.metadata.create_all`.
Re-deploying after model changes requires a rebuild (`--build`).

---

## Option B — Local dev (hot reload)

Postgres runs in Docker; backend and frontend run on the host for fast iteration.

### 1. Start dev Postgres

```bash
sudo docker compose -f docker/docker-compose.dev.yaml up -d
```

This exposes postgres on `localhost:5432` only. Never run this on the production server.

### 2. Backend

```bash
cd backend

# Install deps (creates .venv automatically)
uv sync --extra dev

# First run — apply schema
uv run --env-file .env.dev alembic upgrade head

# Dev server with auto-reload
uv run --env-file .env.dev uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/api/docs
```

`.env.dev` points to `localhost:5432`. See `backend/.env.dev` for the full template.

### 3. Frontend

```bash
cd frontend
bun install       # first time only
bun run dev
# → http://localhost:5173  (proxies /api → localhost:8000)
```

---

## First-time admin setup

After first launch there are no admin accounts. Promote a user:

```bash
# Via psql inside the Docker container
sudo docker exec -it <postgres-container> psql -U medfabric -d medfabric \
  -c "UPDATE doctors SET role='Admin' WHERE username='your_username';"
```

Then reload the frontend — the Admin nav item will appear.

---

## Copying production DB to dev

```bash
# Dump prod → restore dev in one pipe
sudo docker exec <prod-postgres> pg_dump -U medfabric -Fc medfabric | \
  sudo docker exec -i <dev-postgres> pg_restore -U medfabric -d medfabric --clean --if-exists
```

Find container names with `sudo docker ps | grep postgres`.

---

## Import dataset (CSV → DB)

```bash
# Local dev
uv run --env-file backend/.env.dev python scripts/import_dataset_v3.py \
  --dataset-name "Dataset Name" \
  --image-sets   data_sets/example/image_sets.csv \
  --images       data_sets/example/images.csv \
  --env          backend/.env.dev

# Via Docker (production stack running)
sudo docker compose -f docker/docker-compose.v3.yaml exec backend \
  python /app/../scripts/import_dataset_v3.py \
    --dataset-name "Dataset Name" \
    --image-sets   /data/example/image_sets.csv \
    --images       /data/example/images.csv
```

The import is **idempotent** — re-running skips records that already exist.

---

## Monitoring (Uptime Kuma)

Uptime Kuma is included in the production Compose stack and starts automatically.

**First-time setup:**
1. Open `http://<server-ip>:3001` — you will be prompted to create an admin account (local only, no external service).
2. Add the three monitors below.

**Monitors to configure:**

| Name | Type | URL / Host | Expected | Interval |
|---|---|---|---|---|
| MedFabric API | HTTP(S) | `http://backend:8000/api/about/health` | Status 200 | 60 s |
| MedFabric Frontend | HTTP(S) | `http://frontend:80/` | Status 200 | 60 s |
| PostgreSQL | TCP Port | Host `postgres`, Port `5432` | Reachable | 60 s |

> All three targets use Docker service names — they resolve on the internal Compose network and are not reachable from outside the host. Uptime Kuma's own UI is the only thing that needs to be on port 3001.

**Alert channels** (configure under *Settings → Notifications*):

- **Email (SMTP)** — recommended for a hospital intranet; point at the institution's mail relay.
- **Telegram / Slack / Discord** — optional for personal alerts during development.

**Interpreting the health endpoint:**

```
GET /api/about/health
→ 200 {"status": "ok", "version": "3.x.x"}       # app + DB both reachable
→ 503 {"status": "degraded", "detail": "..."}     # DB unreachable
```

A 503 from this endpoint means the backend started but cannot reach PostgreSQL — check `sudo docker compose logs postgres`.

---

## Bug reports

Reports are written to `/data/bug_reports.jsonl` inside the backend container.

```bash
# Read all reports (pretty-printed)
sudo docker exec <backend-container> \
  python3 -c "import sys,json; [print(json.dumps(json.loads(l),indent=2)) for l in open('/data/bug_reports.jsonl')]"
```
