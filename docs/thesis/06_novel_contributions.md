# Chapter 6: Novel Contributions

## Presentation Outline

**Estimated Length**: 8-12 pages  
**Key Purpose**: Deep dive into the event-driven dispatcher pattern as the main technical contribution

---

## 6.1 The Streamlit Challenge

### 6.1.1 Understanding Streamlit's Execution Model

**Present the fundamental problem**:

```python
# Traditional web application (Flask/Django)
@app.route("/increment", methods=["POST"])
def increment():
    session["count"] = session.get("count", 0) + 1
    return redirect("/")

# Streamlit - EVERY interaction reruns the ENTIRE script
import streamlit as st

count = 0  # This resets to 0 on every rerun!

if st.button("Increment"):
    count += 1  # Always shows 1

st.write(f"Count: {count}")  # Always displays "Count: 1"
```

### 6.1.2 Built-in Solution Limitations

| Approach | How It Works | Limitation |
|----------|--------------|------------|
| `st.session_state` | Key-value store | Manual key management |
| `on_change` callback | Widget-level handler | Executes BEFORE main script |
| `st.form` | Batch submissions | Only for form context |
| `st.experimental_rerun()` | Force re-execution | No timing control |

### 6.1.3 The Complex Workflow Problem

```
┌─────────────────────────────────────────────────────────────────┐
│             COMPLEX WORKFLOW REQUIREMENTS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Medical Image Labeling Needs:                                   │
│  ├── Multi-step workflow (navigate → select → score → validate) │
│  ├── Interdependent state (slice affects set validation)        │
│  ├── Dynamic UI (score fields change based on region)           │
│  ├── Batch operations (multiple sets in one session)            │
│  └── Validation before submission                                │
│                                                                  │
│  Streamlit Provides:                                             │
│  ├── Stateless script execution                                  │
│  ├── Widget callbacks that fire before rendering                 │
│  └── Session state dictionary                                    │
│                                                                  │
│  Gap: No pattern for managing complex, interdependent state     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6.2 The Event-Driven Dispatcher Pattern

### 6.2.1 Pattern Overview

**Core Insight**: Treat user interactions as events that are queued and processed at the start of each script execution.

```
┌─────────────────────────────────────────────────────────────────┐
│              EVENT-DRIVEN DISPATCHER PATTERN                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 1: EVENT CAPTURE (in callback)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  User clicks widget → on_change callback fires           │   │
│  │  Callback queues event: raise_flag(EventType.X, key)     │   │
│  │  Streamlit triggers rerun                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  PHASE 2: EVENT PROCESSING (at script start)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  flag_listener() drains queue                             │   │
│  │  For each event:                                          │   │
│  │    1. Resolve widget value (if HalfEvent)                 │   │
│  │    2. Lookup handler in EVENT_DISPATCH                    │   │
│  │    3. Execute handler(state, value)                       │   │
│  │    4. State is mutated                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  PHASE 3: RENDERING (rest of script)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Script renders UI using updated state                    │   │
│  │  New widgets registered with callbacks                    │   │
│  │  Cycle repeats on next interaction                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.2 Why This Works

**Key Innovation**: The queue persists in `st.session_state` while the dispatcher runs at the start of each execution.

| Traditional Approach | This Pattern |
|---------------------|--------------|
| Callback modifies state directly | Callback queues event |
| State change happens before render | State change happens at controlled point |
| Hard to track what changed | Event log shows all changes |
| Widget value may not be available | Widget value resolved after rerun |

---

## 6.3 Pattern Components

### 6.3.1 EventFlags: The Event Queue

```python
class EventFlags:
    """
    Queue-based event buffer.
    
    Key Design Decisions:
    1. Uses standard library queue.Queue for thread-safety
    2. Non-blocking get_nowait() prevents hangs
    3. Stored in session_state for persistence
    """
    
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
    
    def raise_flag(self, event: Event) -> None:
        """
        Queue an event for processing.
        
        Called from widget callbacks.
        """
        self._queue.put(event)
    
    def get(self) -> Optional[Event]:
        """
        Get next event without blocking.
        
        Called from flag_listener at script start.
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
```

**Why Queue Over List?**:

- Thread-safe for potential async operations
- FIFO ordering preserved
- Standard pattern for event systems

### 6.3.2 Event Types: HalfEvent vs CompletedEvent

```python
@dataclass
class HalfEvent:
    """
    Event without payload.
    
    Used when widget value needed but not yet available.
    Example: Number input change (value in session_state)
    """
    event_type: EventType
    key: str  # Widget key to look up value


@dataclass  
class CompletedEvent:
    """
    Event with resolved payload.
    
    Used when value is known at callback time.
    Example: Button click (no value needed)
    """
    event_type: EventType
    key: str
    value: Any  # Already resolved or None for buttons
```

**Resolution Process**:

```python
# In flag_listener
if isinstance(event, HalfEvent):
    # Widget value now available in session_state
    widget_value = st.session_state.get(event.key)
    event = CompletedEvent(
        event_type=event.event_type,
        key=event.key,
        value=widget_value,
    )
```

### 6.3.3 EVENT_DISPATCH: The Routing Table

```python
EVENT_DISPATCH: Dict[EventType, Callable] = {
    # Pattern: EventType → handler_function
    
    # Navigation (no payload)
    EventType.NEXT_IMAGE: handle_next_image,
    EventType.PREV_IMAGE: handle_prev_image,
    
    # Value changes (payload is new value)
    EventType.REGION_SELECTED: handle_region_selected,
    EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED: handle_basal_cortex_left,
    
    # ... 25+ event types total
}
```

**Design Benefits**:

- Single source of truth for event routing
- Easy to add new events (just add entry)
- Clear mapping for debugging
- Testable handlers in isolation

### 6.3.4 Handler Function Pattern

```python
def handle_event_name(
    state: LabelingAppState,
    value: Optional[Any] = None,
) -> None:
    """
    Standard handler signature.
    
    Args:
        state: Mutable central state container
        value: Event payload (widget value or None)
    
    Responsibilities:
        1. Update relevant state attributes
        2. Trigger cascading updates if needed
        3. Update validation status
    """
    # Example: Region selection
    current_image = state.current_session.current_image_session
    
    # Update state
    current_image.region = Region(value)
    
    # Cascade to validation
    update_slice_status(state)
    update_set_status(state)
```

---

## 6.4 Comparison with Existing Patterns

### 6.4.1 Redux (JavaScript)

| Redux Concept | MedFabric Equivalent |
|---------------|---------------------|
| Store | LabelingAppState |
| Action | EventType + value |
| Reducer | Handler function |
| Dispatch | flag_listener loop |
| Action Creator | raise_flag() |

**Key Difference**: Redux uses immutable state updates; MedFabric uses mutable dataclasses (simpler for Python).

### 6.4.2 Observer Pattern

| Observer Pattern | MedFabric Pattern |
|------------------|-------------------|
| Subject maintains observer list | EVENT_DISPATCH maintains handler list |
| Observer subscribes | Handler added to dispatch table |
| Subject notifies | flag_listener calls handlers |
| Observer updates | Handler modifies state |

**Key Difference**: No dynamic subscription; dispatch table is static.

### 6.4.3 Command Pattern

| Command Pattern | MedFabric Pattern |
|-----------------|-------------------|
| Command object | Event (HalfEvent/CompletedEvent) |
| Invoker | flag_listener |
| Receiver | State (LabelingAppState) |
| Execute | Handler function |

**Key Difference**: Commands are data (events), not objects with behavior.

---

## 6.5 Pattern Benefits

### 6.5.1 Separation of Concerns

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   UI Layer       │    │  Dispatcher      │    │   State Layer    │
│                  │    │                  │    │                  │
│ - Render widgets │    │ - Route events   │    │ - Hold data      │
│ - Register       │───▶│ - Call handlers  │───▶│ - Validate       │
│   callbacks      │    │ - Log actions    │    │ - Track changes  │
│                  │    │                  │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### 6.5.2 Testability

```python
# Handlers can be tested in isolation
def test_handle_region_selected():
    state = create_mock_state()
    
    handle_region_selected(state, "BasalCortex")
    
    assert state.current_session.current_image_session.region == Region.BasalCortex
    assert len(state.current_session.slice_status_df) == 1
```

### 6.5.3 Debuggability

```python
# Add logging to flag_listener
def flag_listener(flags, state):
    while not flags.is_empty():
        event = flags.get()
        logging.info(f"Processing: {event.event_type}")
        
        handler = EVENT_DISPATCH.get(event.event_type)
        if handler:
            handler(state, event.value)
            logging.info(f"State after: {state.session_index}")
```

### 6.5.4 Extensibility

```python
# Adding a new event type:
# 1. Add to EventType enum
class EventType(Enum):
    # ... existing
    NEW_FEATURE = "NEW_FEATURE"

# 2. Create handler
def handle_new_feature(state, value):
    # Implementation
    pass

# 3. Add to dispatch table
EVENT_DISPATCH[EventType.NEW_FEATURE] = handle_new_feature

# 4. Wire up widget
st.button("New Feature", on_click=raise_flag, 
          args=(flags, EventType.NEW_FEATURE))
```

---

## 6.6 Pattern Limitations

### 6.6.1 Known Limitations

| Limitation | Mitigation |
|------------|------------|
| Single-threaded processing | Async handlers possible for I/O |
| No undo/redo | Could add event history |
| Memory for large queues | Queue drains each rerun |
| Learning curve | Comprehensive documentation |

### 6.6.2 When NOT to Use

- Simple forms with few fields (use st.form)
- Single-page dashboards (session_state sufficient)
- Read-only applications (no state management needed)

### 6.6.3 When TO Use

- Multi-step workflows
- Interdependent state (changes cascade)
- Dynamic UIs (widgets appear/disappear)
- Complex validation requirements
- Need for event logging/debugging

---

## 6.7 Generalization for Other Projects

### 6.7.1 Reusable Components

```python
# Generic EventFlags - reusable
class EventFlags:
    def __init__(self): ...
    def raise_flag(self, event): ...
    def get(self): ...

# Generic flag_listener - reusable pattern
def flag_listener(flags, state, dispatch_table):
    while not flags.is_empty():
        event = flags.get()
        if isinstance(event, HalfEvent):
            event = resolve_event(event)
        handler = dispatch_table.get(event.event_type)
        if handler:
            handler(state, event.value)

# Application-specific:
# - EventType enum
# - State dataclass
# - Handler functions
# - Dispatch table
```

### 6.7.2 Template for New Projects

```python
# Step 1: Define your events
class EventType(Enum):
    ACTION_A = "ACTION_A"
    ACTION_B = "ACTION_B"

# Step 2: Define your state
@dataclass
class AppState:
    data: List[str] = field(default_factory=list)

# Step 3: Write handlers
def handle_action_a(state, value):
    state.data.append(value)

# Step 4: Create dispatch table
DISPATCH = {
    EventType.ACTION_A: handle_action_a,
}

# Step 5: Wire up in Streamlit
if "flags" not in st.session_state:
    st.session_state.flags = EventFlags()
    st.session_state.app_state = AppState()

flag_listener(st.session_state.flags, st.session_state.app_state, DISPATCH)

# Render UI with callbacks using raise_flag
```

---

## 6.8 Contribution Summary

### 6.8.1 Academic Contribution

> **Novel Pattern**: First documented event-driven dispatcher architecture specifically designed for Streamlit's unique execution model, enabling complex stateful workflows in an otherwise stateless framework.

### 6.8.2 Practical Contribution

| Contribution | Impact |
|--------------|--------|
| EventFlags class | Reusable queue-based event buffer |
| Dispatcher pattern | Scalable event routing |
| HalfEvent/CompletedEvent | Handles widget value timing |
| Handler pattern | Testable, isolated state updates |

### 6.8.3 Documentation Contribution

- Comprehensive pattern documentation
- UML diagrams (sequence, state, activity)
- Code examples and templates
- Comparison with existing patterns

---

## Figures to Include

1. Execution model comparison (traditional vs Streamlit)
2. Event flow sequence diagram
3. Pattern component diagram
4. Redux comparison table
5. Handler execution flowchart
6. Generalized template diagram
