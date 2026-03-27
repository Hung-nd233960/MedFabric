# State Diagram

## Overview

State diagrams show the different states an object or system can be in and the transitions between those states.

---

## Image Set Evaluation State Machine

```mermaid
stateDiagram-v2
    [*] --> NotStarted: Initialize

    NotStarted --> InProgress: First region selected
    
    InProgress --> InProgress: Add region
    InProgress --> InProgress: Enter score
    InProgress --> InProgress: Navigate slices
    
    InProgress --> MissingRegions: Check validation
    InProgress --> IncompleteScores: Check validation
    InProgress --> Valid: All criteria met

    MissingRegions --> InProgress: Add missing region
    IncompleteScores --> InProgress: Enter scores
    
    Valid --> Submitted: Submit
    Valid --> InProgress: Modify scores

    Submitted --> [*]: Complete

    state InProgress {
        [*] --> Labeling
        Labeling --> Labeling: Edit slice
        Labeling --> Validating: Request validation
        Validating --> Labeling: Continue editing
    }

    note right of NotStarted
        No regions selected
        No scores entered
        Status: INVALID
    end note

    note right of Valid
        Has all 3 regions
        All slices COMPLETED
        Status: VALID
    end note
```

---

## Slice Evaluation State Machine

```mermaid
stateDiagram-v2
    [*] --> Unassigned: Load slice

    Unassigned --> RegionSelected: Select region
    RegionSelected --> Unassigned: Clear region (None)
    
    RegionSelected --> PartialScores: Enter first score
    PartialScores --> PartialScores: Enter additional score
    PartialScores --> Completed: All scores filled
    
    Completed --> PartialScores: Clear a score
    Completed --> Unassigned: Clear region

    state RegionSelected {
        [*] --> BasalCortex
        [*] --> BasalCentral
        [*] --> CoronaRadiata
        
        BasalCortex --> BasalCentral: Change region
        BasalCortex --> CoronaRadiata: Change region
        BasalCentral --> BasalCortex: Change region
        BasalCentral --> CoronaRadiata: Change region
        CoronaRadiata --> BasalCortex: Change region
        CoronaRadiata --> BasalCentral: Change region
    }

    note left of Unassigned
        region = None
        status = not tracked
    end note

    note right of Completed
        All required scores filled
        status = COMPLETED
    end note
```

---

## Event Queue State Machine

```mermaid
stateDiagram-v2
    [*] --> Empty: Initialize

    Empty --> HasEvents: raise_flag() called
    
    HasEvents --> Processing: flag_listener() starts
    
    Processing --> Processing: Dequeue & handle event
    Processing --> Empty: Queue exhausted
    
    state Processing {
        [*] --> Dequeue
        Dequeue --> CheckType: Get event
        
        CheckType --> ResolveValue: HalfEvent
        CheckType --> Dispatch: CompletedEvent
        
        ResolveValue --> Dispatch: Create CompletedEvent
        
        Dispatch --> Execute: Lookup handler
        Execute --> UpdateState: Call handler
        UpdateState --> Dequeue: More events?
        UpdateState --> [*]: Queue empty
    }

    note right of HasEvents
        Events queued by callbacks
        Waiting for script rerun
    end note
```

---

## Session Usability State Machine

```mermaid
stateDiagram-v2
    [*] --> IschemicAssessable: Default

    IschemicAssessable --> NonIschemic: Set usability
    IschemicAssessable --> Hemorrhagic: Set usability
    IschemicAssessable --> NonNctEvaluable: Set usability
    
    NonIschemic --> IschemicAssessable: Change back
    Hemorrhagic --> IschemicAssessable: Change back
    NonNctEvaluable --> IschemicAssessable: Change back

    state IschemicAssessable {
        [*] --> RequiresScoring
        RequiresScoring --> HasBasalCortex: Add BC slice
        RequiresScoring --> HasBasalCentral: Add BCe slice
        RequiresScoring --> HasCorona: Add CR slice
        
        HasBasalCortex --> HasTwoRegions: Add 2nd region
        HasBasalCentral --> HasTwoRegions: Add 2nd region
        HasCorona --> HasTwoRegions: Add 2nd region
        
        HasTwoRegions --> HasAllRegions: Add 3rd region
        HasAllRegions --> Valid: All COMPLETED
    }

    state NonIschemic {
        [*] --> AutoValid
        AutoValid: No scoring required
    }

    state Hemorrhagic {
        [*] --> AutoValid2
        AutoValid2: No scoring required
    }

    state NonNctEvaluable {
        [*] --> AutoValid3
        AutoValid3: No scoring required
    }

    note left of IschemicAssessable
        render_score_box_mode = True
        Requires full ASPECTS scoring
    end note

    note right of NonIschemic
        render_score_box_mode = False
        Automatically valid
    end note
```

---

## Page Navigation State Machine

```mermaid
stateDiagram-v2
    [*] --> LoginPage: App Start

    LoginPage --> DashboardPage: Successful login
    LoginPage --> LoginPage: Failed login
    LoginPage --> RegisterPage: Click register
    
    RegisterPage --> LoginPage: Registration complete
    RegisterPage --> RegisterPage: Validation error
    
    DashboardPage --> LabelingPage: Start labeling
    DashboardPage --> GuidePage: View guide
    DashboardPage --> LoginPage: Logout
    
    LabelingPage --> DashboardPage: Submit evaluations
    LabelingPage --> DashboardPage: Cancel/Exit
    LabelingPage --> LoginPage: Logout
    
    GuidePage --> DashboardPage: Back

    state LabelingPage {
        [*] --> ViewingSlice
        
        ViewingSlice --> ViewingSlice: Navigate slices
        ViewingSlice --> ViewingSlice: Navigate sets
        ViewingSlice --> ViewingSlice: Label slice
        ViewingSlice --> ViewingSlice: Adjust display
        
        ViewingSlice --> Submitting: Click submit
        Submitting --> ViewingSlice: Validation failed
        Submitting --> [*]: Submit success
    }
```

---

## DICOM Windowing State

```mermaid
stateDiagram-v2
    [*] --> Default: Load image set

    Default --> CustomWidth: Change width
    Default --> CustomLevel: Change level
    
    CustomWidth --> CustomBoth: Change level
    CustomLevel --> CustomBoth: Change width
    
    CustomWidth --> Default: Reset
    CustomLevel --> Default: Reset
    CustomBoth --> Default: Reset
    
    CustomBoth --> CustomBoth: Adjust width
    CustomBoth --> CustomBoth: Adjust level

    note right of Default
        width = 80 (brain window)
        level = 40 (brain window)
    end note

    note right of CustomBoth
        width = user value
        level = user value
        Persists during session
    end note
```

---

## State Transition Tables

### Image Set Status Transitions

| Current State | Trigger | Condition | Next State |
|--------------|---------|-----------|------------|
| INVALID | Region selected | First region | INVALID |
| INVALID | Score entered | Partial | INVALID |
| INVALID | Score completed | Not all regions | INVALID |
| INVALID | All validated | All 3 regions, all complete | VALID |
| VALID | Region cleared | < 3 regions | INVALID |
| VALID | Score cleared | Slice incomplete | INVALID |
| VALID | Submit | All valid | SUBMITTED |

### Slice Status Transitions

| Current State | Trigger | Condition | Next State |
|--------------|---------|-----------|------------|
| (untracked) | Region = None → Other | Any | Added to DF |
| INCOMPLETED | Score entered | Not all filled | INCOMPLETED |
| INCOMPLETED | Score entered | All filled | COMPLETED |
| COMPLETED | Score cleared | Any | INCOMPLETED |
| (any) | Region = None | Any | Removed from DF |

---

## State Pattern Implementation

The MedFabric system doesn't use a formal state machine library but implements state logic through:

1. **Enum-based states**: `SliceStatus`, `SetStatus`, `ImageSetUsability`
2. **DataFrames for tracking**: `slice_status_df`, `set_status_df`
3. **Validation functions**: `validate_slices()`, `has_required_regions()`, `all_completed()`
4. **Event handlers**: State transitions occur within handler functions

```python
# Example: State transition in handler
def handle_basal_cortex_left_score_changed(state: LabelingAppState, value):
    # Update state
    state.current_session.current_image_session.basal_score_cortex_left = value
    
    # Check for state transition
    if all_scores_filled(state.current_session.current_image_session):
        # Transition: INCOMPLETED → COMPLETED
        state.current_session.slice_status_df = modify_status(
            state.current_session.slice_status_df,
            state.current_session.current_image_session.image_uuid,
            SliceStatus.COMPLETED
        )
        
        # Check set-level transition
        if validate_slices(state.current_session.slice_status_df):
            # Transition: INVALID → VALID
            state.set_status_df = mark_status(
                state.set_status_df,
                state.current_session.uuid,
                SetStatus.VALID
            )
```
