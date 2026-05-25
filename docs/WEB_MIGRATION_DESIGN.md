# MedFabric Web Stack Migration — Design Document

> **Status:** Design finalised — ready to build  
> **Scope:** Full migration from Streamlit monolith to FastAPI + React  
> **Author:** System analysis session, May 2026

---

## Table of Contents

1. [System Purpose](#1-system-purpose)
2. [Current Architecture](#2-current-architecture)
3. [Target Architecture](#3-target-architecture)
4. [Domain Model](#4-domain-model)
5. [Complete Annotation Workflow](#5-complete-annotation-workflow)
6. [Schema Changes](#6-schema-changes)
7. [API Design](#7-api-design)
8. [Frontend Design](#8-frontend-design)
9. [Admin Panel](#9-admin-panel)
10. [Code Reuse Strategy](#10-code-reuse-strategy)
11. [Data Migration](#11-data-migration)
12. [Finalised Scope Additions](#12-finalised-scope-additions)
13. [Final Scope Summary](#13-final-scope-summary)

---

## 1. System Purpose

MedFabric is an **ASPECTS (Alberta Stroke Program Early CT Score) annotation tool** for CT brain scans.

**Primary goal:** Collect high-quality bilateral region scores from radiologists and residents, to be used as ground truth for AI training on ischemic stroke detection.

**Secondary goal (future):** Potential integration with hospital PACS systems.

**Scale:** Small — one imaging medicine department, ~10–50 users (doctors + residents). Not public-facing.

**Deployment:** Hospital intranet, single server, Docker. No cloud, no CDN, no external services.

**Key clinical note:** The system does NOT compute a final ASPECTS score. Aggregation logic across slices (which slice's score is "canonical" — min? max?) is an unresolved clinical debate. The app is a **pure data collection instrument**. Downstream AI pipelines handle aggregation.

---

## 2. Current Architecture

```
┌─────────────────────────────────────────┐
│           Streamlit Monolith            │
│                                         │
│  pages/login.py                         │
│  pages/register.py                      │
│  pages/dashboard.py    ─── medfabric/   │
│  pages/label.py             api/*.py    │
│  pages/guide.py             db/*.py     │
│                                         │
│  st.session_state = application state   │
└─────────────────────┬───────────────────┘
                      │ SQLAlchemy
                      ▼
              SQLite / PostgreSQL
                      │
              Local filesystem
              (DICOM / JPEG files)
```

**Strengths of the current design:**
- `medfabric/api/` is already a clean, separated business logic layer
- ORM models are PostgreSQL-ready (custom `GUID` type handles both dialects)
- Pydantic v2 models are already FastAPI-compatible
- Error hierarchy is clean and domain-separated
- Test suite covers all API functions with in-memory SQLite

**Limitations being replaced:**
- Streamlit's rerun model makes complex UI state painful (hence the EventFlags/dispatcher workaround)
- Single process — no real client/server separation
- `@st.cache_resource` on the DB engine is Streamlit-specific
- Session state is in-memory per Streamlit server process — no horizontal scaling possible
- Image rendering is coupled to UI reruns (windowing change = full page rerun)

---

## 3. Target Architecture

```
┌─────────────────────┐         ┌──────────────────────────┐
│   React (TypeScript) │  JWT    │      FastAPI (Python)     │
│   Vite / SPA         │◄──────►│                          │
│                      │  REST  │  /auth/*                  │
│  - Login / Register  │        │  /datasets/*              │
│  - Dashboard         │        │  /patients/*              │
│  - Label page        │        │  /image-sets/*            │
│  - Admin panel       │        │  /images/{uuid}/render    │
│                      │        │  /evaluations/*           │
│  Zustand (state)     │        │  /admin/*                 │
│  Axios (HTTP)        │        │  /export/*                │
└─────────────────────┘         └────────────┬─────────────┘
                                             │ SQLAlchemy
                                             ▼
                                        PostgreSQL
                                             │
                                     Local filesystem
                                     (DICOM / JPEG)
```

**Technology decisions:**

| Concern | Decision | Reason |
|---|---|---|
| Backend | FastAPI (Python) | Reuses existing api/ layer; async-ready; auto OpenAPI docs |
| Frontend | React + TypeScript (Vite) | Full control over complex label UI; type safety |
| Auth | JWT tokens | Standard for SPA + REST API; stateless backend |
| Database | PostgreSQL | Already supported in ORM; production-grade |
| Image serving | `GET /images/{uuid}/render?wl=X&ww=Y` → PNG | Server-side windowing via existing pydicom code; React uses `<img src>` |
| Image storage | Local filesystem (unchanged) | Hospital intranet constraint; files pre-exist on server |
| Export | CSV / Excel download | Admin downloads for AI pipeline; pandas already in stack |
| Deployment | Docker Compose (backend + frontend + postgres) | Hospital intranet, single server |

---

## 4. Domain Model

### 4.1 Entity Relationship (new schema)

```
DataSet ──────────────────────────────────────┐
  dataset_uuid (PK)                           │
  name                                        │
  description                                 │
       │                                      │
       │ 1:N                                  │ 1:N
       ▼                                      ▼
  Patient                               DoctorDatasetAssignment
    patient_uuid (PK)                     doctor_uuid (FK)
    patient_id                            dataset_uuid (FK)
    dataset_uuid (FK)                     assigned_at
    age, gender, category                 [UNIQUE(doctor_uuid, dataset_uuid)]
       │
       │ 1:N
       ▼
  ImageSet
    uuid (PK)
    index (autoincrement)
    image_set_name
    patient_uuid (FK)
    dataset_uuid (FK)
    image_format (DICOM/JPEG/PNG)
    num_images
    folder_path
    image_window_level, image_window_width
    icd_code, description
       │
       │ 1:N
       ▼
  Image
    uuid (PK)
    image_name
    image_set_uuid (FK)
    slice_index


Doctors
  uuid (PK)
  username (UNIQUE)
  email (UNIQUE)
  password_hash
  role
  is_active          ← NEW
       │
       │ 1:N
       ▼
  LoginSession
    session_uuid (PK)
    doctor_uuid (FK)
    login_time
    is_active
       │
       │ 1:N
       ▼
  AnnotationSession         ← NEW CONCEPT
    id (PK)
    doctor_uuid (FK → Doctors)
    image_set_uuid (FK → ImageSet)
    login_session_uuid (FK → LoginSession)
    started_at
    submitted_at            ← null until submitted
    [UNIQUE(doctor_uuid, image_set_uuid, login_session_uuid)]
       │
       ├── 1:1
       │    ▼
       │  ImageSetEvaluation
       │    id (PK)
       │    annotation_session_id (FK → AnnotationSession)  ← replaces doctor/session FKs
       │    usability (IschemicAssessable | HemorrhagicPresent | Anomaly | Irrelevant)
       │    ischemic_low_quality (bool)
       │    notes                ← NEW
       │
       └── 1:N
            ▼
          ImageEvaluation
            id (PK)
            annotation_session_id (FK → AnnotationSession)  ← replaces doctor/session FKs
            image_uuid (FK → Image)
            region (None | BasalGanglia | CoronaRadiata)
            c_left_score,  c_right_score
            ic_left_score, ic_right_score
            l_left_score,  l_right_score
            i_left_score,  i_right_score
            m1_left_score, m1_right_score
            m2_left_score, m2_right_score
            m3_left_score, m3_right_score
            m4_left_score, m4_right_score
            m5_left_score, m5_right_score
            m6_left_score, m6_right_score
            notes
```

### 4.2 Key design decisions in the schema

**Why `AnnotationSession` exists:**  
The current schema uses `session_uuid` (a login session) as the grouping key for all evaluations. This conflates two different concepts — logging in and annotating. `AnnotationSession` separates them. It is the single FK anchor that both `ImageSetEvaluation` and `ImageEvaluation` reference, making the link between set-level and image-level annotations explicit without requiring a cross-table FK.

**Why `ImageSetEvaluation` is always written:**  
Previously, when a set was `IschemicAssessable + not low quality`, only `ImageEvaluation` records were written (no set-level record). This made "has this doctor evaluated this set?" require checking two tables. Now `ImageSetEvaluation` is always written first, giving a single source of truth for set-level state.

**`Not_Applicable` is a DB convention, not a user concept:**  
When a doctor labels a slice as `BasalGanglia`, corona zone scores (m4–m6 bilateral) are automatically set to `Not_Applicable` on submission. When `CoronaRadiata`, basal zone scores (c, ic, l, i, m1–m3 bilateral) are set to `Not_Applicable`. Doctors never see or choose this value — they only see Damaged / Not Damaged / Not Visible.

**Bilateral scoring is intentional:**  
Standard ASPECTS does not distinguish left from right. This system does, at the Head Doctor's clinical instruction, to capture richer training data for the AI pipeline.

### 4.3 Enumerations

```python
class ImageSetUsability(Enum):
    IschemicAssessable  = "IschemicAssessable"   # Ischemic OR healthy (ASPECTS applicable)
    HemorrhagicPresent  = "HemorrhagicPresent"   # Hemorrhagic stroke
    Anomaly             = "Anomaly"              # Tumor, unrelated pathology
    Irrelevant          = "Irrelevant"           # NEW: wrong organ, corrupted, unknown

class Region(Enum):
    None_         = "None"           # Unclassified (valid — doctor chose to skip)
    BasalGanglia  = "BasalGanglia"   # Scores: c, ic, l, i, m1, m2, m3
    CoronaRadiata = "CoronaRadiata"  # Scores: m4, m5, m6

class RegionScore(Enum):
    Affected          = "Affected"           # "Damaged" in UI
    Not_Affected      = "Not_Affected"       # "Not Damaged" in UI
    Not_In_This_Slice = "Not_In_This_Slice"  # "Not Visible" in UI
    Not_Applicable    = "Not_Applicable"     # DB only — never shown to doctors
```

---

## 5. Complete Annotation Workflow

### 5.1 Doctor flow (end-to-end)

```
1. Doctor registers / logs in
        ↓
   LoginSession created

2. Dashboard loads
   - Shows image sets in their ASSIGNED dataset only
   - Per-image-set: evaluated by this doctor? (✓/✗)
   - Global progress bar: unique image sets with ≥1 doctor evaluation / total

3. Doctor selects image sets to annotate → AnnotationSession(s) created (started_at set)

4. Label page opens — for each selected image set:

   ┌─ SET LEVEL (always first) ────────────────────────────────────────────┐
   │  Doctor chooses usability:                                            │
   │    IschemicAssessable | HemorrhagicPresent | Anomaly | Irrelevant     │
   │  Doctor optionally ticks: Low Quality                                  │
   │                                                                       │
   │  GATE: If (NOT IschemicAssessable) OR (Low Quality = true)            │
   │    → ASPECTS scoring DISABLED                                         │
   │    → Image set is immediately valid for submission                    │
   │                                                                       │
   │  GATE: If (IschemicAssessable AND Low Quality = false)                │
   │    → ASPECTS scoring ENABLED → proceed to image level                │
   └───────────────────────────────────────────────────────────────────────┘

   ┌─ IMAGE LEVEL (only when ASPECTS enabled) ─────────────────────────────┐
   │  Each slice starts as Region = None                                   │
   │                                                                       │
   │  Doctor classifies slice:                                             │
   │    None          → skip (valid, no scores needed)                    │
   │    BasalGanglia  → must fill: c, ic, l, i, m1, m2, m3 (bilateral)   │
   │    CoronaRadiata → must fill: m4, m5, m6 (bilateral)                 │
   │                                                                       │
   │  Each zone score (3 options shown to doctor):                         │
   │    Damaged      → DB: Affected                                        │
   │    Not Damaged  → DB: Not_Affected                                    │
   │    Not Visible  → DB: Not_In_This_Slice                               │
   │    (empty)      → invalid, doctor must fill                           │
   │                                                                       │
   │  IMAGE VALID if:                                                      │
   │    Region = None  OR                                                  │
   │    Region ≠ None AND all relevant zones are filled (not empty)        │
   │                                                                       │
   │  SET VALID if:                                                        │
   │    ≥ 1 BasalGanglia slice  AND                                        │
   │    ≥ 1 CoronaRadiata slice AND                                        │
   │    All classified images are individually Valid                       │
   │                                                                       │
   │  WARNING (non-blocking): if slice indices are not consecutive         │
   │    (a gap may mean a clinically relevant slice was accidentally        │
   │     classified as None)                                               │
   └───────────────────────────────────────────────────────────────────────┘

5. Doctor clicks Submit (only available when all selected sets are Valid)

   Submission writes atomically:
     → ImageSetEvaluation (always)
     → ImageEvaluation × N (only if IschemicAssessable + not low quality)
     → AnnotationSession.submitted_at = now()

6. Doctor returns to dashboard — progress updated
```

### 5.2 Re-annotation

A doctor can annotate the same image set again in a new login session. All versions are kept — each is bound to a distinct `AnnotationSession`. The dashboard shows "evaluated by you" if any `AnnotationSession` exists for that doctor + image set, regardless of count.

There is no in-app UI for viewing or diffing past annotation versions. That is handled offline (via CSV export + pandas).

---

## 6. Schema Changes

| Change | Type | Reason |
|---|---|---|
| Add `Irrelevant` to `ImageSetUsability` | Enum value | Covers wrong organ, corrupted, unknown scans |
| Add `AnnotationSession` table | New table | Clean separation of login vs annotation; anchor for evaluation tables |
| Add `notes` to `ImageSetEvaluation` | New column | Set-level notes parity with image-level notes |
| Add `annotation_session_id` FK to `ImageSetEvaluation` | New FK, replaces `doctor_uuid`/`image_set_uuid`/`session_uuid` | Cleaner model; single join anchor |
| Add `annotation_session_id` FK to `ImageEvaluation` | New FK, replaces `doctor_uuid`/`session_uuid` | Same |
| Add `DoctorDatasetAssignment` table | New table | Admin delegates datasets to doctors |
| Add `is_active` to `Doctors` | New column | Admin can deactivate accounts |
| `conflicted` on `ImageSet` | Ignore (keep column, never write to it) | Conflict detection is out of scope |
| Folder structures: two patterns | Logic change | `dataset/patient_id/scan_name/*.dcm` OR `dataset/patient_id/*.dcm` |

### 6.1 Migration script requirements (SQLite → PostgreSQL)

For existing `IschemicAssessable + good quality` annotations that currently have no `ImageSetEvaluation` record:

```
For each DISTINCT (doctor_uuid, session_uuid, image_set_uuid) 
  found by joining image_evaluations → images → image_sets:
    1. Create AnnotationSession(doctor_uuid, image_set_uuid, login_session_uuid=session_uuid)
    2. Create ImageSetEvaluation(usability=IschemicAssessable, low_quality=False, notes=null)
    3. Backfill ImageEvaluation.annotation_session_id

For existing ImageSetEvaluation records (non-ischemic / low quality):
    1. Create AnnotationSession from (doctor_uuid, session_uuid, image_set_uuid)
    2. Repoint ImageSetEvaluation.annotation_session_id
```

---

## 7. API Design

### 7.1 Route structure

```
POST   /auth/register
POST   /auth/login              → returns JWT
POST   /auth/logout

GET    /datasets/               → doctor sees only assigned datasets
GET    /datasets/{uuid}/progress → own progress + global unique progress

GET    /image-sets/             ?dataset_uuid=...
GET    /image-sets/{uuid}

GET    /images/{uuid}/render    ?wl=35&ww=100  → PNG (StreamingResponse)

POST   /annotation-sessions/           → start annotation (creates AnnotationSession)
POST   /annotation-sessions/{id}/submit → write evaluations, set submitted_at
GET    /annotation-sessions/           ?image_set_uuid=...&doctor_uuid=...

GET    /evaluations/image-sets/{annotation_session_id}
GET    /evaluations/images/    ?annotation_session_id=...

# Admin routes (role-gated)
GET    /admin/doctors/
POST   /admin/doctors/
PATCH  /admin/doctors/{uuid}           → deactivate, change role
GET    /admin/doctors/{uuid}/activity  → login history, annotation progress

POST   /admin/datasets/
POST   /admin/patients/
POST   /admin/image-sets/             → body: folder_path, folder_structure (nested|flat)
GET    /admin/image-sets/{uuid}/scan-folder → preview what would be registered

GET    /export/evaluations    ?dataset_uuid=...  → CSV/Excel download
```

### 7.2 JWT payload

```json
{
  "sub": "doctor_uuid",
  "username": "dr_smith",
  "role": "doctor | admin",
  "exp": 1234567890
}
```

Admin routes check `role == "admin"` via FastAPI dependency.

### 7.3 Image rendering endpoint

Reuses existing `dicom_processing.py` and `jpg_processing.py` directly:

```python
@router.get("/images/{uuid}/render")
async def render_image(uuid: UUID, wl: int = 35, ww: int = 100):
    image = get_image(db, uuid)
    image_set = get_image_set(db, image.image_set_uuid)
    file_path = Path(DATASET_ROOT) / image_set.folder_path / image.image_name

    if image_set.image_format == ImageFormat.DICOM:
        pil_image = dicom_image(file_path, center=wl, width=ww)
    else:
        pil_image = jpg_image(file_path)

    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
```

React displays: `<img src={`/api/images/${uuid}/render?wl=${wl}&ww=${ww}`} />`  
Windowing slider debounces ~300ms before updating the URL param.

---

## 8. Frontend Design

### 8.1 Pages

| Page | Key behaviour |
|---|---|
| `/login` | JWT stored in memory (not localStorage for security) |
| `/register` | Self-registration; account active immediately |
| `/dashboard` | Shows assigned dataset; own progress + global unique progress; multi-select image sets |
| `/label` | The complex page — see below |
| `/admin/*` | Admin-only; redirects if `role != admin` |

### 8.2 Label page state (Zustand store)

```typescript
interface AnnotationStore {
  // Session
  annotationSessionIds: Record<string, string>   // imageSetUuid → annotationSessionId
  currentSetIndex: number
  currentImageIndex: number

  // Per image set
  imageSets: ImageSetEvaluationSession[]

  // Actions
  setUsability(imageSetUuid, usability): void
  setLowQuality(imageSetUuid, bool): void
  setSetNotes(imageSetUuid, notes): void
  setRegion(imageSetUuid, imageUuid, region): void
  setZoneScore(imageSetUuid, imageUuid, zone, score): void
  setImageNotes(imageSetUuid, imageUuid, notes): void

  // Derived (computed)
  isImageValid(imageSetUuid, imageUuid): boolean
  isSetValid(imageSetUuid): boolean
  allSetsValid(): boolean
  hasNonConsecutiveSlices(imageSetUuid): boolean   // warning only
}
```

### 8.3 Layout (label page)

```
┌──────────────┬──────────────────┬────────────────────────┐
│  Col 1       │  Col 2           │  Col 3                 │
│              │                  │                        │
│  [Back] [Out]│  Set-level panel │  Set nav (1 of N)      │
│              │  ─────────────── │  ──────────────────── │
│  <img>       │  Usability       │  Slice status table    │
│  (DICOM PNG) │  [Isch][Hem]     │  (region + valid?)     │
│              │  [Ano][Irrel]    │                        │
│  [◄] [►]     │                  │  ─────────────────── │
│  Slider      │  ☐ Low Quality   │  All sets status       │
│              │                  │                        │
│              │  ─────────────── │  [Submit All] (gated)  │
│              │  ASPECTS scoring │                        │
│              │  (disabled if    │                        │
│              │   gated out)     │                        │
│              │                  │                        │
│              │  Region:         │                        │
│              │  [None][Bas][Cor]│                        │
│              │                  │                        │
│              │  Scores:         │                        │
│              │  c  [D][ND][NV]  │                        │
│              │  ic [D][ND][NV]  │                        │
│              │  ... etc         │                        │
│              │                  │                        │
│              │  Notes (image)   │                        │
│              │  Notes (set)     │                        │
└──────────────┴──────────────────┴────────────────────────┘
```

Windowing controls (DICOM only) sit above the image — window level and width number inputs, debounced 300ms.

---

## 9. Admin Panel

### 9.1 Doctor management

- List all doctors with: username, email, role, is_active, last login time
- Create doctor account
- Deactivate / reactivate doctor
- View per-doctor detail:
  - Login history (LoginSession records)
  - Per-dataset progress: X image sets annotated out of Y assigned
  - Annotation timeline (submitted_at timestamps)

### 9.2 Dataset management

- List datasets and their assigned doctors
- Create dataset
- Assign dataset to doctor(s)

### 9.3 Image set registration (admin only)

Admin provides a server-side folder path. Two folder structures supported:

| Mode | Structure |
|---|---|
| `nested` | `dataset_root/patient_id/scan_name/*.dcm` |
| `flat` | `dataset_root/patient_id/*.dcm` |

Admin flow:
1. Enter dataset root path + choose mode
2. System previews: what patients and image sets would be registered (dry run)
3. Admin confirms → system walks the folder, registers patients, image sets, and images
4. DICOM metadata (window level/width from DICOM tags) auto-filled where available

### 9.4 Export

`GET /export/evaluations?dataset_uuid=X` returns Excel with sheets:

| Sheet | Contents |
|---|---|
| `annotation_sessions` | doctor, image_set, started_at, submitted_at |
| `set_evaluations` | usability, low_quality, notes per annotation session |
| `image_evaluations` | all 20 bilateral zone scores per image per annotation session |
| `doctors` | username, role, is_active |

---

## 10. Code Reuse Strategy

### Reuse directly (move, minor edits)

| Current path | Reuse as | Changes needed |
|---|---|---|
| `medfabric/db/orm_model.py` | Backend ORM | Add `Irrelevant` enum, `AnnotationSession`, `DoctorDatasetAssignment`, `is_active` on Doctors, update FKs |
| `medfabric/db/pydantic_model.py` | FastAPI request/response schemas | Add new models; update existing for new FK fields |
| `medfabric/api/credentials.py` | Auth logic | Remove Streamlit imports (none present) — use as-is |
| `medfabric/api/data_sets.py` | Dataset CRUD | Use as-is |
| `medfabric/api/patients.py` | Patient CRUD | Use as-is |
| `medfabric/api/image_set_input.py` | Image set CRUD | Use as-is |
| `medfabric/api/image_input.py` | Image CRUD | Use as-is |
| `medfabric/api/errors.py` | Exception hierarchy | Add HTTP status mapping for FastAPI exception handlers |
| `medfabric/pages/label_helper/image_loader/dicom_processing.py` | Image render endpoint | Use as-is |
| `medfabric/pages/label_helper/image_loader/jpg_processing.py` | Image render endpoint | Use as-is |
| `medfabric/pages/label_helper/submit_results.py` | Submission logic | Update for new schema (AnnotationSession, always write ImageSetEvaluation) |
| `tests/` | Backend tests | Adapt fixtures for new schema; add FastAPI route tests |

### Discard (Streamlit-specific)

- `medfabric/db/engine.py` — `@st.cache_resource` is Streamlit-only; replace with standard FastAPI DB dependency
- `medfabric/pages/` — all pages replaced by React
- `medfabric/pages/label_helper/state_management.py` — EventFlags/dispatcher replaced by Zustand
- `medfabric/pages/dashboard_helper/` — replaced by React + API calls
- `medfabric/main.py` — replaced by FastAPI `main.py`

---

## 11. Data Migration

Migration is required because **real annotation data exists in SQLite** and must be preserved in PostgreSQL.

### 11.1 Migration steps

```
1. Export SQLite data to JSON or CSV (all tables)

2. In PostgreSQL: run Alembic migrations to create new schema

3. Migrate core tables (no schema change):
   datasets, patients, doctors, image_sets, images
   → direct insert

4. Migrate sessions → login_sessions (rename only)

5. Synthesize AnnotationSession records:
   For each DISTINCT (doctor_uuid, session_uuid, image_set_uuid) 
   found in image_evaluations JOIN images JOIN image_sets:
     CREATE AnnotationSession(
       doctor_uuid = ...,
       image_set_uuid = ...,
       login_session_uuid = session_uuid,
       started_at = login_session.login_time,  -- best approximation
       submitted_at = login_session.login_time  -- submitted within that session
     )

6. For existing ImageSetEvaluation records (non-ischemic / low quality):
   Same synthesis — create AnnotationSession, repoint FK

7. For existing ImageEvaluation records:
   Backfill annotation_session_id from the synthesized AnnotationSession

8. Verify: row counts match; no orphaned FKs
```

### 11.2 Folder path concern

Image files currently reference paths stored in `image_sets.folder_path`. These are relative to a `dataset` root defined in `config.toml`. The migration must ensure the new server's `DATASET_ROOT` env var aligns with where the files actually live.

---

## 12. Finalised Scope Additions

### 12.1 Auto-detect DICOM window parameters — IN SCOPE

When registering an image set, the backend reads `WindowCenter` and `WindowWidth` tags from the first valid DICOM file in the folder and uses them as defaults for `image_window_level` / `image_window_width`. Admin can override before confirming registration.

### 12.2 Soft-delete for image sets — IN SCOPE

Add `is_active: bool = True` to `ImageSet`. Admin can deactivate a set (e.g., wrong files, corrupt DICOMs). Deactivated sets are hidden from the doctor dashboard and cannot be selected for annotation. All existing evaluation data referencing a deactivated set is preserved.

### 12.3 Doctor activity stats — OUT OF SCOPE

The dashboard progress bar and ✓/✗ per row already convey per-doctor progress. A dedicated "My Activity" history page (for educational / supervisory purposes) is deferred — it belongs to a future training/mentorship feature.

### 12.4 The `role` field — IN SCOPE (necessary for admin routes)

`Doctors.role` currently exists but is never checked. The web version requires at minimum two values: `doctor` and `admin`. Admin-gated FastAPI routes check `role == "admin"` via a dependency. Residents and senior doctors are both `doctor` for now.

### 12.5 Notes in export — IN SCOPE

Both image-level notes (`ImageEvaluation.notes`) and set-level notes (`ImageSetEvaluation.notes`) are included in the CSV/Excel export. Notes carry clinically significant observations that the AI pipeline must have access to.

### 12.6 Scrollable dashboard with configurable row count — IN SCOPE

No pagination buttons. The dashboard table has a "rows per page" selector (25 / 50 / 100 / All). Client-side display only — the server returns all assigned image sets for the dataset.

### 12.7 DICOM tag extraction to DB — OUT OF SCOPE

AI team works directly with raw DICOM files + the database. Window params (12.1) are the only DICOM-derived data stored at registration time.

### 12.8 JWT expiry — IN SCOPE (two-token pattern)

- **Access token:** short-lived (2 hours), sent as `Authorization: Bearer` header
- **Refresh token:** shift-length (12 hours), stored in an httpOnly cookie
- Axios interceptor silently refreshes the access token on 401 — doctors never see a mid-annotation login prompt
- `LoginSession.is_active` set to false on explicit logout or refresh token expiry
- Endpoint: `POST /auth/refresh` — validates refresh cookie, issues new access token

### 12.9 Admin audit log — IN SCOPE

```sql
admin_audit_log
  id           PK autoincrement
  admin_uuid   FK → doctors
  action       TEXT   -- "register_dataset" | "deactivate_doctor" | "register_image_set" | "export_download"
  target_type  TEXT   -- "dataset" | "doctor" | "image_set" | "export"
  target_uuid  TEXT   -- UUID of affected entity (nullable for exports)
  timestamp    DATETIME
```

Written automatically alongside each admin action. No extra UI needed — queryable from DB directly.

### 12.10 Image validity status box — IN SCOPE (translates existing behaviour)

Already implemented in the Streamlit label page (`render_valid_message`, `render_score_box_mode`). The React equivalent is a live status component derived from Zustand store state — no backend call:

| Condition | Message | Style |
| --- | --- | --- |
| Region = `None` | "This image does not belong to a region. Make sure it is not in the ASPECTS zone — or annotate it." | Info / neutral |
| Region = Basal or Corona, all relevant zones filled | "This image is valid." | Success / green |
| Region = Basal or Corona, one or more zones empty | "This image is invalid — please fill all score fields." | Warning / amber |

Non-consecutive slice warning (existing behaviour) is also preserved as a non-blocking amber banner.

---

## 13. Final Scope Summary

### In scope

| Area | What is built |
| --- | --- |
| Auth | JWT access + refresh tokens, self-registration, admin manages roles and deactivation |
| Dashboard | Assigned dataset only, own ✓/✗ progress + global unique-set progress, scrollable with row count selector |
| Label page | Set-level gating, ASPECTS scoring, Damaged / Not Damaged / Not Visible, image validity status box, consecutive-slice warning, set validity gate on submit, per-image notes, per-set notes |
| Image serving | `GET /images/{uuid}/render?wl=X&ww=Y` → PNG, DICOM windowing server-side, debounced slider |
| Admin: doctors | Create, deactivate, view login history, view annotation progress per dataset |
| Admin: datasets | Create, assign to doctors |
| Admin: image sets | Register by folder path (nested or flat structure), auto-detect DICOM window params, soft-delete |
| Admin: export | CSV / Excel with all evaluations + notes |
| Admin: audit log | Immutable log of all admin actions |
| Schema | `AnnotationSession` table, `Irrelevant` enum value, `DoctorDatasetAssignment` table, `is_active` on Doctors and ImageSet, `notes` on `ImageSetEvaluation`, `annotation_session_id` FK on both evaluation tables |
| Data migration | SQLite → PostgreSQL with full preservation of existing annotations |

### Out of scope (deferred)

| Feature | Reason |
| --- | --- |
| Doctor "My Activity" history page | Redundant with dashboard; educational use case is a future feature |
| DICOM tag extraction to DB | AI team uses raw DICOM directly; no need to inflate schema |
| Inter-rater conflict detection UI | Analysis done offline; input space too complex for in-app handling |
| PACS integration | Future milestone |
| Resident vs senior doctor role distinction | Future milestone |
| ASPECTS aggregate score computation | Clinically unresolved; AI pipeline decides |

---

*End of design document.*
