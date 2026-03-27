# UI Components

## Overview

The labeling page UI is organized into three columns using Streamlit's grid system. Each render function is responsible for a specific UI element or group of elements.

---

## Layout Structure

```
┌────────────────────────────────────────────────────────────────────────────┐
│ HEADER: Page Config (title, icon, layout="wide")                           │
├──────────────────┬─────────────────────────┬───────────────────────────────┤
│                  │                         │                               │
│    COLUMN 1      │       COLUMN 2          │          COLUMN 3             │
│    (Image)       │      (Controls)         │        (Information)          │
│                  │                         │                               │
│ ┌──────────────┐ │ ┌─────────────────────┐ │ ┌───────────────────────────┐ │
│ │ Logout Btn   │ │ │ Navigation Controls │ │ │ Tab: Set Information      │ │
│ └──────────────┘ │ │ [◄] Slider [►]      │ │ │   ├─ Set Navigation       │ │
│                  │ └─────────────────────┘ │ │   ├─ Current Set Status   │ │
│ ┌──────────────┐ │                         │ │   └─ Slice Status Table   │ │
│ │              │ │ ┌─────────────────────┐ │ └───────────────────────────┘ │
│ │              │ │ │ Image Display       │ │                               │
│ │   CT Image   │ │ │ ├─ Window Width     │ │ ┌───────────────────────────┐ │
│ │   Viewer     │ │ │ └─ Window Level     │ │ │ Tab: All Sets Status      │ │
│ │              │ │ └─────────────────────┘ │ │   ├─ Set Annotations       │ │
│ │              │ │                         │ │   │   ├─ Low Quality       │ │
│ │              │ │ ┌─────────────────────┐ │ │   │   └─ Usability         │ │
│ └──────────────┘ │ │ Labeling Column     │ │ │   ├─ Notes Textarea       │ │
│                  │ │ ├─ Region Selector  │ │ │   └─ Submit Button        │ │
│ Slice: X of Y    │ │ └─ Score Inputs     │ │ └───────────────────────────┘ │
│ Set: A of B      │ └─────────────────────┘ │                               │
│                  │                         │                               │
└──────────────────┴─────────────────────────┴───────────────────────────────┘
```

---

## Render Functions

### render_logout_button

Renders logout button at top of column 1.

```python
def render_logout_button(key: str):
    """Render logout button with callback."""
    st.button(
        "Logout",
        type="secondary",
        key=key,
        on_click=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.LOGOUT,
        ),
    )
```

### render_image

Displays the current CT slice with position information.

```python
def render_image(
    img: Image.Image,
    set_index: int,
    slice_index: int,
    total_slices: int,
):
    """
    Render CT image with position info.
    
    Args:
        img: PIL Image object (processed DICOM/JPEG)
        set_index: Current image set index
        slice_index: Current slice index within set
        total_slices: Total slices in current set
    """
    st.image(img, use_container_width=True)
    st.caption(
        f"Slice {slice_index + 1} of {total_slices} | "
        f"Set {set_index + 1}"
    )
```

### render_image_navigation_controls

Navigation for moving between slices.

```python
def render_image_navigation_controls(
    next_img_key: str,
    prev_img_key: str,
    img_slider_key: str,
    num_images: int,
    current_index: int,
):
    """
    Render slice navigation controls.
    
    Layout:
    ┌───────────────────────────────────┐
    │ [◄ Previous]  [Next ►]            │
    ├───────────────────────────────────┤
    │ ─────────●─────────── (slider)    │
    └───────────────────────────────────┘
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.button(
            "◄ Previous",
            key=prev_img_key,
            on_click=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.PREV_IMAGE,
            ),
            disabled=current_index == 0,
        )
    
    with col2:
        st.button(
            "Next ►",
            key=next_img_key,
            on_click=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.NEXT_IMAGE,
            ),
            disabled=current_index >= num_images - 1,
        )
    
    st.slider(
        "Jump to slice",
        min_value=1,
        max_value=num_images,
        value=current_index + 1,
        key=img_slider_key,
        on_change=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.JUMP_TO_IMAGE,
            img_slider_key,
        ),
    )
```

### render_dicom_windowing_controls

DICOM-specific windowing controls for adjusting brightness/contrast.

```python
def render_dicom_windowing_controls(
    window_width: int,
    window_level: int,
    window_width_key: str,
    window_level_key: str,
    reset_window_key: str,
):
    """
    Render DICOM windowing controls.
    
    Window Width: Controls contrast (range of HU values displayed)
    Window Level: Controls brightness (center HU value)
    
    Layout:
    ┌─────────────────────────────────┐
    │ Window Width:  [____80____]    │
    │ Window Level:  [____40____]    │
    │ [Reset to Default]              │
    └─────────────────────────────────┘
    """
    st.number_input(
        "Window Width",
        min_value=1,
        max_value=4000,
        value=window_width,
        key=window_width_key,
        on_change=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.WINDOWING_WIDTH_CHANGED,
            window_width_key,
        ),
    )
    
    st.number_input(
        "Window Level",
        min_value=-1000,
        max_value=3000,
        value=window_level,
        key=window_level_key,
        on_change=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.WINDOWING_LEVEL_CHANGED,
            window_level_key,
        ),
    )
    
    st.button(
        "Reset to Default",
        key=reset_window_key,
        on_click=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.RESET_WINDOWING,
        ),
    )
```

### render_labeling_column

Main labeling interface with region selection and scoring.

```python
def render_labeling_column(
    region_segmented_key: str,
    key_basal_cortex_left: str,
    key_basal_cortex_right: str,
    key_basal_central_left: str,
    key_basal_central_right: str,
    key_corona_left: str,
    key_corona_right: str,
):
    """
    Render main labeling interface.
    
    Layout depends on selected region:
    
    Region.None_:
    ┌─────────────────────────────────┐
    │ Select Region: [None | BC | BCe | CR] │
    │ (No score inputs shown)              │
    └─────────────────────────────────┘
    
    Region.BasalCortex:
    ┌─────────────────────────────────┐
    │ Select Region: [None | BC | BCe | CR] │
    │ Left:          Right:           │
    │ [Cortex: __]   [Cortex: __]    │
    └─────────────────────────────────┘
    
    Region.BasalCentral:
    ┌─────────────────────────────────┐
    │ Select Region: [None | BC | BCe | CR] │
    │ Left:          Right:           │
    │ [Cortex: __]   [Cortex: __]    │
    │ [Central: __]  [Central: __]   │
    └─────────────────────────────────┘
    
    Region.CoronaRadiata:
    ┌─────────────────────────────────┐
    │ Select Region: [None | BC | BCe | CR] │
    │ Left:          Right:           │
    │ [Corona: __]   [Corona: __]    │
    └─────────────────────────────────┘
    """
    with st.expander("Labeling Controls", expanded=True):
        current_region = st.session_state.app_state \
            .current_session.current_image_session.region
        
        # Region selector (segmented control)
        st.segmented_control(
            "Select Region",
            options=[r.value for r in Region],
            default=current_region.value if current_region else None,
            key=region_segmented_key,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.REGION_SELECTED,
                region_segmented_key,
            ),
        )
        
        # Score inputs (conditionally rendered based on region)
        if current_region != Region.None_:
            acol1, acol2 = st.columns(2)
            
            with acol1:
                st.write("Left:")
                _render_left_scores(
                    current_region,
                    key_basal_cortex_left,
                    key_basal_central_left,
                    key_corona_left,
                )
            
            with acol2:
                st.write("Right:")
                _render_right_scores(
                    current_region,
                    key_basal_cortex_right,
                    key_basal_central_right,
                    key_corona_right,
                )
```

### render_set_column

Navigation controls for moving between image sets.

```python
def render_set_column(
    prev_key: str,
    next_key: str,
    jump_to_key: str,
    current_index: int,
    num_sets: int,
):
    """
    Render set navigation controls.
    
    Only shown when multiple sets are selected.
    
    Layout:
    ┌─────────────────────────────────┐
    │ [◄ Previous Set] [Next Set ►]  │
    │ ─────────●─────────── (slider) │
    └─────────────────────────────────┘
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.button(
            "◄ Previous Set",
            key=prev_key,
            on_click=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.PREV_SET,
            ),
            disabled=current_index == 0,
        )
    
    with col2:
        st.button(
            "Next Set ►",
            key=next_key,
            on_click=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.NEXT_SET,
            ),
            disabled=current_index >= num_sets - 1,
        )
    
    st.slider(
        "Jump to set",
        min_value=1,
        max_value=num_sets,
        value=current_index + 1,
        key=jump_to_key,
        on_change=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.JUMP_TO_SET,
            jump_to_key,
        ),
    )
```

### render_set_labeling_row

Set-level annotation controls.

```python
def render_set_labeling_row(
    low_quality_key: str,
    irrelevant_key: str,
    low_quality_enabled: bool,
):
    """
    Render set-level annotation controls.
    
    Layout:
    ┌─────────────────────────────────┐
    │ Usability: [IschemicAssessable ▼] │
    │ □ Mark as Low Quality           │
    └─────────────────────────────────┘
    """
    # Usability selection
    st.selectbox(
        "Image Set Usability",
        options=[u.value for u in ImageSetUsability],
        key=irrelevant_key,
        on_change=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.MARK_IRRELEVANT_CHANGED,
            irrelevant_key,
        ),
    )
    
    # Low quality checkbox (only for assessable sets)
    if low_quality_enabled:
        st.checkbox(
            "Mark as Low Quality",
            key=low_quality_key,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.MARK_LOW_QUALITY_CHANGED,
                low_quality_key,
            ),
        )
```

---

## Data Tables

### Slice Status Table

Displays status of all labeled slices within current set.

```python
# Column configuration
config_image_eval = {
    "slice_index": st.column_config.NumberColumn(
        "Slice",
        help="Slice number within the image set",
    ),
    "region": st.column_config.TextColumn(
        "Region",
        help="Brain region assigned to this slice",
    ),
    "status": st.column_config.TextColumn(
        "Status",
        help="COMPLETED or INCOMPLETED",
    ),
}

# Rendered in expander
with st.expander("Current Image Set Status", expanded=True):
    st.dataframe(
        app.app_state.current_session.slice_status_df,
        width="stretch",
        hide_index=True,
        column_config=config_image_eval,
        column_order=["slice_index", "region", "status"],
    )
```

### Set Status Table

Displays validation status of all image sets.

```python
# Column configuration
config_set_eval = {
    "index": st.column_config.NumberColumn(
        "Set #",
        help="Image set number",
    ),
    "status": st.column_config.TextColumn(
        "Status",
        help="VALID or INVALID",
    ),
}

# Rendered in expander
with st.expander("All image set statuses", expanded=False):
    invalid_indices = get_invalid_indices(app.app_state.set_status_df)
    
    if invalid_indices:
        st.warning(f"Invalid sets: {list(invalid_indices)}")
    else:
        st.success("All sets valid - ready to submit!")
        st.button(
            "Submit All Evaluations",
            type="primary",
            on_click=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.SUBMIT,
            ),
        )
    
    st.dataframe(
        app.app_state.set_status_df,
        width="stretch",
        hide_index=True,
        column_config=config_set_eval,
        column_order=["index", "status"],
    )
```

---

## Conditional Rendering Logic

### Score Field Visibility

Score input fields are shown based on selected region:

```python
# Score visibility matrix
┌────────────────┬─────────┬─────────┬─────────┐
│   Score Type   │ Basal   │ Basal   │ Corona  │
│                │ Cortex  │ Central │ Radiata │
├────────────────┼─────────┼─────────┼─────────┤
│ Basal Cortex   │    ✓    │    ✓    │         │
│ Basal Central  │         │    ✓    │         │
│ Corona Radiata │         │         │    ✓    │
└────────────────┴─────────┴─────────┴─────────┘
```

### Mode-Based Rendering

```python
# Non-ischemic or low-quality sets skip scoring
if not app.app_state.current_session.render_score_box_mode:
    st.info("This image set is valid for submission.")
else:
    # Show full scoring interface
    ...
```

---

## Key Generation Pattern

Each widget uses a unique key generated by `EnumKeyManager`:

```python
# Key format: {element_type}_{event_type}_{optional_uuid}

# Examples:
"BUTTON_NEXT_IMAGE"
"SLIDER_JUMP_TO_IMAGE_550e8400-e29b-41d4-a716-446655440000"
"NUMBER_INPUT_BASAL_CORTEX_LEFT_SCORE_CHANGED_550e8400..."
"SEGMENTED_CONTROL_REGION_SELECTED_abc123-def456..."
```

**Key Generation Usage**:

```python
# Button key (no UUID needed)
app.key_mngr.make(UIElementType.BUTTON, EventType.NEXT_IMAGE)

# Slider key (includes set UUID for uniqueness)
app.key_mngr.make(
    UIElementType.SLIDER,
    EventType.JUMP_TO_IMAGE,
    app.app_state.current_session.uuid,
)

# Number input key (includes set UUID)
app.key_mngr.make(
    UIElementType.NUMBER_INPUT,
    EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
    app.app_state.current_session.uuid,
)
```

---

## Widget-Event Mapping

| Widget Type | Event Type | Handler |
|-------------|------------|---------|
| Button | `NEXT_IMAGE` | `handle_next_image` |
| Button | `PREV_IMAGE` | `handle_prev_image` |
| Slider | `JUMP_TO_IMAGE` | `handle_jump_to_image` |
| Button | `NEXT_SET` | `handle_next_set` |
| Button | `PREV_SET` | `handle_prev_set` |
| Slider | `JUMP_TO_SET` | `handle_jump_to_set` |
| Number Input | `WINDOWING_WIDTH_CHANGED` | `handle_windowing_width_changed` |
| Number Input | `WINDOWING_LEVEL_CHANGED` | `handle_windowing_level_changed` |
| Button | `RESET_WINDOWING` | `handle_reset_windowing` |
| Segmented Control | `REGION_SELECTED` | `handle_region_selected` |
| Number Input | `BASAL_CORTEX_LEFT_SCORE_CHANGED` | `handle_basal_cortex_left_score_changed` |
| Number Input | `BASAL_CORTEX_RIGHT_SCORE_CHANGED` | `handle_basal_cortex_right_score_changed` |
| Number Input | `BASAL_CENTRAL_LEFT_SCORE_CHANGED` | `handle_basal_central_left_score_changed` |
| Number Input | `BASAL_CENTRAL_RIGHT_SCORE_CHANGED` | `handle_basal_central_right_score_changed` |
| Number Input | `CORONA_LEFT_SCORE_CHANGED` | `handle_corona_left_score_changed` |
| Number Input | `CORONA_RIGHT_SCORE_CHANGED` | `handle_corona_right_score_changed` |
| Selectbox | `MARK_IRRELEVANT_CHANGED` | `handle_mark_irrelevant_changed` |
| Checkbox | `MARK_LOW_QUALITY_CHANGED` | `handle_mark_low_quality_changed` |
| Textarea | `NOTES_CHANGED` | `handle_notes_changed` |
| Button | `SUBMIT` | `handle_submit` |
| Button | `LOGOUT` | `handle_logout` |
