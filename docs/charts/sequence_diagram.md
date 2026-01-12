# Sequence Diagram

## Overview

Sequence diagrams show the order of interactions between objects/components over time.

---

## User Login Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant LP as Login Page
    participant API as Credentials API
    participant DB as Database
    participant SS as Session State

    U->>LP: Enter username/password
    U->>LP: Click Login
    LP->>API: validate_password(username, password)
    API->>DB: Query Doctors table
    DB-->>API: Doctor record or None
    
    alt Doctor not found
        API-->>LP: None
        LP-->>U: Error: Invalid credentials
    else Doctor found
        API->>API: ph.verify(hash, password)
        alt Password invalid
            API-->>LP: None
            LP-->>U: Error: Invalid credentials
        else Password valid
            API->>API: Create SessionCreate
            API->>DB: Insert new Session
            DB-->>API: Session UUID
            API-->>LP: SessionRead object
            LP->>SS: Store user_session
            LP-->>U: Redirect to Dashboard
        end
    end
```

---

## Dashboard to Labeling Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant DP as Dashboard Page
    participant LP as Labeling Page
    participant SI as Session Initialization
    participant API as Image Set API
    participant DB as Database
    participant SS as Session State

    U->>DP: Select datasets (checkboxes)
    U->>DP: Click "Start Labeling"
    DP->>SS: Store selected_scans (List[UUID])
    DP-->>U: Redirect to Labeling Page

    LP->>LP: Check app_state exists?
    
    alt app_state not exists
        LP->>SI: initialize_evaluation_session(db, UUIDs)
        
        loop For each UUID
            SI->>API: get_image_set(db, uuid)
            API->>DB: Query ImageSet + Images
            DB-->>API: ImageSetRead with images
            API-->>SI: ImageSetRead
            SI->>SI: Create ImageSetEvaluationSession
            SI->>SI: Create ImageEvaluationSession per image
        end
        
        SI-->>LP: List[ImageSetEvaluationSession]
        LP->>SS: Create LabelingAppState
        LP->>SS: Initialize set_status_df
    end
    
    LP->>LP: initial_setup()
    LP->>LP: flag_listener(queue, state)
    LP-->>U: Render labeling interface
```

---

## Event Handling Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant W as Streamlit Widget
    participant CB as Callback (raise_flag)
    participant Q as EventFlags Queue
    participant FL as flag_listener
    participant D as Dispatcher (EVENT_DISPATCH)
    participant H as Event Handler
    participant AS as App State
    participant ST as Streamlit

    U->>W: Click button / Change value
    W->>CB: Trigger on_change/on_click
    CB->>Q: put(HalfEvent(type, key))
    CB->>ST: Implicit rerun triggered

    Note over ST: Script reruns from top

    ST->>FL: flag_listener(queue, state)
    
    loop While queue not empty
        FL->>Q: queue.get_nowait()
        Q-->>FL: HalfEvent(type, key)
        FL->>FL: Check if HalfEvent or CompletedEvent
        
        alt HalfEvent (needs widget value)
            FL->>ST: session_state[key]
            ST-->>FL: widget_value
            FL->>FL: Create CompletedEvent(type, key, value)
        end
        
        FL->>D: EVENT_DISPATCH[event_type]
        D-->>FL: handler_function
        FL->>H: handler(state, event_data)
        H->>AS: Modify state attributes
        AS-->>H: Updated
        H-->>FL: Done
    end
    
    FL-->>ST: All events processed
    ST-->>U: Render updated UI
```

---

## Score Entry Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant RC as Region Control
    participant SI as Score Input
    participant CB as Callback
    participant Q as Queue
    participant H as Handler
    participant IS as ImageSession
    participant SD as Slice Status DF
    participant SetD as Set Status DF

    U->>RC: Select "Basal Cortex"
    RC->>CB: raise_flag(REGION_SELECTED, key)
    CB->>Q: Queue event
    
    Note over Q: Rerun
    
    Q-->>H: handle_region_selected(state, data)
    H->>IS: region = Region.BasalCortex
    H->>SD: add_slice(index, uuid, region)
    H-->>U: Show score inputs (Cortex L/R)
    
    U->>SI: Enter 2 (Cortex Left)
    SI->>CB: raise_flag(BASAL_CORTEX_LEFT_SCORE_CHANGED, key)
    CB->>Q: Queue event
    
    Note over Q: Rerun
    
    Q-->>H: handle_basal_cortex_left_score_changed(state, value)
    H->>IS: basal_score_cortex_left = 2
    H->>H: reimplement_score_fields_in_session()
    H->>H: update_region_value()
    
    U->>SI: Enter 3 (Cortex Right)
    SI->>CB: raise_flag(BASAL_CORTEX_RIGHT_SCORE_CHANGED, key)
    
    Note over Q: Rerun
    
    Q-->>H: handle_basal_cortex_right_score_changed(state, value)
    H->>IS: basal_score_cortex_right = 3
    H->>H: Check all scores filled?
    
    alt All scores filled
        H->>SD: modify_status(uuid, COMPLETED)
        H->>H: validate_slices()
        H->>SetD: mark_status(set_uuid, VALID/INVALID)
    end
    
    H-->>U: Update slice status table
```

---

## Submit Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant SB as Submit Button
    participant H as handle_submit
    participant V as Validation
    participant SR as submit_results
    participant API as Evaluation API
    participant DB as Database
    participant SS as Session State

    U->>SB: Click "Submit All Evaluations"
    SB->>H: handle_submit(state)
    
    H->>V: get_invalid_indices(set_status_df)
    V-->>H: invalid_indices
    
    alt Some sets invalid
        H-->>U: Show error (should not happen, button hidden)
    else All valid
        H->>SR: submit_results(state, db_session)
        
        loop For each ImageSetEvaluationSession
            SR->>API: create_image_set_evaluation(set_data)
            API->>DB: INSERT ImageSetEvaluation
            DB-->>API: Success
            
            loop For each ImageEvaluationSession
                SR->>API: create_image_evaluation(image_data)
                API->>DB: INSERT ImageEvaluation
                DB-->>API: Success
            end
        end
        
        SR-->>H: All submitted
        H->>SS: Clear app_state
        H->>SS: Clear selected_scans
        H-->>U: Redirect to Dashboard
    end
```

---

## Image Navigation Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant NB as Next Button
    participant H as handle_next_image
    participant AS as App State
    participant ISS as ImageSetSession
    participant IL as Image Loader
    participant ST as Streamlit

    U->>NB: Click "Next ►"
    NB->>H: handle_next_image(state)
    
    H->>ISS: current_index
    ISS-->>H: 5
    
    H->>ISS: num_images
    ISS-->>H: 25
    
    H->>H: Check 5 < 25-1 ?
    
    alt Can go next
        H->>ISS: current_index = 6
        H-->>ST: Trigger rerender
        
        ST->>IL: dicom_image(path, width, level)
        IL-->>ST: PIL Image
        ST-->>U: Display new slice
    else At last slice
        H-->>U: (Button was disabled, no action)
    end
```

---

## Window Adjustment Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant WW as Window Width Input
    participant WL as Window Level Input
    participant H as Handler
    participant ISS as ImageSetSession
    participant DP as DICOM Processing
    participant ST as Streamlit

    U->>WW: Change width to 100
    WW->>H: handle_windowing_width_changed(state, 100)
    H->>ISS: window_width_current = 100
    
    Note over ST: Rerun
    
    ST->>DP: dicom_image(path, width=100, level=40)
    DP->>DP: load_raw_dicom_image()
    DP->>DP: apply_window(hu, center=40, width=100)
    DP-->>ST: PIL Image (higher contrast)
    ST-->>U: Display adjusted image

    U->>WL: Change level to 60
    WL->>H: handle_windowing_level_changed(state, 60)
    H->>ISS: window_level_current = 60
    
    Note over ST: Rerun
    
    ST->>DP: dicom_image(path, width=100, level=60)
    DP->>DP: apply_window(hu, center=60, width=100)
    DP-->>ST: PIL Image (brighter)
    ST-->>U: Display adjusted image
```

---

## Sequence Notation Reference

| Element | Representation |
|---------|----------------|
| Actor/Object | `participant Name` |
| Synchronous Message | `A->>B: message` |
| Async Message | `A-)B: message` |
| Return | `B-->>A: return` |
| Self-call | `A->>A: method()` |
| Note | `Note over A: text` |
| Alt/Else | `alt condition` ... `else` ... `end` |
| Loop | `loop description` ... `end` |
| Opt (optional) | `opt condition` ... `end` |
| Par (parallel) | `par` ... `and` ... `end` |
| Activation | Rectangle on lifeline |
