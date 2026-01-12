# Chapter 1: Introduction

## Presentation Outline

**Estimated Length**: 5-8 pages  
**Key Purpose**: Establish context, problem, and research objectives

---

## 1.1 Background and Motivation

### Content to Present

1. **Medical Imaging in Stroke Diagnosis**
   - Importance of CT scans in acute ischemic stroke
   - Role of radiologists in image interpretation
   - Time-critical nature of stroke treatment ("time is brain")

2. **ASPECTS Scoring System**
   - Alberta Stroke Program Early CT Score explanation
   - 10-point scoring system for ischemic damage assessment
   - Clinical significance in treatment decisions (thrombolysis eligibility)

3. **Current Challenges in Medical Image Annotation**
   - Manual annotation burden on radiologists
   - Lack of standardized annotation tools
   - Need for training data for AI/ML models
   - Inter-rater variability in scoring

### Figures to Include

- Example CT scan with ASPECTS regions highlighted
- Workflow diagram of current manual annotation process
- Statistics on stroke incidence and diagnosis challenges

---

## 1.2 Problem Statement

### Main Problems to Address

```
┌─────────────────────────────────────────────────────────────────┐
│                     PROBLEM SPACE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. No specialized tool for CT scan ASPECTS annotation          │
│     ├── Generic image viewers lack medical context              │
│     ├── No integrated scoring workflow                          │
│     └── Poor data structure for ML training                     │
│                                                                  │
│  2. Web-based annotation is complex                              │
│     ├── Stateless HTTP paradigm vs stateful labeling            │
│     ├── DICOM handling in browser is challenging                │
│     └── Real-time feedback required for windowing               │
│                                                                  │
│  3. Data management challenges                                   │
│     ├── Multi-slice series need organized workflow              │
│     ├── Multiple annotators need separate sessions              │
│     └── Validation before submission is critical                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Research Questions

1. How can we design a web-based system that provides a seamless CT scan annotation experience?
2. How do we handle complex stateful workflows in Streamlit's stateless execution model?
3. What data model best supports ASPECTS scoring and future ML integration?

---

## 1.3 Research Objectives

### Primary Objectives

| # | Objective | Measurable Outcome |
|---|-----------|-------------------|
| 1 | Design a web-based CT labeling system | Functional web application |
| 2 | Implement ASPECTS scoring workflow | Support all 3 brain regions, L/R hemispheres |
| 3 | Develop novel state management pattern | Event-driven dispatcher for Streamlit |
| 4 | Create structured annotation database | SQLite schema with evaluation records |

### Secondary Objectives

- Support multiple image formats (DICOM, JPEG)
- Enable batch labeling of multiple CT sets
- Provide real-time validation feedback
- Ensure data integrity through structured input

---

## 1.4 Scope and Limitations

### In Scope

- [x] Web-based labeling interface
- [x] DICOM and JPEG image support
- [x] ASPECTS scoring for ischemic stroke
- [x] User authentication and session management
- [x] Multi-set batch labeling
- [x] Validation and submission workflow

### Out of Scope

- [ ] AI-assisted automatic segmentation
- [ ] 3D volume rendering
- [ ] Multi-user collaborative annotation
- [ ] Cloud deployment (local/Docker only)
- [ ] PACS/DICOM server integration

### Known Limitations

1. Single-user sessions (no real-time collaboration)
2. SQLite database (not production-scale)
3. No image preprocessing pipeline
4. Limited to axial CT slices

---

## 1.5 Significance of the Study

### Academic Contributions

1. **Novel Dispatcher Pattern**
   - First documented event-driven architecture for Streamlit
   - Solves fundamental state management challenge
   - Reusable pattern for similar applications

2. **Medical Imaging Domain Application**
   - Domain-specific tool design insights
   - ASPECTS workflow formalization

### Practical Contributions

1. **Open-Source Tool**
   - Available for research institutions
   - Extensible for other scoring systems

2. **Training Data Generation**
   - Structured output for ML model training
   - Consistent annotation format

---

## 1.6 Thesis Structure

### Chapter Overview

| Chapter | Title | Content Summary |
|---------|-------|-----------------|
| 1 | Introduction | ← You are here |
| 2 | Literature Review | Related work, existing tools, gaps |
| 3 | Methodology | Development approach, tools chosen |
| 4 | System Design | Architecture, database, UI design |
| 5 | Implementation | Technical details, code structure |
| 6 | Novel Contributions | Dispatcher pattern deep dive |
| 7 | Testing & Evaluation | Test results, validation |
| 8 | Conclusion | Summary, future work |

---

## Presentation Tips

### For Oral Defense

1. **Start with a story**: "A patient arrives at the ER with stroke symptoms..."
2. **Show the problem visually**: Before/after annotation workflow
3. **Quantify the problem**: Statistics on radiologist workload
4. **Preview the solution**: Quick demo screenshot

### For Written Thesis

1. Use formal academic tone
2. Cite stroke statistics from WHO/medical journals
3. Reference ASPECTS original paper (Barber et al., 2000)
4. Include ethics statement for medical data
