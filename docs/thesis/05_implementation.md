# Chapter 5: Implementation

## Presentation Outline

**Estimated Length**: 12-18 pages  
**Key Purpose**: Present technical implementation details with code examples

---

## 5.1 Project Structure

### 5.1.1 Directory Layout

```
MedFabric/
├── medfabric/                    # Main application package
│   ├── __init__.py
│   ├── main.py                   # Entry point, navigation
│   │
│   ├── api/                      # Data access layer
│   │   ├── config.py             # Configuration loading
│   │   ├── credentials.py        # Password hashing, validation
│   │   ├── sessions.py           # Session CRUD
│   │   ├── data_sets.py          # Dataset CRUD
│   │   ├── patients.py           # Patient CRUD
│   │   ├── image_set_input.py    # ImageSet CRUD
│   │   ├── image_input.py        # Image CRUD
│   │   ├── image_set_evaluation_input.py
│   │   ├── image_evaluation_input.py
│   │   └── errors.py             # Custom exceptions
│   │
│   ├── db/                       # Database layer
│   │   ├── engine.py             # SQLAlchemy engine
│   │   ├── orm_model.py          # ORM table definitions
│   │   └── pydantic_model.py     # Validation schemas
│   │
│   └── pages/                    # Presentation layer
│       ├── login.py
│       ├── register.py
│       ├── dashboard.py
│       ├── label.py              # Main labeling page
│       ├── guide.py
│       │
│       └── label_helper/         # Labeling support modules
│           ├── state_management.py
│           ├── dispatcher.py
│           ├── session_initialization.py
│           ├── image_session_status.py
│           ├── image_set_session_status.py
│           ├── submit_results.py
│           ├── column_config.py
│           │
│           └── image_loader/
│               ├── dicom_processing.py
│               ├── jpg_processing.py
│               └── image_helper.py
│
├── tests/                        # Test suite
├── data_sets/                    # Image data
├── docs/                         # Documentation
├── config.toml                   # Configuration file
├── pyproject.toml                # Dependencies
└── docker-compose.yaml           # Containerization
```

### 5.1.2 Module Responsibilities

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `label.py` | ~760 | Main labeling page, UI rendering |
| `dispatcher.py` | ~690 | Event handlers, dispatch table |
| `state_management.py` | ~200 | State containers, key generation |
| `orm_model.py` | ~250 | Database table definitions |
| `pydantic_model.py` | ~300 | API validation schemas |
| `dicom_processing.py` | ~150 | DICOM loading and windowing |

---

## 5.2 Database Implementation

### 5.2.1 ORM Model Definition

**Present code example**:

```python
# medfabric/db/orm_model.py

class ImageSet(Base):
    """CT scan set with multiple slices."""
    __tablename__ = "ImageSet"
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    index = Column(Integer, nullable=True, autoincrement=True)
    image_set_name = Column(String, nullable=False)
    folder_path = Column(String, nullable=False)
    num_images = Column(Integer, nullable=False)
    
    # DICOM windowing defaults
    image_window_width = Column(Integer, nullable=True)
    image_window_level = Column(Integer, nullable=True)
    
    # Relationships
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey("Patient.uuid"))
    patient = relationship("Patient", back_populates="image_sets")
    images = relationship("Image", back_populates="image_set")
    
    # Format enum
    image_format = Column(Enum(ImageFormat), default=ImageFormat.DICOM)
```

### 5.2.2 Pydantic Schema

```python
# medfabric/db/pydantic_model.py

class ImageSetRead(BaseModel):
    """Schema for reading ImageSet from database."""
    uuid: uuid_lib.UUID
    index: Optional[int]
    image_set_name: str
    folder_path: str
    num_images: int
    image_window_width: Optional[int]
    image_window_level: Optional[int]
    image_format: ImageFormat
    
    # Nested relationships
    patient: Optional["PatientRead"]
    images: List["ImageRead"]
    
    model_config = ConfigDict(from_attributes=True)
```

### 5.2.3 Database Engine

```python
# medfabric/db/engine.py

def get_session_factory() -> Callable[[], DbSession]:
    """Create SQLAlchemy session factory."""
    config = get_paths()
    db_path = config.get("database", "./medfabric.db")
    
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        pool_pre_ping=True,
    )
    
    Base.metadata.create_all(engine)
    
    return sessionmaker(bind=engine)
```

---

## 5.3 API Layer Implementation

### 5.3.1 CRUD Pattern

**Present consistent API pattern**:

```python
# medfabric/api/image_set_input.py

def get_image_set(
    db_session: DbSession,
    image_set_uuid: uuid_lib.UUID,
) -> Optional[ImageSetRead]:
    """
    Retrieve an ImageSet by UUID.
    
    Args:
        db_session: SQLAlchemy session
        image_set_uuid: UUID of ImageSet
        
    Returns:
        ImageSetRead or None if not found
    """
    result = db_session.execute(
        select(ImageSet)
        .where(ImageSet.uuid == image_set_uuid)
        .options(
            selectinload(ImageSet.images),
            selectinload(ImageSet.patient),
        )
    )
    image_set = result.scalar_one_or_none()
    
    if image_set is None:
        return None
    
    return ImageSetRead.model_validate(image_set)
```

### 5.3.2 Authentication API

```python
# medfabric/api/credentials.py

def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return ph.hash(password)


def validate_password(
    db_session: DbSession,
    username: str,
    password: str,
) -> Optional[SessionRead]:
    """
    Validate credentials and create session.
    
    Returns:
        SessionRead if valid, None otherwise
    """
    # Query doctor
    doctor = db_session.execute(
        select(Doctors).where(Doctors.username == username)
    ).scalar_one_or_none()
    
    if doctor is None:
        return None
    
    # Verify password
    try:
        ph.verify(doctor.password, password)
    except VerifyMismatchError:
        return None
    
    # Create session
    session = Session(doctor_uuid=doctor.uuid)
    db_session.add(session)
    db_session.commit()
    
    return SessionRead.model_validate(session)
```

---

## 5.4 State Management Implementation

### 5.4.1 EventFlags Class

```python
# medfabric/pages/label_helper/state_management.py

class EventFlags:
    """
    Queue-based event buffer for Streamlit.
    
    Survives script reruns by storing queue in session state.
    """
    
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
    
    def raise_flag(self, event: Event) -> None:
        """Add event to queue."""
        self._queue.put(event)
    
    def get(self) -> Optional[Event]:
        """Get next event (non-blocking)."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
    
    def is_empty(self) -> bool:
        return self._queue.empty()
```

### 5.4.2 LabelingAppState Dataclass

```python
@dataclass
class LabelingAppState:
    """Central state container for labeling session."""
    
    # Session data
    labeling_session: List[ImageSetEvaluationSession]
    doctor_id: uuid_lib.UUID
    login_session: uuid_lib.UUID
    
    # Navigation
    session_index: int = 0
    
    # Display settings
    brightness: int = 0
    contrast: float = 1.0
    filter_type: FilterType = FilterType.NONE
    
    # Validation tracking
    set_status_df: pd.DataFrame = field(
        default_factory=create_set_status_dataframe
    )
    
    @property
    def current_session(self) -> ImageSetEvaluationSession:
        """Get currently active image set session."""
        return self.labeling_session[self.session_index]
```

### 5.4.3 Key Generation

```python
class EnumKeyManager:
    """Generate unique, parseable widget keys."""
    
    def make(
        self,
        element_type: UIElementType,
        event_type: EventType,
        optional_uuid: Optional[uuid_lib.UUID] = None,
    ) -> str:
        """
        Generate widget key.
        
        Format: {element}_{event}_{uuid?}
        Example: BUTTON_NEXT_IMAGE_550e8400-...
        """
        parts = [element_type.value, event_type.value]
        if optional_uuid:
            parts.append(str(optional_uuid))
        return "_".join(parts)
```

---

## 5.5 Dispatcher Implementation

### 5.5.1 Event Dispatch Table

```python
# medfabric/pages/label_helper/dispatcher.py

EVENT_DISPATCH: Dict[EventType, Callable] = {
    # Navigation
    EventType.NEXT_IMAGE: handle_next_image,
    EventType.PREV_IMAGE: handle_prev_image,
    EventType.JUMP_TO_IMAGE: handle_jump_to_image,
    EventType.NEXT_SET: handle_next_set,
    EventType.PREV_SET: handle_prev_set,
    EventType.JUMP_TO_SET: handle_jump_to_set,
    
    # Display
    EventType.WINDOWING_WIDTH_CHANGED: handle_windowing_width_changed,
    EventType.WINDOWING_LEVEL_CHANGED: handle_windowing_level_changed,
    EventType.RESET_WINDOWING: handle_reset_windowing,
    
    # Scoring
    EventType.REGION_SELECTED: handle_region_selected,
    EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED: handle_basal_cortex_left,
    EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED: handle_basal_cortex_right,
    EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED: handle_basal_central_left,
    EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED: handle_basal_central_right,
    EventType.CORONA_LEFT_SCORE_CHANGED: handle_corona_left,
    EventType.CORONA_RIGHT_SCORE_CHANGED: handle_corona_right,
    
    # Set marking
    EventType.MARK_LOW_QUALITY_CHANGED: handle_mark_low_quality,
    EventType.MARK_IRRELEVANT_CHANGED: handle_mark_irrelevant,
    EventType.NOTES_CHANGED: handle_notes_changed,
    
    # Session control
    EventType.SUBMIT: handle_submit,
    EventType.LOGOUT: handle_logout,
}
```

### 5.5.2 Flag Listener

```python
def flag_listener(
    flags: EventFlags,
    state: LabelingAppState,
) -> None:
    """
    Process all queued events.
    
    Called at start of each script execution.
    """
    while not flags.is_empty():
        event = flags.get()
        
        if event is None:
            break
        
        # Resolve HalfEvent to CompletedEvent
        if isinstance(event, HalfEvent):
            widget_value = st.session_state.get(event.key)
            event = CompletedEvent(
                event_type=event.event_type,
                key=event.key,
                value=widget_value,
            )
        
        # Dispatch to handler
        handler = EVENT_DISPATCH.get(event.event_type)
        if handler:
            handler(state, event.value)
        else:
            logging.warning(f"No handler for {event.event_type}")
```

### 5.5.3 Example Handler

```python
def handle_region_selected(
    state: LabelingAppState,
    value: str,
) -> None:
    """Handle region selection change."""
    current_session = state.current_session
    current_image = current_session.current_image_session
    
    new_region = Region(value) if value else Region.None_
    old_region = current_image.region
    
    if new_region == Region.None_:
        # Clear scores and remove from tracking
        reset_score_fields(current_image)
        current_session.slice_status_df = delete_slice(
            current_session.slice_status_df,
            current_image.image_uuid,
        )
    elif old_region == Region.None_:
        # First region assignment
        current_image.region = new_region
        current_session.slice_status_df = add_slice(
            current_session.slice_status_df,
            current_session.current_index,
            current_image.image_uuid,
            new_region,
        )
    else:
        # Region change - reset scores
        reset_score_fields(current_image)
        current_image.region = new_region
        current_session.slice_status_df = modify_region(
            current_session.slice_status_df,
            current_image.image_uuid,
            new_region,
        )
    
    # Revalidate set
    validate_and_update_set_status(state, current_session)
```

---

## 5.6 Image Processing Implementation

### 5.6.1 DICOM Loading

```python
# medfabric/pages/label_helper/image_loader/dicom_processing.py

def load_raw_dicom_image(file_path: Path) -> Tuple[FileDataset, np.ndarray]:
    """
    Load DICOM and convert to Hounsfield Units.
    
    HU = pixel_value * RescaleSlope + RescaleIntercept
    """
    dcm_obj = pydicom.dcmread(file_path)
    img = dcm_obj.pixel_array.astype(np.int16)
    
    slope = getattr(dcm_obj, "RescaleSlope", 1)
    intercept = getattr(dcm_obj, "RescaleIntercept", 0)
    hu = img * slope + intercept
    
    return dcm_obj, hu


def apply_window(
    img: np.ndarray,
    center: float,
    width: float,
) -> Image.Image:
    """
    Apply CT windowing.
    
    Output = ((clipped - low) / (high - low)) * 255
    """
    low = center - width // 2
    high = center + width // 2
    windowed = np.clip(img, low, high)
    windowed = ((windowed - low) / (high - low) * 255).astype(np.uint8)
    return Image.fromarray(windowed)
```

### 5.6.2 Windowing Visualization

```
Input HU values:  [-1000 -------- 0 -------- +1000]
                          ↓
Window (center=40, width=80):
                  [    0 -- 40 -- 80    ]
                         ↓
Output grayscale:   [0 ---- 128 ---- 255]
```

---

## 5.7 UI Implementation

### 5.7.1 Main Page Structure

```python
# medfabric/pages/label.py

# Page configuration
st.set_page_config(
    page_title="Labeling Phase",
    page_icon=":pencil2:",
    layout="wide",
)

# Session validation
app = st.session_state
if "app_state" not in app:
    # Initialize session
    app.app_state = LabelingAppState(...)

# Event processing
initial_setup()
flag_listener(app.label_flag, app.app_state)

# Three-column layout
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    render_logout_button(...)
    img = dicom_image(...)  # or jpg_image
    render_image(img, ...)

with col2:
    render_image_navigation_controls(...)
    render_dicom_windowing_controls(...)
    render_labeling_column(...)

with col3:
    # Tab-based information display
    tab1, tab2 = st.tabs(["Set Information", "All Sets Status"])
    with tab1:
        render_set_navigation(...)
        render_status_table(...)
    with tab2:
        render_set_annotations(...)
        render_submit_button(...)
```

### 5.7.2 Callback Pattern

```python
def raise_flag(
    flags: EventFlags,
    event_type: EventType,
    key: Optional[str] = None,
) -> None:
    """
    Callback function for widget events.
    
    Queues event for processing after rerun.
    """
    if key:
        event = HalfEvent(event_type=event_type, key=key)
    else:
        event = CompletedEvent(event_type=event_type, key="", value=None)
    
    flags.raise_flag(event)


# Usage in widget
st.button(
    "Next ►",
    key=next_key,
    on_click=raise_flag,
    args=(app.label_flag, EventType.NEXT_IMAGE),
)
```

---

## 5.8 Submission Implementation

### 5.8.1 Submit Flow

```python
# medfabric/pages/label_helper/submit_results.py

def submit_results(
    state: LabelingAppState,
    db_session: DbSession,
) -> bool:
    """
    Submit all evaluations to database.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        for session in state.labeling_session:
            # Create set-level evaluation
            set_eval = ImageSetEvaluationCreate(
                doctor_uuid=state.doctor_id,
                image_set_uuid=session.uuid,
                session_uuid=state.login_session,
                image_set_usability=session.image_set_usability,
                low_quality=session.low_quality,
                notes=session.notes,
            )
            set_eval_uuid = create_image_set_evaluation(db_session, set_eval)
            
            # Create image-level evaluations
            for img_session in session.images_sessions:
                if img_session.region != Region.None_:
                    img_eval = ImageEvaluationCreate(
                        image_set_evaluation_uuid=set_eval_uuid,
                        image_uuid=img_session.image_uuid,
                        region=img_session.region,
                        basal_score_cortex_left=img_session.basal_score_cortex_left,
                        basal_score_cortex_right=img_session.basal_score_cortex_right,
                        # ... other scores
                    )
                    create_image_evaluation(db_session, img_eval)
        
        db_session.commit()
        return True
        
    except Exception as e:
        db_session.rollback()
        logging.error(f"Submit failed: {e}")
        return False
```

---

## 5.9 Configuration Implementation

### 5.9.1 TOML Configuration

```toml
# config.toml

[PATHS]
database = "./medfabric.db"
dataset = "./data_sets"

[WINDOWING]
default_width = 80
default_level = 40

[SESSION]
timeout_minutes = 60
```

### 5.9.2 Configuration Loading

```python
# medfabric/api/config.py

def get_paths() -> Dict[str, str]:
    """Load paths from config.toml."""
    config_path = Path(__file__).parent.parent.parent / "config.toml"
    
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    
    return config.get("PATHS", {})
```

---

## Code Statistics

| Metric | Value |
|--------|-------|
| Total Python files | ~35 |
| Total lines of code | ~5,000 |
| Test files | 9 |
| Test coverage | ~60% (API layer) |
| Documentation files | 15+ |

---

## Key Implementation Challenges

### Challenge 1: Streamlit State Persistence

**Problem**: Variables reset on every rerun  
**Solution**: EventFlags queue in session_state

### Challenge 2: Widget Key Conflicts

**Problem**: Dynamic UIs cause key collisions  
**Solution**: EnumKeyManager with UUID suffixes

### Challenge 3: Score Field Synchronization

**Problem**: Scores must persist during navigation  
**Solution**: Dataclass-based session with explicit updates

### Challenge 4: Validation Cascading

**Problem**: Slice changes must update set status  
**Solution**: Helper functions that propagate changes
