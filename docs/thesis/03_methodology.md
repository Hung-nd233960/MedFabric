# Chapter 3: Methodology

## Presentation Outline

**Estimated Length**: 6-10 pages  
**Key Purpose**: Describe development approach, tools, and design rationale

---

## 3.1 Development Methodology

### 3.1.1 Agile-Inspired Approach

```
┌─────────────────────────────────────────────────────────────────┐
│                 DEVELOPMENT PROCESS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Requirements & Design (2 weeks)                       │
│  ├── Stakeholder interviews (radiologists, researchers)         │
│  ├── ASPECTS workflow analysis                                   │
│  ├── Technology selection                                        │
│  └── Initial architecture design                                 │
│                                                                  │
│  Phase 2: Core Development (6 weeks)                            │
│  ├── Sprint 1: Database & authentication                        │
│  ├── Sprint 2: Dashboard & dataset management                   │
│  ├── Sprint 3: Basic labeling interface                         │
│  └── Sprint 4: Dispatcher pattern implementation                │
│                                                                  │
│  Phase 3: Feature Completion (4 weeks)                          │
│  ├── Sprint 5: DICOM processing & windowing                     │
│  ├── Sprint 6: Validation & submission                          │
│  └── Sprint 7: Testing & documentation                          │
│                                                                  │
│  Phase 4: Evaluation & Refinement (2 weeks)                     │
│  ├── User testing with sample data                              │
│  ├── Bug fixes and improvements                                  │
│  └── Final documentation                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1.2 Iterative Development Rationale

| Principle | Application in This Project |
|-----------|----------------------------|
| **Incremental delivery** | Working prototype after each sprint |
| **User feedback** | Radiologist review of UI mockups |
| **Adaptability** | Dispatcher pattern emerged from initial challenges |
| **Continuous testing** | pytest suite developed alongside features |

---

## 3.2 Technology Stack Selection

### 3.2.1 Core Technologies

| Component | Technology | Version | Justification |
|-----------|------------|---------|---------------|
| **Language** | Python | 3.13+ | Medical imaging ecosystem, data science |
| **Web Framework** | Streamlit | 1.51+ | Rapid development, Python-native |
| **Database** | SQLite | 3.x | Zero-config, portable, sufficient for prototype |
| **ORM** | SQLAlchemy | 2.0+ | Type hints, async support, mature |
| **Validation** | Pydantic | 2.12+ | Data validation, API contracts |
| **Auth** | Argon2 | 21.3+ | Password hashing, security best practice |
| **DICOM** | PyDICOM | 2.4+ | De-facto Python DICOM library |
| **Image Processing** | Pillow, NumPy | Latest | Standard scientific Python |

### 3.2.2 Decision Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│              TECHNOLOGY SELECTION CRITERIA                       │
├─────────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Criteria    │ Weight   │ Streamlit│ Flask    │ React+Django    │
├─────────────┼──────────┼──────────┼──────────┼─────────────────┤
│ Dev Speed   │ 30%      │ ★★★★★   │ ★★★☆☆   │ ★★☆☆☆          │
│ Python Eco  │ 25%      │ ★★★★★   │ ★★★★☆   │ ★★★☆☆          │
│ Med Imaging │ 20%      │ ★★★★☆   │ ★★★☆☆   │ ★★★☆☆          │
│ Scalability │ 15%      │ ★★☆☆☆   │ ★★★★☆   │ ★★★★★          │
│ Maintainab. │ 10%      │ ★★★★☆   │ ★★★☆☆   │ ★★★☆☆          │
├─────────────┼──────────┼──────────┼──────────┼─────────────────┤
│ **Total**   │ 100%     │ **4.35** │ 3.45     │ 3.05            │
└─────────────┴──────────┴──────────┴──────────┴─────────────────┘
```

### 3.2.3 Trade-off Analysis

**Streamlit Advantages**:

- Single-language (Python) development
- Built-in session state
- Hot reload for rapid iteration
- Native pandas/numpy integration
- Free Streamlit Community hosting option

**Streamlit Limitations (and Mitigations)**:

| Limitation | Mitigation Strategy |
|------------|---------------------|
| Stateless execution | Event-driven dispatcher pattern |
| Limited customization | CSS/HTML injection where needed |
| No built-in auth | Custom login page with Argon2 |
| Single-threaded | Async where possible, efficient DB queries |

---

## 3.3 Requirements Analysis

### 3.3.1 Functional Requirements

| ID | Requirement | Priority | Implementation |
|----|-------------|----------|----------------|
| FR1 | User authentication | High | Login/Register pages |
| FR2 | Dataset browsing | High | Dashboard with tree view |
| FR3 | CT slice viewing | High | DICOM/JPEG loader |
| FR4 | Windowing adjustment | High | Number inputs for W/L |
| FR5 | Region selection | High | Segmented control |
| FR6 | ASPECTS scoring | High | Score input fields |
| FR7 | Multi-set labeling | Medium | Session navigation |
| FR8 | Validation feedback | Medium | Status DataFrames |
| FR9 | Batch submission | High | Submit with validation |
| FR10 | Set quality marking | Medium | Usability dropdown |

### 3.3.2 Non-Functional Requirements

| ID | Requirement | Target | Verification |
|----|-------------|--------|--------------|
| NFR1 | Response time | < 2s for image load | Manual testing |
| NFR2 | Session persistence | Survive browser refresh | Session state |
| NFR3 | Data integrity | No data loss on submit | Transaction tests |
| NFR4 | Usability | Minimal training needed | User feedback |
| NFR5 | Extensibility | Support new scoring systems | Modular design |

### 3.3.3 Use Case Derivation

```
┌─────────────────────────────────────────────────────────────────┐
│         STAKEHOLDER → REQUIREMENT → USE CASE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Radiologist                                                     │
│  ├── "I need to quickly review CT slices"                       │
│  │   └── FR3, FR4 → UC: View CT Slice                           │
│  ├── "I need to score brain regions"                            │
│  │   └── FR5, FR6 → UC: Enter ASPECTS Scores                    │
│  └── "I need to handle multiple cases efficiently"              │
│      └── FR7, FR9 → UC: Batch Labeling Session                  │
│                                                                  │
│  Researcher                                                      │
│  ├── "I need structured output for ML training"                 │
│  │   └── NFR3 → Database schema design                          │
│  └── "I need to manage datasets"                                │
│      └── FR2 → UC: Dataset Management                           │
│                                                                  │
│  System Administrator                                            │
│  └── "I need to manage user access"                             │
│      └── FR1 → UC: User Authentication                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3.4 Architecture Design Approach

### 3.4.1 Layered Architecture

**Rationale**: Separation of concerns, testability, maintainability

```
┌─────────────────────────────────────────────────────────────────┐
│                     ARCHITECTURE LAYERS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              PRESENTATION LAYER (Streamlit)                │  │
│  │  ├── Pages (login, register, dashboard, label, guide)     │  │
│  │  └── UI Components (render functions)                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              BUSINESS LOGIC LAYER                          │  │
│  │  ├── State Management (EventFlags, LabelingAppState)       │  │
│  │  ├── Dispatcher (event handlers)                           │  │
│  │  └── Image Processing (DICOM/JPEG)                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              DATA ACCESS LAYER                             │  │
│  │  ├── API Modules (CRUD operations)                         │  │
│  │  └── Pydantic Models (validation)                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              INFRASTRUCTURE LAYER                          │  │
│  │  ├── ORM Models (SQLAlchemy)                               │  │
│  │  ├── Database Engine                                        │  │
│  │  └── Configuration (TOML)                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4.2 Design Patterns Applied

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Event Queue** | EventFlags | Buffer events between reruns |
| **Dispatcher** | EVENT_DISPATCH dict | Route events to handlers |
| **Factory** | Key generation | Create unique widget keys |
| **Repository** | API modules | Abstract database access |
| **Data Transfer Object** | Pydantic models | Validate API contracts |
| **State** | LabelingAppState | Centralize mutable state |

---

## 3.5 Data Collection and Datasets

### 3.5.1 CQ500 Dataset

**Source**: Centre for Advanced Research in Imaging, Neurosciences, and Genomics (CARING), New Delhi

| Attribute | Value |
|-----------|-------|
| Total scans | 491 CT studies |
| Format | DICOM |
| Resolution | Variable (512×512 typical) |
| Slice count | 20-70 per study |
| Annotations | Expert reads available (ground truth) |

**Usage in This Project**:

- Development and testing
- User evaluation sessions
- Validation of output format

### 3.5.2 Data Handling Ethics

- Dataset is publicly available for research
- No patient identifiable information used
- Local storage only (no cloud upload)
- Complies with DICOM de-identification standards

---

## 3.6 Development Environment

### 3.6.1 Tools and Configuration

| Tool | Purpose | Configuration |
|------|---------|---------------|
| VS Code | IDE | Python extension, Pylance |
| Git | Version control | Feature branches |
| Docker | Containerization | Development and deployment |
| pytest | Testing | Fixtures, mocking |
| uv | Package manager | Fast dependency resolution |

### 3.6.2 Project Structure Rationale

```
MedFabric/
├── medfabric/          # Main application package
│   ├── api/            # Data access layer
│   ├── db/             # Database models
│   └── pages/          # UI layer
│       └── label_helper/   # Labeling page modules
├── tests/              # Test suite
├── data_sets/          # Image data (git-ignored)
├── docs/               # Documentation
└── config.toml         # Configuration
```

**Rationale**:

- Flat package structure for simplicity
- Separation of concerns via directories
- Tests mirror source structure
- Configuration externalized
