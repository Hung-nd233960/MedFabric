# MedFabric 3.0

A web-based DICOM CT scan annotation platform for ASPECTS (Alberta Stroke Program Early CT Score) scoring. Designed for multi-doctor annotation workflows with role-based access, draft management, and admin oversight.

---

## Features

- **ASPECTS scoring** — Bilateral (left/right) zone scoring across Basal Ganglia and Corona Radiata slices
- **Image set usability classification** — Ischemic Assessable, Non-Ischemic, Low Quality, Irrelevant, and more
- **Multi-doctor queuing** — annotators work through ordered queues of image sets; progress is tracked per doctor
- **Draft management** — manual saves and automatic drafts on every annotation change; drafts can be restored, promoted, or discarded on exit
- **Three viewing modes**
  - *Annotate* — full scoring UI with real-time validation
  - *Reader* — read-only review of submitted annotations or drafts
  - *Preview* — image viewer with patient/set metadata, no annotation UI
- **Management Board** — in-session overlay showing submission status and per-slice validity across an entire queue
- **Admin panel** — dataset management, doctor account creation, submission review, Excel export
- **DICOM rendering** — server-side window level/width rendering; adjustable per image
- **JWT authentication** — access + refresh token pair; forced password change on first login

---

## Architecture

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Zustand |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL 16 |
| Image processing | pydicom, Pillow, NumPy |
| Container | Docker + Docker Compose |

The frontend is built as a static SPA served by Nginx. The backend exposes a REST API at `/api`. All three services run together via Docker Compose.

---

## Quick Start

### Prerequisites

- Docker Engine ≥ 24
- Docker Compose v2 (`docker compose`)
- DICOM dataset files accessible on the host

### 1. Configure environment

```bash
cp backend/example.env backend/.env
```

Edit `backend/.env` and set at minimum:

```env
POSTGRES_PASSWORD=your_secure_password
JWT_SECRET_KEY=your_long_random_secret
DATASET_ROOT=/absolute/path/to/your/dicom/folders
```

Full list of environment variables is documented in the [Configuration](#configuration) section below.

### 2. Build and start

```bash
cd docker
docker compose -f docker-compose.v3.yaml up --build -d
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (dev): http://localhost:8000/api/docs

### 3. Create the admin account

On first startup, the backend creates a default admin account:

| Field | Default |
|---|---|
| Username | `admin` |
| Password | `admin` |

**Change the password immediately** after first login. The admin username can be configured via `ADMIN_USERNAMES` in `.env`.

### 4. Import a dataset

Use the provided import script to load image sets and images from CSV files into the database:

```bash
python scripts/import_dataset_v3.py \
  --dataset-name "My Dataset" \
  --image-sets   data_sets/my_dataset/image_sets.csv \
  --images       data_sets/my_dataset/images.csv \
  --env          backend/.env
```

The script connects directly to PostgreSQL using `DATABASE_URL` from the env file. Run it from the project root.

**CSV schema:**

`image_sets.csv`

| Column | Description |
|---|---|
| `image_set_uuid` | Unique identifier for the set |
| `num_images` | Number of slices |
| `folder_path` | Path relative to `DATASET_ROOT` |
| `image_format` | `DICOM`, `JPEG`, or `PNG` |
| `window_center` | Default window level |
| `window_width` | Default window width |
| `description` | Free-text description (optional) |
| `code` | Dataset index shown in the UI |

`images.csv`

| Column | Description |
|---|---|
| `file_name` | File name within the set's folder |
| `image_set_uuid` | Parent set UUID |
| `slice_index` | Display order |

`prognosis.csv` (optional) — extra per-set metadata merged into description.

---

## Configuration

All settings are read from environment variables (or `backend/.env`).

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://medfabric:changeme@localhost:5432/medfabric` | Full PostgreSQL connection string |
| `POSTGRES_PASSWORD` | `changeme` | Password used in the Compose-internal connection |
| `JWT_SECRET_KEY` | `CHANGE_ME_IN_PRODUCTION` | Secret for signing JWTs — **must be changed in production** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_HOURS` | `12` | Refresh token lifetime |
| `DATASET_ROOT` | `/data/datasets` | Host path mounted read-only into the backend container |
| `ADMIN_USERNAMES` | `["admin"]` | Usernames that receive the Admin role on account creation |
| `REGISTRATION_CODE` | *(empty)* | If set, enables self-registration with this code; leave empty to disable |
| `LOG_LEVEL` | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `EXPOSE_API_DOCS` | `true` | Whether to serve `/api/docs` and `/api/redoc` — disable in production |
| `DOCKER_VERSION` | *(empty)* | Optional build label shown in the About dialog |

---

## Project Structure

```
MedFabric/
├── backend/
│   ├── app/
│   │   ├── core/         # Config, database engine, auth utilities
│   │   ├── db/           # SQLAlchemy models, Pydantic schemas
│   │   ├── routers/      # FastAPI route handlers (one file per domain)
│   │   ├── services/     # Business logic (image rendering, export)
│   │   └── main.py       # App factory, middleware, router registration
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/   # Shared UI components and layout
│   │   ├── pages/        # Route-level page components
│   │   ├── store/        # Zustand state stores
│   │   └── lib/          # API client, type definitions, utilities
│   ├── Dockerfile
│   └── package.json
├── docker/
│   └── docker-compose.v3.yaml
├── scripts/
│   └── import_dataset_v3.py
└── data_sets/            # DICOM/image files (mounted into container)
```

---

## User Roles

| Role | Capabilities |
|---|---|
| **Doctor** | Annotate assigned datasets, save/restore drafts, review own submissions |
| **Admin** | All doctor capabilities + manage doctors, datasets, and assignments; review all submissions; export results |

Admins assign specific datasets to specific doctors. Doctors only see their assigned dataset.

---

## Annotation Workflow

1. Admin imports a dataset and assigns it to one or more doctors.
2. Doctor logs in, selects image sets from the Dashboard, and starts an annotation session.
3. For each image set the doctor:
   - Classifies **usability** (Ischemic Assessable, Non-Ischemic, Low Quality, etc.)
   - If Ischemic Assessable and not low quality: scores each ASPECTS zone (Normal / Abnormal) bilaterally for each relevant slice
   - Optionally adds notes at the set and slice level
4. Auto-drafts are saved every 2.5 seconds after the last change. A manual Save Draft is also available.
5. When complete, the doctor submits. Submissions are final and visible to admins.
6. Admins can review any doctor's submission in Reader Mode and export results to Excel.

---

## Development

### Backend (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
DATABASE_URL=postgresql+psycopg2://medfabric:changeme@localhost:5432/medfabric \
  uvicorn app.main:app --reload
```

### Frontend (local)

```bash
cd frontend
npm install
npm run dev          # starts Vite dev server at http://localhost:5173
```

The dev server proxies `/api` to `http://localhost:8000` via Vite config.

> **Note:** TypeScript errors shown by the IDE may be false positives if `node_modules` is not installed locally. The authoritative type check is the Docker build (`tsc -b && vite build`).

---

## Export

Admins can export annotation results to Excel from the Admin panel. The export includes per-set usability, bilateral ASPECTS zone scores for every doctor, and metadata (Patient ID, ICD code, description).

---

## License

Internal research tool. Not for clinical use without institutional validation.
