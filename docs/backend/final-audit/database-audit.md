# PaperLens Atlas — Database Audit

## 1. Relational Model & Schema Verification

All 13 SQLAlchemy models were audited for relationship completeness, cascade deletions, constraints, and index coverage:

| Table Name | Model Class | Primary Key | Foreign Keys | Key Constraints / Indexes | Cascade Semantics | Audit Status |
|---|---|---|---|---|---|---|
| `users` | `User` | `id` (UUID) | None | Unique `email` (indexed) | N/A | **VERIFIED** |
| `workspaces` | `Workspace` | `id` (UUID) | `user_id -> users.id` | Indexed `user_id` | `ON DELETE CASCADE` | **VERIFIED** |
| `papers` | `Paper` | `id` (UUID) | `workspace_id -> workspaces.id` | Indexed `workspace_id`, `status` | `ON DELETE CASCADE` | **VERIFIED** |
| `paper_pages` | `PaperPage` | `id` (UUID) | `paper_id -> papers.id` | `UNIQUE(paper_id, page_number)` | `ON DELETE CASCADE` | **VERIFIED** |
| `paper_sections` | `PaperSection` | `id` (UUID) | `paper_id -> papers.id` | Indexed `paper_id` | `ON DELETE CASCADE` | **VERIFIED** |
| `paper_chunks` | `PaperChunk` | `id` (UUID) | `paper_id -> papers.id`, `section_id -> paper_sections.id` | Indexed `paper_id`, `section_id` | `ON DELETE CASCADE` | **VERIFIED** |
| `paper_analysis` | `PaperAnalysis`| `id` (UUID) | `paper_id -> papers.id` | Unique `paper_id` (1:1) | `ON DELETE CASCADE` | **VERIFIED** |
| `questions` | `Question` | `id` (UUID) | `paper_id -> papers.id`, `user_id -> users.id` | Indexed `paper_id` | `ON DELETE CASCADE` | **VERIFIED** |
| `answers` | `Answer` | `id` (UUID) | `question_id -> questions.id` | Unique `question_id` (1:1) | `ON DELETE CASCADE` | **VERIFIED** |
| `retrieved_evidence`| `RetrievedEvidence`| `id` (UUID)| `question_id -> questions.id`, `chunk_id -> paper_chunks.id`| Indexed `question_id` | `ON DELETE CASCADE` | **VERIFIED** |
| `answer_evidence` | `AnswerEvidence` | `id` (UUID) | `answer_id -> answers.id`, `chunk_id -> paper_chunks.id` | Indexed `answer_id`, `chunk_id` | `ON DELETE CASCADE` | **VERIFIED** |
| `activity_logs` | `ActivityLog` | `id` (UUID) | `workspace_id -> workspaces.id`, `user_id -> users.id` | Indexed `workspace_id`, `created_at` | `ON DELETE CASCADE` | **VERIFIED** |
| `ai_execution_logs`| `AIExecutionLog`| `id` (UUID) | `question_id -> questions.id` | Indexed `question_id` | `ON DELETE SET NULL`| **VERIFIED** |

---

## 2. Migration Integrity

- Migration engine: **Alembic**.
- Local auto-initialization: Validated via `Base.metadata.create_all()` with custom SQLite vector & UUID shims in `app/db/sqlite_shim.py`.
- No table schema drift or missing relationships detected.
