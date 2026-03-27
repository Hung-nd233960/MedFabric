# Chapter 2: Literature Review

## Presentation Outline

**Estimated Length**: 8-12 pages  
**Key Purpose**: Survey existing work, identify gaps, justify approach

---

## 2.1 Medical Image Annotation Systems

### 2.1.1 Commercial Solutions

| Tool | Vendor | Strengths | Limitations |
|------|--------|-----------|-------------|
| Labelbox | Labelbox Inc. | Cloud-native, team collaboration | Generic, no DICOM support |
| V7 Darwin | V7 Labs | AI-assisted, video support | Expensive, not medical-focused |
| CVAT | Intel | Open-source, self-hosted | Complex setup, no medical workflow |
| 3D Slicer | Kitware | Full DICOM, 3D support | Desktop only, steep learning curve |
| ITK-SNAP | U Penn | Segmentation-focused | Manual contours, not scoring |

### 2.1.2 Academic/Research Tools

| Tool | Institution | Focus | Gap for This Work |
|------|-------------|-------|-------------------|
| OHIF Viewer | OHIF Foundation | DICOM viewing | No annotation workflow |
| Cornerstone.js | Cornerstone | Web DICOM rendering | Library only, not application |
| RadiAnt | Medixant | Desktop viewer | No web, no annotation |
| ePAD | Stanford | Annotation platform | Complex, research-focused |

### Content to Discuss

1. **Desktop vs Web-Based Tools**
   - Accessibility considerations
   - Installation barriers for clinical staff
   - Data centralization benefits

2. **Generic vs Medical-Specific**
   - DICOM handling complexity
   - Windowing requirements
   - Clinical workflow integration

### Key Reference Papers

```
1. Rubin, D.L., et al. (2008). "ePAD: A semantic annotation platform..."
   - Foundational work on web-based medical annotation
   
2. Fedorov, A., et al. (2012). "3D Slicer as an Image Computing Platform..."
   - Desktop medical imaging standard
   
3. Urban, T., et al. (2017). "LesionTracker: A medical imaging platform..."
   - Web-based lesion tracking approach
```

---

## 2.2 ASPECTS Scoring in Clinical Practice

### 2.2.1 ASPECTS Overview

**Original Paper**: Barber, P.A., et al. (2000). "Validity and reliability of a quantitative computed tomography score in predicting outcome of hyperacute stroke before thrombolytic therapy."

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASPECTS BRAIN REGIONS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GANGLIONIC LEVEL (Basal Ganglia)                               │
│  ├── C: Caudate nucleus                                          │
│  ├── L: Lentiform nucleus                                        │
│  ├── IC: Internal capsule                                        │
│  ├── I: Insular ribbon                                           │
│  ├── M1: Anterior MCA cortex                                     │
│  ├── M2: MCA cortex lateral to insular ribbon                   │
│  └── M3: Posterior MCA cortex                                    │
│                                                                  │
│  SUPRAGANGLIONIC LEVEL (Corona Radiata)                         │
│  ├── M4: Anterior MCA territory                                  │
│  ├── M5: Lateral MCA territory                                   │
│  └── M6: Posterior MCA territory                                 │
│                                                                  │
│  Scoring: 10 - (number of regions with early ischemic changes)  │
│  Range: 0 (complete MCA infarct) to 10 (normal)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2.2 Inter-Rater Reliability Studies

| Study | Finding | Implication |
|-------|---------|-------------|
| Barber et al. (2000) | κ = 0.71-0.89 | Moderate-good agreement |
| Pexman et al. (2001) | Training improves reliability | Need standardized tools |
| Puetz et al. (2009) | Dichotomized (>7 vs ≤7) more reliable | Threshold-based decisions |

### 2.2.3 Automated ASPECTS Systems

| System | Approach | Accuracy | Limitations |
|--------|----------|----------|-------------|
| e-ASPECTS | Deep learning | 80-85% | Black-box, needs validation |
| Brainomix | Commercial AI | Regulatory approved | Proprietary, expensive |
| RAPID ASPECTS | Perfusion-based | High sensitivity | Requires CTP, not NCCT |

### Gap Identified

> "While automated systems exist, there is no open-source, standardized tool for **manual ASPECTS annotation** that can generate **training data** for these AI systems."

---

## 2.3 Web Application Frameworks for Data-Intensive Tools

### 2.3.1 Framework Comparison

| Framework | Type | Strengths | For This Project |
|-----------|------|-----------|------------------|
| React | JS Frontend | Most flexible, huge ecosystem | High complexity, separate backend |
| Vue.js | JS Frontend | Simpler than React | Still needs backend |
| Django | Python Full-stack | Robust, ORM built-in | Heavy, complex templates |
| Flask | Python Micro | Lightweight, flexible | Manual session management |
| **Streamlit** | Python Data App | Rapid development, Python-native | Stateless challenge |
| Gradio | Python ML Demo | Easy ML integration | Limited customization |

### 2.3.2 Streamlit Deep Dive

**Why Streamlit for Medical Imaging?**

1. **Python Ecosystem**
   - Native PyDICOM integration
   - NumPy/PIL image processing
   - No JavaScript for data scientists

2. **Rapid Prototyping**
   - Single-file applications
   - Hot reloading
   - Built-in widgets

3. **Data Science Focus**
   - DataFrame display
   - Plotting integration
   - Session state for ML models

**The Streamlit Challenge**

```python
# Streamlit's Execution Model
# Every interaction reruns the ENTIRE script

import streamlit as st

count = 0  # Reset to 0 on every rerun!

if st.button("Increment"):
    count += 1  # Will always show 1

st.write(f"Count: {count}")  # Always 1
```

### 2.3.3 Existing Streamlit State Solutions

| Pattern | Description | Limitation |
|---------|-------------|------------|
| `st.session_state` | Built-in dictionary | Manual key management |
| `st.experimental_rerun` | Force rerun | No control over timing |
| `on_change` callbacks | Widget-level handlers | Execute before main script |
| `st.form` | Batch submissions | Limited to form context |

### Gap Identified

> "No documented pattern exists for managing **complex, multi-step workflows** with **interdependent state** in Streamlit applications."

---

## 2.4 Event-Driven Architectures

### 2.4.1 Traditional Event-Driven Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| Observer | Objects subscribe to events | GUI frameworks |
| Pub/Sub | Decoupled publishers/subscribers | Message queues |
| Command | Encapsulate actions as objects | Undo/redo systems |
| Event Sourcing | Store state as event sequence | Banking systems |

### 2.4.2 Event-Driven in Web Applications

**Frontend Frameworks**

- React: Virtual DOM reconciliation
- Vue: Reactive data binding
- Svelte: Compile-time reactivity

**Backend Patterns**

- CQRS (Command Query Responsibility Segregation)
- Event-driven microservices
- Webhook-based integrations

### 2.4.3 Inspiration for This Work

```
┌─────────────────────────────────────────────────────────────────┐
│              EVENT-DRIVEN ARCHITECTURE INSPIRATION               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  From Redux (JavaScript):                                        │
│  ├── Single source of truth (store)                             │
│  ├── Actions describe what happened                              │
│  ├── Reducers specify state transitions                         │
│  └── Dispatch mechanism for actions                              │
│                                                                  │
│  Adapted for Streamlit:                                          │
│  ├── LabelingAppState = store                                    │
│  ├── EventType enum = action types                               │
│  ├── Handler functions = reducers                                │
│  └── flag_listener = dispatch loop                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2.5 Database Design for Annotation Systems

### 2.5.1 Annotation Data Models

| Approach | Description | Use Case |
|----------|-------------|----------|
| Document-based | JSON/BSON storage | Flexible schemas |
| Relational | Normalized tables | Structured queries |
| Graph-based | Node-edge relationships | Complex ontologies |

### 2.5.2 Medical Imaging Standards

| Standard | Purpose | Relevance |
|----------|---------|-----------|
| DICOM | Image format + metadata | Primary input format |
| HL7 FHIR | Healthcare data exchange | Future integration |
| AIM (Annotation & Image Markup) | Structured annotations | Output format option |

---

## 2.6 Summary and Research Gap

### Identified Gaps

| Gap | Description | This Work's Contribution |
|-----|-------------|--------------------------|
| **G1** | No open-source ASPECTS annotation tool | MedFabric system |
| **G2** | Streamlit lacks complex state patterns | Event-driven dispatcher |
| **G3** | No standardized annotation format for ASPECTS | Structured database schema |
| **G4** | Web-based DICOM annotation is rare | Integrated DICOM handling |

### Research Contribution Statement

> This thesis addresses the identified gaps by presenting **MedFabric**, a web-based CT scan labeling system that introduces a **novel event-driven dispatcher pattern** for Streamlit applications, enabling complex stateful workflows for medical image annotation.

---

## Key References to Cite

### Medical Imaging & ASPECTS

1. Barber, P.A., et al. (2000). Lancet. *ASPECTS original paper*
2. Pexman, J.H., et al. (2001). AJNR. *ASPECTS reliability study*
3. Puetz, V., et al. (2009). Stroke. *ASPECTS inter-rater variability*

### Annotation Tools

4. Rubin, D.L., et al. (2008). J Digital Imaging. *ePAD platform*
2. Fedorov, A., et al. (2012). Magn Reson Imaging. *3D Slicer*

### Web Frameworks

6. Streamlit Documentation (2024). *Official docs*
2. Abadi, D., et al. (2019). *Redux pattern documentation*

### Event-Driven Architecture

8. Fowler, M. (2005). *Event Sourcing*
2. Gamma, E., et al. (1994). *Design Patterns: Observer*
