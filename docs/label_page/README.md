# Labeling Page Architecture Documentation

## Overview

The Labeling Page (`medfabric/pages/label.py`) is the most complex component of the MedFabric system. It implements a **novel event-driven dispatcher pattern** specifically designed to work within Streamlit's unique execution model.

This documentation is split into multiple files for clarity:

| Document | Description |
|----------|-------------|
| [01_architecture_overview.md](01_architecture_overview.md) | High-level architecture and design rationale |
| [02_state_management.md](02_state_management.md) | State management system with EventFlags and LabelingAppState |
| [03_dispatcher_pattern.md](03_dispatcher_pattern.md) | The event dispatcher pattern and handler implementations |
| [04_session_initialization.md](04_session_initialization.md) | Session data structures and initialization flow |
| [05_ui_components.md](05_ui_components.md) | UI rendering functions and component breakdown |
| [06_image_processing.md](06_image_processing.md) | DICOM/JPEG image loading and windowing |

## UML Diagrams

All UML diagrams are located in the [../charts/](../charts/) directory:

| Diagram | Type | Description |
|---------|------|-------------|
| [use_case_diagram.md](../charts/use_case_diagram.md) | Use Case | Actor interactions with the labeling system |
| [activity_diagram.md](../charts/activity_diagram.md) | Activity | Workflow and decision points |
| [sequence_diagram.md](../charts/sequence_diagram.md) | Sequence | Object interactions over time |
| [state_diagram.md](../charts/state_diagram.md) | State Machine | Application state transitions |
| [class_diagram.md](../charts/class_diagram.md) | Class | Data structures and relationships |
| [component_diagram.md](../charts/component_diagram.md) | Component | System component architecture |
| [flowchart.md](../charts/flowchart.md) | Flowchart | Execution flow and logic |

## Why This Pattern?

### The Streamlit Challenge

Streamlit's execution model presents unique challenges:

1. **Full Script Re-execution**: Every user interaction triggers a complete re-run of the script
2. **State Volatility**: Local variables are lost between reruns
3. **Widget Key Conflicts**: Dynamic UIs require careful key management
4. **Callback Timing**: `on_change` callbacks execute *before* the main script

### The Solution: Event Queue + Dispatcher

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT RERUN CYCLE                         │
│                                                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  User    │───▶│ Callback │───▶│  Queue   │───▶│ Dispatch │  │
│  │  Click   │    │ raise_   │    │  Event   │    │  Handler │  │
│  │          │    │  flag()  │    │          │    │          │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                        │         │
│                                                        ▼         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Script Execution                       │   │
│  │  1. flag_listener() processes queued event               │   │
│  │  2. Handler updates app_state                             │   │
│  │  3. UI renders with new state                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

To understand this system, read the documents in order:

1. Start with **Architecture Overview** for the big picture
2. Read **State Management** to understand data structures
3. Study **Dispatcher Pattern** for the core innovation
4. Review **Session Initialization** for data flow
5. Explore **UI Components** for rendering logic
6. Check **Image Processing** for medical imaging specifics

## Key Concepts

| Concept | Description |
|---------|-------------|
| **EventFlags** | Queue-based event buffer surviving Streamlit reruns |
| **EventType** | Enum defining all possible user interactions |
| **CompletedEvent** | Event with associated payload (widget value) |
| **HalfEvent** | Event without payload (button clicks) |
| **Dispatcher** | Dictionary mapping EventType to handler functions |
| **LabelingAppState** | Central state container for all labeling data |
| **EnumKeyManager** | Generates unique, parseable widget keys |
