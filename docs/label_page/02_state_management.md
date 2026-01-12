# State Management System

## Overview

The state management system is the foundation of the labeling page's event-driven architecture. It consists of three primary components:

1. **EventFlags** - Event queue surviving Streamlit reruns
2. **LabelingAppState** - Central state container
3. **EnumKeyManager** - Widget key factory

---

## EventFlags: The Event Queue

### Purpose

`EventFlags` acts as a message queue that persists across Streamlit reruns, allowing callbacks to communicate with the main script.

### Implementation

```python
@dataclass
class HalfEvent:
    """Event without payload (e.g., button clicks)."""
    type: EventType

@dataclass
class CompletedEvent:
    """Event with payload (e.g., slider values)."""
    type: EventType
    payload: str  # Key of the widget that triggered the event

class EventFlags:
    def __init__(self):
        self._queue: List[Union[HalfEvent, CompletedEvent]] = []

    def push(self, event: Union[HalfEvent, CompletedEvent]):
        """Add event to the queue."""
        self._queue.append(event)

    def pop(self) -> Optional[Union[HalfEvent, CompletedEvent]]:
        """Remove and return first event, or None if empty."""
        return self._queue.pop(0) if self._queue else None

    def has_events(self) -> bool:
        return bool(self._queue)

    def clear(self):
        self._queue.clear()
```

### Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      EVENT LIFECYCLE                             │
└─────────────────────────────────────────────────────────────────┘

  CALLBACK PHASE                    SCRIPT PHASE
  (Before rerun)                    (During rerun)
       │                                 │
       ▼                                 ▼
┌─────────────┐                  ┌─────────────────┐
│ User clicks │                  │ flag_listener() │
│   button    │                  │                 │
└──────┬──────┘                  └────────┬────────┘
       │                                  │
       ▼                                  ▼
┌─────────────┐                  ┌─────────────────┐
│ on_click    │                  │   flag.pop()    │
│ callback    │                  │                 │
└──────┬──────┘                  └────────┬────────┘
       │                                  │
       ▼                                  ▼
┌─────────────┐                  ┌─────────────────┐
│ raise_flag  │                  │ EVENT_DISPATCH  │
│ (flag,type) │                  │   [event.type]  │
└──────┬──────┘                  └────────┬────────┘
       │                                  │
       ▼                                  ▼
┌─────────────┐                  ┌─────────────────┐
│ flag.push   │─ ─ ─ ─ ─ ─ ─ ─ ─▶│ handler(event,  │
│ (HalfEvent) │   QUEUE PERSISTS │   app_state)    │
└─────────────┘   IN SESSION     └─────────────────┘
                    STATE
```

### HalfEvent vs CompletedEvent

| Event Type | Use Case | Payload | Example |
|------------|----------|---------|---------|
| `HalfEvent` | Simple actions | None | Button click |
| `CompletedEvent` | Value changes | Widget key | Slider change |

```python
# HalfEvent - No need to read widget value
st.button("Next", on_click=raise_flag, 
          args=(flag, EventType.NEXT_IMAGE))

# CompletedEvent - Need to read widget value
st.slider("Brightness", -100, 100, 
          on_change=raise_flag,
          args=(flag, EventType.BRIGHTNESS_CHANGED, key))
```

---

## EventType: The Event Catalog

### All Event Types

```python
class EventType(Enum):
    """Types of user interaction events."""
    
    # Session Events
    LOGIN = auto()
    LOGOUT = auto()
    
    # Image Navigation
    NEXT_IMAGE = auto()
    PREV_IMAGE = auto()
    JUMP_TO_IMAGE = auto()
    
    # Set Navigation
    NEXT_SET = auto()
    PREV_SET = auto()
    JUMP_TO_SET = auto()
    
    # Image Adjustments
    BRIGHTNESS_CHANGED = auto()
    CONTRAST_CHANGED = auto()
    FILTER_CHANGED = auto()
    RESET_ADJUSTMENTS = auto()
    
    # DICOM Windowing
    WINDOWING_LEVEL_CHANGED = auto()
    WINDOWING_WIDTH_CHANGED = auto()
    RESET_WINDOWING = auto()
    
    # Region Selection
    REGION_SELECTED = auto()
    
    # Scoring Changes
    BASAL_CORTEX_LEFT_SCORE_CHANGED = auto()
    BASAL_CORTEX_RIGHT_SCORE_CHANGED = auto()
    BASAL_CENTRAL_LEFT_SCORE_CHANGED = auto()
    BASAL_CENTRAL_RIGHT_SCORE_CHANGED = auto()
    CORONA_LEFT_SCORE_CHANGED = auto()
    CORONA_RIGHT_SCORE_CHANGED = auto()
    NOTES_CHANGED = auto()
    
    # Set Markings
    MARK_IRRELEVANT_CHANGED = auto()
    MARK_LOW_QUALITY_CHANGED = auto()
    
    # Submission
    SAVE = auto()
    CANCEL = auto()
    SUBMIT = auto()
```

### Event Categories

```
┌─────────────────────────────────────────────────────────────────┐
│                      EVENT TYPE TAXONOMY                         │
└─────────────────────────────────────────────────────────────────┘

                        EventType
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   Navigation           Display            Evaluation
        │                   │                   │
   ┌────┴────┐        ┌────┴────┐        ┌────┴────┐
   │         │        │         │        │         │
 Image     Set     Brightness  DICOM   Region   Score
   │         │        │       Windowing   │         │
┌──┴──┐  ┌──┴──┐  ┌──┴──┐   ┌──┴──┐  ┌──┴──┐  ┌──┴──┐
NEXT  PREV NEXT PREV  ↑  ↓   W  L   Basal Corona Basal
JUMP  JUMP                          Cortex      Central
```

---

## LabelingAppState: Central State Container

### Structure

```python
@dataclass
class LabelingAppState:
    """Central state for the labeling application."""
    
    # Core data
    labeling_session: List[ImageSetEvaluationSession]  # All image sets
    doctor_id: uuid_lib.UUID                            # Current user
    login_session: uuid_lib.UUID                        # Auth session
    
    # Display settings
    brightness: int = DEFAULT_BRIGHTNESS
    contrast: float = DEFAULT_CONTRAST
    filter_type: FilterType = FilterType.NONE
    
    # Navigation state
    session_index: int = 0  # Current image set index
    
    # Validation tracking
    set_status_df: pd.DataFrame = field(default_factory=create_set_status_dataframe)
    all_sessions_satisfactory: bool = False
    
    @property
    def current_session(self) -> ImageSetEvaluationSession:
        """Convenience accessor for current image set."""
        return self.labeling_session[self.session_index]
```

### State Hierarchy

```
LabelingAppState
│
├── labeling_session: List[ImageSetEvaluationSession]
│   │
│   └── ImageSetEvaluationSession
│       ├── uuid: UUID
│       ├── image_set_name: str
│       ├── num_images: int
│       ├── folder_path: Path
│       ├── window_width_current: int
│       ├── window_level_current: int
│       ├── image_set_usability: ImageSetUsability
│       ├── low_quality: bool
│       ├── current_index: int
│       ├── slice_status_df: DataFrame  ─────────┐
│       │                                         │
│       └── images_sessions: List[ImageEvalSession]
│           │                                     │
│           └── ImageEvaluationSession            │
│               ├── image_uuid: UUID              │
│               ├── image_name: str               │
│               ├── image_path: Path         ◄────┘ Tracked here
│               ├── slice_index: int
│               ├── region: Region
│               ├── basal_score_central_left: int?
│               ├── basal_score_central_right: int?
│               ├── basal_score_cortex_left: int?
│               ├── basal_score_cortex_right: int?
│               ├── corona_score_left: int?
│               ├── corona_score_right: int?
│               └── notes: str?
│
├── set_status_df: DataFrame
│   └── Tracks VALID/INVALID status for each set
│
└── session_index: int
    └── Points to current ImageSetEvaluationSession
```

---

## EnumKeyManager: Widget Key Factory

### Purpose

Generates unique, parseable widget keys that:

1. Prevent key collisions across dynamic widgets
2. Include context (element type, event type, UUID)
3. Can be parsed to extract metadata

### Implementation

```python
@dataclass(frozen=True)
class ParsedKey:
    element_type: UIElementType
    use: EventType | str
    uuid: Optional[str]

@dataclass(frozen=True)
class EnumKeyManager:
    separator: str = "_"

    def make(
        self,
        element_type: UIElementType,
        use: EventType | str,
        obj_uuid: Optional[str | uuid_lib.UUID] = None,
    ) -> str:
        """Generate a unique widget key."""
        use_val = use.name if isinstance(use, EventType) else str(use)
        key = f"{element_type.value}{self.separator}{use_val}"
        if obj_uuid:
            key += f"{self.separator}{obj_uuid}"
        return key

    def parse(self, key: str) -> ParsedKey:
        """Parse a key back into its components."""
        parts = key.split(self.separator)
        element_type = UIElementType(parts[0])
        use = EventType[parts[1]]
        uuid = parts[2] if len(parts) == 3 else None
        return ParsedKey(element_type=element_type, use=use, uuid=uuid)
```

### UIElementType Enum

```python
class UIElementType(Enum):
    BUTTON = "button"
    SLIDER = "slider"
    SELECTBOX = "selectbox"
    SEGMENTED_CONTROL = "segmented_control"
    NUMBER_INPUT = "number_input"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"
```

### Key Generation Examples

```python
key_mngr = EnumKeyManager()

# Simple key (no UUID context)
key = key_mngr.make(UIElementType.BUTTON, EventType.LOGOUT)
# Result: "button_LOGOUT"

# Key with UUID context (for set-specific widgets)
key = key_mngr.make(
    UIElementType.SLIDER, 
    EventType.JUMP_TO_IMAGE,
    session.uuid
)
# Result: "slider_JUMP_TO_IMAGE_550e8400-e29b-41d4-a716-446655440000"

# Parsing a key
parsed = key_mngr.parse("slider_JUMP_TO_IMAGE_550e8400-e29b-41d4-a716-446655440000")
# Result: ParsedKey(
#     element_type=UIElementType.SLIDER,
#     use=EventType.JUMP_TO_IMAGE,
#     uuid="550e8400-e29b-41d4-a716-446655440000"
# )
```

---

## raise_flag: The Event Publisher

### Implementation

```python
def raise_flag(
    flag: EventFlags,
    event_type: EventType,
    payload: Optional[str] = None,
):
    """Push an event to the queue.
    
    Args:
        flag: EventFlags instance from session state
        event_type: Type of event that occurred
        payload: Widget key (for CompletedEvent) or None (for HalfEvent)
    """
    if payload is None:
        flag.push(HalfEvent(type=event_type))
    else:
        flag.push(CompletedEvent(type=event_type, payload=payload))
```

### Usage Patterns

```python
# Pattern 1: Button (no value to read)
st.button(
    "Next Image",
    on_click=raise_flag,
    args=(app.label_flag, EventType.NEXT_IMAGE),
)

# Pattern 2: Slider (value needed)
key = app.key_mngr.make(UIElementType.SLIDER, EventType.BRIGHTNESS_CHANGED)
st.slider(
    "Brightness",
    -100, 100,
    key=key,
    on_change=raise_flag,
    args=(app.label_flag, EventType.BRIGHTNESS_CHANGED, key),
)

# Pattern 3: Number input with context UUID
key = app.key_mngr.make(
    UIElementType.NUMBER_INPUT,
    EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
    app.app_state.current_session.uuid
)
st.number_input(
    "Basal Cortex Score",
    min_value=0, max_value=3,
    key=key,
    on_change=raise_flag,
    args=(app.label_flag, EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED, key),
)
```

---

## State Persistence in session_state

### Initialization

```python
def initial_setup():
    """Initialize event flags in Streamlit session state."""
    if "label_flag" not in st.session_state:
        st.session_state.label_flag = EventFlags()
    if "key_mngr" not in st.session_state:
        st.session_state.key_mngr = EnumKeyManager()

# In main script
app = st.session_state  # Alias for brevity

if "app_state" not in app:
    app.app_state = LabelingAppState(
        labeling_session=initialize_evaluation_session(...),
        doctor_id=doctor_uuid,
        login_session=user_session.session_uuid,
    )
```

### Session State Structure

```
st.session_state
│
├── label_flag: EventFlags
│   └── _queue: List[HalfEvent | CompletedEvent]
│
├── key_mngr: EnumKeyManager
│   └── separator: "_"
│
├── app_state: LabelingAppState
│   └── (All labeling state)
│
├── user: UUID (from login)
├── user_session: SessionRead (from login)
├── selected_scans: List[UUID] (from dashboard)
│
└── [Dynamic widget keys...]
    ├── "button_NEXT_IMAGE"
    ├── "slider_BRIGHTNESS_CHANGED"
    ├── "number_input_BASAL_CORTEX_LEFT_SCORE_CHANGED_uuid..."
    └── ...
```

---

## Thread Safety and Concurrency

### Streamlit's Model

- Each user session has its own `session_state`
- No shared state between users
- Single-threaded within a session

### Our Design

- `EventFlags` queue handles one event per rerun
- `flag.clear()` prevents stale event accumulation
- State mutations happen in controlled handler functions

```python
def flag_listener(flag: EventFlags, app_state: LabelingAppState):
    """Process one event (if any) using the dispatch table."""
    event = flag.pop()
    flag.clear()  # Ensure only one event is processed
    if not event:
        return
    
    handler = EVENT_DISPATCH.get(event.type)
    if handler is not None:
        handler(event, app_state)
```
