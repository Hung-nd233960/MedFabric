# MedFabric — Feature Proposals

> Evaluation of proposed features before implementation.
> Status: **Design · not yet built**

---

## 1. Distribute the frontend as an Electron app

### Context

MedFabric is deployed as a Docker Compose stack — PostgreSQL + FastAPI backend + Nginx serving the React SPA — on a hospital intranet. Doctors open the app in a browser. DICOM rendering is server-side (pydicom + Pillow). All persistent state lives in PostgreSQL.

The proposal is to repackage the React frontend as an Electron desktop application so doctors run a native window instead of a browser tab.

### What Electron would and would not change

| | Electron | Current (browser) |
|---|---|---|
| Backend required | Yes (unchanged) | Yes |
| PostgreSQL required | Yes (unchanged) | Yes |
| DICOM server required | Yes (unchanged) | Yes |
| Browser chrome visible | No | Yes |
| OS taskbar integration | Yes | No |
| Install on each workstation | Yes (~200 MB) | No |
| Automatic updates | Needs electron-updater | Redeploy Docker, done |
| IT policy hurdle | App installation approval | None (browser) |

### Analysis

Electron packages only the renderer (the browser). Because DICOM decoding, session management, and the database all run on the server, Electron would still need the Docker stack running on a central machine and would still make HTTP requests to it. The only thing replaced is the browser window.

The gain — a chrome-free window — is real but minor. The costs are substantial for a hospital intranet deployment:

- **IT friction.** Hospitals typically require approval and packaging for desktop software installations. A web app needs nothing.
- **Update burden.** Deploying a fix currently means `docker compose pull && docker compose up`. With Electron, every workstation either needs auto-update infrastructure or manual reinstallation.
- **New tech surface.** Electron adds a main-process / renderer-process model, IPC, `contextBridge`, and Node.js bundling on top of the existing stack — none of which are needed since the app does not use local file system APIs or OS integration.
- **Binary size vs zero.** ~200 MB Electron binary per workstation vs. nothing (browser already installed).

### Verdict: Not recommended

The web + Docker model is the correct architecture for a multi-doctor, server-authoritative, hospital-intranet tool. Electron would add a large maintenance surface for a marginal UX gain.

### Better alternative if an "app-like" window is desired: PWA

A Progressive Web App adds a `manifest.json` and one service-worker registration (~30 lines). Doctors can click "Install" in the browser address bar; the app opens in its own frameless window with no URL bar, appears in the OS taskbar, and receives automatic updates on next open — identical to Electron's window behaviour, with zero installation overhead or build pipeline change.

---

## 2. Apply `beforeunload` to Annotation Mode

### Context

LabelPage already has a navigation guard: `navGuardStore` registers an interceptor on mount that checks for `dirty` state (usability set, low-quality flag, set notes, or any slice with a region or notes filled in). When a doctor clicks a React Router link or the Exit button while dirty, a custom `ConfirmDialog` appears before navigating.

**Gap.** The React Router interceptor only fires for in-app programmatic navigation. It does not fire for:

| Action | Currently protected |
|---|---|
| Exit button / in-app link (in-app) | ✅ `navGuardStore` interceptor |
| Browser refresh (F5 / Ctrl+R) | ❌ |
| Close browser tab (Ctrl+W) | ❌ |
| Browser back button | ❌ |
| Typing a new URL in the address bar | ❌ |

### Solution: `beforeunload` event listener

`window.addEventListener('beforeunload', handler)` fires for all browser-level navigation before the React app has a chance to respond. When the handler calls `event.preventDefault()` and sets `event.returnValue`, the browser shows a native confirmation dialog ("Changes you made may not be saved. Leave site?"). The message text cannot be customised in modern browsers for security reasons — only the prompt itself can be triggered.

**Activation condition** — only active when all of the following hold:
1. Route is LabelPage (component is mounted)
2. `!isReadMode && !isPreviewMode` (annotation mode only)
3. `dirty === true` (same logic as the existing navGuard dirty check)

**Verdict: Recommended — implemented in `LabelPage.tsx`.**

---

## 3. Sortable columns in admin tables

### Current state

Five admin pages render data tables with static `<th>` headers — no sort logic exists in any of them:

| Page | Sortable columns available |
|---|---|
| `DoctorsPage` | Username, Full Name, Role, Status, Source, Created |
| `DatasetsPage` | Name, Status, Progress, Created |
| `SubmissionsPage` | Image Set, ICD, Doctor, Submitted |
| `AssignmentsPage` | Doctor, Role, Dataset, Progress, Since |
| `ImageSetsPage` | Name, ICD, Slices, Evaluators, Status |
| `PatientsPage` | Patient ID, Age, Gender, Category |

The doctor-facing `DashboardPage` already has full sort logic (`sortCol` + `sortDir` state, clickable `<th>` buttons with `ArrowUpDown` / `ArrowUp` / `ArrowDown` icons) — the pattern can be copied directly.

### Analysis

For an admin managing tens to hundreds of doctors or thousands of image sets, the inability to sort makes the tables impractical. Sorting by "Submitted" to find the most recent annotation, by "Progress" to see which doctors are furthest behind, or by "Status" to filter inactive accounts are all daily tasks.

The implementation cost is low: per-table `sortCol` / `sortDir` state, one `handleSort` click handler, and replacing static `<th>` with clickable `<button>` wrappers. All data is already in the client (no server pagination). The Lucide icons and sort utility are already imported in DashboardPage and can be reused.

### Verdict: Recommended — straightforward, high administrative value

Implementation order by impact:
1. `SubmissionsPage` — most frequently used for reviewing work
2. `DoctorsPage` — most frequently managed by admin
3. `AssignmentsPage` — progress tracking
4. `DatasetsPage` and `ImageSetsPage` — lower volume, lower urgency

---

## 4. Dedicated admin analytics dashboard

### Proposal

A new admin route (`/admin/analytics`) with a dataset selector. Once a dataset is chosen, it renders two sections:

**Section A — Global statistics (non-test accounts only)**

The global view excludes test-account annotations so that calibration runs don't inflate the real-world numbers.

**(a) Completion pie**
- **Done**: image sets with ≥ 1 submission from a non-test doctor
- **Not yet**: remaining image sets
- Shows: N done (X%) / N remaining (Y%)

**(b) Contributor pie**
- One slice per non-test doctor who submitted ≥ 1 annotation in the dataset
- Each slice = that doctor's unique annotated image set count / total unique sets with any non-test annotation
- Shows relative contribution across the team
- Note: uses unique sets (not raw submission count) so a doctor re-annotating a set is not double-counted

**(c) Usability distribution pie**
- All image-set-level evaluations from non-test doctors, grouped by usability value
- Slices: IschemicAssessable / HemorrhagicPresent / Anomaly / Irrelevant
- If multiple doctors annotated the same set with different usability values, each submission counts independently — this reflects the annotation agreement landscape, not just one value per set

**Test account question**: Yes, (a) (b) (c) should all exclude test accounts. These charts represent the clinical data collection result, not internal calibration. Test annotations should not change the apparent completion rate or usability distribution.

**Three separate pie charts**: Correct — they answer three different questions and share no axis. Stacking them or combining would obscure the individual insights.

**Section B — Per-doctor breakdown (all accounts, including test)**

A card grid or list, one card per doctor who has annotated in this dataset. Includes test accounts because this section is for internal review (calibration comparison, quality checks). Each card shows:

- Doctor name / username
- Test account badge (if `is_test`)
- Number of sets annotated
- Usability breakdown (small horizontal bar or mini-pie per card)
- Last annotation timestamp
- Cards sorted by annotation count descending (most active first)

### Backend requirements

New endpoint:

```
GET /api/admin/analytics?dataset_uuid={uuid}
```

Response shape:
```json
{
  "dataset": { "name": "...", "total_image_sets": 120 },
  "global": {
    "annotated_sets": 87,
    "unannotated_sets": 33,
    "contributors": [
      { "doctor_uuid": "...", "username": "Dr. A", "full_name": "...", "unique_sets": 45 }
    ],
    "usability_counts": {
      "IschemicAssessable": 62,
      "HemorrhagicPresent": 11,
      "Anomaly": 8,
      "Irrelevant": 6
    }
  },
  "per_doctor": [
    {
      "doctor_uuid": "...",
      "username": "Dr. A",
      "full_name": "...",
      "is_test": false,
      "annotated_count": 45,
      "last_annotation": "2026-05-20T08:14:00Z",
      "usability_counts": {
        "IschemicAssessable": 30,
        "HemorrhagicPresent": 8,
        "Anomaly": 5,
        "Irrelevant": 2
      }
    }
  ]
}
```

All fields under `global` are computed excluding rows where `doctors.is_test = true`. All entries under `per_doctor` include everyone.

### Frontend requirements

**Chart library.** No chart library is currently installed. Recommended: **recharts** — the most widely used React chart library, TypeScript-native, PieChart + Pie + Cell + Tooltip + Legend covers all three charts. Single package install (`bun add recharts`). Alternative `@nivo/pie` is prettier but heavier and requires multiple `@nivo/*` packages.

**New route.** Add `/admin/analytics` in `App.tsx` under the `RequireAdmin` guard.

**Dataset selector.** A `<select>` or shadcn `Select` at the top of the page, populated from `GET /api/datasets`. Stats load/reload when the selection changes.

**Responsive layout.** The three Section A pies should sit in a 3-column grid on wide screens and stack on narrow ones. Section B cards go in a 2–3 column responsive grid.

### Verdict: Recommended — high value for research oversight

This dashboard closes the gap between raw data export and real-time visibility. For a thesis context it also provides the exact figures needed for a "dataset collection status" section (completion %, usability distribution, per-annotator breakdown). The three separate pie charts are the right visualisation choice for the three independent questions.

**Suggested implementation order:**
1. Backend analytics endpoint (one service function + one router endpoint)
2. Frontend dataset selector + Section A pies (Completion + Usability first, simplest queries)
3. Contributor pie (requires per-doctor aggregation)
4. Section B doctor cards

---

## 5. Telegram Notification System

### Context

MedFabric runs on a hospital intranet with Tailscale for remote access. There is no push-notification mechanism today — admins have no real-time awareness of doctor activity or dataset progress without opening the admin panel. Two channels of notification are proposed:

1. **Login alerts** — instant notification when any doctor logs in.
2. **12-hour progress reports** — sent at 09:00 and 21:00, tallying new submissions over the preceding window.

A lightweight **admin testing panel** is also proposed so that the Telegram config can be verified without writing test scripts.

---

### Architecture: where the logic lives

All Telegram logic lives in the FastAPI backend only. No new container is required — the backend already runs continuously and owns the database.

| Concern | Solution |
|---|---|
| HTTP calls to Telegram Bot API | `httpx.AsyncClient` in a thin `telegram.py` service |
| Scheduled 12h reports | `APScheduler` (`AsyncIOScheduler`) started in FastAPI lifespan |
| Login events | Hook directly into `POST /auth/login` after successful auth |
| Timezone | `SCHEDULER_TIMEZONE` env var (e.g. `Asia/Ho_Chi_Minh`) |
| Feature on/off | Entire feature is inert if `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` are unset |

The Telegram module is **opt-in via env vars**. If the vars are absent, every notify call is a no-op — no errors, no log spam. The module can be removed entirely by deleting `telegram.py`, its import in `auth.py`, and the admin endpoint, leaving zero footprint.

---

### New env vars

```
TELEGRAM_BOT_TOKEN=123456:ABC-...
TELEGRAM_CHAT_ID=-100xxxxxxxxx
SCHEDULER_TIMEZONE=Asia/Ho_Chi_Minh
```

These are added to `Settings` in `config.py` as `Optional[str]` with a `None` default.

---

### New files

```
backend/app/services/telegram.py    ← Telegram HTTP client + message formatters
backend/app/services/scheduler.py   ← APScheduler setup + 12h report jobs
```

`telegram.py` exposes:

- `async notify_login(doctor)` — login alert, skips if `doctor.is_test`
- `async send_12h_report(db)` — queries the last 12 hours, formats, sends
- `async send_message(text)` — raw send, used by the admin test endpoint

`scheduler.py` exposes:

- `start_scheduler()` / `stop_scheduler()` called from FastAPI lifespan in `main.py`

---

### Login notification

Called in `auth.py` `login()` after `_build_token_response`, fired as a background task so it does not add latency to the login response:

```python
from fastapi import BackgroundTasks
from app.services.telegram import notify_login

@router.post("/login", response_model=TokenResponse)
def login(..., background_tasks: BackgroundTasks, ...):
    ...
    token_resp = _build_token_response(doctor, response, db)
    background_tasks.add_task(notify_login, doctor)
    return token_resp
```

Message format:

```
🔔 Dr. Nguyen Van A (nguyenvana) signed in
⏰ 14:35 | 01 Jun 2026
```

Refresh (`/auth/refresh`) does **not** trigger a notification — only explicit `/login` does. This prevents noise from token renewals every 2 hours.

---

### 12-hour report

Scheduled at `hour='9,21', minute=0` via `CronTrigger`. Queries:

```sql
SELECT
    d.full_name, d.username,
    ds.name AS dataset_name,
    ise.image_set_name, ise.order_index
FROM image_set_evaluations ise
JOIN doctors d ON d.uuid = ise.doctor_uuid
JOIN image_sets imgs ON imgs.uuid = ise.image_set_uuid
JOIN datasets ds ON ds.uuid = imgs.dataset_uuid
WHERE ise.created_at >= NOW() - INTERVAL '12 hours'
ORDER BY d.full_name, ds.name, ise.order_index
```

Then per-dataset global progress is appended from the same stats used by the analytics dashboard.

**Message format (with submissions):**

```
📊 MedFabric — 12h Report
🕘 09:00 | 01 Jun 2026

✅ 4 new submissions since 21:00 yesterday:

Dr. Nguyen Van A (nguyenvana)
  📁 CT Brain Stroke
    • Set #42 — ISC-0042
    • Set #67 — ISC-0067

Dr. Tran Thi B (tranthib)
  📁 CXR COVID
    • Set #15 — CXR-0015

Dr. Tran Thi B (tranthib)
  📁 CT Brain Stroke
    • Set #103 — ISC-0103

━━━━━━━━━━━━━━━
📈 Dataset Progress
  CT Brain Stroke: 87/120 (72%)
  CXR COVID: 34/80 (42%)
```

**Message format (no submissions):**

```
📊 MedFabric — 12h Report
🕘 21:00 | 01 Jun 2026

💤 No new submissions since 09:00 today.

━━━━━━━━━━━━━━━
📈 Dataset Progress
  CT Brain Stroke: 87/120 (72%)
  CXR COVID: 34/80 (42%)
```

The global progress section is always included so the admin gets a consistent snapshot even on quiet windows.

---

### Admin testing panel

**Design principle:** The testing panel is a convenience tool for validating config. It has no database state, no side effects beyond sending a Telegram message, and can be removed (or disabled) at any time without migration.

**Backend** — two new endpoints under `POST /api/admin/telegram/`:

| Endpoint | Action |
| --- | --- |
| `POST /api/admin/telegram/test` | Sends `🔧 Test message from MedFabric Admin` |
| `POST /api/admin/telegram/send-report` | Triggers the 12h report immediately |
| `GET /api/admin/telegram/preview-report` | Returns the formatted report as a string without sending it |
| `GET /api/admin/telegram/status` | Returns `{ "configured": true/false, "chat_id": "...last 4 digits..." }` |

All endpoints are guarded by the existing admin-role dependency. They live in `routers/admin.py` as a small group.

**Frontend** — a collapsible card at the bottom of admin settings (not a nav item). Only rendered if `GET /api/admin/telegram/status` returns `configured: true`. Shows:

- Config status indicator
- "Send test message" button
- "Preview report" button — shows the formatted text in a `<pre>` block on the page
- "Send report now" button

The entire frontend component is self-contained and can be deleted without touching any other component.

**Why not make it persistent/configurable from the UI?** Storing the bot token in the database creates a secret management problem (it needs to be encrypted at rest, access-controlled, and rotated). Env vars are the correct place for credentials in a Docker Compose deployment. The UI panel is for *verifying* that the configured credential works, not for managing it.

---

### Kuma integration (complementary)

Uptime Kuma (added to `docker-compose.tailscale.yaml`) has native Telegram notification support. After deploying, configure Kuma to monitor:

- `http://backend:8000/api/about` — backend health
- `http://frontend:80` — nginx/frontend
- `http://postgres:5432` — (via TCP ping)

Kuma sends its own alerts to the same Telegram bot/chat. This covers **infrastructure down** events (container crash, OOM kill), which the app-level scheduler cannot detect (a dead backend can't send a report). The two systems are complementary:

| Alert source | Coverage |
| --- | --- |
| App scheduler (APScheduler) | Login events, submission reports |
| Kuma | Container health, service unavailability |

---

### Additional suggestions

**Doctor inactivity alert.** A third scheduled job (daily, e.g. 08:00) that checks for doctors with active dataset assignments who have made zero submissions in the past 48 hours. Useful for spotting stalled annotators early.

**Dataset completion alert.** After each successful submission in the evaluation endpoint, check if the dataset just hit 100%. If so, call `notify_dataset_complete(dataset)`. One-shot event, minimal query overhead.

**Login notification cooldown.** If a doctor logs out and back in multiple times in one session (e.g., session expires), the login alerts can become noisy. A simple in-memory cooldown (per-doctor, 30-minute window stored in a `dict` in `telegram.py`) keeps it to one notification per meaningful session. This is optional and can be skipped if noise is acceptable.

---

### Verdict: Recommended

The Telegram notification system adds real-time awareness with minimal complexity. The APScheduler approach requires no new container and uses only one new dependency (`apscheduler`). The entire feature is off by default and truly removable. The admin testing panel addresses the practical need for config verification without creating a secret-management footprint.

**Suggested implementation order:**
1. `telegram.py` service (message formatting + HTTP client) with no-op guard
2. `scheduler.py` + lifespan wiring — 12h report job
3. Login notification hook in `auth.py`
4. Admin test endpoints + frontend testing panel
5. (Optional) inactivity + completion alerts
