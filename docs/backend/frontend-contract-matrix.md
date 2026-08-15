# PaperLens Atlas — Frontend Contract Matrix

This contract matrix defines every API interaction between the React 19 frontend (`frontend/src/`) and the FastAPI backend (`backend/app/`).

---

## 1. Authentication & Identity Contracts

| UI Feature | Frontend Source | Endpoint | Method | Request Schema | Response Schema | Auth Type | DB Tables | Backend Handler |
|---|---|---|---|---|---|---|---|---|
| **Guest Auto-Register** | `src/lib/api.ts:ensureGuestAuth` | `/api/v1/auth/register` | `POST` | `{"email", "password", "name"}` | `{"access_token", "token_type", "user"}` | Public | `users`, `workspaces` | `auth.register` |
| **Email Login** | `src/components/app/AuthModal.tsx` | `/api/v1/auth/login` | `POST` | `{"email", "password"}` | `{"access_token", "token_type", "user"}` | Public (Rate limit 20/min) | `users`, `workspaces` | `auth.login` |
| **OAuth Login** | `src/components/app/AuthModal.tsx` | `/api/v1/auth/oauth` | `POST` | `{"provider", "email", "name", "provider_id"}` | `{"access_token", "token_type", "user"}` | Public | `users`, `workspaces` | `auth.oauth_login` |
| **User Sign Out** | `src/components/app/Sidebar.tsx` | `/api/v1/auth/logout` | `POST` | Empty | `{"status": "ok", "message"}` | Cookie / Header | N/A | `auth.logout` |
| **Profile Hydration** | `src/components/app/Sidebar.tsx` | `/api/v1/auth/me` | `GET` | Empty | `{"id", "email", "name", "is_admin", "workspace_id"}` | `paperlens_token` cookie or Bearer | `users`, `workspaces` | `auth.get_me` |

---

## 2. Document & Paper Management Contracts

| UI Feature | Frontend Source | Endpoint | Method | Request Schema | Response Schema | Auth Type | DB Tables | Backend Handler |
|---|---|---|---|---|---|---|---|---|
| **Upload PDF** | `src/routes/upload.tsx`, `UploadModal.tsx` | `/api/v1/papers/upload` | `POST` | `multipart/form-data` (`file`, optional `workspace_id`) | `PaperUploadResponse` (`paper_id`, `file_name`, `status`) | Required (Tenant scoped) | `papers`, `workspaces` | `papers.upload_paper` |
| **List Papers** | `src/routes/papers.tsx`, `dashboard.tsx` | `/api/v1/papers` | `GET` | Optional query params | `PaperResponse[]` | Required (Tenant scoped) | `papers`, `workspaces` | `papers.list_papers` |
| **Paper Detail** | `src/routes/paper.$id.tsx` | `/api/v1/papers/{id}` | `GET` | Path `id: UUID` | `PaperResponse` | Required (Anti-IDOR 404) | `papers`, `workspaces` | `papers.get_paper` |
| **Delete Paper** | `src/routes/papers.tsx` | `/api/v1/papers/{id}` | `DELETE` | Path `id: UUID` | `204 No Content` / Empty | Required (Anti-IDOR 404) | `papers`, `paper_pages`, `paper_sections`, `paper_chunks` | `papers.delete_paper` |
| **Poll Status** | `src/components/app/UploadModal.tsx` | `/api/v1/papers/{id}/status` | `GET` | Path `id: UUID` | `PaperStatusResponse` (`stage`, `progress`, `stages_detail`) | Required (Anti-IDOR 404) | `papers` | `papers.get_paper_status` |
| **Retry Pipeline**| `src/routes/paper.$id.tsx` | `/api/v1/papers/{id}/retry` | `POST` | Path `id: UUID` | `{"message", "paper_id", "status"}` | Required (Anti-IDOR 404) | `papers` | `papers.retry_paper` |

---

## 3. Scientific Analysis & Grounded Q&A Contracts

| UI Feature | Frontend Source | Endpoint | Method | Request Schema | Response Schema | Auth Type | DB Tables | Backend Handler |
|---|---|---|---|---|---|---|---|---|
| **Grounded Q&A** | `src/routes/paper.$id.tsx` (Q&A Tab) | `/api/v1/papers/{id}/questions` | `POST` | `{"question": string}` | `QuestionAnsweringResponse` (`question_id`, `answer`, `abstained`, `support_score`, `sources: [{page, section, chunk_id, text}]`) | Required (Rate limit 30/min) | `questions`, `answers`, `answer_evidence`, `paper_chunks` | `papers.ask_question` |
| **Structured Summary** | `src/routes/paper.$id.tsx` (Overview Tab) | `/api/v1/papers/{id}/analysis` | `GET` | Path `id: UUID` | `PaperAnalysisResponse` (10 fields) | Required (Anti-IDOR 404) | `paper_analysis` | `papers.get_paper_analysis` |
| **Methodology** | `src/routes/paper.$id.tsx` (Methodology Tab) | `/api/v1/papers/{id}/methodology` | `GET` | Path `id: UUID` | `MethodologyExtractionResponse` (8 parts) | Required (Anti-IDOR 404) | `paper_analysis` | `papers.get_paper_methodology` |
| **Contributions** | `src/routes/paper.$id.tsx` (Contributions Tab) | `/api/v1/papers/{id}/contributions` | `GET` | Path `id: UUID` | `ContributionExtractionResponse` (Explicit vs Inferred) | Required (Anti-IDOR 404) | `paper_analysis` | `papers.get_paper_contributions` |
| **Benchmark Eval** | `src/routes/paper.$id.tsx` | `/api/v1/papers/{id}/evaluate` | `POST` | Path `id: UUID` | `EvaluationBenchmarkReport` (3-way RAG comparison) | Required (Anti-IDOR 404) | `evaluation_runs`, `papers` | `papers.evaluate_paper` |

---

## 4. Administration & System Health Contracts

| UI Feature | Frontend Source | Endpoint | Method | Request Schema | Response Schema | Auth Type | DB Tables | Backend Handler |
|---|---|---|---|---|---|---|---|---|
| **Admin Stats** | `src/components/app/AdminModal.tsx` | `/api/v1/admin/stats` | `GET` | Empty | `{"total_users", "total_papers", "ready_papers", "total_questions"}` | Required (Admin only) | `users`, `papers`, `questions` | `admin.get_admin_stats` |
| **Admin Users** | `src/components/app/AdminModal.tsx` | `/api/v1/admin/users` | `GET` | Empty | Array of User profiles | Required (Admin only) | `users`, `workspaces` | `admin.get_admin_users` |
| **Delete User** | `src/components/app/AdminModal.tsx` | `/api/v1/admin/users/{id}` | `DELETE` | Path `id: UUID` | `204 No Content` | Required (Admin only) | `users` | `admin.delete_admin_user` |
| **System Health** | `src/routes/settings.tsx` | `/api/v1/health` | `GET` | Empty | `{"status", "environment", "database", "ai_service"}` | Public | N/A | `health.health_check` |
