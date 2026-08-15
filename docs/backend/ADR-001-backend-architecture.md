# Architecture Decision Record (ADR-001)

## Title: PaperLens Atlas Backend Architecture, AI Fallback & Tenancy Strategy

- **Status**: Approved & Implemented
- **Date**: 2026-08-15
- **Deciders**: Backend Architect, AI/RAG Engineer, Security Engineer

---

## 1. Context & Problem Statement

Scientific research papers contain rich structural hierarchy, mathematical formulations, and evidential claims that are destroyed by generic RAG systems. Furthermore, generic chatbots suffer from hallucinated citations, unverified answers on unanswerable questions, and lack of offline execution.

PaperLens Atlas requires a modular, production-ready backend that:
1. Preserves scientific document structure and metadata provenance.
2. Implements hybrid retrieval (BM25Okapi + dense vector cosine similarity + section taxonomy routing).
3. Enforces strict evidence verification (RapidFuzz $\ge 90$) and controlled abstention ($S_{\text{support}} \ge 0.70$).
4. Operates locally as a first-class citizen (local extractive/pseudo-embedding models) with policy-driven Gemini fallback.
5. Guarantees multi-tenant workspace isolation (Anti-IDOR) and secure session management.

---

## 2. Decision Summary

### 2.1 Framework & Concurrency
- **Decision**: Python 3.11+ with **FastAPI** and **async SQLAlchemy 2.0**.
- **Rationale**: FastAPI provides high-performance asynchronous request handling, native Pydantic v2 data validation, and automatic OpenAPI generation. SQLAlchemy 2.0 async sessions ensure non-blocking I/O during database transactions.

### 2.2 Database & Storage Strategy
- **Decision**: **PostgreSQL with `pgvector`** for production; **SQLite with in-memory vector fallback** for single-command zero-config local development.
- **Rationale**: PostgreSQL + `pgvector` provides ACID compliance and fast vector similarity indexing (IVFFlat/HNSW). SQLite compatibility via custom shims ensures researchers and students can run PaperLens offline without Docker or external DB services.

### 2.3 AI Provider Hierarchy: Local-First with Confidence-Aware Gemini Fallback
- **Decision**: Local model / rule-based extractor is **Primary**; Google Gemini is **Fallback** only when local confidence or evidence coverage is insufficient.
- **Rationale**: Prevents external API vendor lock-in, eliminates costs during development/offline demos, and maintains user privacy. When Gemini is called, it is constrained to `<UNTRUSTED_DOCUMENT_CONTENT>` with verified passages only.

### 2.4 Authoritative Evidence & Citation Provenance
- **Decision**: Citation metadata (`page_number`, `section_title`, `chunk_id`) is strictly bound to database rows. Generated citation quotes are verified using `RapidFuzz` ($S \ge 90$) against chunk text.
- **Rationale**: Eliminates LLM hallucinated page numbers and fabricated quotes.

### 2.5 Security, Workspace Isolation & Authentication
- **Decision**: `httpOnly`, `SameSite=Lax` cookies (`paperlens_token`) for sessions; `get_workspace_scoped_paper` query-level tenant isolation returning `404 Not Found`.
- **Rationale**: Neutralizes XSS token exfiltration and eliminates cross-tenant IDOR existence probing.

### 2.6 Pipeline Durability & Reconciler
- **Decision**: Startup background task `reconcile_stuck_papers` marking jobs stuck $> 15\text{ min}$ as `FAILED`, paired with `POST /papers/{id}/retry`.
- **Rationale**: Ensures the system self-heals after crashes or abrupt server restarts.

---

## 3. Consequences

### Positive
- Zero citation hallucinations: citations are physically backed by database records.
- Complete offline portability without requiring OpenAI/Gemini API keys.
- Robust security posture against IDOR, XSS, CSRF, and prompt injections.
- Seamless compatibility with the existing React 19 frontend.

### Negative / Trade-offs
- Local extractive mode produces concise answers compared to generative LLMs when API keys are disabled.
- Hybrid BM25 computation incurs a minor CPU overhead over pure vector search, mitigated by chunk-level indexing.
