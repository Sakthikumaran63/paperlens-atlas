# PaperLens Development & Agentic Guidelines

## 1. Monorepo Setup Commands

### Backend (`backend/`)

```bash
cd backend
python -m venv venv

# Activate venv:
# Windows: .\venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (`frontend/`)

```bash
cd frontend
npm install
npm run dev
```

---

## 2. Testing Execution Guide

### Backend Tests

```bash
cd backend
python -m pytest tests/
```

### Evaluation Benchmark

```bash
cd backend
python scripts/run_evaluation.py
```

### Frontend Build & Format Check

```bash
cd frontend
npm run build
npm run format
```

---

## 3. Mandatory Agentic Development Rules

When developing PaperLens using autonomous AI coding assistants, the following rules MUST be preserved without exception:

1. **Rule 1 — Scope Boundaries**: Do NOT add features outside the specified scope (e.g. multi-agent networks, citation graphs, automated thesis writers) without explicit scope approval.
2. **Rule 2 — Architectural Stability**: Do NOT replace core architectural choices (FastAPI, SQLAlchemy 2.x, PostgreSQL, pgvector, PyMuPDF, TanStack Router) without explicit user justification.
3. **Rule 3 — Provenance & No Fabrication**: Never allow the LLM to invent page numbers or source passages. Sources MUST originate from database metadata.
4. **Rule 4 — Evidence First**: Prefer a controlled abstention (*"I couldn't find enough information..."*) over an ungrounded candidate answer.
5. **Rule 5 — Empirical Validation**: Never claim scientific novelty or benchmark improvements without running the evaluation framework.
6. **Rule 6 — No-Commit Directive**: When instructed not to commit, write all code to local files without executing git commit or push commands.

---

## 4. Coding Principles

- **Modularity**: Maintain clean separation between API routes, Pydantic schemas, SQLAlchemy models, and core services.
- **Type Safety**: Enforce explicit TypeScript interfaces in the frontend and Pydantic models in the backend.
- **Explicit Error Handling**: Use structured HTTP exception payloads rather than raw text errors.
