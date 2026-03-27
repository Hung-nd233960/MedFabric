# Flowchart

## Overview

Flowcharts show the step-by-step execution flow of processes in the MedFabric system.

---

## Main Application Flow

```mermaid
flowchart TD
    A[Start Application] --> B[Load config.toml]
    B --> C[Initialize Database Engine]
    C --> D[Check Session State]
    
    D --> E{User Logged In?}
    E -->|No| F[Show Login Page]
    E -->|Yes| G[Show Navigation Menu]
    
    F --> H{Login Success?}
    H -->|No| F
    H -->|Yes| I[Create Session]
    I --> G
    
    G --> J{Page Selection}
    J -->|Dashboard| K[Load Dashboard]
    J -->|Labeling| L[Load Labeling Page]
    J -->|Guide| M[Load Guide Page]
    J -->|Logout| N[Clear Session]
    N --> F
    
    K --> O[Display Datasets]
    O --> P{Scans Selected?}
    P -->|No| O
    P -->|Yes| Q[Start Labeling Button]
    Q --> L
    
    L --> R[Initialize Labeling Session]
    R --> S[Enter Event Loop]
    S --> T{Submit Clicked?}
    T -->|No| S
    T -->|Yes| U[Save to Database]
    U --> K

    style A fill:#e8f5e9
    style U fill:#e8f5e9
```

---

## Labeling Page Event Loop

```mermaid
flowchart TD
    A[Enter Labeling Page] --> B[Check app_state exists]
    
    B --> C{app_state exists?}
    C -->|No| D[Initialize Session]
    D --> E[Create LabelingAppState]
    E --> F[Create Status DataFrames]
    C -->|Yes| G[Skip Initialization]
    
    F --> G
    G --> H[Call initial_setup]
    H --> I[Call flag_listener]
    
    I --> J{Queue Empty?}
    J -->|No| K[Dequeue Event]
    K --> L[Lookup Handler]
    L --> M[Execute Handler]
    M --> N[Update State]
    N --> J
    
    J -->|Yes| O[Render Column 1]
    O --> P[Load Image]
    P --> Q[Apply Windowing]
    Q --> R[Display Image]
    
    R --> S[Render Column 2]
    S --> T[Navigation Controls]
    T --> U[Display Controls]
    U --> V[Labeling Controls]
    
    V --> W[Render Column 3]
    W --> X[Set Information Tab]
    X --> Y[Status Tables]
    Y --> Z[Submit Section]
    
    Z --> AA[Wait for User Interaction]
    AA --> AB{Widget Callback?}
    AB -->|Yes| AC[raise_flag]
    AC --> AD[Queue Event]
    AD --> AE[Trigger Rerun]
    AE --> A
    
    AB -->|No| AA

    style A fill:#e3f2fd
    style AE fill:#fff3e0
```

---

## Event Processing Flowchart

```mermaid
flowchart TD
    A[flag_listener Called] --> B[Get Queue Reference]
    B --> C{Queue Empty?}
    
    C -->|Yes| D[Return - Render UI]
    
    C -->|No| E[queue.get_nowait]
    E --> F[Get Event]
    
    F --> G{Event Type?}
    
    G -->|HalfEvent| H[Extract Key]
    H --> I[Get Widget Value]
    I --> J[Create CompletedEvent]
    J --> K[Process Event]
    
    G -->|CompletedEvent| K
    
    K --> L[Lookup in EVENT_DISPATCH]
    L --> M{Handler Found?}
    
    M -->|No| N[Log Warning]
    N --> C
    
    M -->|Yes| O[Get Handler Function]
    O --> P{Needs Data?}
    
    P -->|Yes| Q[Pass event.value]
    P -->|No| R[Call Without Data]
    
    Q --> S[Execute Handler]
    R --> S
    
    S --> T[Handler Modifies State]
    T --> U[Update Status DFs]
    U --> C

    style A fill:#e3f2fd
    style D fill:#e8f5e9
```

---

## Score Entry Flowchart

```mermaid
flowchart TD
    A[User Enters Score] --> B[Widget on_change Triggers]
    B --> C[raise_flag Called]
    C --> D[Queue HalfEvent]
    D --> E[Streamlit Reruns]
    
    E --> F[flag_listener Processes]
    F --> G[Resolve Widget Value]
    G --> H[Create CompletedEvent]
    
    H --> I[Dispatch to Handler]
    I --> J[Update ImageEvaluationSession]
    
    J --> K{Score Value None?}
    K -->|Yes| L[Clear Score Field]
    K -->|No| M[Set Score Value]
    
    L --> N[reimplement_score_fields_in_session]
    M --> N
    
    N --> O[Check All Scores Filled]
    O --> P{All Required Scores?}
    
    P -->|No| Q[Status = INCOMPLETED]
    P -->|Yes| R[Status = COMPLETED]
    
    Q --> S[update_region_value]
    R --> S
    
    S --> T[Update slice_status_df]
    T --> U[validate_slices]
    
    U --> V{Valid?}
    V -->|Yes| W[Set Status = VALID]
    V -->|No| X[Set Status = INVALID]
    
    W --> Y[Update set_status_df]
    X --> Y
    
    Y --> Z[Render Updated UI]

    style A fill:#e3f2fd
    style Z fill:#e8f5e9
```

---

## Region Selection Flowchart

```mermaid
flowchart TD
    A[User Selects Region] --> B[Segmented Control Changes]
    B --> C[raise_flag REGION_SELECTED]
    C --> D[Process Event]
    
    D --> E[Get New Region Value]
    E --> F{New Region = None?}
    
    F -->|Yes| G[Clear All Scores]
    G --> H[Remove from slice_status_df]
    H --> I[Hide Score Inputs]
    
    F -->|No| J{Was Previous None?}
    
    J -->|Yes| K[Add to slice_status_df]
    J -->|No| L[Update Region in DF]
    
    K --> M[reset_score_fields]
    L --> M
    
    M --> N[Clear Old Score Values]
    N --> O[Set New Region]
    
    O --> P{Region Type?}
    
    P -->|BasalCortex| Q[Show Cortex L/R]
    P -->|BasalCentral| R[Show Cortex + Central L/R]
    P -->|CoronaRadiata| S[Show Corona L/R]
    
    Q --> T[Status = INCOMPLETED]
    R --> T
    S --> T
    
    T --> U[Validate Set]
    I --> U
    
    U --> V[Update set_status_df]
    V --> W[Render Updated UI]

    style A fill:#e3f2fd
    style W fill:#e8f5e9
```

---

## Submit Evaluation Flowchart

```mermaid
flowchart TD
    A[User Clicks Submit] --> B[raise_flag SUBMIT]
    B --> C[handle_submit Called]
    
    C --> D[Get set_status_df]
    D --> E[get_invalid_indices]
    
    E --> F{Any Invalid Sets?}
    F -->|Yes| G[Show Error Message]
    G --> H[Abort Submit]
    
    F -->|No| I[Get Database Session]
    I --> J[Loop Through Sessions]
    
    J --> K[Create ImageSetEvaluationCreate]
    K --> L[Call create_image_set_evaluation]
    L --> M[Get Evaluation UUID]
    
    M --> N[Loop Through Images]
    N --> O{Region != None?}
    
    O -->|No| P[Skip Image]
    O -->|Yes| Q[Create ImageEvaluationCreate]
    
    Q --> R[Call create_image_evaluation]
    R --> S[Save to Database]
    
    S --> T{More Images?}
    T -->|Yes| N
    T -->|No| U{More Sessions?}
    
    P --> T
    
    U -->|Yes| J
    U -->|No| V[Commit Transaction]
    
    V --> W[Clear app_state]
    W --> X[Clear selected_scans]
    X --> Y[Redirect to Dashboard]

    style A fill:#e3f2fd
    style Y fill:#e8f5e9
    style H fill:#ffebee
```

---

## DICOM Image Loading Flowchart

```mermaid
flowchart TD
    A[Request DICOM Image] --> B[dicom_image Called]
    B --> C[load_raw_dicom_image]
    
    C --> D[pydicom.dcmread]
    D --> E{Valid DICOM?}
    
    E -->|No| F[Raise InvalidDicomFileError]
    F --> G[Show Error to User]
    
    E -->|Yes| H[Get pixel_array]
    H --> I[Cast to int16]
    I --> J[Get RescaleSlope]
    J --> K[Get RescaleIntercept]
    
    K --> L[Calculate HU]
    L --> M[hu = img * slope + intercept]
    
    M --> N[apply_window Called]
    N --> O[Calculate Window Bounds]
    O --> P[low = center - width/2]
    P --> Q[high = center + width/2]
    
    Q --> R[np.clip to bounds]
    R --> S[Normalize to 0-255]
    S --> T[Cast to uint8]
    
    T --> U[Create PIL Image]
    U --> V[Return Image]
    
    V --> W[render_image]
    W --> X[st.image Display]

    style A fill:#e3f2fd
    style X fill:#e8f5e9
    style G fill:#ffebee
```

---

## Set Validation Flowchart

```mermaid
flowchart TD
    A[Validate Image Set] --> B[Get image_set_usability]
    
    B --> C{Usability Type?}
    
    C -->|NonIschemic| D[render_score_box_mode = False]
    C -->|Hemorrhagic| D
    C -->|NonNctEvaluable| D
    D --> E[Status = VALID]
    E --> F[Return VALID]
    
    C -->|IschemicAssessable| G[render_score_box_mode = True]
    G --> H[Get slice_status_df]
    
    H --> I[has_required_regions]
    I --> J{Has BC, BCe, CR?}
    
    J -->|No| K[Status = INVALID]
    K --> L[Return INVALID]
    
    J -->|Yes| M[all_completed]
    M --> N{All COMPLETED?}
    
    N -->|No| O[Status = INVALID]
    O --> L
    
    N -->|Yes| P[consecutive_slices]
    P --> Q{Slices Consecutive?}
    
    Q -->|No| R[Set Warning Flag]
    R --> S[Status = VALID with Warning]
    
    Q -->|Yes| T[Status = VALID]
    
    S --> U[Return VALID]
    T --> U

    style A fill:#e3f2fd
    style F fill:#e8f5e9
    style U fill:#e8f5e9
    style L fill:#ffebee
```

---

## Navigation Flowchart

```mermaid
flowchart TD
    subgraph "Slice Navigation"
        A1[Next Slice Button] --> B1{current < num-1?}
        B1 -->|Yes| C1[current_index += 1]
        B1 -->|No| D1[Button Disabled]
        
        A2[Prev Slice Button] --> B2{current > 0?}
        B2 -->|Yes| C2[current_index -= 1]
        B2 -->|No| D2[Button Disabled]
        
        A3[Slice Slider] --> B3[Jump to index - 1]
    end
    
    subgraph "Set Navigation"
        A4[Next Set Button] --> B4{session_index < len-1?}
        B4 -->|Yes| C4[session_index += 1]
        B4 -->|No| D4[Button Disabled]
        
        A5[Prev Set Button] --> B5{session_index > 0?}
        B5 -->|Yes| C5[session_index -= 1]
        B5 -->|No| D5[Button Disabled]
        
        A6[Set Slider] --> B6[Jump to index - 1]
    end
    
    C1 --> E[Load New Slice Image]
    C2 --> E
    B3 --> E
    
    C4 --> F[Load New Set]
    C5 --> F
    B6 --> F
    
    F --> G[Reset to Slice 0]
    G --> E

    style A1 fill:#e3f2fd
    style A2 fill:#e3f2fd
    style A3 fill:#e3f2fd
    style A4 fill:#fff3e0
    style A5 fill:#fff3e0
    style A6 fill:#fff3e0
```

---

## Flowchart Symbols Reference

| Symbol | Meaning |
|--------|---------|
| Rounded Rectangle | Start/End (Terminal) |
| Rectangle | Process/Action |
| Diamond | Decision |
| Parallelogram | Input/Output |
| Arrow | Flow Direction |
| Dotted Line | Alternative Flow |

---

## Decision Summary

| Decision Point | True Path | False Path |
|----------------|-----------|------------|
| User Logged In? | Show Dashboard | Show Login |
| app_state exists? | Skip Init | Initialize |
| Queue Empty? | Render UI | Process Event |
| Handler Found? | Execute | Log Warning |
| All Scores Filled? | COMPLETED | INCOMPLETED |
| Has Required Regions? | Check Completed | INVALID |
| Slices Consecutive? | Clean VALID | VALID with Warning |
| Any Invalid Sets? | Show Error | Submit All |
| Valid DICOM? | Process | Show Error |
