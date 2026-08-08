# PaperLens FastAPI REST API Reference

Base URL: `http://localhost:8000/api/v1`

---

## 1. Authentication Endpoints

### `POST /auth/register`
- **Description**: Register a new user and create default workspace.
- **Request Body**: `{"email": "user@example.com", "password": "Password123!"}`
- **Response** `201 Created`: `{"access_token": "jwt...", "token_type": "bearer", "user": {"id": "...", "email": "..."}}`

### `POST /auth/login`
- **Description**: Authenticate user and issue JWT access token.
- **Request Body**: `{"email": "user@example.com", "password": "Password123!"}`
- **Response** `200 OK`: `{"access_token": "jwt...", "token_type": "bearer", "user": {...}}`

### `GET /auth/me`
- **Description**: Return authenticated user profile and default workspace ID.
- **Headers**: `Authorization: Bearer <jwt_token>`

---

## 2. Paper Ingestion & Management Endpoints

### `POST /papers/upload`
- **Description**: Upload PDF paper (20MB limit) and initiate non-blocking background pipeline.
- **Request**: `multipart/form-data` with `file: UploadFile`
- **Response** `201 Created`: `{"id": "uuid", "title": "Paper Title", "status": "PROCESSING", "stage": "EXTRACTING", "progress": 20}`

### `GET /papers`
- **Description**: List papers in authenticated user's workspace.
- **Response** `200 OK`: Array of `PaperResponse` objects (`id`, `title`, `authors`, `publication_year`, `status`, `stage`, `progress`, `created_at`).

### `GET /papers/{paper_id}`
- **Description**: Get paper details, page count, and section list.

### `DELETE /papers/{paper_id}`
- **Description**: Delete paper and cascade delete associated pages, sections, chunks, and vector embeddings.

### `GET /papers/{paper_id}/status`
- **Description**: Poll background pipeline stage status and progress percentage.
- **Response**: `{"paper_id": "...", "status": "PROCESSING", "stage": "EMBEDDING", "progress": 80, "stage_details": {...}}`

### `POST /papers/{paper_id}/retry`
- **Description**: Re-trigger background analysis pipeline for a failed paper.

---

## 3. Analysis & Q&A Endpoints

### `POST /papers/{paper_id}/questions`
- **Description**: **Main Grounded Q&A Endpoint**. Executes 15-step grounded RAG pipeline.
- **Request Body**: `{"question": "What dataset was used?"}`
- **Response** `200 OK`:
```json
{
  "question_id": "q_123",
  "question": "What dataset was used?",
  "question_type": "DATASET",
  "answer": "The authors evaluate on ImageNet and WMT 2014.",
  "abstained": false,
  "support_score": 0.91,
  "sources": [
    {
      "page": 5,
      "section": "Experiments",
      "chunk_id": "c_456",
      "text": "We evaluate on WMT 2014..."
    }
  ]
}
```

### `GET /papers/{paper_id}/analysis`
- **Description**: Return 10-field structured paper summary.

### `GET /papers/{paper_id}/methodology`
- **Description**: Return 8-component structured methodology extraction.

### `GET /papers/{paper_id}/contributions`
- **Description**: Return explicit vs inferred key contributions.

### `POST /papers/{paper_id}/evaluate`
- **Description**: Run 3-way RAG evaluation benchmark (`BASELINE_RAG` vs `STRUCTURE_AWARE_RAG` vs `STRUCTURE_AWARE_RAG_WITH_VERIFICATION`).

---

## 4. Diagnostics Endpoint

### `GET /api/v1/health` & `GET /health`
- **Description**: Multi-component health check (Application, Database `SELECT 1` ping, Vector storage, AI service configurations).
