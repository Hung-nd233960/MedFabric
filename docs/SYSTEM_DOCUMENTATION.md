# MedFabric System Documentation

A comprehensive guide to the MedFabric CT Scan Labeling System architecture, components, and testing infrastructure.

---

## Table of Contents

- [MedFabric System Documentation](#medfabric-system-documentation)
  - [Table of Contents](#table-of-contents)
  - [1. System Overview](#1-system-overview)
    - [Primary Use Case: Ischemic Stroke Assessment](#primary-use-case-ischemic-stroke-assessment)
  - [2. Architecture Diagram](#2-architecture-diagram)
  - [3. Technology Stack](#3-technology-stack)
  - [4. Directory Structure](#4-directory-structure)
  - [5. Database Layer](#5-database-layer)
    - [5.1 ORM Models](#51-orm-models)
      - [Entity Relationship Diagram](#entity-relationship-diagram)
      - [Key ORM Classes](#key-orm-classes)
      - [Enumerations](#enumerations)
      - [Platform-Independent UUID Type](#platform-independent-uuid-type)
    - [5.2 Pydantic Models](#52-pydantic-models)
      - [Model Pattern](#model-pattern)
    - [5.3 Database Engine](#53-database-engine)
      - [Session Factory](#session-factory)
      - [SQLite Pragmas](#sqlite-pragmas)
  - [6. API Layer](#6-api-layer)
    - [6.1 Authentication \& Credentials](#61-authentication--credentials)
      - [Password Hashing](#password-hashing)
      - [Registration Flow](#registration-flow)
    - [6.2 Session Management](#62-session-management)
    - [6.3 Data Sets](#63-data-sets)
    - [6.4 Patients](#64-patients)
    - [6.5 Image Sets](#65-image-sets)
    - [6.6 Images](#66-images)
    - [6.7 Evaluations](#67-evaluations)
      - [Image Set Evaluation](#image-set-evaluation)
      - [Image Evaluation](#image-evaluation)
    - [6.8 Error Handling](#68-error-handling)
  - [7. Pages (UI Layer)](#7-pages-ui-layer)
    - [7.1 Login Page](#71-login-page)
    - [7.2 Registration Page](#72-registration-page)
    - [7.3 Dashboard Page](#73-dashboard-page)
    - [7.4 Label Page](#74-label-page)
      - [State Management](#state-management)
      - [Image Processing](#image-processing)
      - [UI Components](#ui-components)
    - [7.5 Guide Page](#75-guide-page)
  - [8. Configuration System](#8-configuration-system)
    - [Configuration File](#configuration-file)
    - [Configuration Loading](#configuration-loading)
  - [9. Testing Infrastructure](#9-testing-infrastructure)
    - [9.1 Test Configuration](#91-test-configuration)
    - [9.2 Test Categories](#92-test-categories)
    - [9.3 Test Design Patterns](#93-test-design-patterns)
      - [Happy Path Testing](#happy-path-testing)
      - [Error Condition Testing](#error-condition-testing)
      - [Parametrized Testing](#parametrized-testing)
      - [Boundary Testing](#boundary-testing)
      - [Region-Score Matrix Testing](#region-score-matrix-testing)
  - [10. Data Flow Diagrams](#10-data-flow-diagrams)
    - [Authentication Flow](#authentication-flow)
    - [Evaluation Flow](#evaluation-flow)
  - [11. Security Considerations](#11-security-considerations)
    - [Authentication Security](#authentication-security)
    - [Authorization](#authorization)
    - [Input Validation](#input-validation)
  - [12. Development Guidelines](#12-development-guidelines)
    - [Adding New Entities](#adding-new-entities)
    - [Error Handling Pattern](#error-handling-pattern)
    - [Running Tests](#running-tests)
  - [Appendix: Quick Reference](#appendix-quick-reference)
    - [Common API Patterns](#common-api-patterns)
    - [Session State Keys (Streamlit)](#session-state-keys-streamlit)
    - [Score Limits Reference](#score-limits-reference)

---

## 1. System Overview

**MedFabric** is a web-based CT scan labeling tool designed for medical professionals (doctors/radiologists) to evaluate and annotate medical imaging data. The system facilitates:

- **Multi-user authentication** with secure password hashing
- **Session-based access control** for tracking evaluations
- **Dataset management** for organizing medical imaging data
- **Patient record management** linked to image sets
- **Image set evaluation** with usability classifications
- **Individual image evaluation** with region-specific scoring (Basal Ganglia, Corona Radiata)
- **Progress tracking** for labeled vs. unlabeled data
- **DICOM and JPEG image format support** with windowing adjustments

### Primary Use Case: Ischemic Stroke Assessment

The system is specialized for evaluating CT scans for ischemic stroke indicators using a standardized scoring system:

| Region | Maximum Score | Description |
|--------|---------------|-------------|
| Basal Ganglia (Central) | 4 | Central basal ganglia assessment |
| Basal Ganglia (Cortex) | 3 | Cortical basal ganglia assessment |
| Corona Radiata | 3 | White matter pathway assessment |

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                        │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌───────┐ ┌───────────┐ │
│  │ Login   │ │ Register │ │ Dashboard │ │ Label │ │   Guide   │ │
│  │  Page   │ │   Page   │ │   Page    │ │ Page  │ │   Page    │ │
│  └────┬────┘ └────┬─────┘ └─────┬─────┘ └───┬───┘ └───────────┘ │
│       │           │             │           │                    │
│       └───────────┴─────────────┴───────────┘                    │
│                         │                                        │
│                    Streamlit Framework                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                          API LAYER                               │
│  ┌─────────────┐ ┌──────────┐ ┌────────────┐ ┌────────────────┐ │
│  │ credentials │ │ sessions │ │  data_sets │ │    patients    │ │
│  └─────────────┘ └──────────┘ └────────────┘ └────────────────┘ │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐   │
│  │ image_input │ │image_set_    │ │   image_evaluation_     │   │
│  │             │ │    input     │ │        input            │   │
│  └─────────────┘ └──────────────┘ └─────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     errors.py (Custom Exceptions)           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                       DATABASE LAYER                             │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   orm_model    │  │  pydantic_model  │  │     engine      │  │
│  │  (SQLAlchemy)  │  │   (Validation)   │  │  (Connection)   │  │
│  └────────────────┘  └──────────────────┘  └─────────────────┘  │
│                              │                                   │
│                    ┌─────────┴─────────┐                        │
│                    │    database.py    │                        │
│                    │  (Base & Config)  │                        │
│                    └───────────────────┘                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  SQLite/PostgreSQL │
                    │     Database       │
                    └───────────────────┘
```

---

## 3. Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Frontend** | Streamlit | 1.51.0+ | Web UI framework |
| **Backend** | Python | 3.13+ | Core application logic |
| **ORM** | SQLAlchemy | 2.0.44+ | Database abstraction |
| **Validation** | Pydantic | 2.12.5+ | Data validation & serialization |
| **Authentication** | Passlib + Argon2 | 1.7.4+ | Password hashing |
| **Database** | SQLite/PostgreSQL | - | Data persistence |
| **Medical Imaging** | PyDICOM | 3.0.1+ | DICOM file processing |
| **Image Processing** | OpenCV, Matplotlib | - | Image manipulation |
| **Testing** | Pytest | 9.0.1+ | Unit & integration testing |
| **Data Analysis** | Pandas | 2.3.3+ | Data manipulation |

---

## 4. Directory Structure

```
MedFabric/
├── medfabric/                    # Main application package
│   ├── main.py                   # Application entry point
│   ├── api/                      # Business logic layer
│   │   ├── config.py             # Configuration loading
│   │   ├── credentials.py        # Authentication logic
│   │   ├── data_sets.py          # Dataset CRUD operations
│   │   ├── errors.py             # Custom exception hierarchy
│   │   ├── get_evaluated_sets.py # Evaluation retrieval
│   │   ├── get_image_set.py      # Image set retrieval
│   │   ├── get_images.py         # Image retrieval
│   │   ├── image_evaluation_input.py    # Image evaluation logic
│   │   ├── image_input.py        # Image CRUD operations
│   │   ├── image_set_evaluation_input.py # Set evaluation logic
│   │   ├── image_set_input.py    # Image set CRUD operations
│   │   ├── patients.py           # Patient CRUD operations
│   │   ├── sessions.py           # Session management
│   │   └── utils/                # API utilities
│   │       ├── normalize_folder_path.py
│   │       └── image_set_path_updater.py
│   ├── db/                       # Database layer
│   │   ├── database.py           # Base configuration
│   │   ├── engine.py             # Session factory
│   │   ├── orm_model.py          # SQLAlchemy ORM models
│   │   ├── pydantic_model.py     # Pydantic validation models
│   │   └── utils/                # Database utilities
│   │       ├── delete_db.py
│   │       ├── init_db.py
│   │       └── reset_db.py
│   └── pages/                    # Streamlit UI pages
│       ├── login.py              # Login page
│       ├── register.py           # Registration page
│       ├── dashboard.py          # Main dashboard
│       ├── label.py              # Labeling interface
│       ├── guide.py              # User guide
│       ├── utils.py              # Page utilities
│       ├── dashboard_helper/     # Dashboard components
│       └── label_helper/         # Labeling components
│           ├── state_management.py
│           ├── session_initialization.py
│           ├── dispatcher.py
│           ├── image_loader/     # Image processing
│           └── ...
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest fixtures
│   ├── credential_test.py
│   ├── dataset_test.py
│   ├── image_evaluation_input_test.py
│   ├── image_input_test.py
│   ├── image_set_evaluation_input_test.py
│   ├── image_set_input_test.py
│   ├── patient_test.py
│   ├── sessions_test.py
│   └── valid_path_test.py
├── data_sets/                    # Medical imaging data
│   ├── cq500_dcm/                # DICOM datasets
│   ├── cq500_jpg/                # JPEG datasets
│   └── e_hospital/               # Hospital data
├── docs/                         # Documentation
│   ├── UserGuide.md
│   └── images/
├── config.toml                   # Application configuration
├── pyproject.toml                # Project dependencies
├── docker-compose.yaml           # Container orchestration
└── initialize.sh                 # Setup script
```

---

## 5. Database Layer

### 5.1 ORM Models

Located in `medfabric/db/orm_model.py`, the ORM layer defines the database schema using SQLAlchemy declarative mapping.

#### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   DataSet    │       │   Doctors    │       │   Session    │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ dataset_uuid │◄──┐   │ uuid (PK)    │◄──────│ doctor_uuid  │
│ name         │   │   │ username     │       │ session_uuid │
│ description  │   │   │ role         │       │ login_time   │
└──────────────┘   │   │ email        │       │ is_active    │
       │           │   │ password_hash│       └──────────────┘
       │           │   └──────────────┘              │
       ▼           │                                 │
┌──────────────┐   │                                 │
│   Patient    │   │                                 │
├──────────────┤   │                                 │
│ patient_uuid │◄──┼───────────────────────────────┐ │
│ patient_id   │   │                               │ │
│ dataset_uuid │───┘                               │ │
│ category     │                                   │ │
│ age          │                                   │ │
│ gender       │                                   │ │
└──────────────┘                                   │ │
       │                                           │ │
       ▼                                           │ │
┌──────────────┐       ┌──────────────────────┐    │ │
│   ImageSet   │       │ ImageSetEvaluation   │    │ │
├──────────────┤       ├──────────────────────┤    │ │
│ uuid (PK)    │◄──────│ image_set_uuid       │    │ │
│ index        │       │ doctor_uuid          │────┘ │
│ dataset_uuid │       │ session_uuid         │──────┘
│ image_set_   │       │ ischemic_low_quality │
│    name      │       │ image_set_usability  │
│ patient_uuid │       └──────────────────────┘
│ image_format │
│ num_images   │
│ folder_path  │
│ conflicted   │
└──────────────┘
       │
       ▼
┌──────────────┐       ┌──────────────────────┐
│    Image     │       │  ImageEvaluation     │
├──────────────┤       ├──────────────────────┤
│ uuid (PK)    │◄──────│ image_uuid           │
│ image_name   │       │ doctor_uuid          │
│ image_set_   │       │ session_uuid         │
│    uuid      │       │ region               │
│ slice_index  │       │ basal_score_*        │
└──────────────┘       │ corona_score_*       │
                       │ notes                │
                       └──────────────────────┘
```

#### Key ORM Classes

| Class | Table Name | Purpose | Key Fields |
|-------|------------|---------|------------|
| `DataSet` | `datasets` | Groups of medical images | `dataset_uuid`, `name`, `description` |
| `Patient` | `patients` | Patient records | `patient_uuid`, `patient_id`, `age`, `gender`, `category` |
| `Doctors` | `doctors` | User accounts | `uuid`, `username`, `password_hash`, `email`, `role` |
| `Session` | `sessions` | Login sessions | `session_uuid`, `doctor_uuid`, `login_time`, `is_active` |
| `ImageSet` | `image_sets` | CT scan session | `uuid`, `image_set_name`, `patient_uuid`, `num_images`, `folder_path` |
| `Image` | `images` | Individual slice | `uuid`, `image_name`, `image_set_uuid`, `slice_index` |
| `ImageSetEvaluation` | `image_set_evaluations` | Set-level assessment | `doctor_uuid`, `image_set_uuid`, `usability`, `ischemic_low_quality` |
| `ImageEvaluation` | `image_evaluations` | Slice-level scoring | `image_uuid`, `region`, `basal_score_*`, `corona_score_*` |

#### Enumerations

```python
class ImageFormat(Enum):
    DICOM = "DICOM"
    JPEG = "JPEG"
    PNG = "PNG"

class Region(Enum):
    None_ = "None"
    BasalCentral = "BasalGangliaCentral"
    BasalCortex = "BasalGangliaCortex"
    CoronaRadiata = "CoronaRadiata"

class ImageSetUsability(Enum):
    IschemicAssessable = "IschemicAssessable"
    HemorrhagicPresent = "HemorrhagicPresent"
    Indeterminate = "Indeterminate"
    Normal = "Normal"
    TrueIrrelevant = "TrueIrrelevant"

class Gender(Enum):
    Male = "Male"
    Female = "Female"
    Other = "Other"
```

#### Platform-Independent UUID Type

The `GUID` TypeDecorator provides cross-database UUID support:

```python
class GUID(TypeDecorator):
    """Platform-independent UUID type.
    
    - PostgreSQL: Uses native UUID type
    - SQLite: Stores as 36-character strings
    """
    impl = CHAR
    cache_ok = True
```

**Reasoning**: This abstraction allows the application to run on SQLite during development and PostgreSQL in production without code changes.

### 5.2 Pydantic Models

Located in `medfabric/db/pydantic_model.py`, these models provide:

- **Input validation** before database operations
- **Data serialization** for API responses
- **Type safety** with Python type hints

#### Model Pattern

Each entity has three model variants:

| Suffix | Purpose | Example |
|--------|---------|---------|
| `Base` | Common fields shared by all variants | `PatientBase` |
| `Create` | Input validation for creation | `PatientCreate` |
| `Read` | Response serialization | `PatientRead` |

```python
class PatientBase(OrmBase):
    patient_id: Annotated[str, StringConstraints(min_length=1)]
    dataset_uuid: UUID
    category: Optional[str] = None
    age: Annotated[int, Field(ge=0, le=130)] | None = None
    gender: Optional[Gender] = None

class PatientCreate(PatientBase):
    patient_uuid: Optional[UUID] = None  # Auto-generated if not provided

class PatientRead(PatientBase):
    patient_uuid: UUID  # Required in responses
```

**Reasoning**: This pattern separates concerns between input (flexible) and output (strict) data contracts while sharing common validation logic.

### 5.3 Database Engine

Located in `medfabric/db/engine.py` and `medfabric/db/database.py`.

#### Session Factory

```python
@st.cache_resource
def get_session_factory():
    """Cached session factory for Streamlit apps."""
    engine = create_engine(
        DATABASE_URL,
        echo=True,
        connect_args={"check_same_thread": False}  # SQLite thread safety
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
```

**Reasoning**:

- `@st.cache_resource`: Ensures single engine instance across Streamlit reruns
- `check_same_thread=False`: Required for SQLite in multi-threaded Streamlit
- `autoflush=False`: Explicit control over when changes are flushed

#### SQLite Pragmas

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")    # Write-Ahead Logging
    cursor.execute("PRAGMA foreign_keys=ON")     # Enforce FK constraints
```

**Reasoning**:

- `journal_mode=WAL`: Better concurrent read/write performance
- `foreign_keys=ON`: SQLite doesn't enforce FK by default

---

## 6. API Layer

The API layer (`medfabric/api/`) contains business logic separated from UI and database concerns.

### 6.1 Authentication & Credentials

Located in `medfabric/api/credentials.py`

#### Password Hashing

```python
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Reasoning**: Argon2 is the winner of the Password Hashing Competition and provides:

- Memory-hard algorithm (resistant to GPU attacks)
- Configurable time/memory cost
- Built-in salt management

#### Registration Flow

```python
def register_doctor(session, username, password, **kwargs) -> Doctors:
    # 1. Validate with Pydantic
    doctor_validator = DoctorCreate(
        username=username,
        password_hash=hash_password(password),
        email=kwargs.get("email"),
    )
    
    # 2. Create ORM object
    doctor = Doctors(
        uuid=uuid4(),
        username=doctor_validator.username,
        email=doctor_validator.email,
        password_hash=doctor_validator.password_hash,
    )
    
    # 3. Persist with error handling
    try:
        session.add(doctor)
        session.commit()
        return doctor
    except IntegrityError:
        session.rollback()
        raise DuplicateEntryError(f"Username '{username}' already exists.")
```

**Reasoning**:

- Pydantic validation catches input errors before database operations
- UUID generated at application level for predictability
- Rollback on integrity errors maintains transaction consistency

### 6.2 Session Management

Located in `medfabric/api/sessions.py`

Sessions track doctor login activity and are required for evaluations.

```python
def create_session(db_session, doctor_uuid) -> Session:
    """Create a new login session for a doctor."""
    if not doctor_exists(db_session, doctor_uuid):
        raise UserNotFoundError(f"Doctor UUID does not exist: {doctor_uuid}")
    
    new_sess = Session(doctor_uuid=doctor_uuid)
    db_session.add(new_sess)
    db_session.commit()
    return new_sess

def deactivate_session(db_session, session_uuid) -> None:
    """Mark a session as inactive (logout)."""
    sess = db_session.get(Session, session_uuid)
    if not sess:
        raise SessionNotFoundError(f"Session {session_uuid} does not exist")
    
    sess.is_active = False
    db_session.commit()
```

**Reasoning**:

- Sessions enable audit trails for evaluations
- Soft-delete (is_active=False) preserves history
- Session-doctor linking prevents unauthorized evaluations

### 6.3 Data Sets

Located in `medfabric/api/data_sets.py`

Datasets group related medical images (e.g., from the same study or hospital).

```python
def add_data_set(session, name, description=None, dataset_uuid=None) -> DataSet:
    # Validation
    if check_data_set_exists_by_name(session, name):
        raise DataSetAlreadyExistsError(f"Data set '{name}' already exists.")
    
    # UUID generation
    if dataset_uuid is None:
        dataset_uuid = uuid_lib.uuid4()
    
    data_set = DataSet(name=name, description=description, dataset_uuid=dataset_uuid)
    session.add(data_set)
    session.commit()
    return data_set
```

**Reasoning**:

- Name uniqueness prevents confusion
- Optional UUID allows deterministic imports
- Description provides context for dataset purpose

### 6.4 Patients

Located in `medfabric/api/patients.py`

Patients are scoped to datasets to allow duplicate patient IDs across different studies.

```python
def add_patient(session, patient_id, data_set_uuid, patient_uuid=None, 
                category=None, age=None, gender=None) -> Patient:
    # Dataset existence check
    if not check_data_set_exists_by_uuid(session, data_set_uuid):
        raise PatientInvalidDataError(f"Data set UUID does not exist: {data_set_uuid}")
    
    # Duplicate check within dataset
    if check_patient_exists_by_id(session, patient_id, data_set_uuid):
        raise PatientAlreadyExistsError(f"Patient with ID {patient_id} already exists.")
```

**Reasoning**:

- Dataset-scoped patient IDs allow data from multiple sources
- Composite unique constraint: `(patient_id, dataset_uuid)`
- Optional demographics (age, gender) for anonymized data

### 6.5 Image Sets

Located in `medfabric/api/image_set_input.py`

An ImageSet represents one CT scan session containing multiple slices.

```python
def add_image_set(session, image_set_name, num_images, image_format,
                  image_window_level, image_window_width, dataset_uuid,
                  patient_uuid, folder_path, ...) -> ImageSet:
    
    # Patient validation
    if not check_patient_exists_by_uuid(session, patient_uuid, dataset_uuid):
        raise PatientNotFoundError(f"Patient '{patient_uuid}' not found.")
    
    # DICOM windowing validation
    if image_format == ImageFormat.DICOM:
        if image_window_level is None or image_window_width is None:
            raise InvalidImageSetError(
                "DICOM image sets must have window level and window width defined."
            )
    else:
        # Non-DICOM formats don't use windowing
        image_window_level = None
        image_window_width = None
```

**Reasoning**:

- DICOM windowing parameters enable proper visualization
- `folder_path` allows file-based image storage
- `num_images` enables slice index validation

### 6.6 Images

Located in `medfabric/api/image_input.py`

Individual slices within an image set.

```python
def add_image(session, image_name, image_set_uuid, slice_index, 
              image_uuid=None) -> Image:
    
    # Image set existence
    image_set = get_image_set(session, image_set_uuid)
    if not image_set:
        raise ImageSetNotFoundError(f"Image set '{image_set_uuid}' does not exist.")
    
    # Slice index bounds
    if slice_index >= image_set.num_images:
        raise InvalidImageError(
            f"Slice index {slice_index} exceeds number of images ({image_set.num_images})."
        )
    
    # Duplicate checks
    if check_image_exists_by_set_and_index(session, image_set_uuid, slice_index):
        raise ImageAlreadyExistsError(f"Slice index '{slice_index}' already exists.")
```

**Reasoning**:

- Slice index validation prevents out-of-bounds errors
- Unique constraint on (image_set_uuid, slice_index)
- Image name uniqueness within sets prevents duplicate file references

### 6.7 Evaluations

#### Image Set Evaluation

Located in `medfabric/api/image_set_evaluation_input.py`

Overall assessment of a CT scan session.

```python
def add_evaluate_image_set(session, doctor_uuid, image_set_uuid, session_uuid,
                           image_set_usability, ischemic_low_quality=False) -> ImageSetEvaluation:
    
    # Authorization checks
    session_result = get_session(session, session_uuid)
    if session_result.doctor_uuid != doctor_uuid:
        raise SessionMismatchError("Session does not belong to the specified doctor.")
    if not session_result.is_active:
        raise SessionInactiveError("Session is not active.")
    
    # Logical validation
    if usability == ImageSetUsability.IschemicAssessable and not ischemic_low_quality:
        raise InvalidEvaluationError(
            "For 'IschemicAssessable' usability, 'ischemic_low_quality' must be True."
        )
```

**Reasoning**:

- Session validation ensures evaluations are attributed to logged-in users
- Usability classification guides workflow (assessable vs. skip)
- Ischemic flag tracks low-quality but still assessable cases

#### Image Evaluation

Located in `medfabric/api/image_evaluation_input.py`

Slice-level scoring with region-specific requirements.

```python
def add_evaluate_image(session, doctor_uuid, image_uuid, session_uuid,
                       region, basal_score_central_left=None, 
                       basal_score_central_right=None, ...):
    
    # Region-score consistency
    region_score_requirements(
        region,
        basal_score_central_left,
        basal_score_central_right,
        basal_score_cortex_left,
        basal_score_cortex_right,
        corona_score_left,
        corona_score_right,
    )
    
    # Score range validation
    validate_evaluation_scores(
        basal_score_central_left=basal_score_central_left,
        basal_score_central_right=basal_score_central_right,
        ...
    )
```

**Region-Score Requirements Matrix**:

| Region | Required Scores | Forbidden Scores |
|--------|-----------------|------------------|
| `None_` | None | All scores must be None |
| `BasalCentral` | central_left, central_right, cortex_left, cortex_right | corona_* |
| `BasalCortex` | cortex_left, cortex_right | central_*, corona_* |
| `CoronaRadiata` | corona_left, corona_right | basal_* |

**Reasoning**:

- Region selection determines which scores are clinically relevant
- Enforcing required/forbidden scores prevents invalid combinations
- Bilateral scoring (left/right) reflects anatomical symmetry

### 6.8 Error Handling

Located in `medfabric/api/errors.py`

Hierarchical exception classes enable granular error handling.

```python
class MedFabricError(Exception):
    """Base class for all MedFabric API errors."""

# Domain-specific hierarchies
class DataSetError(MedFabricError): ...
class InvalidDataSetError(DataSetError): ...
class DataSetNotFoundError(DataSetError): ...
class DataSetAlreadyExistsError(DataSetError): ...

class SessionError(MedFabricError): ...
class InvalidUUIDError(SessionError): ...
class SessionNotFoundError(SessionError): ...
class SessionInactiveError(SessionError): ...
class SessionMismatchError(SessionError): ...

class AuthError(MedFabricError): ...
class InvalidCredentialsError(AuthError): ...
class UserNotFoundError(AuthError): ...

class DatabaseError(MedFabricError): ...
class DuplicateEntryError(DatabaseError): ...
class ConstraintViolationError(DatabaseError): ...

class ImageSetError(MedFabricError): ...
class ImageError(MedFabricError): ...
class PatientError(MedFabricError): ...
class EvaluationError(MedFabricError): ...
```

**Reasoning**:

- Hierarchical exceptions allow catching at desired granularity
- Domain separation (Auth, Session, ImageSet) enables targeted handling
- Descriptive names improve error message clarity

---

## 7. Pages (UI Layer)

The UI layer uses Streamlit's page-based navigation system.

### 7.1 Login Page

Located in `medfabric/pages/login.py`

```python
st.set_page_config(page_title="Login", page_icon=":key:", layout="centered")

with st.form("login_form", clear_on_submit=True):
    st.title("Login to MedFabric")
    username_input = st.text_input("Username:")
    password_input = st.text_input("Password:", type="password")
    
    if st.form_submit_button("Login"):
        session = get_session_factory()()
        try:
            doctor = login_doctor(session, username_input, password_input)
            st.session_state.user = doctor.uuid
            st.session_state.user_session = create_session(session, doctor.uuid)
            st.switch_page("pages/dashboard.py")
        except UserNotFoundError:
            st.error("User not found.")
        except InvalidCredentialsError:
            st.error("Invalid password.")
```

**Reasoning**:

- Form prevents multiple submissions
- Session state persists authentication across page navigations
- Error-specific messages guide user actions

### 7.2 Registration Page

Located in `medfabric/pages/register.py`

```python
with st.form("registration_form"):
    username_input = st.text_input("Username:")
    password_input_1 = st.text_input("Password:", type="password")
    password_input_2 = st.text_input("Confirm Password:", type="password")
    
    if st.form_submit_button("Register"):
        if password_input_1 != password_input_2:
            st.error("Passwords do not match.")
        elif check_doctor_already_exists(session, username_input):
            st.error("Username already exists.")
        else:
            register_doctor(session, username_input, password_input_1)
            st.switch_page("pages/login.py")
```

**Reasoning**:

- Password confirmation prevents typos
- Pre-check for existing username provides immediate feedback
- Redirect to login after successful registration

### 7.3 Dashboard Page

Located in `medfabric/pages/dashboard.py`

The central hub showing evaluation progress and scan selection.

```python
@st.cache_data
def get_image_sets_with_evaluation_status(_db_session, doctor_uuid, dataset_uuid):
    """Retrieve DataFrame with evaluation status for each image set."""
    evaluated_ids = get_doctor_image_sets(_db_session, doctor_uuid)
    all_image_sets = get_all_image_sets_in_a_data_set(_db_session, dataset_uuid)
    
    df = pd.DataFrame([
        {
            "index": imgset.index,
            "uuid": imgset.uuid,
            "scan_id": imgset.image_set_name,
            "patient_id": get_patient_by_uuid(_db_session, imgset.patient_uuid).patient_id,
            "num_images": imgset.num_images,
            "evaluated": "✅ Evaluated" if imgset.uuid in evaluated_ids else "❌ Not Evaluated",
            "edit": False,
        }
        for imgset in all_image_sets
    ])
    return df, len(evaluated_ids), len(df), len(evaluated_ids) / len(df)
```

**Features**:

- Progress bar showing completion percentage
- Interactive data editor for scan selection
- Multi-select for batch evaluation

**Reasoning**:

- Caching prevents redundant database queries
- Visual indicators (✅/❌) provide quick status overview
- Batch selection improves workflow efficiency

### 7.4 Label Page

Located in `medfabric/pages/label.py`

The most complex page handling image display, navigation, and evaluation input.

#### State Management

```python
class EventType(Enum):
    PREV_SET = "prev_set"
    NEXT_SET = "next_set"
    JUMP_TO_SET = "jump_to_set"
    PREV_IMAGE = "prev_image"
    NEXT_IMAGE = "next_image"
    JUMP_TO_IMAGE = "jump_to_image"
    REGION_SELECTED = "region_selected"
    LOGOUT = "logout"
    ...
```

**Reasoning**:

- Event-driven architecture handles Streamlit's rerun model
- Enum-based events prevent string typos
- Flag system coordinates state changes

#### Image Processing

```python
# DICOM windowing
def dicom_image(file_path, window_level, window_width):
    ds = pydicom.dcmread(file_path)
    pixel_array = ds.pixel_array
    
    lower = window_level - window_width / 2
    upper = window_level + window_width / 2
    windowed = np.clip(pixel_array, lower, upper)
    normalized = ((windowed - lower) / (upper - lower) * 255).astype(np.uint8)
    
    return normalized

# JPEG processing
def jpg_image(file_path):
    return cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
```

**Reasoning**:

- DICOM windowing controls contrast/brightness for diagnostic viewing
- Separate handlers for format-specific processing
- Normalized output (0-255) for consistent display

#### UI Components

```python
def render_image_navigation_controls(next_key, prev_key, slider_key, num_images, current_index):
    with st.expander("Image Navigation", expanded=True):
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.button("Prev Image", key=prev_key, on_click=raise_flag, 
                      args=(EventType.PREV_IMAGE,))
        with col2:
            st.button("Next Image", key=next_key, on_click=raise_flag,
                      args=(EventType.NEXT_IMAGE,))
        with col3:
            st.slider("Jump to image", 1, num_images, current_index + 1,
                      key=slider_key, on_change=raise_flag,
                      args=(EventType.JUMP_TO_IMAGE, slider_key))
```

**Reasoning**:

- Button + slider combination for both sequential and random access
- Expanders organize related controls
- Callback-based updates maintain state consistency

### 7.5 Guide Page

Located in `medfabric/pages/guide.py`

```python
file_path = Path("docs/UserGuide.md").read_text(encoding="utf-8")

for line in file_path.split("\n"):
    if line.strip().startswith("![alt text]"):
        image_path = line[line.find("(") + 1 : line.find(")")]
        st.image(f"docs/{image_path}")
    else:
        st.markdown(line)
```

**Reasoning**:

- Markdown-based documentation for easy updates
- Image extraction enables embedded screenshots
- In-app guide reduces context switching

---

## 8. Configuration System

Located in `config.toml` and `medfabric/api/config.py`

### Configuration File

```toml
[criterion]
BasalCentral = 4
BasalCortex = 3
CoronaRadiata = 3

[path]
dataset = "./data_sets"

[image_adjustments]
default_brightness = 0
default_contrast = 1.0
default_filter = "None"
```

### Configuration Loading

```python
def load_config() -> dict[str, Any]:
    """Load the full config.toml as a dict."""
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)

# Derived constants
CRITERION = get_criterion()
BASAL_CENTRAL_MAX = CRITERION.get("BasalCentral", 4)
BASAL_CORTEX_MAX = CRITERION.get("BasalCortex", 3)
CORONA_MAX = CRITERION.get("CoronaRadiata", 3)

SCORE_LIMITS = {
    "basal_score_central_left": BASAL_CENTRAL_MAX,
    "basal_score_central_right": BASAL_CENTRAL_MAX,
    "basal_score_cortex_left": BASAL_CORTEX_MAX,
    "basal_score_cortex_right": BASAL_CORTEX_MAX,
    "corona_score_left": CORONA_MAX,
    "corona_score_right": CORONA_MAX,
}
```

**Reasoning**:

- TOML format is human-readable and Python-native (tomllib in 3.11+)
- Externalized configuration enables deployment customization
- Derived constants reduce runtime config lookups

---

## 9. Testing Infrastructure

### 9.1 Test Configuration

Located in `tests/conftest.py`

```python
@pytest.fixture
def db_session():
    """Create a fresh in-memory database per test."""
    url = "sqlite:///:memory:"
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()

@pytest.fixture
def dataset_uuid(db_session):
    """Create and return a dataset UUID for tests requiring a dataset."""
    dataset = DataSet(name="test_dataset")
    db_session.add(dataset)
    db_session.commit()
    return dataset.dataset_uuid
```

**Reasoning**:

- In-memory SQLite provides fast, isolated test execution
- Fresh database per test prevents state leakage
- Fixture dependencies (dataset_uuid → db_session) reduce boilerplate

### 9.2 Test Categories

| Test File | API Module | Coverage Focus |
|-----------|------------|----------------|
| `credential_test.py` | `credentials.py` | Password hashing, registration, login |
| `sessions_test.py` | `sessions.py` | Session creation, deactivation, listing |
| `dataset_test.py` | `data_sets.py` | Dataset CRUD, duplicate detection |
| `patient_test.py` | `patients.py` | Patient creation, validation |
| `image_set_input_test.py` | `image_set_input.py` | Image set creation, constraints |
| `image_input_test.py` | `image_input.py` | Image creation, slice indexing |
| `image_set_evaluation_input_test.py` | `image_set_evaluation_input.py` | Set evaluation logic |
| `image_evaluation_input_test.py` | `image_evaluation_input.py` | Region scoring, validation |
| `valid_path_test.py` | - | Path validation utilities |

### 9.3 Test Design Patterns

#### Happy Path Testing

```python
def test_register_doctor_success(db_session):
    doctor = register_doctor(db_session, "alice", "pw123", email="alice@example.com")
    assert doctor.username == "alice"
    assert doctor.email == "alice@example.com"
    assert doctor.password_hash != "pw123"  # should be hashed
    assert isinstance(doctor.uuid, uuid.UUID)
    
    # Verify persistence
    found = db_session.query(Doctors).filter_by(username="alice").first()
    assert found is not None
```

**Pattern**: Verify return value AND database state.

#### Error Condition Testing

```python
def test_register_doctor_duplicate_username(db_session):
    register_doctor(db_session, "bob", "pw123")
    with pytest.raises(DuplicateEntryError) as excinfo:
        register_doctor(db_session, "bob", "pw456")
    assert "already exists" in str(excinfo.value)
```

**Pattern**: Use `pytest.raises` context manager with assertion on error message.

#### Parametrized Testing

```python
@pytest.mark.parametrize(
    "category, age, gender",
    [
        ("oncology", None, None),
        (None, 45, None),
        (None, None, Gender.Male),
        ("cardiology", 60, Gender.Female),
    ],
)
def test_add_patient_success_variations(db_session, category, age, gender, dataset_uuid):
    pid = f"p_{category}_{age}_{gender}"
    patient = add_patient(db_session, pid, category=category, age=age, 
                          gender=gender, data_set_uuid=dataset_uuid)
    assert patient.category == category
    assert patient.age == age
    assert patient.gender == gender
```

**Pattern**: Test multiple input combinations with single test function.

#### Boundary Testing

```python
def test_add_image_slice_index_too_large(db_session, image_set):
    with pytest.raises(InvalidImageError):
        add_image(db_session, "img1", image_set.uuid, 99)  # image_set.num_images = 3

def test_add_image_negative_slice_index(db_session, image_set):
    with pytest.raises(InvalidImageError):
        add_image(db_session, "img1", image_set.uuid, -1)
```

**Pattern**: Test boundaries (max+1, negative) for numeric constraints.

#### Region-Score Matrix Testing

```python
@pytest.mark.parametrize(
    "region,scores",
    [
        (Region.None_, dict.fromkeys([...], None)),  # All None for None_ region
        (Region.BasalCentral, {"basal_score_central_left": 1, ...}),  # Required present
        (Region.BasalCortex, {"basal_score_cortex_left": 1, ...}),
        (Region.CoronaRadiata, {"corona_score_left": 1, ...}),
    ],
)
def test_success_cases_region_enforcement(region, scores):
    region_score_requirements(region, **scores)  # Should not raise

@pytest.mark.parametrize(
    "region,scores",
    [
        (Region.None_, {"basal_score_central_left": 1, ...}),  # Forbidden present
        (Region.BasalCentral, {"basal_score_central_right": None, ...}),  # Missing required
    ],
)
def test_failure_cases_region_enforcement(region, scores):
    with pytest.raises(InvalidEvaluationError):
        region_score_requirements(region, **scores)
```

**Pattern**: Separate success and failure cases for complex business rules.

---

## 10. Data Flow Diagrams

### Authentication Flow

```
┌──────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────┐
│ User │────▶│ Login Page  │────▶│ credentials │────▶│ Doctors  │
│      │     │             │     │  .login_    │     │  table   │
│      │     │ (Streamlit) │     │  doctor()   │     │          │
└──────┘     └─────────────┘     └──────┬──────┘     └──────────┘
                                        │
                                        ▼
                                 ┌─────────────┐
                                 │ sessions.   │
                                 │ create_     │
                                 │ session()   │
                                 └──────┬──────┘
                                        │
                                        ▼
                                 ┌─────────────┐     ┌──────────┐
                                 │ Session     │────▶│ Sessions │
                                 │ State       │     │  table   │
                                 │ (st.session)│     │          │
                                 └─────────────┘     └──────────┘
```

### Evaluation Flow

```
┌────────────┐     ┌────────────┐     ┌──────────────────┐
│ Dashboard  │────▶│ Label Page │────▶│ Session          │
│ (select    │     │ (display   │     │ Validation       │
│  scans)    │     │  images)   │     │ (doctor match,   │
└────────────┘     └─────┬──────┘     │  active check)   │
                         │            └────────┬─────────┘
                         │                     │
                         ▼                     ▼
                  ┌─────────────┐     ┌──────────────────┐
                  │ Image Set   │────▶│ Set Evaluation   │
                  │ Usability   │     │ (usability,      │
                  │ Selection   │     │  ischemic flag)  │
                  └─────────────┘     └────────┬─────────┘
                         │                     │
                         ▼                     ▼
                  ┌─────────────┐     ┌──────────────────┐
                  │ Region      │────▶│ Image Evaluation │
                  │ Selection & │     │ (scores by       │
                  │ Scoring     │     │  region)         │
                  └─────────────┘     └──────────────────┘
```

---

## 11. Security Considerations

### Authentication Security

| Aspect | Implementation | Rationale |
|--------|----------------|-----------|
| **Password Hashing** | Argon2 via Passlib | Memory-hard, GPU-resistant |
| **Password Storage** | Hash only, no plain text | Standard security practice |
| **Session Tokens** | UUID4 (122-bit random) | Cryptographically secure |
| **Session Expiry** | `is_active` flag | Manual logout + server control |

### Authorization

| Check | Implementation | Location |
|-------|----------------|----------|
| Session-Doctor match | `session.doctor_uuid == doctor_uuid` | Evaluation APIs |
| Session active | `session.is_active == True` | Evaluation APIs |
| Entity existence | Pre-operation checks | All CRUD operations |

### Input Validation

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| Pydantic Models | Type annotations, Field constraints | Structural validation |
| API Functions | Business logic checks | Domain rule enforcement |
| Database Constraints | UNIQUE, FK, CHECK | Data integrity |

---

## 12. Development Guidelines

### Adding New Entities

1. **ORM Model** (`medfabric/db/orm_model.py`):

   ```python
   class NewEntity(Base):
       __tablename__ = "new_entities"
       uuid: Mapped[uuid_lib.UUID] = mapped_column(GUID(), primary_key=True)
       # ... fields ...
   ```

2. **Pydantic Models** (`medfabric/db/pydantic_model.py`):

   ```python
   class NewEntityBase(OrmBase): ...
   class NewEntityCreate(NewEntityBase): ...
   class NewEntityRead(NewEntityBase): ...
   ```

3. **API Module** (`medfabric/api/new_entity.py`):

   ```python
   def add_new_entity(session, ...) -> NewEntity:
       # Validation
       # Creation
       # Error handling
   ```

4. **Tests** (`tests/new_entity_test.py`):

   ```python
   def test_add_new_entity_success(db_session): ...
   def test_add_new_entity_duplicate(db_session): ...
   def test_add_new_entity_invalid(db_session): ...
   ```

### Error Handling Pattern

```python
def my_api_function(session, ...):
    try:
        # 1. Pydantic validation
        validated = MyModel(...)
    except ValidationError as exc:
        raise InvalidMyEntityError(f"Validation failed: {exc}") from exc
    
    # 2. Business logic checks
    if not some_exists_check(session, validated.foreign_id):
        raise ForeignEntityNotFoundError(...)
    
    try:
        # 3. Database operation
        entity = MyEntity(...)
        session.add(entity)
        session.commit()
        return entity
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateEntryError(...) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DatabaseError(...) from exc
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/credential_test.py

# Run with verbose output
pytest -v tests/

# Run with coverage
pytest --cov=medfabric tests/
```

---

## Appendix: Quick Reference

### Common API Patterns

| Operation | Function | Returns |
|-----------|----------|---------|
| Create | `add_*()` | ORM object |
| Read One | `get_*()` | Pydantic Read model or None |
| Read Many | `get_all_*()` | List of Pydantic Read models |
| Check Exists | `check_*_exists()` | bool |
| Update | Direct ORM modification | - |
| Delete | `deactivate_*()` or ORM delete | - |

### Session State Keys (Streamlit)

| Key | Type | Purpose |
|-----|------|---------|
| `user` | UUID | Logged-in doctor's UUID |
| `user_session` | SessionRead | Active login session |
| `selected_scans` | List[UUID] | Scans selected for evaluation |
| `all_sets_df` | DataFrame | Dashboard data |
| `dashboard_initialized` | bool | Initialization flag |

### Score Limits Reference

| Score Field | Max Value | Region(s) |
|-------------|-----------|-----------|
| `basal_score_central_*` | 4 | BasalCentral |
| `basal_score_cortex_*` | 3 | BasalCentral, BasalCortex |
| `corona_score_*` | 3 | CoronaRadiata |
