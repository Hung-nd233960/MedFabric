# Dispatcher Pattern

## Overview

The Dispatcher is the core innovation enabling event-driven programming within Streamlit. It translates queued events into state mutations via a dispatch table pattern.

---

## The Dispatch Table

### Implementation

```python
EVENT_DISPATCH: Dict[EventType, Callable] = {
    # Navigation - Image
    EventType.NEXT_IMAGE: handle_next_image,
    EventType.PREV_IMAGE: handle_prev_image,
    EventType.JUMP_TO_IMAGE: handle_jump_to_image,
    
    # Navigation - Set
    EventType.NEXT_SET: handle_next_set,
    EventType.PREV_SET: handle_prev_set,
    EventType.JUMP_TO_SET: handle_jump_to_set,
    
    # Display Adjustments
    EventType.BRIGHTNESS_CHANGED: handle_brightness_changed,
    EventType.CONTRAST_CHANGED: handle_contrast_changed,
    EventType.RESET_ADJUSTMENTS: handle_reset_adjustments,
    
    # DICOM Windowing
    EventType.WINDOWING_LEVEL_CHANGED: handle_windowing_level_changed,
    EventType.WINDOWING_WIDTH_CHANGED: handle_windowing_width_changed,
    EventType.RESET_WINDOWING: handle_reset_windowing,
    
    # Region & Scoring
    EventType.REGION_SELECTED: handle_region_selected,
    EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED: handle_basal_central_left_score,
    EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED: handle_basal_central_right_score,
    EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED: handle_basal_cortex_left_score,
    EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED: handle_basal_cortex_right_score,
    EventType.CORONA_LEFT_SCORE_CHANGED: handle_corona_left_score,
    EventType.CORONA_RIGHT_SCORE_CHANGED: handle_corona_right_score,
    EventType.NOTES_CHANGED: handle_notes_changed,
    
    # Set Markings
    EventType.MARK_IRRELEVANT_CHANGED: handle_mark_irrelevant,
    EventType.MARK_LOW_QUALITY_CHANGED: handle_mark_low_quality,
    
    # Session Control
    EventType.LOGOUT: handle_logout,
    EventType.SUBMIT: handle_submit,
}
```

### Dispatch Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DISPATCH MECHANISM                           │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   Event      │        │   Dispatch   │        │   Handler    │
│   Queue      │───────▶│   Table      │───────▶│   Function   │
│              │        │              │        │              │
│ CompletedEvt │        │ EventType →  │        │ handle_xxx() │
│ type=NEXT_IMG│        │ Callable     │        │              │
└──────────────┘        └──────────────┘        └──────────────┘
                                                       │
                                                       ▼
                                               ┌──────────────┐
                                               │ LabelingApp  │
                                               │ State        │
                                               │ (mutated)    │
                                               └──────────────┘
```

---

## The Flag Listener

### Implementation

```python
def flag_listener(flag: EventFlags, app_state: LabelingAppState):
    """Process one event (if any) using the dispatch table.
    
    Called at the start of each Streamlit rerun, before UI rendering.
    """
    # 1. Pop first event from queue
    event: Optional[Union[HalfEvent, CompletedEvent]] = flag.pop()
    
    # 2. Clear remaining events (prevents stale accumulation)
    flag.clear()
    
    # 3. Exit early if no event
    if not event:
        return
    
    # 4. Lookup handler in dispatch table
    handler = EVENT_DISPATCH.get(event.type)
    
    # 5. Execute handler if found
    if handler is not None:
        handler(event, app_state)
```

### Why Clear the Queue?

```
Scenario without clear():
─────────────────────────
1. User clicks "Next" rapidly 5 times
2. Queue accumulates: [NEXT, NEXT, NEXT, NEXT, NEXT]
3. Rerun 1: Process NEXT (now at image 2)
4. Rerun 2: Process NEXT (now at image 3)
5. ...unexpected rapid navigation

Scenario with clear():
──────────────────────
1. User clicks "Next" rapidly 5 times
2. Queue accumulates: [NEXT, NEXT, NEXT, NEXT, NEXT]
3. Rerun 1: Pop NEXT, clear rest, process (now at image 2)
4. Subsequent clicks queue fresh events
5. Controlled, predictable behavior
```

---

## Handler Categories

### Category 1: Navigation Handlers

**Purpose**: Move through images or image sets

```python
def handle_next_image(event: HalfEvent, app_state: LabelingAppState):
    """Move to the next image in current set (wraps around)."""
    app_state.current_session.current_index = (
        app_state.current_session.current_index + 1
    ) % app_state.current_session.num_images
    
    # Sync UI state with new image
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_prev_image(event: HalfEvent, app_state: LabelingAppState):
    """Move to the previous image (wraps around)."""
    app_state.current_session.current_index = (
        app_state.current_session.current_index - 1
    ) % app_state.current_session.num_images
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_jump_to_image(event: CompletedEvent, app_state: LabelingAppState):
    """Jump to specific image by slider value."""
    if event.payload:
        # Read slider value from session state
        app_state.current_session.current_index = (
            st.session_state[event.payload] - 1  # 1-indexed to 0-indexed
        )
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)
```

### Category 2: Display Handlers

**Purpose**: Adjust image visualization

```python
def handle_brightness_changed(event: CompletedEvent, app_state: LabelingAppState):
    """Update brightness setting from slider."""
    app_state.brightness = st.session_state[event.payload]


def handle_windowing_level_changed(event: CompletedEvent, app_state: LabelingAppState):
    """Update DICOM window level."""
    app_state.current_session.window_level_current = st.session_state[event.payload]


def handle_reset_windowing(event: HalfEvent, app_state: LabelingAppState, 
                           app=st.session_state):
    """Reset DICOM windowing to defaults."""
    # Reset internal state
    app_state.current_session.window_level_current = (
        app_state.current_session.window_level_default
    )
    app_state.current_session.window_width_current = (
        app_state.current_session.window_width_default
    )
    
    # Also update widget values in session_state
    app[app.key_mngr.make(
        UIElementType.NUMBER_INPUT,
        EventType.WINDOWING_WIDTH_CHANGED,
        app.app_state.current_session.uuid,
    )] = app_state.current_session.window_width_default
    
    app[app.key_mngr.make(
        UIElementType.NUMBER_INPUT,
        EventType.WINDOWING_LEVEL_CHANGED,
        app.app_state.current_session.uuid,
    )] = app_state.current_session.window_level_default
```

### Category 3: Scoring Handlers

**Purpose**: Update evaluation scores with validation

```python
def handle_basal_central_left_score(event: CompletedEvent, app_state: LabelingAppState):
    """Update basal central left score and validate."""
    # 1. Update score in image session
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_central_left = st.session_state[event.payload]
    
    # 2. Evaluate if scoring is complete
    evaluate_score_and_update_status(app_state)
    
    # 3. Check if entire set is now valid
    if validate_slices(app_state.current_session.slice_status_df):
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
        app_state.current_session.render_valid_message = True
    else:
        app_state.current_session.render_valid_message = False
```

### Category 4: Region Selection Handler

**Purpose**: Handle brain region selection with complex validation

```python
def handle_region_selected(event: CompletedEvent, app_state: LabelingAppState):
    """Handle region selection with score field management."""
    # 1. Get selected value from widget
    payload_content = st.session_state[event.payload] if event.payload else None
    img_session = app_state.current_session.current_image_session
    
    if payload_content is None:
        # Region cleared - reset all scores
        img_session.region = Region.None_
        reset_score_fields(app_state, Region.None_)
        reset_score_fields_in_session(Region.None_)
        
        # Remove from slice tracking
        app_state.current_session.slice_status_df = delete_slice(
            app_state.current_session.slice_status_df, 
            img_session.image_uuid
        )
        
    elif payload_content == "BasalGangliaCentral":
        img_session.region = Region.BasalCentral
        reset_score_fields(app_state, Region.BasalCentral)
        reset_score_fields_in_session(Region.BasalCentral)
        
        # Add/update in slice tracking
        app_state.current_session.slice_status_df = handle_df_region_change(
            app_state.current_session.slice_status_df,
            app_state.current_session.current_index,
            img_session.image_uuid,
            Region.BasalCentral,
        )
        
    # ... similar for BasalGangliaCortex and CoronaRadiata
    
    # Check consecutive slices requirement
    app_state.current_session.consecutive_slices = consecutive_slices(
        app_state.current_session.slice_status_df
    )
```

### Category 5: Set Marking Handlers

**Purpose**: Handle set-level annotations

```python
def handle_mark_irrelevant(event: CompletedEvent, app_state: LabelingAppState):
    """Handle usability classification change."""
    raw_value = st.session_state[event.payload]
    app_state.current_session.image_set_usability = (
        image_set_usability_translation_dict[raw_value]
    )
    
    if app_state.current_session.image_set_usability != ImageSetUsability.IschemicAssessable:
        # Non-ischemic: clear all scores
        for img in app_state.current_session.images_sessions:
            img.region = Region.None_
            reset_score_fields(app_state, Region.None_)
            reset_score_fields_in_session(Region.None_)
        
        # Clear slice tracking and mark as valid
        app_state.current_session.slice_status_df = clear_all_slices()
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
    else:
        # Ischemic: needs scoring
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.INVALID,
        )
    
    # Update UI rendering mode
    disable_score_fields(app_state)


def handle_mark_low_quality(event: CompletedEvent, app_state: LabelingAppState):
    """Handle low quality flag toggle."""
    app_state.current_session.low_quality = st.session_state[event.payload]
    
    if app_state.current_session.low_quality:
        # Low quality: clear scores but mark as valid
        for img in app_state.current_session.images_sessions:
            img.region = Region.None_
            reset_score_fields(app_state, Region.None_)
        
        app_state.current_session.slice_status_df = clear_all_slices()
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
    else:
        # Quality restored: needs re-evaluation
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.INVALID,
        )
    
    disable_score_fields(app_state)
```

### Category 6: Session Control Handlers

**Purpose**: Handle login/logout and submission

```python
def handle_logout(event: HalfEvent, app_state: LabelingAppState):
    """Clear session and redirect to login."""
    reset()  # Clears session_state and switches page


def handle_submit(event: HalfEvent, app_state: LabelingAppState):
    """Submit all evaluations to database."""
    db_session = get_session_factory()()
    
    for image_set in app_state.labeling_session:
        submit_image_set_results(
            db_session=db_session,
            doctor_uuid=app_state.doctor_id,
            session_uuid=app_state.login_session,
            result=image_set,
        )
    
    db_session.close()
    reset()  # Return to dashboard
```

---

## Helper Functions

### Score Field Management

```python
def reset_score_fields(app_state: LabelingAppState, mode: Region):
    """Reset score fields in ImageEvaluationSession based on region."""
    img_session = app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ]
    
    if mode == Region.BasalCentral:
        # Keep basal scores, clear corona
        img_session.corona_score_left = None
        img_session.corona_score_right = None
        
    elif mode == Region.CoronaRadiata:
        # Keep corona scores, clear basal
        img_session.basal_score_central_left = None
        img_session.basal_score_central_right = None
        img_session.basal_score_cortex_left = None
        img_session.basal_score_cortex_right = None
        
    elif mode == Region.None_:
        # Clear all scores
        img_session.corona_score_left = None
        img_session.corona_score_right = None
        img_session.basal_score_central_left = None
        img_session.basal_score_central_right = None
        img_session.basal_score_cortex_left = None
        img_session.basal_score_cortex_right = None


def reset_score_fields_in_session(mode: Region, app=st.session_state):
    """Reset widget values in session_state to match internal state."""
    # Similar logic but updates st.session_state widget keys
    # This ensures widgets display correct values on rerun
```

### UI State Synchronization

```python
def update_region_value(app_state: LabelingAppState, app=st.session_state):
    """Sync region pills widget with internal state."""
    region = app_state.current_session.current_image_session.region
    
    key = app.key_mngr.make(
        UIElementType.SEGMENTED_CONTROL,
        EventType.REGION_SELECTED,
        app_state.current_session.current_image_session.image_uuid,
    )
    
    region_map = {
        Region.BasalCortex: "BasalGangliaCortex",
        Region.BasalCentral: "BasalGangliaCentral",
        Region.CoronaRadiata: "CoronaRadiata",
    }
    
    app[key] = region_map.get(region)  # None for Region.None_


def reimplement_score_fields_in_session(app_state: LabelingAppState, 
                                         app=st.session_state):
    """Restore score widget values from internal state."""
    img_session = app_state.current_session.current_image_session
    
    # Each score field gets its value from the image session
    app[app.key_mngr.make(
        UIElementType.NUMBER_INPUT,
        EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
        app_state.current_session.uuid,
    )] = img_session.basal_score_central_left
    
    # ... similar for all other score fields
```

### Validation Helpers

```python
def evaluate_score_and_update_status(app_state: LabelingAppState):
    """Check if current image has complete scoring."""
    img_session = app_state.current_session.current_image_session
    
    if score_based_evaluation(img_session):
        # All required scores present
        app_state.current_session.slice_status_df = modify_status(
            app_state.current_session.slice_status_df,
            img_session.image_uuid,
            SliceStatus.COMPLETED,
        )
    else:
        # Incomplete scoring
        app_state.current_session.slice_status_df = modify_status(
            app_state.current_session.slice_status_df,
            img_session.image_uuid,
            SliceStatus.INCOMPLETED,
        )


def disable_score_fields(app_state: LabelingAppState):
    """Determine if score input should be enabled."""
    if (app_state.current_session.image_set_usability 
            != ImageSetUsability.IschemicAssessable
        or app_state.current_session.low_quality):
        app_state.current_session.render_score_box_mode = False
    else:
        app_state.current_session.render_score_box_mode = True
```

---

## Translation Dictionaries

### Usability Translation

```python
image_set_usability_translation_dict = {
    "Ischemic": ImageSetUsability.IschemicAssessable,
    "Hemorrhagic": ImageSetUsability.HemorrhagicPresent,
    "Undertermined": ImageSetUsability.Indeterminate,
    "Normal": ImageSetUsability.Normal,
    "True Irrelevant": ImageSetUsability.TrueIrrelevant,
}
```

This maps user-friendly selectbox options to database enum values.

---

## Adding New Event Handlers

### Step-by-Step Guide

1. **Add EventType**:

```python
class EventType(Enum):
    # ... existing types
    MY_NEW_EVENT = auto()
```

1. **Create Handler Function**:

```python
def handle_my_new_event(event: CompletedEvent, app_state: LabelingAppState):
    """Handle my new event."""
    value = st.session_state[event.payload]
    # Update app_state as needed
    app_state.some_property = value
```

1. **Register in Dispatch Table**:

```python
EVENT_DISPATCH: Dict[EventType, Callable] = {
    # ... existing handlers
    EventType.MY_NEW_EVENT: handle_my_new_event,
}
```

1. **Create UI Widget**:

```python
key = app.key_mngr.make(UIElementType.SLIDER, EventType.MY_NEW_EVENT)
st.slider(
    "My New Slider",
    0, 100,
    key=key,
    on_change=raise_flag,
    args=(app.label_flag, EventType.MY_NEW_EVENT, key),
)
```
