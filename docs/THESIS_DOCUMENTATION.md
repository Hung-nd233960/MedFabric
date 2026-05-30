# MedFabric 3.0 — Thesis Documentation

> **Project:** MedFabric 3.0 — DICOM CT Scan Annotation Platform for ASPECTS Scoring  
> **Stack:** FastAPI · React 18 · PostgreSQL 16 · Docker  
> **Date:** May 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Use Cases](#2-use-cases)
3. [Database Schema](#3-database-schema)
4. [API Specification](#4-api-specification)
5. [Frontend Pages & Routes](#5-frontend-pages--routes)
6. [Non-Functional Properties](#6-non-functional-properties)

---

## 1. System Overview

MedFabric is a **web-based DICOM annotation platform** for collecting bilateral ASPECTS (Alberta Stroke Program Early CT Score) scores from radiologists and residents. Collected scores serve as ground-truth labels for downstream ischemic-stroke AI training.

**Key design decisions:**

| Decision | Rationale |
|---|---|
| Server-side DICOM rendering | Browser cannot natively decode DICOM; avoids shipping large client-side libraries |
| No final ASPECTS score computed | Aggregation across slices is an unresolved clinical question — the system is a pure data collection instrument |
| Bilateral scoring (left + right per zone) | All 10 ASPECTS zones are recorded independently for each hemisphere |
| Draft + auto-draft system | Prevents annotation loss on accidental navigation; manual save takes priority over auto-save |
| Role-based access (Doctor / Admin) | Doctors can only see and annotate their own assigned dataset; Admins manage everything |
| JWT access + refresh token pair | Short-lived access token (header) + long-lived refresh token (HttpOnly cookie) |

---

## 2. Use Cases

### 2.1 Actor Definitions

| Actor | Description |
|---|---|
| **Doctor** | Radiologist or resident assigned to annotate a dataset |
| **Admin** | System administrator; manages accounts, datasets, and monitors progress |

---

### 2.2 Doctor Use Cases

#### UC-D01: Login
- **Actor:** Doctor  
- **Trigger:** Navigate to `/login`  
- **Flow:** Enter username + password → receive access token + refresh token cookie → redirect to Dashboard  
- **Alternate:** Account inactive → 403 Forbidden

#### UC-D02: First-Login Account Setup
- **Actor:** Doctor  
- **Trigger:** `must_change_password` or `must_set_name` flags set by admin  
- **Flow:** After login, system redirects to Change Password page → doctor sets full name and/or new password → flags cleared

#### UC-D03: View Dashboard
- **Actor:** Doctor  
- **Trigger:** Navigate to `/`  
- **Flow:** System loads assigned dataset + image set queue with per-image-set status (unannotated / draft / submitted) and overall progress count

#### UC-D04: View DICOM Image Set
- **Actor:** Doctor  
- **Trigger:** Select an image set from the queue  
- **Flow:** System fetches image list → renders each DICOM slice as PNG via server-side windowing (adjustable WL/WW)

#### UC-D05: Classify Image Set Usability
- **Actor:** Doctor  
- **Trigger:** Open annotation page for an image set  
- **Flow:** Doctor selects one of:
  - `IschemicAssessable` — suitable for ASPECTS scoring
  - `HemorrhagicPresent` — hemorrhage present
  - `Anomaly` — other anomaly
  - `Irrelevant` — not relevant for assessment

#### UC-D06: Score Bilateral ASPECTS Zones
- **Actor:** Doctor  
- **Precondition:** UC-D05 selected `IschemicAssessable` and low-quality flag is off  
- **Flow:** For each slice (Basal Ganglia or Corona Radiata region), score all 10 zones × 2 hemispheres:
  - Zones: C, IC, L, I, M1, M2, M3, M4, M5, M6
  - Scores per zone: `Affected` | `Not_Affected` | `Not_In_This_Slice` | `Not_Applicable`

#### UC-D07: Save Draft
- **Actor:** Doctor  
- **Trigger:** Manual save button or keyboard shortcut  
- **Flow:** Current annotation state serialised → `POST /api/evaluations/draft` → persisted in `annotation_sessions.draft_payload`

#### UC-D08: Auto-Save Draft
- **Actor:** System (triggered by annotation changes)  
- **Flow:** After each change, debounced save → `POST /api/evaluations/auto-draft` → stored separately from manual draft; manual draft takes priority on restore

#### UC-D09: Restore Draft
- **Actor:** Doctor  
- **Trigger:** Re-open an image set that has a draft  
- **Flow:** System detects existing draft → prompt to restore or discard → if restore: pre-fill annotation form with saved payload

#### UC-D10: Submit Annotation
- **Actor:** Doctor  
- **Trigger:** Click submit on the annotation page  
- **Flow:** `POST /api/evaluations/submit` → creates `ImageSetEvaluation` + `ImageEvaluation` rows → marks `annotation_session.submitted_at` → image set marked as annotated in the queue

#### UC-D11: View Annotation History
- **Actor:** Doctor  
- **Flow:** `GET /api/annotation-sessions/my-history` returns chronological list of draft-saved, draft-deleted, and submitted events

#### UC-D12: Manage Settings & Preferences
- **Actor:** Doctor  
- **Flow:** Navigate to `/settings` → toggle dark mode, tooltip mode, keyboard hints, navigation mode → `PUT /api/auth/preferences` persists JSON blob per doctor

#### UC-D13: Change Password
- **Actor:** Doctor  
- **Flow:** Navigate to `/change-password` → enter current + new password → `POST /api/auth/change-password`

---

### 2.3 Admin Use Cases

#### UC-A01: Create Doctor Account
- **Actor:** Admin  
- **Flow:** `POST /api/admin/doctors` with username, password, full name, role, is_test flag → account created with `must_change_password=true`

#### UC-A02: Manage Doctor Accounts
- **Actor:** Admin  
- **Flow:** List all doctors → deactivate/reactivate, reset password, update full name, toggle test-account flag via `PATCH /api/admin/doctors/{uuid}`

#### UC-A03: Create Dataset
- **Actor:** Admin  
- **Flow:** `POST /api/datasets` → new dataset created; patients and image sets can then be attached

#### UC-A04: Register Patients & Image Sets
- **Actor:** Admin  
- **Flow:** `POST /api/patients` → `POST /api/image-sets` with folder path, window settings, ICD code; system validates folder existence

#### UC-A05: Assign Dataset to Doctor
- **Actor:** Admin  
- **Flow:** `POST /api/admin/assignments` → doctor now sees the assigned dataset in their queue; one active assignment per doctor at a time

#### UC-A06: Monitor Submission Progress
- **Actor:** Admin  
- **Flow:** `GET /api/admin/submissions` returns all submitted sessions with doctor name, image set, timestamp; `GET /api/datasets` returns global progress counts

#### UC-A07: Review Submitted Annotations
- **Actor:** Admin  
- **Flow:** `GET /api/admin/submission/by-image-set/{uuid}?doctor_uuid=...` returns full annotation payload for any doctor+image set combination

#### UC-A08: Manage Active Drafts
- **Actor:** Admin  
- **Flow:** `GET /api/admin/drafts` lists all active drafts across all doctors; `DELETE /api/admin/drafts/{session_uuid}` clears a stuck draft

#### UC-A09: Export Annotations
- **Actor:** Admin  
- **Flow:** `GET /api/export/annotations?format=xlsx&dataset_uuid=...` downloads all submissions as Excel or CSV file

#### UC-A10: View Audit Log
- **Actor:** Admin  
- **Flow:** `GET /api/admin/audit-log` returns all admin mutations (create, deactivate, assign, reset-password, delete-draft, etc.) with timestamps

---

## 3. Database Schema

### 3.1 Entity Overview

| Table | Primary Key | Description |
|---|---|---|
| `datasets` | `dataset_uuid` (UUID) | Named collection of patients/image sets |
| `patients` | `patient_uuid` (UUID) | Patient record within a dataset |
| `doctors` | `uuid` (UUID) | User account (Doctor or Admin role) |
| `image_sets` | `index` (int autoincrement), `uuid` (UUID unique) | A folder of DICOM slices for one patient scan |
| `images` | `uuid` (UUID) | Individual DICOM slice within an image set |
| `login_sessions` | `session_uuid` (UUID) | One row per JWT issuance event |
| `annotation_sessions` | `annotation_session_uuid` (UUID) | One doctor's work on one image set (draft + submission anchor) |
| `image_set_evaluations` | `id` (int) | Set-level usability classification, 1:1 with annotation_session |
| `image_evaluations` | `id` (int) | Per-slice bilateral ASPECTS zone scores |
| `doctor_dataset_assignments` | `id` (int) | Active dataset delegation from admin to doctor |
| `admin_audit_log` | `id` (int) | Append-only record of all admin mutations |

---

### 3.2 Table Definitions

#### `datasets`
| Column | Type | Constraints |
|---|---|---|
| `dataset_uuid` | UUID | PK, default uuid4 |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE |
| `description` | TEXT | nullable |
| `is_active` | BOOLEAN | NOT NULL, default true |
| `created_at` | TIMESTAMPTZ | NOT NULL |

#### `patients`
| Column | Type | Constraints |
|---|---|---|
| `patient_uuid` | UUID | PK |
| `patient_id` | VARCHAR(255) | NOT NULL |
| `dataset_uuid` | UUID | FK → datasets, NOT NULL |
| `category` | VARCHAR(255) | nullable |
| `age` | INTEGER | nullable |
| `gender` | ENUM(Male, Female, Other) | nullable |

Unique constraint: `(patient_id, dataset_uuid)`

#### `doctors`
| Column | Type | Constraints |
|---|---|---|
| `uuid` | UUID | PK |
| `username` | VARCHAR(255) | NOT NULL, UNIQUE, min 3 chars |
| `role` | ENUM(Doctor, Admin) | NOT NULL, default Doctor |
| `email` | VARCHAR(255) | UNIQUE, nullable |
| `password_hash` | VARCHAR(1024) | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default true |
| `is_test` | BOOLEAN | NOT NULL, default false |
| `full_name` | VARCHAR(255) | nullable |
| `must_change_password` | BOOLEAN | NOT NULL, default false |
| `must_set_name` | BOOLEAN | NOT NULL, default false |
| `registration_source` | VARCHAR(64) | NOT NULL, default 'admin_created' |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `last_seen` | TIMESTAMPTZ | nullable |
| `preferences` | JSONB | nullable |

#### `image_sets`
| Column | Type | Constraints |
|---|---|---|
| `index` | INTEGER | PK, autoincrement |
| `uuid` | UUID | UNIQUE, NOT NULL |
| `dataset_uuid` | UUID | FK → datasets |
| `patient_uuid` | UUID | FK → patients |
| `image_set_name` | VARCHAR(512) | NOT NULL |
| `image_format` | ENUM(DICOM, JPEG, PNG) | NOT NULL, default DICOM |
| `image_window_level` | INTEGER | nullable |
| `image_window_width` | INTEGER | nullable |
| `num_images` | INTEGER | NOT NULL |
| `folder_path` | VARCHAR(1024) | NOT NULL, UNIQUE |
| `description` | TEXT | nullable |
| `icd_code` | VARCHAR(64) | nullable |
| `is_active` | BOOLEAN | NOT NULL, default true |
| `created_at` | TIMESTAMPTZ | NOT NULL |

Unique constraint: `(image_set_name, patient_uuid, dataset_uuid)`

#### `images`
| Column | Type | Constraints |
|---|---|---|
| `uuid` | UUID | PK |
| `image_name` | VARCHAR(512) | NOT NULL |
| `image_set_uuid` | UUID | FK → image_sets.uuid |
| `slice_index` | INTEGER | NOT NULL |

Unique constraint: `(image_name, image_set_uuid, slice_index)`

#### `login_sessions`
| Column | Type | Constraints |
|---|---|---|
| `session_uuid` | UUID | PK |
| `doctor_uuid` | UUID | FK → doctors |
| `login_time` | TIMESTAMPTZ | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default true |

#### `annotation_sessions`
| Column | Type | Constraints |
|---|---|---|
| `annotation_session_uuid` | UUID | PK |
| `doctor_uuid` | UUID | FK → doctors |
| `image_set_uuid` | UUID | FK → image_sets |
| `login_session_uuid` | UUID | FK → login_sessions |
| `started_at` | TIMESTAMPTZ | NOT NULL |
| `submitted_at` | TIMESTAMPTZ | nullable — null = not yet submitted |
| `draft_payload` | TEXT | nullable — JSON, manual save |
| `draft_saved_at` | TIMESTAMPTZ | nullable |
| `draft_deleted_at` | TIMESTAMPTZ | nullable — soft delete |
| `auto_draft_payload` | TEXT | nullable — JSON, auto-save |
| `auto_draft_saved_at` | TIMESTAMPTZ | nullable |

#### `image_set_evaluations`
| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `annotation_session_uuid` | UUID | FK → annotation_sessions, UNIQUE |
| `image_set_uuid` | UUID | FK → image_sets |
| `image_set_usability` | ENUM(IschemicAssessable, HemorrhagicPresent, Anomaly, Irrelevant) | NOT NULL |
| `ischemic_low_quality` | BOOLEAN | NOT NULL |
| `notes` | TEXT | nullable |

#### `image_evaluations`
| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `annotation_session_uuid` | UUID | FK → annotation_sessions |
| `image_uuid` | UUID | FK → images |
| `region` | ENUM(None, BasalGanglia, CoronaRadiata) | NOT NULL |
| `{zone}_{side}_score` × 20 | ENUM(Affected, Not_Affected, Not_In_This_Slice, Not_Applicable) | NOT NULL each |
| `notes` | TEXT | nullable |

Zones: `c, ic, l, i, m1, m2, m3, m4, m5, m6` — each has `_left_score` and `_right_score`  
Unique constraint: `(annotation_session_uuid, image_uuid)`

#### `doctor_dataset_assignments`
| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `doctor_uuid` | UUID | FK → doctors |
| `dataset_uuid` | UUID | FK → datasets |
| `assigned_at` | TIMESTAMPTZ | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default true |

#### `admin_audit_log`
| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `admin_uuid` | UUID | FK → doctors |
| `action` | VARCHAR(128) | NOT NULL (e.g. CREATE, DEACTIVATE, ASSIGN_DATASET, RESET_PASSWORD) |
| `target_table` | VARCHAR(128) | NOT NULL |
| `target_id` | VARCHAR(255) | nullable |
| `detail` | TEXT | nullable |
| `timestamp` | TIMESTAMPTZ | NOT NULL |

---

### 3.3 Entity Relationship Summary

```
datasets ──< patients ──< image_sets ──< images
    │                          │
    └──< doctor_dataset_assignments       │
               │                         │
           doctors ──< login_sessions    │
               │                         │
               └──< annotation_sessions ─┘
                          │
               ┌──────────┴───────────┐
               │                      │
   image_set_evaluations    image_evaluations
```

Key relationships:
- One **dataset** → many **patients** → many **image sets** → many **images**
- One **doctor** → many **annotation sessions** (one per image set attempt)
- One **annotation session** → one **image_set_evaluation** + many **image_evaluations**
- One **doctor** can have one active **dataset assignment** at a time

---

## 4. API Specification

All endpoints are prefixed with `/api`. Authentication uses `Authorization: Bearer <access_token>` unless noted.

**Rate limits:** Auth endpoints are rate-limited (5–30 req/min via slowapi).

---

### 4.1 Auth — `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Self-register with invite code |
| POST | `/auth/login` | None | Login → access token + refresh cookie |
| POST | `/auth/refresh` | Refresh cookie | Rotate tokens |
| POST | `/auth/logout` | Bearer | Deactivate login session, clear cookie |
| POST | `/auth/setup-account` | Bearer | First-login: set name and/or new password |
| POST | `/auth/change-password` | Bearer | Change own password |
| POST | `/auth/heartbeat` | Bearer | Update last_seen timestamp |
| GET | `/auth/me` | Bearer | Return own profile |
| GET | `/auth/preferences` | Bearer | Return UI preferences JSON |
| PUT | `/auth/preferences` | Bearer | Persist UI preferences JSON |

**Login request:**
```json
{ "username": "string", "password": "string" }
```

**Login / token response:**
```json
{
  "access_token": "string",
  "must_change_password": false,
  "must_set_name": false,
  "preferences": { "dark": false, "tooltip_mode": "hover", "show_kbd_hints": true, ... }
}
```

---

### 4.2 Datasets — `/api/datasets`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/datasets/` | Doctor | List all datasets (with total image sets + global progress) |
| POST | `/datasets/` | Admin | Create dataset |
| GET | `/datasets/{dataset_uuid}` | Doctor | Get single dataset |
| PATCH | `/datasets/{dataset_uuid}` | Admin | Update description or is_active |

**Dataset response fields:** `dataset_uuid`, `name`, `description`, `is_active`, `created_at`, `total_image_sets`, `global_progress`

---

### 4.3 Patients — `/api/patients`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/patients/by-dataset/{dataset_uuid}` | Doctor | List patients in dataset |
| POST | `/patients/` | Admin | Register new patient |
| GET | `/patients/{patient_uuid}` | Doctor | Get patient |
| PATCH | `/patients/{patient_uuid}` | Admin | Update patient metadata |

---

### 4.4 Image Sets — `/api/image-sets`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/image-sets/by-dataset/{dataset_uuid}` | Doctor | List image sets with per-doctor progress flags |
| POST | `/image-sets/` | Admin | Register new image set (folder must exist) |
| GET | `/image-sets/{image_set_uuid}` | Doctor | Get image set with patient demographics |
| PATCH | `/image-sets/{image_set_uuid}` | Admin | Update window settings, description, icd_code, is_active |

**ImageSetWithProgress extra fields:** `dataset_index`, `evaluated_by_me`, `in_draft_by_me`, `total_evaluators`

---

### 4.5 Images — `/api/images`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/images/by-image-set/{image_set_uuid}` | Doctor | List slices (uuid + slice_index) |
| GET | `/images/{image_uuid}/render?wl=&ww=` | Doctor | Render DICOM slice as PNG (server-side windowing) |

Default windowing: WL=35, WW=100 (CT brain standard). Override via `?wl=&ww=` query params.

---

### 4.6 Annotation Sessions — `/api/annotation-sessions`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/annotation-sessions/` | Doctor | Open new session for an image set |
| GET | `/annotation-sessions/mine` | Doctor | List own sessions (optional `?submitted_only=true`) |
| GET | `/annotation-sessions/my-history` | Doctor | Chronological activity events (draft_saved, draft_deleted, submitted) |
| GET | `/annotation-sessions/{uuid}` | Doctor | Get single session (own only) |

---

### 4.7 Evaluations — `/api/evaluations`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/evaluations/submit` | Doctor | Submit final annotation (creates ImageSetEvaluation + ImageEvaluations) |
| GET | `/evaluations/{session_uuid}/set-evaluation` | Doctor | Read back set-level evaluation |
| GET | `/evaluations/{session_uuid}/image-evaluations` | Doctor | Read back all slice evaluations |
| POST | `/evaluations/draft` | Doctor | Manual save draft |
| POST | `/evaluations/auto-draft` | Doctor | Auto-save draft (does not overwrite manual) |
| GET | `/evaluations/drafts/mine` | Doctor | List all own active drafts |
| GET | `/evaluations/draft/by-image-set/{uuid}` | Doctor | Get best draft for image set (newer of manual vs auto) |
| DELETE | `/evaluations/draft/by-image-set/{uuid}` | Doctor | Discard active draft for image set |
| GET | `/evaluations/submission/by-image-set/{uuid}` | Doctor | Read own submitted annotation as draft-shaped payload |

**Submit body:**
```json
{
  "annotation_session_uuid": "uuid",
  "usability": "IschemicAssessable",
  "low_quality": false,
  "notes": "optional",
  "image_evaluations": [
    {
      "image_uuid": "uuid",
      "region": "BasalGanglia",
      "c_left_score": "Affected",
      "c_right_score": "Not_Affected",
      "ic_left_score": "Not_In_This_Slice",
      ...
    }
  ]
}
```

---

### 4.8 Dashboard — `/api/dashboard`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/dashboard/` | Doctor | Queue stats: assigned dataset, total sets, submitted count, draft count |

---

### 4.9 Admin — `/api/admin`

#### Doctor Management

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/doctors` | Admin | List all doctors (`?include_inactive=true`) |
| POST | `/admin/doctors` | Admin | Create doctor account |
| PATCH | `/admin/doctors/{uuid}` | Admin | Update: is_active, password, full_name, is_test |

#### Dataset Assignment

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/admin/assignments` | Admin | Assign dataset to doctor |
| GET | `/admin/assignments/{doctor_uuid}` | Admin | Get active assignment + progress |
| DELETE | `/admin/assignments/{id}` | Admin | Revoke assignment |

#### Draft Management

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/drafts` | Admin | List all active drafts (all doctors) |
| DELETE | `/admin/drafts/{session_uuid}` | Admin | Delete any draft |

#### Submissions & Audit

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/submissions` | Admin | List all submitted sessions (`?dataset_uuid=...`) |
| GET | `/admin/submission/by-image-set/{uuid}` | Admin | Read any doctor's submission (`?doctor_uuid=...`) |
| GET | `/admin/audit-log` | Admin | Paginated admin action log (`?limit=&offset=`) |

---

### 4.10 Export — `/api/export`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/export/annotations?format=xlsx&dataset_uuid=` | Admin | Download all annotations as Excel or CSV |

---

### 4.11 System — `/api/about`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/about/` | None | Return app name, version, creator, uptime |

---

## 5. Frontend Pages & Routes

### Doctor Routes

| Route | Component | Description |
|---|---|---|
| `/login` | LoginPage | Username + password form |
| `/register` | RegisterPage | Self-registration with invite code |
| `/` | DashboardPage | Queue overview + progress |
| `/label` | LabelPage | Full annotation UI (image viewer + zone scoring) |
| `/change-password` | ChangePasswordPage | Change own password |
| `/settings` | SettingsPage | UI preferences (dark mode, keyboard hints, nav mode) |

### Admin Routes (role-gated)

| Route | Component | Description |
|---|---|---|
| `/admin/doctors` | DoctorsPage | Create, deactivate, reset password for accounts |
| `/admin/datasets` | DatasetsPage | Create and manage datasets |
| `/admin/patients` | PatientsPage | Register and view patients |
| `/admin/image-sets` | ImageSetsPage | Register and configure DICOM sets |
| `/admin/assignments` | AssignmentsPage | Assign datasets to doctors |
| `/admin/submissions` | SubmissionsPage | Review all submitted annotations |
| `/admin/export` | ExportPage | Download Excel/CSV export |

---

## 6. Non-Functional Properties

### Security
- JWT access token (short-lived, Bearer header) + refresh token (HttpOnly cookie, `/api/auth/refresh` path only)
- `must_change_password` flag forces password change on first login
- Security response headers: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`
- Rate limiting on auth endpoints (slowapi)
- Role-based access enforced at every endpoint via `get_current_doctor` / `get_current_admin` dependencies
- Soft-delete for doctors and image sets (no hard deletes of clinical data)

### Data Integrity
- `annotation_session` is the single FK anchor for all evaluation data
- Admin audit log is append-only (no updates or deletes)
- Test accounts (`is_test=true`) excluded from global progress counts
- Cannot remove `is_test` flag after submissions exist

### DICOM Rendering
- Server-side: pydicom + Pillow + NumPy
- Default brain CT window: WL=35 HU, WW=100 HU
- Per-image-set window override stored in DB
- Per-request window override via query params

### Deployment
- Docker Compose: PostgreSQL 16 + FastAPI (uvicorn) + Nginx (serves React SPA + proxies `/api`)
- Environment config via `.env` file (see `backend/example.env`)
- Schema migrations via `_add_missing_columns()` at startup (ALTER TABLE IF NOT EXISTS pattern)
