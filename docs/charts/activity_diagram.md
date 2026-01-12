# Activity Diagram

## Overview

Activity diagrams show the workflow and decision points in the MedFabric labeling process.

---

## Complete Labeling Workflow

```mermaid
flowchart TD
    Start([Start]) --> Login[Login Page]
    Login --> ValidCreds{Valid Credentials?}
    ValidCreds -->|No| LoginError[Show Error]
    LoginError --> Login
    ValidCreds -->|Yes| Dashboard[Dashboard Page]

    Dashboard --> SelectDataset[Select Dataset]
    SelectDataset --> SelectScans[Select CT Scans]
    SelectScans --> StartLabeling[Click Start Labeling]
    StartLabeling --> InitSession[Initialize Labeling Session]

    InitSession --> LoadSets[Load Selected Image Sets]
    LoadSets --> LoadSlices[Load All Slices per Set]
    LoadSlices --> CreateState[Create LabelingAppState]
    CreateState --> LabelingPage[Enter Labeling Page]

    LabelingPage --> DisplaySlice[Display Current CT Slice]
    DisplaySlice --> UserAction{User Action?}

    %% Navigation Actions
    UserAction -->|Next/Prev Slice| NavigateSlice[Update Slice Index]
    NavigateSlice --> DisplaySlice

    UserAction -->|Next/Prev Set| NavigateSet[Update Set Index]
    NavigateSet --> DisplaySlice

    UserAction -->|Adjust Window| UpdateWindow[Update Window Values]
    UpdateWindow --> DisplaySlice

    %% Labeling Actions
    UserAction -->|Select Region| SelectRegion[Assign Region to Slice]
    SelectRegion --> UpdateSliceDF[Add/Update Slice Status DF]
    UpdateSliceDF --> ShowScores[Show Score Inputs]
    ShowScores --> DisplaySlice

    UserAction -->|Enter Score| EnterScore[Update Score Value]
    EnterScore --> CheckComplete{All Scores Entered?}
    CheckComplete -->|No| DisplaySlice
    CheckComplete -->|Yes| MarkComplete[Mark Slice COMPLETED]
    MarkComplete --> ValidateSet[Validate Current Set]
    ValidateSet --> UpdateSetDF[Update Set Status DF]
    UpdateSetDF --> DisplaySlice

    %% Set-Level Actions
    UserAction -->|Mark Non-Ischemic| MarkNonIschemic[Set Usability = NonIschemic]
    MarkNonIschemic --> AutoValid[Auto-Validate Set]
    AutoValid --> UpdateSetDF

    UserAction -->|Mark Low Quality| MarkLowQuality[Toggle Low Quality Flag]
    MarkLowQuality --> DisplaySlice

    %% Submission
    UserAction -->|Submit| CheckAllValid{All Sets Valid?}
    CheckAllValid -->|No| ShowWarning[Show Invalid Sets Warning]
    ShowWarning --> DisplaySlice
    CheckAllValid -->|Yes| SubmitDB[Submit to Database]
    SubmitDB --> Success[Show Success Message]
    Success --> Dashboard

    %% Exit
    UserAction -->|Logout| ConfirmLogout[Confirm Logout]
    ConfirmLogout --> ClearSession[Clear Session State]
    ClearSession --> Login

    style Start fill:#e8f5e9
    style Success fill:#e8f5e9
    style LoginError fill:#ffebee
    style ShowWarning fill:#fff3e0
```

---

## Slice Labeling Sub-Activity

```mermaid
flowchart TD
    Start([Enter Slice]) --> HasRegion{Region Selected?}
    
    HasRegion -->|No| ShowRegionControl[Display Region Selector]
    ShowRegionControl --> WaitRegion[/Wait for Input/]
    WaitRegion --> RegionSelected[User Selects Region]
    RegionSelected --> RegionNone{Region = None?}
    
    RegionNone -->|Yes| ClearScores[Clear All Scores]
    ClearScores --> RemoveFromDF[Remove from Slice Status DF]
    RemoveFromDF --> End([Done])
    
    RegionNone -->|No| AddToDF[Add to Slice Status DF]
    AddToDF --> ShowScoreInputs[Show Score Input Fields]
    ShowScoreInputs --> HasRegion
    
    HasRegion -->|Yes| CheckRegionType{Region Type?}
    
    CheckRegionType -->|Basal Cortex| ShowCortex[Show Cortex L/R Inputs]
    CheckRegionType -->|Basal Central| ShowCentral[Show Cortex + Central L/R]
    CheckRegionType -->|Corona Radiata| ShowCorona[Show Corona L/R Inputs]
    
    ShowCortex --> EnterScores[/Enter Scores/]
    ShowCentral --> EnterScores
    ShowCorona --> EnterScores
    
    EnterScores --> AllFilled{All Required Scores Filled?}
    AllFilled -->|No| WaitScore[/Wait for Input/]
    WaitScore --> EnterScores
    
    AllFilled -->|Yes| MarkSliceComplete[Status = COMPLETED]
    MarkSliceComplete --> CheckSetValid[Check Set Validation]
    CheckSetValid --> End
    
    style Start fill:#e3f2fd
    style End fill:#e3f2fd
```

---

## Set Validation Sub-Activity

```mermaid
flowchart TD
    Start([Validate Set]) --> CheckUsability{Usability Type?}
    
    CheckUsability -->|IschemicAssessable| CheckRegions{Has All 3 Regions?}
    CheckUsability -->|NonIschemic| AutoValid1[Set = VALID]
    CheckUsability -->|Hemorrhagic| AutoValid2[Set = VALID]
    CheckUsability -->|NonNctEvaluable| AutoValid3[Set = VALID]
    
    AutoValid1 --> End([Done])
    AutoValid2 --> End
    AutoValid3 --> End
    
    CheckRegions -->|No| SetInvalid1[Set = INVALID]
    SetInvalid1 --> ShowMissingRegions[Show Missing Regions Warning]
    ShowMissingRegions --> End
    
    CheckRegions -->|Yes| CheckComplete{All Slices COMPLETED?}
    
    CheckComplete -->|No| SetInvalid2[Set = INVALID]
    SetInvalid2 --> ShowIncomplete[Show Incomplete Slices Warning]
    ShowIncomplete --> End
    
    CheckComplete -->|Yes| CheckConsecutive{Slices Consecutive?}
    
    CheckConsecutive -->|No| ShowConsecWarning[Show Non-Consecutive Warning]
    ShowConsecWarning --> SetValid[Set = VALID with Warning]
    
    CheckConsecutive -->|Yes| SetValid2[Set = VALID]
    SetValid --> End
    SetValid2 --> End
    
    style Start fill:#fff3e0
    style End fill:#fff3e0
    style SetInvalid1 fill:#ffebee
    style SetInvalid2 fill:#ffebee
    style SetValid fill:#e8f5e9
    style SetValid2 fill:#e8f5e9
```

---

## Event Processing Activity

```mermaid
flowchart TD
    Start([Script Run]) --> InitFlags[Initialize EventFlags Queue]
    InitFlags --> CheckQueue{Events in Queue?}
    
    CheckQueue -->|No| RenderUI[Render UI Components]
    
    CheckQueue -->|Yes| DequeueEvent[Dequeue Event]
    DequeueEvent --> CheckEventType{Event Type?}
    
    CheckEventType -->|HalfEvent| GetWidgetValue[Get Widget Value from Key]
    GetWidgetValue --> CreateComplete[Create CompletedEvent]
    CreateComplete --> ProcessEvent
    
    CheckEventType -->|CompletedEvent| ProcessEvent[Lookup Handler in EVENT_DISPATCH]
    
    ProcessEvent --> ExecuteHandler[Execute Handler Function]
    ExecuteHandler --> UpdateState[Update App State]
    UpdateState --> UpdateStatusDFs[Update Status DataFrames]
    UpdateStatusDFs --> CheckQueue
    
    RenderUI --> RegisterCallbacks[Register Widget Callbacks]
    RegisterCallbacks --> DisplayWidgets[Display All Widgets]
    DisplayWidgets --> WaitInteraction[/Wait for User Interaction/]
    
    WaitInteraction --> CallbackTriggered[Callback: raise_flag()]
    CallbackTriggered --> QueueEvent[Add Event to EventFlags]
    QueueEvent --> TriggerRerun[Streamlit Reruns Script]
    TriggerRerun --> Start
    
    style Start fill:#e3f2fd
    style QueueEvent fill:#fff3e0
    style TriggerRerun fill:#fff3e0
```

---

## Swimlane Diagram (Cross-Functional)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              LABELING WORKFLOW                                       │
├─────────────────┬─────────────────────┬─────────────────────┬───────────────────────┤
│     User        │      UI Layer       │    State Layer      │    Database Layer     │
├─────────────────┼─────────────────────┼─────────────────────┼───────────────────────┤
│                 │                     │                     │                       │
│ ○ Start         │                     │                     │                       │
│ │               │                     │                     │                       │
│ ▼               │                     │                     │                       │
│ Enter Credentials───▶ Login Form      │                     │                       │
│                 │     │               │                     │                       │
│                 │     ▼               │                     │                       │
│                 │ Validate ──────────────────────────────────────▶ Check Credentials │
│                 │     │               │                     │         │             │
│                 │     ◄───────────────────────────────────────────────┘             │
│                 │     │               │                     │                       │
│ ◄────────────────── Dashboard         │                     │                       │
│                 │                     │                     │                       │
│ Select Scans ──────▶ Checkbox Grid    │                     │                       │
│                 │     │               │                     │                       │
│ Start Labeling ────▶ Button Click     │                     │                       │
│                 │     │               │                     │                       │
│                 │     └──────────────────▶ Initialize       │                       │
│                 │                     │   Session           │                       │
│                 │                     │     │               │                       │
│                 │                     │     └──────────────────────▶ Load ImageSets │
│                 │                     │     ◄────────────────────────────┘          │
│                 │                     │     │               │                       │
│                 │                     │ Create State        │                       │
│                 │                     │     │               │                       │
│                 │ ◄───────────────────────┘                 │                       │
│ ◄────────────────── Labeling Page     │                     │                       │
│                 │                     │                     │                       │
│ Click Widget ─────▶ Callback          │                     │                       │
│                 │     │               │                     │                       │
│                 │     └──────────────────▶ Queue Event      │                       │
│                 │                     │     │               │                       │
│                 │ Rerun ◄─────────────────┘                 │                       │
│                 │     │               │                     │                       │
│                 │     └──────────────────▶ Process Event    │                       │
│                 │                     │     │               │                       │
│                 │                     │ Update State        │                       │
│                 │                     │     │               │                       │
│                 │ ◄───────────────────────┘                 │                       │
│ ◄────────────────── Render Updated UI │                     │                       │
│                 │                     │                     │                       │
│ Submit ────────────▶ Submit Button    │                     │                       │
│                 │     │               │                     │                       │
│                 │     └──────────────────▶ Validate         │                       │
│                 │                     │     │               │                       │
│                 │                     │     └──────────────────────▶ Save Results   │
│                 │                     │                     │         │             │
│                 │ ◄─────────────────────────────────────────────────┘               │
│ ◄────────────────── Success           │                     │                       │
│                 │                     │                     │                       │
│ ● End           │                     │                     │                       │
│                 │                     │                     │                       │
└─────────────────┴─────────────────────┴─────────────────────┴───────────────────────┘
```

---

## Activity Notation Legend

| Symbol | Meaning |
|--------|---------|
| ○ | Initial State |
| ● | Final State |
| ◇ | Decision Point |
| ▭ | Action/Activity |
| ⬚ | Sub-Activity |
| ═══ | Swimlane Boundary |
| /text/ | Wait State/Delay |
| ──▶ | Control Flow |
| - - ▶ | Object Flow |
