# Chapter 4: System Design

## Presentation Outline

**Estimated Length**: 10-15 pages  
**Key Purpose**: Present architecture, database design, and UI/UX design

---

## 4.1 System Architecture

### 4.1.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MEDFABRIC SYSTEM ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                        │
│  │   Web Browser   │                                                        │
│  │  (User Client)  │                                                        │
│  └────────┬────────┘                                                        │
│           │ HTTP/WebSocket                                                   │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    STREAMLIT SERVER                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                  PRESENTATION LAYER                          │    │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌───────────┐ ┌─────────┐          │    │   │
│  │  │  │  Login  │ │Dashboard│ │  Labeling │ │  Guide  │          │    │   │
│  │  │  │  Page   │ │  Page   │ │   Page    │ │  Page   │          │    │   │
│  │  │  └─────────┘ └─────────┘ └─────┬─────┘ └─────────┘          │    │   │
│  │  └────────────────────────────────┼─────────────────────────────┘    │   │
│  │                                   │                                  │   │
│  │  ┌────────────────────────────────▼─────────────────────────────┐   │   │
│  │  │                  BUSINESS LOGIC LAYER                         │   │   │
│  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │   │   │
│  │  │  │    State     │ │  Dispatcher  │ │    Image     │          │   │   │
│  │  │  │  Management  │ │   (Events)   │ │  Processing  │          │   │   │
│  │  │  └──────────────┘ └──────────────┘ └──────────────┘          │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                   │                                  │   │
│  │  ┌────────────────────────────────▼─────────────────────────────┐   │   │
│  │  │                  DATA ACCESS LAYER                            │   │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │   │   │
│  │  │  │Credential│ │ Sessions │ │ DataSets │ │Evaluation│         │   │   │
│  │  │  │   API    │ │   API    │ │   API    │ │   APIs   │         │   │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────┬──────────────────────────────────┘   │
│                                     │                                       │
│  ┌──────────────────────────────────▼──────────────────────────────────┐   │
│  │                    INFRASTRUCTURE LAYER                              │   │
│  │  ┌────────────────────┐    ┌────────────────────┐                   │   │
│  │  │   SQLite Database  │    │    File System     │                   │   │
│  │  │   (Evaluations)    │    │  (DICOM/JPEG)      │                   │   │
│  │  └────────────────────┘    └────────────────────┘                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1.2 Component Interactions

**Present a component diagram showing**:

- How pages interact with API modules
- How the dispatcher routes events
- How state flows through the system

*Reference*: [Component Diagram](../charts/component_diagram.md)

---

## 4.2 Database Design

### 4.2.1 Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENTITY RELATIONSHIP DIAGRAM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────┐         ┌───────────┐         ┌───────────┐                 │
│  │  Doctors  │         │  Session  │         │  DataSet  │                 │
│  ├───────────┤         ├───────────┤         ├───────────┤                 │
│  │ uuid (PK) │◄────────│doctor_uuid│         │ uuid (PK) │                 │
│  │ username  │         │ uuid (PK) │         │ name      │                 │
│  │ password  │         │ timestamp │         │ path      │                 │
│  │ full_name │         │ active    │         │ format    │                 │
│  │ email     │         └───────────┘         └─────┬─────┘                 │
│  └───────────┘                                     │                        │
│       │                                            │ 1:N                    │
│       │                                            ▼                        │
│       │         ┌───────────┐              ┌───────────────┐               │
│       │         │  Patient  │              │   ImageSet    │               │
│       │         ├───────────┤              ├───────────────┤               │
│       │         │ uuid (PK) │◄─────────────│ patient_uuid  │               │
│       │         │patient_id │              │ uuid (PK)     │               │
│       │         │ name      │              │ name          │               │
│       │         │ metadata  │              │ folder_path   │               │
│       │         └───────────┘              │ num_images    │               │
│       │                                    │ window_w/l    │               │
│       │                                    └───────┬───────┘               │
│       │                                            │                        │
│       │         ┌────────────────────────┐         │ 1:N                   │
│       │         │  ImageSetEvaluation    │         ▼                        │
│       │         ├────────────────────────┤  ┌───────────┐                  │
│       └────────▶│ doctor_uuid (FK)       │  │   Image   │                  │
│                 │ image_set_uuid (FK)    │◄─┤───────────┤                  │
│                 │ uuid (PK)              │  │ uuid (PK) │                  │
│                 │ session_uuid (FK)      │  │ name      │                  │
│                 │ usability              │  │ path      │                  │
│                 │ low_quality            │  │ slice_idx │                  │
│                 │ notes                  │  └─────┬─────┘                  │
│                 └────────────────────────┘        │                        │
│                             │                     │                        │
│                             │ 1:N                 │ 1:1                    │
│                             ▼                     ▼                        │
│                 ┌────────────────────────────────────┐                     │
│                 │        ImageEvaluation             │                     │
│                 ├────────────────────────────────────┤                     │
│                 │ uuid (PK)                          │                     │
│                 │ image_set_evaluation_uuid (FK)     │                     │
│                 │ image_uuid (FK)                    │                     │
│                 │ region                             │                     │
│                 │ basal_cortex_left/right            │                     │
│                 │ basal_central_left/right           │                     │
│                 │ corona_left/right                  │                     │
│                 │ notes                              │                     │
│                 └────────────────────────────────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2.2 Table Specifications

**Present each table with**:

- Column definitions
- Data types
- Constraints
- Purpose

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| Doctors | User accounts | uuid, username, password_hash |
| Session | Login sessions | uuid, doctor_uuid, timestamp |
| DataSet | Dataset metadata | uuid, name, path |
| Patient | Patient info | uuid, patient_id |
| ImageSet | CT scan sets | uuid, folder_path, num_images |
| Image | Individual slices | uuid, name, slice_index |
| ImageSetEvaluation | Set-level annotations | usability, low_quality, notes |
| ImageEvaluation | Slice-level annotations | region, all score fields |

### 4.2.3 Data Integrity Constraints

```sql
-- Foreign key relationships
ImageSet.patient_uuid → Patient.uuid
Image.image_set_uuid → ImageSet.uuid
ImageSetEvaluation.doctor_uuid → Doctors.uuid
ImageSetEvaluation.image_set_uuid → ImageSet.uuid
ImageEvaluation.image_set_evaluation_uuid → ImageSetEvaluation.uuid
ImageEvaluation.image_uuid → Image.uuid

-- Business rules (enforced in code)
- Score values: 0-10 for basal, 0-6 for corona
- Region must be one of: None, BasalCortex, BasalCentral, CoronaRadiata
- Session must be active for labeling
```

---

## 4.3 User Interface Design

### 4.3.1 Page Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      PAGE NAVIGATION FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌───────────────┐                             │
│                    │    Login      │                             │
│                    │    Page       │                             │
│                    └───────┬───────┘                             │
│                            │                                     │
│           ┌────────────────┼────────────────┐                   │
│           │                │                │                    │
│           ▼                ▼                ▼                    │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│    │  Register   │  │  Dashboard  │  │    Guide    │           │
│    │    Page     │  │    Page     │  │    Page     │           │
│    └─────────────┘  └──────┬──────┘  └─────────────┘           │
│                            │                                     │
│                            ▼                                     │
│                    ┌───────────────┐                             │
│                    │   Labeling    │                             │
│                    │     Page      │                             │
│                    └───────┬───────┘                             │
│                            │                                     │
│                            ▼                                     │
│                    ┌───────────────┐                             │
│                    │   Submit →    │                             │
│                    │   Dashboard   │                             │
│                    └───────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3.2 Labeling Page Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│ [Logout]                    MedFabric - Labeling                           │
├─────────────────────┬──────────────────────────┬───────────────────────────┤
│                     │                          │                           │
│                     │  Navigation              │  Set Information          │
│                     │  [◄ Prev] [Next ►]       │  ┌─────────────────────┐  │
│                     │  [────●────────] Slider  │  │ Set 1 of 3          │  │
│   ┌─────────────┐   │                          │  │ ICD: I63.9          │  │
│   │             │   │  Image Display           │  │ Index: 145          │  │
│   │             │   │  ┌────────────────────┐  │  └─────────────────────┘  │
│   │   CT Scan   │   │  │ Window Width: [80] │  │                           │
│   │    Image    │   │  │ Window Level: [40] │  │  [◄ Prev Set] [Next ►]    │
│   │             │   │  │ [Reset to Default] │  │                           │
│   │             │   │  └────────────────────┘  │  Current Set Status       │
│   │             │   │                          │  ┌─────────────────────┐  │
│   └─────────────┘   │  Labeling Controls       │  │ ⚠ Not yet valid     │  │
│                     │  ┌────────────────────┐  │  │                     │  │
│   Slice 12 of 45    │  │ Region:            │  │  │ Slice | Region | ✓  │  │
│   Set 1 of 3        │  │ [None|BC|BCe|CR]   │  │  │ 5     | BC     | ✓  │  │
│                     │  │                    │  │  │ 8     | BCe    | ✓  │  │
│                     │  │ Left:    Right:    │  │  │ 15    | CR     | ✗  │  │
│                     │  │ [2]      [3]       │  │  └─────────────────────┘  │
│                     │  └────────────────────┘  │                           │
│                     │                          │  [Submit All Evaluations] │
│                     │                          │                           │
└─────────────────────┴──────────────────────────┴───────────────────────────┘
```

### 4.3.3 UI/UX Design Principles

| Principle | Application |
|-----------|-------------|
| **Visibility of system status** | Status tables, validation messages |
| **Match real-world conventions** | ASPECTS terminology, medical workflow |
| **User control** | Navigation, reset buttons, undo (region clearing) |
| **Consistency** | Same layout across sets, consistent button placement |
| **Error prevention** | Input validation, required field marking |
| **Recognition over recall** | Region labels visible, score limits shown |
| **Flexibility** | Slider + buttons for navigation |
| **Aesthetic design** | Clean 3-column layout, minimal clutter |

---

## 4.4 State Management Design

### 4.4.1 State Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                       STATE HIERARCHY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  st.session_state (Streamlit)                                   │
│  │                                                               │
│  ├── user_session: SessionRead                                  │
│  │   ├── doctor_uuid                                             │
│  │   └── session_uuid                                            │
│  │                                                               │
│  ├── selected_scans: List[UUID]                                 │
│  │                                                               │
│  ├── label_flag: EventFlags                                     │
│  │   └── _queue: Queue[Event]                                   │
│  │                                                               │
│  ├── key_mngr: EnumKeyManager                                   │
│  │                                                               │
│  └── app_state: LabelingAppState                                │
│      ├── doctor_id: UUID                                         │
│      ├── login_session: UUID                                     │
│      ├── session_index: int (current set)                       │
│      ├── set_status_df: DataFrame                               │
│      │                                                           │
│      └── labeling_session: List[ImageSetEvaluationSession]      │
│          │                                                       │
│          └── [each session]                                      │
│              ├── uuid, name, num_images                          │
│              ├── current_index (current slice)                   │
│              ├── window_width/level                              │
│              ├── slice_status_df                                 │
│              │                                                   │
│              └── images_sessions: List[ImageEvaluationSession]  │
│                  │                                               │
│                  └── [each image]                                │
│                      ├── image_uuid, path, slice_index           │
│                      ├── region                                  │
│                      └── score fields (6 total)                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4.2 Event Flow Design

**Present the event-driven pattern**:

1. User interaction triggers callback
2. Callback queues event
3. Script reruns
4. Dispatcher processes queue
5. Handler updates state
6. UI renders with new state

*Reference*: [Dispatcher Pattern](../label_page/03_dispatcher_pattern.md)

---

## 4.5 Security Design

### 4.5.1 Authentication Flow

```
┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
│  User   │      │  Login  │      │  API    │      │   DB    │
└────┬────┘      └────┬────┘      └────┬────┘      └────┬────┘
     │                │                │                │
     │ Enter creds    │                │                │
     │───────────────▶│                │                │
     │                │ validate()     │                │
     │                │───────────────▶│                │
     │                │                │ Query doctor   │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │                │
     │                │                │ Argon2 verify  │
     │                │                │ (in memory)    │
     │                │◀───────────────│                │
     │                │                │                │
     │                │ Create session │                │
     │                │───────────────▶│                │
     │                │                │ Insert session │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │◀───────────────│                │                │
     │ Redirect       │                │                │
```

### 4.5.2 Security Measures

| Measure | Implementation |
|---------|----------------|
| Password hashing | Argon2id (memory-hard) |
| Session tokens | UUID v4 (random) |
| Session expiry | Configurable timeout |
| Input validation | Pydantic models |
| SQL injection | SQLAlchemy ORM (parameterized) |
| Path traversal | Path validation in API |

---

## 4.6 Deployment Design

### 4.6.1 Docker Architecture

```dockerfile
# Deployment options presented
1. Local development (streamlit run)
2. Docker container (single image)
3. Docker Compose (with volume mounts)
```

### 4.6.2 Configuration Management

| Config | Source | Purpose |
|--------|--------|---------|
| Database path | config.toml | Database location |
| Dataset path | config.toml | Image file location |
| Server port | Environment | Streamlit port |
| Log level | Environment | Debug output |

---

## Figures to Include

1. System architecture diagram (detailed)
2. Entity-relationship diagram
3. Page navigation flowchart
4. Labeling page wireframe/mockup
5. State hierarchy diagram
6. Event flow sequence diagram
7. Authentication sequence diagram
8. Deployment diagram
