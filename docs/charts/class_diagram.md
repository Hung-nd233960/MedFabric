# Class Diagram

## Overview

Class diagrams show the structure of the system including classes, their attributes, methods, and relationships.

---

## Core Data Models

```mermaid
classDiagram
    class LabelingAppState {
        +List~ImageSetEvaluationSession~ labeling_session
        +UUID doctor_id
        +UUID login_session
        +int session_index
        +int brightness
        +float contrast
        +FilterType filter_type
        +DataFrame set_status_df
        +current_session: ImageSetEvaluationSession
    }

    class ImageSetEvaluationSession {
        +int set_index
        +UUID uuid
        +str image_set_name
        +str patient_id
        +int num_images
        +Path folder_path
        +List~ImageEvaluationSession~ images_sessions
        +int window_width_default
        +int window_level_default
        +int window_width_current
        +int window_level_current
        +str notes
        +bool low_quality
        +str icd_code
        +str description
        +ImageSetUsability image_set_usability
        +ImageFormat image_set_format
        +int current_index
        +DataFrame slice_status_df
        +bool consecutive_slices
        +DataFrame patient_information
        +bool render_score_box_mode
        +bool render_valid_message
        +current_image_session: ImageEvaluationSession
    }

    class ImageEvaluationSession {
        +UUID image_uuid
        +str image_name
        +Path image_path
        +int slice_index
        +Region region
        +int basal_score_central_left
        +int basal_score_central_right
        +int basal_score_cortex_left
        +int basal_score_cortex_right
        +int corona_score_left
        +int corona_score_right
        +str notes
        +Dict image_metadata
    }

    LabelingAppState "1" --> "*" ImageSetEvaluationSession : contains
    ImageSetEvaluationSession "1" --> "*" ImageEvaluationSession : contains
```

---

## Event System Classes

```mermaid
classDiagram
    class EventFlags {
        -Queue~Event~ _queue
        +get_nowait() Event
        +put(event: Event) void
        +empty() bool
    }

    class HalfEvent {
        +EventType event_type
        +str key
    }

    class CompletedEvent {
        +EventType event_type
        +str key
        +Any value
    }

    class EventType {
        <<enumeration>>
        NEXT_IMAGE
        PREV_IMAGE
        JUMP_TO_IMAGE
        NEXT_SET
        PREV_SET
        JUMP_TO_SET
        REGION_SELECTED
        BASAL_CORTEX_LEFT_SCORE_CHANGED
        BASAL_CORTEX_RIGHT_SCORE_CHANGED
        BASAL_CENTRAL_LEFT_SCORE_CHANGED
        BASAL_CENTRAL_RIGHT_SCORE_CHANGED
        CORONA_LEFT_SCORE_CHANGED
        CORONA_RIGHT_SCORE_CHANGED
        WINDOWING_WIDTH_CHANGED
        WINDOWING_LEVEL_CHANGED
        RESET_WINDOWING
        MARK_LOW_QUALITY_CHANGED
        MARK_IRRELEVANT_CHANGED
        NOTES_CHANGED
        SUBMIT
        LOGOUT
    }

    class UIElementType {
        <<enumeration>>
        BUTTON
        SLIDER
        NUMBER_INPUT
        SEGMENTED_CONTROL
        SELECTBOX
        CHECKBOX
        TEXTAREA
    }

    class EnumKeyManager {
        +make(element: UIElementType, event: EventType, uuid: UUID) str
        +parse(key: str) Tuple
    }

    EventFlags --> HalfEvent : queues
    EventFlags --> CompletedEvent : queues
    HalfEvent --> EventType : uses
    CompletedEvent --> EventType : uses
    EnumKeyManager --> UIElementType : uses
    EnumKeyManager --> EventType : uses
```

---

## Database ORM Models

```mermaid
classDiagram
    class DataSet {
        +int id
        +UUID uuid
        +str name
        +Path folder_path
        +Optional~int~ num_image_sets
    }

    class Patient {
        +int id
        +UUID uuid
        +str patient_id
        +Optional~DataSet~ dataset
    }

    class Doctors {
        +int id
        +UUID uuid
        +str username
        +str email
        +str hashed_password
        +bool is_admin
    }

    class Session {
        +int id
        +UUID uuid
        +UUID doctor_uuid
        +datetime created_at
        +datetime expires_at
        +bool is_active
    }

    class ImageSet {
        +int id
        +UUID uuid
        +str image_set_name
        +int index
        +ImageFormat image_format
        +Path folder_path
        +int num_images
        +int image_window_width
        +int image_window_level
        +str description
        +str icd_code
        +Patient patient
    }

    class Image {
        +int id
        +UUID uuid
        +str image_name
        +int slice_index
        +UUID image_set_uuid
    }

    class ImageSetEvaluation {
        +int id
        +UUID uuid
        +UUID image_set_uuid
        +UUID session_uuid
        +str notes
        +bool low_quality
        +ImageSetUsability usability
    }

    class ImageEvaluation {
        +int id
        +UUID uuid
        +UUID image_uuid
        +UUID image_set_evaluation_uuid
        +Region region
        +int basal_score_cortex_left
        +int basal_score_cortex_right
        +int basal_score_central_left
        +int basal_score_central_right
        +int corona_score_left
        +int corona_score_right
        +str notes
    }

    DataSet "1" --> "*" Patient : has
    DataSet "1" --> "*" ImageSet : contains
    Patient "1" --> "*" ImageSet : has
    ImageSet "1" --> "*" Image : contains
    Doctors "1" --> "*" Session : creates
    Session "1" --> "*" ImageSetEvaluation : produces
    ImageSet "1" --> "*" ImageSetEvaluation : evaluated_by
    ImageSetEvaluation "1" --> "*" ImageEvaluation : contains
    Image "1" --> "*" ImageEvaluation : evaluated_by
```

---

## Pydantic Models (API Layer)

```mermaid
classDiagram
    class DoctorCreate {
        +str username
        +str email
        +str password
    }

    class DoctorRead {
        +int id
        +UUID uuid
        +str username
        +str email
        +bool is_admin
    }

    class SessionCreate {
        +UUID doctor_uuid
    }

    class SessionRead {
        +UUID session_uuid
        +UUID doctor_uuid
        +datetime created_at
        +datetime expires_at
        +bool is_active
    }

    class ImageSetRead {
        +int id
        +UUID uuid
        +str image_set_name
        +int index
        +ImageFormat image_format
        +Path folder_path
        +int num_images
        +List~ImageRead~ images
    }

    class ImageRead {
        +int id
        +UUID uuid
        +str image_name
        +int slice_index
    }

    class ImageEvaluationCreate {
        +UUID image_uuid
        +UUID image_set_evaluation_uuid
        +Region region
        +int basal_score_cortex_left
        +int basal_score_cortex_right
        +int basal_score_central_left
        +int basal_score_central_right
        +int corona_score_left
        +int corona_score_right
        +str notes
    }

    class ImageSetEvaluationCreate {
        +UUID image_set_uuid
        +UUID session_uuid
        +str notes
        +bool low_quality
        +ImageSetUsability usability
    }

    DoctorCreate ..> DoctorRead : becomes
    SessionCreate ..> SessionRead : becomes
    ImageSetEvaluationCreate ..> ImageEvaluation : creates
```

---

## Enumerations

```mermaid
classDiagram
    class Region {
        <<enumeration>>
        None_
        BasalCortex
        BasalCentral
        CoronaRadiata
    }

    class ImageFormat {
        <<enumeration>>
        DICOM
        JPEG
    }

    class ImageSetUsability {
        <<enumeration>>
        IschemicAssessable
        NonIschemic
        Hemorrhagic
        NonNctEvaluable
    }

    class SliceStatus {
        <<enumeration>>
        COMPLETED
        INCOMPLETED
    }

    class SetStatus {
        <<enumeration>>
        VALID
        INVALID
    }

    class FilterType {
        <<enumeration>>
        NONE
        GAUSSIAN_BLUR
        SHARPEN
        EDGE_DETECTION
    }
```

---

## Image Processing Classes

```mermaid
classDiagram
    class DicomProcessing {
        <<module>>
        +load_raw_dicom_image(path) Tuple~FileDataset, ndarray~
        +apply_window(img, center, width) Image
        +dicom_image(path, center, width) Image
        +dicom_to_dict_str(dicom) Dict
        +extract_searchable_info(dicom) Dict
    }

    class JpgProcessing {
        <<module>>
        +load_jpg_image(path) Image
        +jpg_image(path) Image
    }

    class ImageHelper {
        <<module>>
        +render_image(img, set_idx, img_idx, num) void
    }

    class PILImage {
        <<external>>
    }

    class FileDataset {
        <<external>>
        +pixel_array: ndarray
        +RescaleSlope: float
        +RescaleIntercept: float
    }

    DicomProcessing ..> PILImage : produces
    DicomProcessing ..> FileDataset : uses
    JpgProcessing ..> PILImage : produces
    ImageHelper ..> PILImage : displays
```

---

## Dispatcher Pattern Classes

```mermaid
classDiagram
    class Dispatcher {
        <<module>>
        +EVENT_DISPATCH: Dict~EventType, Callable~
        +flag_listener(queue, state) void
        +raise_flag(queue, event_type, key) void
    }

    class NavigationHandlers {
        <<module>>
        +handle_next_image(state)
        +handle_prev_image(state)
        +handle_jump_to_image(state, data)
        +handle_next_set(state)
        +handle_prev_set(state)
        +handle_jump_to_set(state, data)
    }

    class DisplayHandlers {
        <<module>>
        +handle_windowing_width_changed(state, data)
        +handle_windowing_level_changed(state, data)
        +handle_reset_windowing(state)
    }

    class ScoringHandlers {
        <<module>>
        +handle_region_selected(state, data)
        +handle_basal_cortex_left_score_changed(state, data)
        +handle_basal_cortex_right_score_changed(state, data)
        +handle_basal_central_left_score_changed(state, data)
        +handle_basal_central_right_score_changed(state, data)
        +handle_corona_left_score_changed(state, data)
        +handle_corona_right_score_changed(state, data)
    }

    class SetHandlers {
        <<module>>
        +handle_mark_low_quality_changed(state, data)
        +handle_mark_irrelevant_changed(state, data)
        +handle_notes_changed(state, data)
    }

    class SessionHandlers {
        <<module>>
        +handle_submit(state)
        +handle_logout(state)
    }

    Dispatcher --> NavigationHandlers : dispatches to
    Dispatcher --> DisplayHandlers : dispatches to
    Dispatcher --> ScoringHandlers : dispatches to
    Dispatcher --> SetHandlers : dispatches to
    Dispatcher --> SessionHandlers : dispatches to
```

---

## Class Relationships Summary

| Relationship | Type | Description |
|--------------|------|-------------|
| LabelingAppState → ImageSetEvaluationSession | Composition | State contains sessions |
| ImageSetEvaluationSession → ImageEvaluationSession | Composition | Set contains slices |
| EventFlags → Event | Aggregation | Queue holds events |
| DataSet → ImageSet | Composition | Dataset contains sets |
| ImageSet → Image | Composition | Set contains images |
| Dispatcher → Handler | Dependency | Dispatcher calls handlers |
| ORM Model → Pydantic Model | Realization | ORM implements Pydantic interface |

---

## Design Patterns Used

| Pattern | Where Used | Purpose |
|---------|------------|---------|
| **Dataclass** | Session models | Immutable data containers |
| **Enum** | EventType, Region, etc. | Type-safe constants |
| **Factory** | EnumKeyManager.make() | Generate unique widget keys |
| **Command** | EVENT_DISPATCH | Encapsulate event handling |
| **State** | SliceStatus, SetStatus | Track object states |
| **Repository** | API layer | Abstract database access |
