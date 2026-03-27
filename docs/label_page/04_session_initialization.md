# Session Initialization

## Overview

Session initialization transforms database records into in-memory data structures optimized for the labeling workflow. This happens once when the user first enters the labeling page.

---

## Data Structures

### ImageEvaluationSession

Represents a single CT slice with its evaluation data.

```python
@dataclass
class ImageEvaluationSession:
    """In-memory representation of a single image evaluation."""
    
    # Identity
    image_uuid: uuid_lib.UUID
    image_name: str
    image_path: Path
    slice_index: int
    
    # Evaluation data (mutable during labeling)
    region: Region = Region.None_
    basal_score_central_left: Optional[int] = None
    basal_score_central_right: Optional[int] = None
    basal_score_cortex_left: Optional[int] = None
    basal_score_cortex_right: Optional[int] = None
    corona_score_left: Optional[int] = None
    corona_score_right: Optional[int] = None
    notes: Optional[str] = None
    
    # Metadata (optional)
    image_metadata: Optional[Dict[str, str]] = None
```

### ImageSetEvaluationSession

Represents a complete CT scan session with all its slices.

```python
@dataclass
class ImageSetEvaluationSession:
    """In-memory representation of an image set evaluation."""
    
    # Identity
    set_index: int                          # Database index
    uuid: uuid_lib.UUID                     # Unique identifier
    image_set_name: str                     # Display name
    patient_id: Optional[str]               # Patient reference
    
    # Image data
    num_images: int                         # Total slices
    folder_path: Path                       # File system path
    images_sessions: List[ImageEvaluationSession]  # All slices
    
    # DICOM windowing
    window_width_default: Optional[int]     # From database
    window_level_default: Optional[int]
    window_width_current: Optional[int]     # User-adjusted
    window_level_current: Optional[int]
    
    # Set-level evaluation
    notes: Optional[str] = None
    low_quality: bool = False
    icd_code: Optional[str] = None
    description: Optional[str] = None
    image_set_usability: ImageSetUsability = ImageSetUsability.IschemicAssessable
    image_set_format: ImageFormat = ImageFormat.DICOM
    
    # Navigation state
    current_index: int = 0                  # Currently viewed slice
    
    # Validation state
    slice_status_df: pd.DataFrame = field(default_factory=initialize_slice_df)
    consecutive_slices: bool = False
    
    # UI state
    patient_information: Optional[pd.DataFrame] = None
    render_score_box_mode: bool = True      # Enable/disable scoring
    render_valid_message: bool = False      # Show validation success
    
    @property
    def current_image_session(self) -> ImageEvaluationSession:
        """Get currently active image session."""
        return self.images_sessions[self.current_index]
```

---

## Initialization Flow

### Sequence Diagram

```
┌──────────┐     ┌──────────────┐     ┌────────────┐     ┌─────────────┐
│  label.py│     │session_init  │     │   API      │     │  Database   │
└────┬─────┘     └──────┬───────┘     └─────┬──────┘     └──────┬──────┘
     │                  │                   │                   │
     │ selected_scans   │                   │                   │
     │ (from dashboard) │                   │                   │
     │──────────────────▶                   │                   │
     │                  │                   │                   │
     │                  │ For each UUID:    │                   │
     │                  │───────────────────▶                   │
     │                  │                   │                   │
     │                  │                   │ get_image_set()   │
     │                  │                   │──────────────────▶│
     │                  │                   │                   │
     │                  │                   │◀──────────────────│
     │                  │                   │ ImageSetRead      │
     │                  │◀───────────────────                   │
     │                  │                   │                   │
     │                  │ Build ImageSetEvaluationSession       │
     │                  │ Build ImageEvaluationSession (each)   │
     │                  │                   │                   │
     │◀─────────────────│                   │                   │
     │ List[ImageSet    │                   │                   │
     │   EvaluationSess]│                   │                   │
     │                  │                   │                   │
     │ Create           │                   │                   │
     │ LabelingAppState │                   │                   │
     │                  │                   │                   │
```

### Code Flow

```python
# In label.py - Main initialization
if "app_state" not in app:
    db_session = get_session_factory()()
    
    app.app_state = LabelingAppState(
        labeling_session=initialize_evaluation_session(
            db_session=db_session,
            image_set_uuids=selected_scans,  # From dashboard selection
        ),
        doctor_id=doctor_uuid,
        login_session=user_session.session_uuid,
    )
    
    db_session.close()
    
    # Initialize set status tracking
    for sess in app.app_state.labeling_session:
        app.app_state.set_status_df = add_row(
            app.app_state.set_status_df, 
            sess.uuid, 
            SetStatus.INVALID  # All start as invalid
        )
```

---

## Initialization Functions

### initialize_evaluation_session

Entry point that processes all selected image sets.

```python
def initialize_evaluation_session(
    db_session: db_Session, 
    image_set_uuids: List[uuid_lib.UUID]
) -> List[ImageSetEvaluationSession]:
    """
    Initialize evaluation sessions for selected image sets.
    
    Args:
        db_session: SQLAlchemy session
        image_set_uuids: UUIDs selected in dashboard
        
    Returns:
        List of initialized ImageSetEvaluationSession objects
    """
    sessions: List[ImageSetEvaluationSession] = []
    
    for img_set_uuid in image_set_uuids:
        session = initialize_image_set_evaluation(db_session, img_set_uuid)
        sessions.append(session)
        
    return sessions
```

### initialize_image_set_evaluation

Creates a single ImageSetEvaluationSession from database.

```python
def initialize_image_set_evaluation(
    db_session: db_Session, 
    image_set_uuid: uuid_lib.UUID
) -> ImageSetEvaluationSession:
    """
    Initialize one image set evaluation session.
    
    Args:
        db_session: SQLAlchemy session
        image_set_uuid: UUID of image set to load
        
    Returns:
        Fully initialized ImageSetEvaluationSession
    """
    # 1. Fetch from database
    image_set = get_image_set(db_session, image_set_uuid)
    if image_set is None:
        raise ValueError(f"Image set with UUID {image_set_uuid} not found.")
    
    # 2. Get all images in set
    images_in_set: List[ImageRead] = image_set.images
    
    # 3. Create ImageEvaluationSession for each image
    image_sessions: List[ImageEvaluationSession] = []
    for img in images_in_set:
        img_session = initialize_image_evaluation(
            image_read_object=img,
            parent_path=Path(image_set.folder_path),
            dataset_path=Path(PATHS.get("dataset", "/data_set")),
        )
        image_sessions.append(img_session)
    
    # 4. Build ImageSetEvaluationSession
    return ImageSetEvaluationSession(
        set_index=image_set.index,
        uuid=image_set.uuid,
        description=image_set.description or "",
        icd_code=image_set.icd_code or "",
        image_set_name=image_set.image_set_name,
        image_set_format=image_set.image_format,
        window_width_default=image_set.image_window_width,
        window_level_default=image_set.image_window_level,
        patient_id=image_set.patient.patient_id if image_set.patient else None,
        num_images=image_set.num_images,
        folder_path=Path(image_set.folder_path),
        images_sessions=image_sessions,
        current_index=0,
        patient_information=None,
    )
```

### initialize_image_evaluation

Creates a single ImageEvaluationSession from database.

```python
def initialize_image_evaluation(
    image_read_object: ImageRead, 
    parent_path: Path, 
    dataset_path: Optional[Path] = None
) -> ImageEvaluationSession:
    """
    Initialize one image evaluation session.
    
    Args:
        image_read_object: Pydantic model from database
        parent_path: Image set folder path
        dataset_path: Base dataset path (optional)
        
    Returns:
        Initialized ImageEvaluationSession
    """
    image = image_read_object
    
    # Construct full file path
    if dataset_path:
        image_path = dataset_path / parent_path / image.image_name
    else:
        image_path = parent_path / image.image_name
    
    return ImageEvaluationSession(
        image_uuid=image.uuid,
        image_name=image.image_name,
        image_path=image_path,
        slice_index=image.slice_index,
        # All evaluation fields default to None/Region.None_
    )
```

---

## Status Tracking DataFrames

### Slice Status DataFrame

Tracks evaluation status for individual slices within an image set.

```python
def initialize_slice_df() -> pd.DataFrame:
    """Create empty slice status DataFrame."""
    return pd.DataFrame(columns=["slice_index", "image_uuid", "region", "status"])
```

**Schema**:

| Column | Type | Description |
|--------|------|-------------|
| slice_index | int | 1-indexed slice number |
| image_uuid | str | UUID of the image |
| region | str | Selected brain region |
| status | str | COMPLETED or INCOMPLETED |

**Operations**:

```python
def add_slice(df, slice_index, image_uuid, region, status=SliceStatus.INCOMPLETED):
    """Add new slice to tracking."""
    new_row = {
        "slice_index": slice_index + 1,  # 1-indexed
        "image_uuid": str(image_uuid),
        "region": region.value,
        "status": status.value,
    }
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)


def delete_slice(df, image_uuid):
    """Remove slice from tracking (when region cleared)."""
    return df[df["image_uuid"] != str(image_uuid)]


def modify_status(df, image_uuid, status):
    """Update slice status."""
    df.loc[df["image_uuid"] == str(image_uuid), "status"] = status.value
    return df


def modify_region(df, image_uuid, region):
    """Update slice region."""
    df.loc[df["image_uuid"] == str(image_uuid), "region"] = region.value
    return df
```

### Set Status DataFrame

Tracks validation status for entire image sets.

```python
def create_set_status_dataframe() -> pd.DataFrame:
    """Create empty set status DataFrame."""
    return pd.DataFrame(columns=["index", "set_uuid", "status"])
```

**Schema**:

| Column | Type | Description |
|--------|------|-------------|
| index | int | Auto-incrementing row number |
| set_uuid | str | UUID of the image set |
| status | str | VALID or INVALID |

**Operations**:

```python
def add_row(df, set_uuid, status):
    """Add new set to tracking."""
    next_index = 1 if df.empty else df["index"].max() + 1
    new_row = {"index": next_index, "set_uuid": str(set_uuid), "status": status.value}
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)


def mark_status(df, set_uuid, status):
    """Update set status."""
    df.loc[df["set_uuid"] == str(set_uuid), "status"] = status.value
    return df


def get_invalid_indices(df):
    """Get indices of invalid sets."""
    return df.loc[df["status"] == SetStatus.INVALID.value, "index"].tolist()
```

---

## Validation Logic

### Slice Validation

```python
def has_required_regions(df: pd.DataFrame) -> bool:
    """Check if all required brain regions are present."""
    required_regions = {
        Region.BasalCentral.value,
        Region.BasalCortex.value,
        Region.CoronaRadiata.value,
    }
    regions_present = set(df["region"].unique())
    return required_regions.issubset(regions_present)


def all_completed(df: pd.DataFrame) -> bool:
    """Check if all slices have complete scoring."""
    return bool((df["status"] == SliceStatus.COMPLETED.value).all())


def validate_slices(df: pd.DataFrame) -> bool:
    """Full validation: required regions + all completed."""
    return bool(has_required_regions(df) and all_completed(df))


def consecutive_slices(df: pd.DataFrame) -> bool:
    """Check if annotated slices are consecutive (no gaps)."""
    if df.empty:
        return True
    
    values = df["slice_index"].sort_values().to_numpy()
    return (values[-1] - values[0] + 1) == len(values) and \
           len(set(values)) == len(values)
```

### Validation State Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                  SET VALIDATION STATES                         │
└───────────────────────────────────────────────────────────────┘

                    ┌─────────────┐
                    │   INITIAL   │
                    │  (INVALID)  │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │ Ischemic  │  │ Non-Ische │  │Low Quality│
    │Assessable │  │   mic     │  │           │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │              │              │
          │              │              │
          ▼              ▼              ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │ Need All  │  │   AUTO    │  │   AUTO    │
    │ 3 Regions │  │   VALID   │  │   VALID   │
    │ + Scores  │  │           │  │           │
    └─────┬─────┘  └───────────┘  └───────────┘
          │
          │ All regions present?
          │ All slices completed?
          │ Slices consecutive?
          │
          ▼
    ┌───────────┐
    │   VALID   │
    │ (Submit)  │
    └───────────┘
```

---

## Memory Layout

### After Initialization

```
st.session_state.app_state: LabelingAppState
│
├── doctor_id: UUID
├── login_session: UUID
├── brightness: 0
├── contrast: 1.0
├── filter_type: FilterType.NONE
├── session_index: 0
│
├── set_status_df: DataFrame
│   ┌───────┬──────────────────────────────────┬─────────┐
│   │ index │ set_uuid                         │ status  │
│   ├───────┼──────────────────────────────────┼─────────┤
│   │ 1     │ 550e8400-e29b-41d4-a716-44665... │ INVALID │
│   │ 2     │ 6ba7b810-9dad-11d1-80b4-00c04... │ INVALID │
│   └───────┴──────────────────────────────────┴─────────┘
│
└── labeling_session: List
    │
    ├── [0] ImageSetEvaluationSession
    │   ├── uuid: 550e8400-e29b-41d4-a716-446655440000
    │   ├── image_set_name: "CQ500-CT-100"
    │   ├── num_images: 25
    │   ├── current_index: 0
    │   ├── slice_status_df: DataFrame (empty initially)
    │   │
    │   └── images_sessions: List
    │       ├── [0] ImageEvaluationSession
    │       │   ├── image_uuid: abc123...
    │       │   ├── image_name: "slice_001.dcm"
    │       │   ├── image_path: /data_sets/cq500_dcm/.../slice_001.dcm
    │       │   ├── slice_index: 0
    │       │   ├── region: Region.None_
    │       │   └── (all scores: None)
    │       │
    │       ├── [1] ImageEvaluationSession
    │       │   └── ...
    │       └── ...
    │
    └── [1] ImageSetEvaluationSession
        └── ...
```

---

## Path Resolution

### Dataset Path Construction

```python
# Configuration
PATHS = {"dataset": "./data_sets"}

# Image path construction
dataset_path = Path(PATHS.get("dataset", "/data_set"))
folder_path = Path(image_set.folder_path)  # e.g., "cq500_dcm/CQ500-CT-100"
image_name = image.image_name              # e.g., "slice_001.dcm"

full_path = dataset_path / folder_path / image_name
# Result: ./data_sets/cq500_dcm/CQ500-CT-100/slice_001.dcm
```

### Path Structure

```
data_sets/
├── cq500_dcm/
│   ├── CQ500-CT-100/
│   │   ├── Unknown Study/
│   │   │   └── CT PLAIN THIN/
│   │   │       ├── slice_001.dcm
│   │   │       ├── slice_002.dcm
│   │   │       └── ...
│   │   └── ...
│   └── ...
└── cq500_jpg/
    └── ...
```
