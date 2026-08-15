# PaperLens Atlas

### Evidence-Grounded Scientific Document Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.0+-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS v4](https://img.shields.io/badge/Tailwind_CSS-v4.0-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![pgvector](https://img.shields.io/badge/pgvector-Supported-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.24+-2A4B7C.svg?style=flat)](https://pymupdf.readthedocs.io/)
[![RapidFuzz](https://img.shields.io/badge/RapidFuzz-3.14+-FF6F00.svg?style=flat)](https://github.com/maxbachmann/RapidFuzz)
[![rank--bm25](https://img.shields.io/badge/rank__bm25-0.2.2-4CAF50.svg?style=flat)](https://github.com/dorianbrown/rank_bm25)
[![Slowapi](https://img.shields.io/badge/Slowapi-Rate_Limiting-blueviolet.svg?style=flat)](https://slowapi.readthedocs.io/)

> **Understand research papers. Ask questions. Follow the evidence.**

---

## 📑 Table of Contents

- [1. Executive Overview](#1-executive-overview)
  - [The Problem with Generic RAG on Scientific Literature](#the-problem-with-generic-rag-on-scientific-literature)
  - [The PaperLens Solution](#the-paperlens-solution)
- [2. System Architecture & End-to-End Pipeline](#2-system-architecture--end-to-end-pipeline)
  - [Architectural Topology](#architectural-topology)
  - [Scientific Ingestion Pipeline](#scientific-ingestion-pipeline)
  - [Structure-Aware Grounded Q&A Pipeline](#structure-aware-grounded-qa-pipeline)
- [3. Core Technical Innovations & RAG Mechanics](#3-core-technical-innovations--rag-mechanics)
  - [Structure-Aware Chunking & Section Taxonomy](#structure-aware-chunking--section-taxonomy)
  - [Question Intent Routing (14 Taxonomies)](#question-intent-routing-14-taxonomies)
  - [Hybrid Retrieval Scoring (BM25 + Semantic + Section Boost)](#hybrid-retrieval-scoring-bm25--semantic--section-boost)
  - [Citation Provenance & RapidFuzz Quote Verification](#citation-provenance--rapidfuzz-quote-verification)
  - [Controlled Uncertainty & Safe Abstention](#controlled-uncertainty--safe-abstention)
  - [Zero-Dependency Offline Extractive AI Engine](#zero-dependency-offline-extractive-ai-engine)
- [4. Security, Isolation & Durability Hardening](#4-security-isolation--durability-hardening)
  - [Cookie-Based Authentication & Session Hydration](#cookie-based-authentication--session-hydration)
  - [Systematic Anti-IDOR Workspace Isolation](#systematic-anti-idor-workspace-isolation)
  - [PDF Prompt Injection Defense](#pdf-prompt-injection-defense)
  - [Sliding-Window Rate Limiting (Slowapi)](#sliding-window-rate-limiting-slowapi)
  - [Pipeline Durability & Automatic Reconciler](#pipeline-durability--automatic-reconciler)
- [5. Database Entity Relational Architecture](#5-database-entity-relational-architecture)
- [6. Base Research Papers & Verified Evaluation](#6-base-research-papers--verified-evaluation)
- [7. Benchmark Framework (QASPER 3-Way RAG Comparison)](#7-benchmark-framework-qasper-3-way-rag-comparison)
- [8. Complete REST API Reference](#8-complete-rest-api-reference)
- [9. Frontend Application Feature Tour](#9-frontend-application-feature-tour)
- [10. Repository File Structure](#10-repository-file-structure)
- [11. Quick Start & Local Setup](#11-quick-start--local-setup)
  - [Prerequisites](#prerequisites)
  - [1-Click Offline Launcher (PowerShell)](#1-click-offline-launcher-powershell)
  - [Manual Backend Installation](#manual-backend-installation)
  - [Manual Frontend Installation](#manual-frontend-installation)
  - [Environment Variables (.env) Reference](#environment-variables-env-reference)
  - [Running Test Suites](#running-test-suites)
- [12. Complete Documentation Sitemap](#12-complete-documentation-sitemap)
- [13. License](#13-license)

---

## 1. Executive Overview

PaperLens Atlas is an evidence-grounded scientific document intelligence platform engineered specifically for students, researchers, engineers, and academics.

### The Problem with Generic RAG on Scientific Literature

Standard RAG tools treat PDF files as flat, unstructured text dumps. They slice documents into uniform fixed-character sliding windows, generate vector embeddings, and execute naive nearest-neighbor search. This results in three critical failure modes:

1. **Loss of Structural Context**: Generic RAG treats text from `Related Work` identically to text from `Methodology` or `Results`. A query such as *"What dataset was evaluated?"* routinely retrieves prior datasets discussed in historical literature surveys rather than the paper's actual contribution.
2. **Citation Hallucinations**: Standard LLMs asked to output page numbers or section references routinely fabricate plausible citations because they lack direct binding to database provenance records.
3. **Over-Confidence & False Answering**: Generic RAG systems attempt to answer every question even when the uploaded document contains zero relevant evidence (e.g., answering financial stock questions against a coastal oceanography paper).

### The PaperLens Solution

PaperLens is built on the foundational principle:

$$\textbf{An answer is only as useful as the evidence supporting it.}$$

- **Structure-Aware Taxonomy**: Automatically detects and preserves 12 scientific section types and 14 question intent classifications.
- **Hybrid Retrieval**: Blends dense semantic vector embeddings, normalized **BM25 Okapi** keyword scoring, and section taxonomy priority routing.
- **Database Provenance Binding**: Citation metadata (`page_number`, `section_title`, `chunk_id`) is strictly bound to database rows, eliminating LLM citation fabrications.
- **RapidFuzz Quote Verification**: Every cited quote is checked against source text using exact substring matching and `RapidFuzz` ($S_{\text{match}} \ge 90$). Fabricated quotes are dropped before database persistence.
- **Explicit Abstention Guard**: If the computed support score falls below threshold ($S_{\text{support}} < 0.70$) or if no verifiable citations survive, PaperLens safely refuses:
  > *"I couldn't find enough information in the uploaded paper to answer this reliably."*
- **Offline Mode as a First-Class Citizen**: Functions completely locally without external API keys or paid third-party dependencies.

---

## 2. System Architecture & End-to-End Pipeline

### Architectural Topology

```text
                               ┌────────────────────────────────────────┐
                               │           React 19 Frontend            │
                               │  (TanStack Router + Tailwind v4 + Lucide)│
                               └───────────────────┬────────────────────┘
                                                   │ HTTP / REST API (Port 8000)
                                                   │ Credentials: Cookie / Header
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │         FastAPI Async Backend          │
                               │   (Slowapi Limiter + Auth + Deps)      │
                               └───────────────────┬────────────────────┘
                                                   │
       ┌───────────────────────────────────────────┼────────────────────────────────────────────┐
       ▼                                           ▼                                            ▼
┌──────────────┐                         ┌───────────────────┐                        ┌────────────────────┐
│ PyMuPDF PDF  │                         │ Pipeline Engine   │                        │ Grounded Q&A RAG   │
│ Extractor    │                         │ (Async Pipeline)  │                        │ Engine             │
└──────────────┘                         └─────────┬─────────┘                        └─────────┬──────────┘
                                                   │                                            │
                                                   ▼                                            ▼
                                         ┌───────────────────┐                        ┌────────────────────┐
                                         │ Section Detector  │                        │ Question Classifier│
                                         │ & Chunking Engine │                        │ (14 Taxonomies)    │
                                         └─────────┬─────────┘                        └─────────┬──────────┘
                                                   │                                            │
                                                   ▼                                            ▼
                                         ┌───────────────────┐                        ┌────────────────────┐
                                         │ Embedding Service │                        │ Hybrid Retrieval   │
                                         │ (OpenAI / Offline)│                        │ (Dense + BM25Okapi)│
                                         └─────────┬─────────┘                        └─────────┬──────────┘
                                                   │                                            │
                                                   ▼                                            ▼
                                         ┌───────────────────┐                        ┌────────────────────┐
                                         │ 10-Field Summary  │                        │ RapidFuzz Verifier │
                                         │ & Method Extractor│                        │ & Abstention Guard │
                                         └───────────────────┘                        └────────────────────┘
```

### Scientific Ingestion Pipeline

When a scientific PDF is uploaded (`POST /api/v1/papers/upload`), the backend initiates an asynchronous multi-stage ingestion worker:

```text
[UPLOADED 0%] ──► [EXTRACTING 20%] ──► [STRUCTURING 40%] ──► [CHUNKING 60%] ──► [EMBEDDING 80%] ──► [ANALYZING 95%] ──► [READY 100%]
```

1. **Extraction (`PDFExtractor`)**: PyMuPDF extracts raw text, page geometries, font metadata, and titles while preserving strict page boundaries.
2. **Structuring (`SectionDetector`)**: Rule-based regex & lexical heuristics classify headings into a 12-type scientific taxonomy.
3. **Chunking (`ChunkingEngine`)**: Generates ~400-token semantic chunks that strictly honor section and page boundaries without cross-boundary bleeding.
4. **Embedding (`EmbeddingService` / `IndexingService`)**: Computes 1536-dimensional vectors (OpenAI `text-embedding-3-small` or deterministic offline hashing) stored in `PaperChunk.embedding`.
5. **Analysis (`SummaryService`)**: Extracts 10-field executive summary, 8-part methodology breakdown, and explicit vs. inferred contribution claims.

### Structure-Aware Grounded Q&A Pipeline

```text
User Question
      │
      ▼
1. Question Classification (Intent: DATASET, METHODOLOGY, RESULT, etc.)
      │
      ▼
2. Candidate Retrieval: Dense Vector Cosine Similarity + BM25Okapi Keyword Ranking
      │
      ▼
3. Structure-Aware Scoring: Composite weighting boosted by section alignment
      │
      ▼
4. Evidence Selection & Budget Context Assembly (<UNTRUSTED_DOCUMENT_CONTENT>)
      │
      ▼
5. Grounded LLM Generation (or Offline Extractive Model)
      │
      ▼
6. Citation Verification: Exact substring + RapidFuzz (Score >= 90)
      │
      ▼
7. Support Score Evaluation (Threshold S >= 0.70)
     ├── Passed ──► Answer + DB-Bound Source Provenance (Page, Section, Text)
     └── Failed ──► Controlled Refusal (Abstention)
```

---

## 3. Core Technical Innovations & RAG Mechanics

### Structure-Aware Chunking & Section Taxonomy

Scientific papers possess hierarchical meaning. PaperLens categorizes all paper sections into a 12-class normalized taxonomy:

| Section Taxonomy | Description | Target Question Affinity |
|---|---|---|
| `ABSTRACT` | High-level summary of problem and results | `OBJECTIVE`, `GENERAL` |
| `INTRODUCTION` | Motivation, background, and research questions | `PROBLEM`, `BACKGROUND` |
| `RELATED_WORK` | Prior literature and comparative baseline context | `RELATED_WORK` |
| `METHODOLOGY` | Formulations, algorithms, model architecture, datasets | `METHODOLOGY`, `DATASET`, `MODEL` |
| `EXPERIMENTS` | Experimental setup, training hyperparameters, baselines | `EXPERIMENT`, `SETUP` |
| `RESULTS` | Quantitative findings, benchmark tables, ablation studies | `RESULT`, `METRIC` |
| `DISCUSSION` | Interpretations, theoretical implications, qualitative analysis | `DISCUSSION` |
| `CONCLUSION` | Final takeaways and summary of contributions | `CONCLUSION` |
| `LIMITATIONS` | Failure cases, constraints, and scope boundaries | `LIMITATION` |
| `FUTURE_WORK` | Recommended future research directions | `FUTURE_WORK` |
| `REFERENCES` | Bibliography (excluded from semantic chunking) | N/A |
| `OTHER` | Miscellaneous sections (appendices, acknowledgements) | `GENERAL` |

### Question Intent Routing (14 Taxonomies)

`QuestionClassificationService` inspects incoming queries using intent pattern matching to assign a target taxonomy:
`METHODOLOGY`, `DATASET`, `RESULT`, `LIMITATION`, `EXPERIMENT`, `METRIC`, `OBJECTIVE`, `PROBLEM`, `CONCLUSION`, `BACKGROUND`, `RELATED_WORK`, `FUTURE_WORK`, `DEFINITION`, and `GENERAL`.

### Hybrid Retrieval Scoring (BM25 + Semantic + Section Boost)

Unlike naive RAG, PaperLens computes a composite hybrid score across all candidate chunks:

$$\text{final\_score} = (0.60 \times \text{semantic\_score}) + (0.25 \times \text{section\_score}) + (0.15 \times \text{bm25\_score})$$

Where:
- $\text{semantic\_score} \in [0, 1]$: Cosine similarity between question embedding and chunk embedding.
- $\text{section\_score} \in \{0.0, 0.5, 1.0\}$: Priority boost if the chunk's section matches the question's target taxonomy.
- $\text{bm25\_score} \in [0, 1]$: Normalized `rank_bm25.BM25Okapi` score across the candidate chunk corpus:
  $$\text{bm25\_score}(c) = \frac{\text{raw\_bm25}(c) - \min(\text{scores})}{\max(\text{scores}) - \min(\text{scores}) + 10^{-6}}$$

### Citation Provenance & RapidFuzz Quote Verification

To eradicate citation hallucinations:
1. Every answer evidence reference must quote exact text from an underlying `PaperChunk`.
2. The verification engine (`EvidenceVerificationService.verify_quote`) evaluates candidate citations:
   - **Exact Match**: Is the quote a direct substring of the chunk?
   - **Fuzzy Match**: If not exact, does `rapidfuzz.fuzz.partial_ratio(quote, chunk_text) \ge 90.0`?
3. Any cited quote failing this check is stripped before persisting `AnswerEvidence` database records.
4. If all quotes for an answer fail verification, the system falls back to safe abstention.

### Controlled Uncertainty & Safe Abstention

When a user asks a question that cannot be proven by the uploaded text:
- `EvidenceVerificationService.evaluate_support()` computes a semantic and lexical overlap metric $S_{\text{support}} \in [0, 1]$.
- If $S_{\text{support}} < 0.70$, the pipeline sets `abstained = true` and returns the standardized refusal:
  > *"I couldn't find enough information in the uploaded paper to answer this reliably."*

### Zero-Dependency Offline Extractive AI Engine

PaperLens operates locally without external API keys via [app/services/offline_ai.py](file:///d:/sakthi/paperlens-atlas/backend/app/services/offline_ai.py):
- **Deterministic 1536-D Pseudo-Embeddings**: Generated via SHA-256 seed hashing of token n-grams and normalized using L2 unit vectors.
- **Rule-Based Summary & Methodology Extraction**: Heuristic regex matchers extract key objectives, dataset names, formulas, and quantitative findings directly from section text.
- **Extractive Grounded Q&A**: BM25 and keyword frequency ranking identify the top candidate sentences from relevant sections to construct grounded, citation-bound answers.

---

## 4. Security, Isolation & Durability Hardening

### Cookie-Based Authentication & Session Hydration
- JWT tokens are issued and stored in secure `httpOnly`, `SameSite=Lax` cookies (`paperlens_token`), preventing client-side script access and neutralizing XSS token exfiltration.
- Backend dependency `_extract_token` checks cookies first with `Authorization: Bearer` header fallback for API automation.
- Added `POST /api/v1/auth/logout` to terminate sessions and clear cookies.
- Frontend hydrates user profile on application startup via `GET /api/v1/auth/me`.

### Systematic Anti-IDOR Workspace Isolation
- All paper, chunk, analysis, and Q&A operations enforce query-level tenancy via `get_workspace_scoped_paper`:
  ```python
  stmt = (
      select(Paper)
      .join(Workspace, Paper.workspace_id == Workspace.id)
      .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
  )
  ```
- Unauthorized or cross-tenant requests return **404 Not Found** (instead of 403), eliminating attacker existence probing and IDOR vulnerabilities.

### PDF Prompt Injection Defense
- Untrusted PDF content is wrapped in passive XML tags: `<UNTRUSTED_DOCUMENT_CONTENT>` inside system prompts.
- Explicit system overrides instruct the LLM to treat paper content strictly as passive data and ignore any embedded roleplay or system prompt override directives.

### Sliding-Window Rate Limiting (Slowapi)
- `POST /api/v1/auth/login`: 20 requests / minute
- `POST /api/v1/auth/register`: 10 requests / minute
- `POST /api/v1/papers/{id}/questions`: 30 requests / minute
- Exceeded thresholds return `HTTP 429 Too Many Requests`.

### Pipeline Durability & Automatic Reconciler
- Background task `reconcile_stuck_papers` executes on startup to identify papers stuck in non-terminal processing states for $> 15\text{ minutes}$ and marks them `FAILED`.
- Added `POST /api/v1/papers/{paper_id}/retry` endpoint to resume and re-trigger pipeline execution on failed papers.

---

## 5. Database Entity Relational Architecture

PaperLens employs 11 relational models with strict foreign key constraints and cascade deletion:

```mermaid
erDiagram
    USER ||--o{ WORKSPACE : owns
    WORKSPACE ||--o{ PAPER : contains
    PAPER ||--o{ PAPER_PAGE : extracts
    PAPER ||--o{ PAPER_SECTION : segments
    PAPER ||--o{ PAPER_CHUNK : indexes
    PAPER ||--o| PAPER_ANALYSIS : synthesizes
    PAPER ||--o{ QUESTION : receives
    QUESTION ||--o{ ANSWER : produces
    QUESTION ||--o{ RETRIEVED_EVIDENCE : retrieves
    ANSWER ||--o{ ANSWER_EVIDENCE : binds
    PAPER_CHUNK ||--o{ ANSWER_EVIDENCE : references
    PAPER_CHUNK ||--o{ RETRIEVED_EVIDENCE : references

    USER {
        uuid id PK
        string email UK
        string hashed_password
        string name
        boolean is_active
        boolean is_admin
        datetime created_at
    }
    WORKSPACE {
        uuid id PK
        uuid user_id FK
        string name
        string slug
    }
    PAPER {
        uuid id PK
        uuid workspace_id FK
        string title
        string authors
        integer page_count
        string status
        string stage
        integer progress
        string file_path
    }
    PAPER_CHUNK {
        uuid id PK
        uuid paper_id FK
        uuid section_id FK
        integer page_number
        text content
        vector_1536 embedding
        integer token_count
    }
    ANSWER {
        uuid id PK
        uuid question_id FK
        text answer_text
        boolean abstained
        float support_score
    }
    ANSWER_EVIDENCE {
        uuid id PK
        uuid answer_id FK
        uuid chunk_id FK
        text quote_text
        float confidence_score
    }
```

---

## 6. Base Research Papers & Verified Evaluation

PaperLens has been tested against 6 full-length peer-reviewed scientific papers located in [backend/Data/base paper/](file:///d:/sakthi/paperlens-atlas/backend/Data/base%20paper):

| # | Paper Title / File | Domain | Key Topics Tested | Q&A Pass Rate |
|---|---|---|---|---|
| 1 | `1-s2.0-S0378383924001029-main.pdf` | Coastal Geosciences | **SandSnap**: Mobile photo sieving, beach sediment mapping | **100% (PASS)** |
| 2 | `Earth Surf Processes Landf - 2023 - Matsumoto.pdf` | Geomorphology | **MDGS**: Automated mobile digital grain size estimation | **100% (PASS)** |
| 3 | `applsci-13-03268-v2.pdf` | Remote Sensing | **Shoreline Monitoring**: Machine learning & satellite review | **100% (PASS)** |
| 4 | `esurf-10-349-2022.pdf` | Hydrology / Fluvial | **BASEGRAIN**: Optical gravel sizing, river sediment dynamics | **100% (PASS)** |
| 5 | `jmse-12-00172.pdf` | Marine Science | **Drone AI**: Particle size prediction from UAV imagery | **100% (PASS)** |
| 6 | `remotesensing-16-01763.pdf` | Radar Remote Sensing | **SAR**: Sentinel-1 backscatter gravel beach grain sizing | **100% (PASS)** |

All 6 papers successfully completed the full 5-stage ingestion pipeline and passed verified grounded Q&A with real DB-bound citations.

---

## 7. Benchmark Framework (QASPER 3-Way RAG Comparison)

PaperLens includes a native 3-way evaluation harness comparing retrieval and generation architectures:

1. **`BASELINE_RAG`**: Standard fixed-character sliding window chunking + pure vector cosine similarity.
2. **`STRUCTURE_AWARE_RAG`**: Section taxonomy routing + BM25 Okapi hybrid scoring.
3. **`STRUCTURE_AWARE_RAG_WITH_VERIFICATION`**: Structure-aware retrieval + RapidFuzz citation verification + support score abstention guard.

### Evaluation Metrics Computed

- **Recall@K & Precision@K**: Fraction of ground-truth evidence chunks retrieved in the top $K$ results.
- **Mean Reciprocal Rank (MRR)**: Average reciprocal rank of the first relevant evidence chunk.
- **Grounding Accuracy**: Percentage of answer claims directly supported by verified citations.
- **Abstention Accuracy**: Precision and recall of the system on unanswerable test queries.

### QASPER Dataset Ingestion CLI

```bash
cd backend
python scripts/ingest_qasper_benchmark.py --limit 100 --split dev
```

---

## 8. Complete REST API Reference

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `POST` | `/auth/register` | Register new user & workspace | 10 / min |
| `POST` | `/auth/login` | Authenticate & set httpOnly cookie | 20 / min |
| `POST` | `/auth/logout` | Clear session & authentication cookie | — |
| `GET` | `/auth/me` | Hydrate authenticated user profile | — |
| `POST` | `/papers/upload` | Upload PDF & start ingestion pipeline | — |
| `GET` | `/papers` | List papers in workspace | — |
| `GET` | `/papers/{id}` | Get paper metadata, pages & sections | — |
| `DELETE`| `/papers/{id}` | Delete paper & cascade delete chunks | — |
| `GET` | `/papers/{id}/status` | Poll pipeline stage & progress percentage | — |
| `POST` | `/papers/{id}/retry` | Re-trigger failed pipeline worker | — |
| `POST` | `/papers/{id}/questions` | **Main Grounded Q&A** (BM25 + RapidFuzz) | 30 / min |
| `GET` | `/papers/{id}/analysis` | Get 10-field structured summary | — |
| `GET` | `/papers/{id}/methodology`| Get 8-part structured methodology | — |
| `GET` | `/papers/{id}/contributions`| Get explicit vs inferred contributions | — |
| `POST` | `/papers/{id}/evaluate` | Run 3-way RAG benchmark evaluation | — |
| `GET` | `/health` | Multi-subsystem health check | — |

---

## 9. Frontend Application Feature Tour

Built with React 19, TanStack Router, Tailwind CSS v4, and Lucide Icons:

- **Dashboard (`/dashboard`)**: Summary statistics (total papers, ready papers, total chunks, Q&A queries executed), live recent activity feed, and quick upload zone.
- **Paper Library (`/papers`)**: Searchable, filterable library with status badges (`PROCESSING`, `READY`, `FAILED`), stage indicators, and deletion triggers.
- **Upload Modal**: Drag-and-drop PDF uploader with real-time polling displaying extraction, structuring, chunking, and embedding progress percentages.
- **Interactive Paper Workspace (`/papers/$id`)**:
  - **Overview**: Executive summary, problem statement, objectives, and limitations.
  - **Methodology Tab**: Approach, algorithms, models, datasets, and hyperparameters.
  - **Contributions Tab**: Explicit author claims vs inferred empirical findings.
  - **Grounded Q&A Tab**: Question input with instant taxonomy classification, support score meters, verified citation cards, and direct page-jumping.
  - **Chunks Inspector**: Browse all extracted chunks, section assignments, and token counts.
- **Activity Feed (`/activity`)**: Real-time log of uploads, Q&A queries, and pipeline transitions.
- **Settings (`/settings`)**: Workspace preferences, API key overrides, and local offline mode toggles.

---

## 10. Repository File Structure

```text
paperlens-atlas/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/             # auth.py, papers.py, questions.py, health.py, admin.py
│   │   │   ├── deps.py             # Auth & anti-IDOR get_workspace_scoped_paper dependencies
│   │   │   └── router.py           # Master API router configuration
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic BaseSettings environment configuration
│   │   │   ├── limiter.py          # Centralized Slowapi rate limiter instance
│   │   │   ├── logging.py          # Structured logger setup
│   │   │   └── security.py         # Passlib bcrypt hashing & JWT tokens
│   │   ├── db/
│   │   │   ├── base.py             # Declarative SQLAlchemy base
│   │   │   ├── session.py          # Async engine & sessionmaker
│   │   │   ├── sqlite_shim.py      # SQLite vector & UUID compatibility shim
│   │   │   └── types.py            # Custom DB types (GUID, Vector fallback)
│   │   ├── models/                 # User, Workspace, Paper, Page, Section, Chunk, Answer, etc.
│   │   ├── schemas/                # Pydantic request/response validation schemas
│   │   ├── services/
│   │   │   ├── answer_generation_service.py    # Grounded Q&A generation & citation assembly
│   │   │   ├── contribution_extraction_service.py # Explicit vs inferred contribution mining
│   │   │   ├── embedding_service.py            # Dense vector embeddings
│   │   │   ├── evaluation_service.py           # 3-way RAG evaluation harness
│   │   │   ├── evidence_selection_service.py   # Context budget assembly & deduplication
│   │   │   ├── evidence_verification_service.py# RapidFuzz & support score verification
│   │   │   ├── indexing_service.py             # Vector storage & indexing
│   │   │   ├── llm_service.py                  # Prompt templates & safety wrappers
│   │   │   ├── methodology_extraction_service.py # 8-part methodology extractor
│   │   │   ├── offline_ai.py                   # Zero-dependency offline extractive AI engine
│   │   │   ├── paper_processing_service.py     # High-level paper processing orchestrator
│   │   │   ├── pdf_extractor.py                # PyMuPDF text & metadata extraction
│   │   │   ├── pipeline_orchestrator.py        # 5-stage async pipeline orchestrator
│   │   │   ├── pipeline_reconciler.py          # Stalled paper background reconciler
│   │   │   ├── question_classifier.py          # 14-taxonomy question intent classifier
│   │   │   ├── retrieval_service.py            # pgvector cosine similarity search
│   │   │   ├── retrieval_strategy_service.py   # Structure-aware BM25Okapi hybrid retrieval
│   │   │   ├── section_detector.py             # 12-taxonomy section detector
│   │   │   └── summary_service.py              # 10-field structured summary extractor
│   │   ├── utils/
│   │   │   └── storage.py          # UUID file persistence & MIME validation
│   │   └── main.py                 # FastAPI application factory, CORS, lifespan & exceptions
│   ├── Data/base paper/            # 6 reference research papers for evaluation
│   ├── scripts/                    # CLI evaluation & benchmark ingestion scripts
│   ├── tests/                      # 23 pytest test modules
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/app/         # Sidebar, Header, AuthModal, UploadModal, CitationCard, etc.
│   │   ├── components/ui/          # Radix & Tailwind design system components
│   │   ├── lib/
│   │   │   ├── api.ts              # Centralized API client with cookie credentials & types
│   │   │   └── utils.ts            # UI helper utilities
│   │   ├── routes/                 # TanStack Router file-based pages
│   │   └── index.css               # Design tokens & typography
│   └── package.json                # Frontend dependencies & scripts
├── docs/                           # Complete technical specification suite
├── scratch/                        # Automated test & verification scripts
├── run_offline.ps1                 # 1-Click offline application runner (PowerShell)
├── DOCUMENTATION.md                # Exhaustive master technical documentation
└── README.md                       # Public project overview & quick start
```

---

## 11. Quick Start & Local Setup

### Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher (with npm)
- **Database**: SQLite (default local mode) or PostgreSQL 15+ with `pgvector` extension

### 1-Click Offline Launcher (PowerShell)

On Windows, launch both backend and frontend servers with a single command:

```powershell
.\run_offline.ps1
```

- **Frontend**: `http://localhost:8080` (or `http://localhost:5173`)
- **Backend API**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`

---

### Manual Backend Installation

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the FastAPI development server
python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

---

### Manual Frontend Installation

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

---

### Environment Variables (`.env`) Reference

Create a `.env` file in the `backend/` directory to customize configurations:

```env
# Application Settings
ENVIRONMENT=development
PROJECT_NAME=paperlens-backend
API_V1_STR=/api/v1
SECRET_KEY=your-super-secret-jwt-signing-key-here-32-chars-min
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration (SQLite default / PostgreSQL optional)
DATABASE_URL=sqlite+aiosqlite:///./paperlens_local.db
# For PostgreSQL with pgvector:
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/paperlens

# AI & LLM Services (Optional — Offline fallback active if omitted)
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small

# Storage Limits
MAX_UPLOAD_SIZE_BYTES=20971520
UPLOAD_DIR=storage/uploads
```

---

### Running Test Suites

```bash
# 1. Run Unit & Service Tests (PyTest)
cd backend
pytest

# 2. Run Architectural Improvements Verification Suite (Cookie Auth, Anti-IDOR, RapidFuzz, BM25, Limiter, Reconciler)
python scratch/test_improvements.py

# 3. Run End-to-End Base Papers Pipeline Test across all 6 research papers
python scratch/test_full_pipeline.py
```

---

## 12. Complete Documentation Sitemap

| Document | Purpose |
|---|---|
| **[DOCUMENTATION.md](DOCUMENTATION.md)** | Comprehensive master technical specification, database models, RAG engine, and API reference |
| **[docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md)** | Product identity, target users, features, workflow, and scope boundaries |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Monorepo layout, frontend/backend architecture, processing pipeline, and evidence lineage |
| **[docs/RESEARCH.md](docs/RESEARCH.md)** | Research novelty, structure-aware retrieval vs baseline RAG, hypotheses, and long-term vision |
| **[docs/DATASET.md](docs/DATASET.md)** | Benchmark dataset schema, question difficulty taxonomy, and provenance binding |
| **[docs/EVALUATION.md](docs/EVALUATION.md)** | 3-way RAG comparison (`BASELINE_RAG` vs `STRUCTURE_AWARE_RAG` vs `WITH_VERIFICATION`) & metrics |
| **[docs/API.md](docs/API.md)** | Complete FastAPI REST API reference with request/response schemas |
| **[docs/SECURITY.md](docs/SECURITY.md)** | Cookie auth, anti-IDOR isolation, PDF prompt injection defense, rate limiting, and sanitization |
| **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** | Setup instructions, coding principles, and agentic AI operating guidelines |
| **[docs/TESTING.md](docs/TESTING.md)** | Test strategy, test matrix, and verification commands |

---

## 13. License

Copyright © 2026 PaperLens Team. All rights reserved.

> **Understand research papers. Ask questions. Follow the evidence.**
