# PaperLens

### Evidence-Grounded AI Research Paper Assistant

> **Understand research papers. Ask questions. Follow the evidence.**

PaperLens is an AI-powered research paper analysis platform designed to help students, researchers, engineers, and academics understand scientific papers faster and more reliably.

Unlike generic AI chatbots that treat PDF files as plain text dumps, PaperLens is engineered specifically around the **structure and evidential nature of scientific documents**.

The central principle of PaperLens is:

> **An answer is only as useful as the evidence supporting it.**

When sufficient evidence cannot be found within an uploaded paper, PaperLens explicitly abstains:

> **"I couldn't find enough information in the uploaded paper to answer this reliably."**

---

## System Architecture Pipeline

```text
PDF Upload
      ↓
Scientific Structure & Section Detection
      ↓
Structure-Aware Semantic Chunking
      ↓
Question Classification (14 Taxonomy Types)
      ↓
Section-Aware Vector & Metadata Retrieval
      ↓
Evidence Selection & Ranking
      ↓
Grounded LLM Answer Generation
      ↓
Evidence Verification Layer
      ↓
Answer / Abstention (with Page + Section Provenance)
```

---

## Documentation Directory

The complete technical specification of PaperLens is organized into specialized reference documents in [`docs/`](file:///d:/sakthi/paperlens-atlas/docs/):

* **[Product Specification](docs/PRODUCT_SPEC.md)** — Core identity, product philosophy, target users, features, workflow, and scope boundaries.
* **[System Architecture](docs/ARCHITECTURE.md)** — Monorepo structure, frontend/backend architecture, processing pipeline, RAG engine, database schema, and evidence lineage.
* **[Research Novelty & Vision](docs/RESEARCH.md)** — Research novelty, structure-aware retrieval vs baseline RAG, hypotheses, and long-term vision.
* **[Dataset Specification](docs/DATASET.md)** — Benchmark dataset schema, question difficulty taxonomy, answerable/unanswerable formatting, and provenance binding.
* **[Evaluation Framework](docs/EVALUATION.md)** — 3-way RAG comparison (`BASELINE_RAG` vs `STRUCTURE_AWARE_RAG` vs `STRUCTURE_AWARE_RAG_WITH_VERIFICATION`), metric formulas (Recall@K, Precision@K, MRR, Grounding, Abstention), and benchmark execution.
* **[API Reference](docs/API.md)** — Complete FastAPI REST API endpoint documentation.
* **[Security & AI Safety](docs/SECURITY.md)** — Authentication, workspace isolation, PDF validation, path traversal protection, **PDF prompt injection defense** (`<UNTRUSTED_DOCUMENT_CONTENT>`), and secret sanitization.
* **[Development & Agentic Rules](docs/DEVELOPMENT.md)** — Monorepo setup, testing instructions, coding principles, and strict rules for agentic AI tools.

---

## Key Features

- **10-Field Structured Summarization**: Automatically extracts Executive Summary, Problem Statement, Objective, Methodology Summary, Key Contributions, Dataset, Experimental Setup, Key Results, Limitations, and Conclusion.
- **Dedicated Methodology Extraction**: Extracts 8 components (Approach, Model, Algorithms, Dataset, Preprocessing, Training, Experiments, Metrics) with strict non-inference fallbacks.
- **Explicit vs Inferred Contribution Mining**: Distinguishes explicit author contribution claims from inferred findings with page and section bindings.
- **Structure-Aware Question Answering**: Classifies questions into 14 taxonomy types and routes retrieval priorities to relevant paper sections.
- **Evidence Provenance & Verification**: Displays page numbers, section names, and exact source text passages generated **exclusively from database metadata records**.
- **Controlled Uncertainty & Abstention**: Refuses unsupported or out-of-scope questions with factual support score verification.

---

## Monorepo Layout

```text
paperlens-atlas/
├── frontend/             # React (Vite + TanStack Router) application
├── backend/              # FastAPI async backend & PostgreSQL pgvector ORM
├── docs/                 # Authoritative product, research & technical specifications
├── docker-compose.yml    # Container composition specification
└── README.md             # Public introduction & document directory
```

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:8080` (or `http://localhost:5173`) and connect to the backend at `http://localhost:8000/api/v1`.

---

## License & Project Identity

Copyright © 2026 PaperLens Team. All rights reserved.  
> **Understand the paper. Follow the evidence.**
