# PaperLens System Architecture

## 1. Monorepo Organization

PaperLens is organized as a clean production monorepo:

```text
paperlens-atlas/
├── frontend/             # Vite + React 19 + TanStack Router + TailwindCSS v4
├── backend/              # FastAPI + SQLAlchemy 2.x + PostgreSQL pgvector + PyMuPDF
├── docs/                 # Authoritative technical & research specification suite
│   ├── architecture/     # Backend architecture report
│   ├── api/              # API reference
│   ├── research/         # Research novelty & hypotheses
│   └── evaluation/       # Benchmark schema & evaluation results
├── docker-compose.yml    # Container composition specification
└── README.md             # Master project entry point
```

---

## 2. Frontend Architecture (`frontend/`)

- **Routing**: TanStack Router (`src/routes/`) with file-based routing (`__root.tsx`, `index.tsx`, `upload.tsx`, `papers.tsx`, `paper.$id.tsx`, `dashboard.tsx`, `settings.tsx`, `activity.tsx`).
- **Centralized API Client** (`src/lib/api.ts`): Configured via `VITE_API_BASE_URL` with `credentials: "include"`, supports automatic httpOnly cookie-based session persistence, `getMe()` hydration on mount, and HTTP error codes (`400`, `401`, `403`, `404`, `413`, `422`, `429`, `500`, network errors).
- **Evidence Rendering**: Displays `answer`, support score percentage, and exact source passages (`page`, `section`, `text`) generated **exclusively from backend database metadata records**.
- **Refusal Rendering**: Renders standard abstention message when backend returns `abstained=true`:
  *"I couldn't find enough information in the uploaded paper to answer this reliably."*

---

## 3. Backend Architecture (`backend/`)

Built with Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x Async ORM, and PostgreSQL with `pgvector` (or SQLite with in-memory vector fallback).

```text
backend/
├── app/
│   ├── api/routes/       # Auth, papers, questions, analysis, methodology, contributions, evaluation, health
│   ├── core/             # Settings, security (bcrypt, JWT), limiter (Slowapi), logging
│   ├── db/               # Async Engine, Session Manager, and SQLite compatibility shim
│   ├── models/           # 11 SQLAlchemy Models (User, Workspace, Paper, Page, Section, Chunk, Analysis, etc.)
│   ├── schemas/          # Pydantic validation schemas
│   ├── services/         # PDF Extractor, Section Detector, Chunker, Embedding, Indexer, Retrieval (BM25), QA, Verification (RapidFuzz), Reconciler, Offline AI
│   └── utils/            # Storage manager (file size validation, UUID path traversal protection)
├── tests/                # 23 pytest test files + end-to-end verification suites
├── alembic/              # Database migration scripts
├── scripts/              # CLI evaluation runner (run_evaluation.py)
└── Dockerfile            # Container build script
```

---

## 4. Scientific Document Ingestion Pipeline & Durability

When a paper is uploaded (`POST /api/v1/papers/upload`), the worker orchestrates background execution non-blockingly:

```text
UPLOADED (0%) ──► EXTRACTING (20%) ──► STRUCTURING (40%) ──► CHUNKING (60%) ──► EMBEDDING (80%) ──► ANALYZING (95%) ──► READY (100%)
```

1. **Extraction (`PDFExtractor`)**: Extract page text with PyMuPDF preserving page numbers.
2. **Section Detection (`SectionDetector`)**: Map headings to 12 taxonomy types.
3. **Structure-Aware Chunking (`ChunkingEngine`)**: Split text into ~400 token chunks preserving section and page boundaries.
4. **Indexing (`IndexingService`)**: Generate embeddings using OpenAI-compatible API (or deterministic offline hashing) and store vectors in `paper_chunks.embedding` (`vector(1536)`).
5. **Analysis (`SummaryService`)**: Extract 10-field structured summary, methodology, and contributions.
6. **Pipeline Durability (`PipelineReconciler`)**: Reconciler task scans on startup for papers stuck in non-terminal stages $> 15\text{ mins}$, marks them `FAILED`, and allows resumption via `POST /papers/{paper_id}/retry`.

---

## 5. Structure-Aware RAG Engine

1. **Question Classification (`QuestionClassificationService`)**: Classify question into 14 taxonomy types (`METHODOLOGY`, `DATASET`, `RESULT`, `MODEL`, etc.).
2. **Retrieval Routing**: Priority boost for candidate chunks residing in relevant section types.
3. **BM25 & Vector Hybrid Scoring**:
   $$\text{final\_score} = (\text{semantic\_score} \times 0.60) + (\text{section\_score} \times 0.25) + (\text{bm25\_score} \times 0.15)$$
4. **Evidence Selection (`EvidenceSelectionService`)**: Deduplicate chunks and construct context budget package.
5. **Grounded Answer Generation (`LLMService`)**: Prompt LLM with strict instructions, enclosing document text inside `<UNTRUSTED_DOCUMENT_CONTENT>` XML tags. (Falls back to offline extractive keyword Q&A when no API key is present).
6. **Citation Quote Verification (`EvidenceVerificationService`)**: Verify every cited quote against chunk text with exact substring + `RapidFuzz` ($S \ge 90$). Drop unverified citations.
7. **Evidence Support Verification**: Compute support score. If `support_score < 0.70` or zero verified citations survive, override with refusal response.

---

## 6. Database Entity Relationships

```text
User ──► Workspace ──► Paper ──► PaperPage
                         │  ├──► PaperSection
                         │  ├──► PaperChunk (vector 1536)
                         │  └──► PaperAnalysis
                         │
                         └──► Question ──► Answer ──► AnswerEvidence ──► PaperChunk
                                 │
                                 └──► RetrievedEvidence ──► PaperChunk
```
