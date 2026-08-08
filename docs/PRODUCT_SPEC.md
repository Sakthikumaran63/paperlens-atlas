# PaperLens Product Specification

## 1. Product Identity & Philosophy

PaperLens is a research-focused AI platform designed for evidence-grounded scientific document understanding.

### Core Philosophy

1. **Principle 1 — Evidence First**: The system prioritizes evidence over fluency. A verifiable, grounded response is always preferred over an ungrounded fluent response.
2. **Principle 2 — Scientific Structure Matters**: A research paper is not a homogeneous block of text. Sections like `Methodology`, `Results`, and `Limitations` serve distinct evidential roles.
3. **Principle 3 — The LLM Is Not the Knowledge Source**: The LLM is a reasoning and natural language synthesis engine. The uploaded paper is the single source of truth.
4. **Principle 4 — Traceability**: Every generated claim must be bound to verifiable page numbers, section titles, and source text snippets in database metadata.
5. **Principle 5 — Controlled Uncertainty (Abstention)**: When evidence is insufficient, refusing to answer with *"I couldn't find enough information in the uploaded paper to answer this reliably."* is a successful system behavior.
6. **Principle 6 — Measurability**: System improvements are evaluated empirically on standardized benchmark datasets measuring Retrieval, Answer Quality, Grounding, and Abstention accuracy.

---

## 2. Target Users

- **Undergraduate & Postgraduate Students**: For understanding complex assignments, literature reviews, and thesis preparation.
- **Researchers & Academics**: For rapid methodology extraction, experimental setup verification, and key contribution auditing.
- **Engineers & Practitioners**: For understanding technical architecture papers, reproducing baseline algorithms, and identifying datasets.
- **Academic Supervisors**: For evaluating literature submissions, checking experimental details, and reviewing paper contributions.

---

## 3. Core Features

### 3.1 Document Ingestion & Structure Detection
- Accepts PDF uploads up to 20MB.
- Extracts page-by-page text preserving page identity.
- Rule-based section detection categorizing 12 scientific taxonomy types (`ABSTRACT`, `INTRODUCTION`, `RELATED_WORK`, `METHODOLOGY`, `DATASET`, `EXPERIMENTS`, `RESULTS`, `DISCUSSION`, `LIMITATIONS`, `CONCLUSION`, `REFERENCES`, `APPENDIX`).

### 3.2 10-Field Structured Summarization
Generates a structured analysis stored in `PaperAnalysis`:
1. Executive Summary
2. Problem Statement
3. Objective
4. Methodology Summary
5. Key Contributions
6. Dataset
7. Experimental Setup
8. Key Results
9. Limitations
10. Conclusion

### 3.3 Dedicated Methodology Extraction
Extracts 8 specific experimental parameters (`approach`, `model`, `algorithms`, `dataset`, `preprocessing`, `training`, `experimental_setup`, `metrics`). Returns `"Not specified in the paper"` without inferring unstated details.

### 3.4 Key Contribution Mining
Extracts explicit contribution statements from Introduction, Abstract, Conclusion, and "Our contributions" sections, distinguishing explicit claims from evidence-supported inferred findings.

### 3.5 Grounded Question Answering & Evidence Provenance
Classifies questions into 14 taxonomy types, routes retrieval to relevant sections, ranks candidates using combined structure-aware scoring, and returns verifiable sources with exact page numbers, section titles, and text passages.

---

## 4. User Workflow

```text
User ──► Upload PDF ──► PDF Validation ──► Async Processing Pipeline
                                                  │
                                                  ▼
View Analysis ◄── Paper Ready ◄── Indexing & Summary Extraction
     │
     ▼
Ask Question ──► Classification ──► Structure Retrieval ──► Verification
                                                                  │
                                                        ┌─────────┴─────────┐
                                                        ▼                   ▼
                                                     Answer              Abstain
```

---

## 5. Scope Boundaries — What We Are Not Building

To preserve product identity and prevent scope creep, the initial PaperLens platform **explicitly excludes** the following features:

- ❌ Citation graphs or co-citation networks
- ❌ Author collaboration graphs
- ❌ Literature discovery / web search engines
- ❌ Paper recommendation systems
- ❌ Multi-agent autonomous research workflows
- ❌ Automatic thesis or paper writing engines
- ❌ Foundation LLM pre-training from scratch
- ❌ General-purpose ungrounded chat interface

Any proposal to add these features requires a deliberate product scope revision.
