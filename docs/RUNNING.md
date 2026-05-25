# Running MedFabric 3.0

## Option A — Docker Compose (recommended)

```bash
# 1. Copy and fill in secrets
cp backend/.env.example backend/.env
# Edit backend/.env — at minimum set:
#   JWT_SECRET_KEY=<openssl rand -hex 32>
#   POSTGRES_PASSWORD=<choose a password>
#   DATASET_ROOT=<absolute path to your DICOM folder, or leave as ../data_sets>

# 2. Build and start all three services (postgres + backend + frontend)
cd docker
docker compose -f docker-compose.v3.yaml up --build

# Frontend → http://localhost:3000
# Backend API docs → http://localhost:8000/api/docs
```

The backend automatically runs `alembic upgrade head` on startup, so the DB schema
is created on first launch.

---

## Option B — Local dev (faster iteration)

### Prerequisites

- Python ≥ 3.11
- Node.js ≥ 20
- A running PostgreSQL instance (or spin one up with Docker):

```bash
docker run -d --name medfabric-pg \
  -e POSTGRES_DB=medfabric \
  -e POSTGRES_USER=medfabric \
  -e POSTGRES_PASSWORD=changeme \
  -p 5432:5432 \
  postgres:16-alpine
```

### Backend

```bash
cd backend

# Install dependencies (uv or pip)
pip install -e .          # or: uv sync

# Configure
cp .env.example .env
# Edit .env: DATABASE_URL, JWT_SECRET_KEY, DATASET_ROOT

# Run migrations
alembic upgrade head

# Start dev server (auto-reload)
uvicorn app.main:app --reload
# → http://localhost:8000/api/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173  (proxies /api → localhost:8000)
```

---

## Import existing dataset (CSV → v3 DB)

The script `scripts/import_dataset_v3.py` is a drop-in replacement for the old
`importer.py`. It reads the same three CSVs and writes directly to the new schema.

```bash
# From project root (local dev):
python scripts/import_dataset_v3.py \
  --dataset-name "E Hospital Dataset" \
  --dataset-desc  "Filtered E Hospital dataset" \
  --image-sets    data_sets/e_hospital/image_sets.csv \
  --images        data_sets/e_hospital/images.csv \
  --prognosis     data_sets/e_hospital/prognosis.csv \
  --env           backend/.env

# Via Docker (after the stack is up):
docker compose -f docker/docker-compose.v3.yaml exec backend \
  python /app/../scripts/import_dataset_v3.py \
    --dataset-name "E Hospital Dataset" \
    --image-sets   /data/e_hospital/image_sets.csv \
    --images       /data/e_hospital/images.csv \
    --env          /app/../.env
```

The import is **idempotent** — re-running it skips records that already exist.

---

## First-time admin setup

After the DB is initialized there are no admin accounts. Promote a user via SQL
or the backend shell:

```bash
# Option 1 — psql
psql $DATABASE_URL -c "UPDATE doctors SET role='Admin' WHERE username='your_username';"

# Option 2 — Python shell (local dev)
cd backend
python - <<'EOF'
from app.core.database import SessionLocal
from app.db.models import Doctors, DoctorRole
db = SessionLocal()
d = db.query(Doctors).filter_by(username="your_username").first()
d.role = DoctorRole.Admin
db.commit()
print("Done")
db.close()
EOF
```

Then reload the frontend — the Admin nav item will appear.

---

## Differences from v2 (Streamlit)

| v2 | v3 |
| --- | --- |
| `medfabric.db.orm_model` | `backend/app/db/models.py` |
| `medfabric.db.engine.get_session_factory_bare()` | `app.core.database.SessionLocal` |
| `medfabric.api.data_sets.add_data_set` | `app.services.datasets.create_dataset` |
| `medfabric.api.patients.add_patient` | `app.services.patients.create_patient` |
| `medfabric.api.image_set_input.add_image_set` | `app.services.image_sets.register_image_set` |
| `medfabric.api.image_input.add_image` | direct ORM `Image(...)` insert |
| `Session` table | renamed to `LoginSession`, new `AnnotationSession` added |
| `ImageSetUsability` (3 values) | +`Irrelevant` |
| Port 8501 (Streamlit) | Port 8000 (backend) + 3000 (frontend) |
