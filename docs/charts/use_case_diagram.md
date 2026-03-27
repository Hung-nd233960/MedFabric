# Use Case Diagram

## Overview

This diagram shows the interactions between actors (users) and the MedFabric system.

---

## Mermaid Diagram

```mermaid
graph TB
    subgraph Actors
        D[👨‍⚕️ Doctor/Radiologist]
        A[👤 Administrator]
    end

    subgraph "MedFabric System"
        subgraph "Authentication"
            UC1((Login))
            UC2((Logout))
            UC3((Register Account))
        end

        subgraph "Dataset Management"
            UC4((View Available Datasets))
            UC5((Select CT Scans for Labeling))
            UC6((Import New Dataset))
        end

        subgraph "CT Scan Labeling"
            UC7((View CT Slice))
            UC8((Navigate Between Slices))
            UC9((Adjust Window/Level))
            UC10((Select Brain Region))
            UC11((Enter ASPECTS Scores))
            UC12((Mark Set as Low Quality))
            UC13((Mark Set as Non-Ischemic))
            UC14((Add Notes))
        end

        subgraph "Session Management"
            UC15((Navigate Between Sets))
            UC16((View Validation Status))
            UC17((Submit Evaluations))
        end

        subgraph "Data Access"
            UC18((View User Guide))
        end
    end

    %% Doctor interactions
    D --> UC1
    D --> UC2
    D --> UC4
    D --> UC5
    D --> UC7
    D --> UC8
    D --> UC9
    D --> UC10
    D --> UC11
    D --> UC12
    D --> UC13
    D --> UC14
    D --> UC15
    D --> UC16
    D --> UC17
    D --> UC18

    %% Administrator interactions
    A --> UC1
    A --> UC2
    A --> UC3
    A --> UC6
    A --> UC4

    %% Include relationships
    UC7 -.->|includes| UC8
    UC7 -.->|includes| UC9
    UC10 -.->|includes| UC11
    UC17 -.->|requires| UC16

    %% Extend relationships
    UC11 -.->|extends| UC14
    UC5 -.->|extends| UC7

    style D fill:#e1f5fe
    style A fill:#fff3e0
```

---

## Use Case Descriptions

### UC1: Login

| Field | Description |
|-------|-------------|
| **Actor** | Doctor, Administrator |
| **Description** | User authenticates with username and password |
| **Precondition** | User has registered account |
| **Main Flow** | 1. User enters credentials<br>2. System validates credentials<br>3. System creates session<br>4. User is redirected to dashboard |
| **Alternative Flow** | 2a. Invalid credentials → Show error |
| **Postcondition** | User session is active |

### UC5: Select CT Scans for Labeling

| Field | Description |
|-------|-------------|
| **Actor** | Doctor |
| **Description** | Doctor selects one or more CT scans to evaluate |
| **Precondition** | User is logged in, datasets are available |
| **Main Flow** | 1. View available datasets<br>2. Expand dataset to see image sets<br>3. Select image sets via checkboxes<br>4. Click "Start Labeling" |
| **Postcondition** | Selected scans loaded into labeling session |

### UC10: Select Brain Region

| Field | Description |
|-------|-------------|
| **Actor** | Doctor |
| **Description** | Doctor assigns a brain region to current CT slice |
| **Precondition** | CT slice is displayed |
| **Main Flow** | 1. View current slice<br>2. Identify anatomical region<br>3. Select region from segmented control<br>4. Region is saved to slice |
| **Options** | Basal Cortex, Basal Central, Corona Radiata, None |
| **Postcondition** | Slice region is assigned, score fields appear |

### UC11: Enter ASPECTS Scores

| Field | Description |
|-------|-------------|
| **Actor** | Doctor |
| **Description** | Doctor enters ASPECTS scores for slice |
| **Precondition** | Brain region is selected (not None) |
| **Main Flow** | 1. Score inputs appear based on region<br>2. Enter left hemisphere score<br>3. Enter right hemisphere score<br>4. Scores saved to session |
| **Validation** | Values must be 0-10 for cortex/central, 0-6 for corona |
| **Postcondition** | Slice marked as COMPLETED |

### UC17: Submit Evaluations

| Field | Description |
|-------|-------------|
| **Actor** | Doctor |
| **Description** | Doctor submits all completed evaluations |
| **Precondition** | All image sets are VALID |
| **Main Flow** | 1. All sets show VALID status<br>2. Click "Submit All Evaluations"<br>3. System saves to database<br>4. Redirect to dashboard |
| **Alternative Flow** | 1a. Some sets INVALID → Submit button hidden |
| **Postcondition** | Evaluations persisted to database |

---

## Actor Descriptions

### Doctor/Radiologist

- Primary user of the system
- Reviews CT scans for ischemic stroke assessment
- Assigns brain regions and ASPECTS scores
- Submits completed evaluations

### Administrator

- Manages user accounts
- Imports new datasets
- Has read access to all data
- Cannot perform medical evaluations

---

## UML Text Notation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MedFabric System                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Authentication                                │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────────────┐                  │   │
│  │  │  Login  │    │ Logout  │    │ Register Account│                  │   │
│  │  └─────────┘    └─────────┘    └─────────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      CT Scan Labeling                                │   │
│  │  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐        │   │
│  │  │ View CT Slice│  │ Select Region   │  │ Enter Scores     │        │   │
│  │  └──────────────┘  └─────────────────┘  └──────────────────┘        │   │
│  │                                                                      │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐        │   │
│  │  │ Adjust Window  │  │ Navigate Slice │  │ Mark Low Quality│        │   │
│  │  └────────────────┘  └────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Session Management                               │   │
│  │  ┌─────────────────┐  ┌────────────────┐  ┌────────────────────┐    │   │
│  │  │ Navigate Sets   │  │ View Status    │  │ Submit Evaluations │    │   │
│  │  └─────────────────┘  └────────────────┘  └────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

        ┌─────────┐                                     ┌───────────────┐
        │ Doctor  │─────────────────────────────────────│ Administrator │
        └─────────┘                                     └───────────────┘
```

---

## Relationships

### Include Relationships (<<include>>)

- View CT Slice **includes** Navigate Between Slices
- View CT Slice **includes** Adjust Window/Level
- Select Brain Region **includes** Enter ASPECTS Scores

### Extend Relationships (<<extend>>)

- Enter ASPECTS Scores **extends** Add Notes
- Select CT Scans **extends** View CT Slice

### Generalization

- Doctor and Administrator both **inherit** basic authentication capabilities
