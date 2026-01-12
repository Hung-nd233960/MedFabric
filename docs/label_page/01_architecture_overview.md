# Architecture Overview

## The Streamlit Execution Challenge

### Understanding Streamlit's Model

Streamlit operates fundamentally differently from traditional web frameworks:

```
Traditional Web Framework:
┌────────┐     ┌────────┐     ┌────────┐
│ Client │────▶│ Server │────▶│ Handler│
│ Event  │     │ Routes │     │ Updates│
└────────┘     └────────┘     └────────┘
                                  │
                                  ▼
                            ┌──────────┐
                            │ Response │
                            │ (Partial)│
                            └──────────┘

Streamlit:
┌────────┐     ┌─────────────────────────────────┐
│ Widget │────▶│    ENTIRE SCRIPT RE-EXECUTES    │
│ Change │     │  (Top to bottom, every time)    │
└────────┘     └─────────────────────────────────┘
```

### The Problem This Creates

1. **Lost Context**: Local variables disappear between runs
2. **Race Conditions**: Callbacks fire before main script
3. **Widget Conflicts**: Dynamic widgets need stable, unique keys
4. **State Synchronization**: UI must reflect state after updates

### Our Solution: The Dispatcher Pattern

We've implemented an **event-driven architecture** that:

1. **Captures events** via `on_change` callbacks
2. **Queues them** in persistent `st.session_state`
3. **Processes them** at the start of each rerun
4. **Updates state** before UI rendering

---

## System Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      label.py                                ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  ││
│  │  │   Column 1  │  │   Column 2  │  │      Column 3       │  ││
│  │  │   (Image)   │  │  (Controls) │  │  (Status/Submit)    │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                      STATE MANAGEMENT LAYER                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   EventFlags    │  │ LabelingAppState│  │  EnumKeyManager │  │
│  │   (Queue)       │  │ (Central State) │  │  (Key Factory)  │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │            │
│           └────────────────────┼────────────────────┘            │
│                                │                                 │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
┌────────────────────────────────┴─────────────────────────────────┐
│                       DISPATCHER LAYER                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    flag_listener()                           │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │              EVENT_DISPATCH Dictionary                │   │ │
│  │  │  EventType.NEXT_IMAGE  ──▶  handle_next_image()       │   │ │
│  │  │  EventType.PREV_IMAGE  ──▶  handle_prev_image()       │   │ │
│  │  │  EventType.REGION_SEL  ──▶  handle_region_selected()  │   │ │
│  │  │  ...                   ──▶  ...                       │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
┌────────────────────────────────┴─────────────────────────────────┐
│                    SESSION INITIALIZATION LAYER                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ ImageSetEval    │  │ ImageEval       │  │   Status        │   │
│  │ Session         │  │ Session         │  │   Tracking      │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
┌────────────────────────────────┴─────────────────────────────────┐
│                      IMAGE PROCESSING LAYER                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ DICOM Processing│  │ JPEG Processing │  │ Image Rendering │   │
│  │ (Windowing)     │  │ (Load/Display)  │  │ (Streamlit)     │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
medfabric/pages/
├── label.py                          # Main labeling page
└── label_helper/
    ├── __init__.py
    ├── state_management.py           # EventFlags, EventType, LabelingAppState
    ├── dispatcher.py                 # Event handlers and dispatch table
    ├── session_initialization.py     # Data structure initialization
    ├── image_session_status.py       # Slice-level status tracking
    ├── image_set_session_status.py   # Set-level status tracking
    ├── submit_results.py             # Database submission logic
    ├── unsatisfactory_sessions.py    # Validation logic
    ├── column_config.py              # Streamlit column configurations
    └── image_loader/
        ├── __init__.py
        ├── dicom_processing.py       # DICOM loading and windowing
        ├── jpg_processing.py         # JPEG/PNG loading
        └── image_helper.py           # Common rendering utilities
```

---

## Execution Flow

### Complete Rerun Cycle

```
┌──────────────────────────────────────────────────────────────────┐
│                     STREAMLIT RERUN CYCLE                         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. USER INTERACTION                                               │
│    User clicks button / changes slider / selects option           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. ON_CHANGE CALLBACK (Before rerun)                              │
│    raise_flag(flag, EventType.XXX, payload)                       │
│    └── Pushes HalfEvent or CompletedEvent to EventFlags queue    │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. SCRIPT STARTS FROM TOP                                         │
│    ┌────────────────────────────────────────────────────────────┐│
│    │ initial_setup()                                             ││
│    │   └── Ensures EventFlags and KeyManager exist               ││
│    └────────────────────────────────────────────────────────────┘│
│                              │                                    │
│                              ▼                                    │
│    ┌────────────────────────────────────────────────────────────┐│
│    │ flag_listener(app.label_flag, app.app_state)               ││
│    │   ├── Pops event from queue                                ││
│    │   ├── Looks up handler in EVENT_DISPATCH                   ││
│    │   └── Executes handler(event, app_state)                   ││
│    └────────────────────────────────────────────────────────────┘│
│                              │                                    │
│                              ▼                                    │
│    ┌────────────────────────────────────────────────────────────┐│
│    │ UI RENDERING                                                ││
│    │   ├── Column 1: Image display                              ││
│    │   ├── Column 2: Navigation + Controls                      ││
│    │   └── Column 3: Status + Submission                        ││
│    └────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ WAIT FOR INPUT  │
                    └─────────────────┘
```

---

## Design Principles

### 1. Single Source of Truth

All mutable state lives in `LabelingAppState`:

```python
@dataclass
class LabelingAppState:
    labeling_session: List[ImageSetEvaluationSession]  # All evaluation data
    doctor_id: uuid_lib.UUID                            # Current user
    login_session: uuid_lib.UUID                        # Auth session
    brightness: int                                     # Display settings
    contrast: float
    filter_type: FilterType
    session_index: int                                  # Current set index
    set_status_df: pd.DataFrame                        # Validation status
```

### 2. Immutable Event Types

Events are strongly typed via enums:

```python
class EventType(Enum):
    NEXT_IMAGE = auto()
    PREV_IMAGE = auto()
    REGION_SELECTED = auto()
    # ... 25+ event types
```

### 3. Handler Isolation

Each event type has a dedicated handler function:

```python
def handle_next_image(event: HalfEvent, app_state: LabelingAppState):
    app_state.current_session.current_index = (
        app_state.current_session.current_index + 1
    ) % app_state.current_session.num_images
```

### 4. Key Uniqueness

Widget keys are generated programmatically:

```python
key = app.key_mngr.make(
    UIElementType.BUTTON,      # Widget type
    EventType.NEXT_IMAGE,      # Purpose
    app.app_state.current_session.uuid  # Context (optional)
)
# Result: "button_NEXT_IMAGE_550e8400-e29b-41d4-a716-446655440000"
```

---

## Benefits of This Architecture

| Benefit | Description |
|---------|-------------|
| **Predictable State** | All state changes happen through handlers |
| **Debuggable** | Events can be logged/inspected |
| **Testable** | Handlers can be unit tested in isolation |
| **Maintainable** | Adding features = adding event types + handlers |
| **Type-Safe** | Enums prevent typos and enable IDE support |
| **Streamlit-Compatible** | Works with rerun model, not against it |

---

## Trade-offs

| Trade-off | Mitigation |
|-----------|------------|
| More boilerplate | Code generation could help |
| Learning curve | Comprehensive documentation |
| Single event per rerun | Adequate for user interactions |
| Memory in session_state | Minimal overhead per session |
