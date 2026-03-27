# UML Diagrams

## Overview

This directory contains comprehensive UML diagrams documenting the MedFabric system architecture and behavior. All diagrams use Mermaid syntax for native GitHub/GitLab rendering.

---

## Diagram Index

| Diagram | Purpose | Key Content |
|---------|---------|-------------|
| [Use Case Diagram](use_case_diagram.md) | Who uses the system and what they do | Actors, use cases, relationships |
| [Activity Diagram](activity_diagram.md) | Workflow and decision points | Complete labeling workflow, swimlanes |
| [Sequence Diagram](sequence_diagram.md) | Object interactions over time | Login, labeling, event handling sequences |
| [State Diagram](state_diagram.md) | State machines and transitions | Slice, set, and session states |
| [Class Diagram](class_diagram.md) | Data structures and relationships | All dataclasses, ORM models, enums |
| [Component Diagram](component_diagram.md) | System organization | Layers, packages, dependencies |
| [Flowchart](flowchart.md) | Execution flow | Event loop, score entry, submission |

---

## Quick Links by Topic

### User Interactions

- [Use Case: Labeling Workflow](use_case_diagram.md#uc10-select-brain-region)
- [Activity: Complete Labeling Workflow](activity_diagram.md#complete-labeling-workflow)
- [Sequence: Score Entry](sequence_diagram.md#score-entry-sequence)

### Event System (Novel Dispatcher Pattern)

- [Sequence: Event Handling](sequence_diagram.md#event-handling-sequence)
- [Activity: Event Processing](activity_diagram.md#event-processing-activity)
- [State: Event Queue States](state_diagram.md#event-queue-state-machine)
- [Flowchart: Event Loop](flowchart.md#labeling-page-event-loop)

### Data Model

- [Class: Core Data Models](class_diagram.md#core-data-models)
- [Class: Database ORM](class_diagram.md#database-orm-models)
- [Class: Pydantic Schemas](class_diagram.md#pydantic-models-api-layer)

### System Architecture

- [Component: System Architecture](component_diagram.md#system-architecture)
- [Component: Package Structure](component_diagram.md#package-diagram)
- [Component: Deployment](component_diagram.md#deployment-diagram)

### State Management

- [State: Image Set Evaluation](state_diagram.md#image-set-evaluation-state-machine)
- [State: Slice Evaluation](state_diagram.md#slice-evaluation-state-machine)
- [State: Page Navigation](state_diagram.md#page-navigation-state-machine)

---

## Diagram Types Explained

### Behavioral Diagrams

| Type | Shows | When to Use |
|------|-------|-------------|
| **Use Case** | System capabilities from user perspective | Requirements, feature planning |
| **Activity** | Workflow with decisions and parallel paths | Process documentation |
| **Sequence** | Object interactions in time order | API design, debugging |
| **State** | Object lifecycle and transitions | Complex state logic |

### Structural Diagrams

| Type | Shows | When to Use |
|------|-------|-------------|
| **Class** | Data structures and relationships | Data model design |
| **Component** | System modules and dependencies | Architecture documentation |

### Process Diagrams

| Type | Shows | When to Use |
|------|-------|-------------|
| **Flowchart** | Step-by-step execution logic | Algorithm documentation |

---

## Mermaid Rendering

All diagrams use [Mermaid](https://mermaid.js.org/) syntax. To view:

1. **GitHub/GitLab**: Renders automatically in markdown preview
2. **VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **Local**: Use `npx mermaid-cli` or [Mermaid Live Editor](https://mermaid.live/)

---

## Related Documentation

- [Label Page Architecture](../label_page/README.md) - Detailed component documentation
- [System Documentation](../SYSTEM_DOCUMENTATION.md) - Complete system overview
- [User Guide](../UserGuide.md) - End-user documentation
