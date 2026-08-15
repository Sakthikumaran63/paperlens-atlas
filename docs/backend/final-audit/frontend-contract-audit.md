# PaperLens Atlas — Frontend Contract Audit

## 1. Traceability Audit (Frontend Request $\rightarrow$ Backend Response)

| Screen / Component | Frontend Source | Function / Hook | Method | Target URL | Expected Response Schema | Used Response Fields | Status |
|---|---|---|---|---|---|---|---|
| **App Layout** | `Sidebar.tsx` | `getMe()` | `GET` | `/api/v1/auth/me` | `UserResponse` | `id`, `email`, `name`, `is_admin` | **VERIFIED** |
| **Auth Modal** | `AuthModal.tsx` | `loginUser()` | `POST` | `/api/v1/auth/login` | `Token` | `access_token`, `token_type`, `user` | **VERIFIED** |
| **Auth Modal** | `AuthModal.tsx` | `registerUser()`| `POST` | `/api/v1/auth/register` | `Token` | `access_token`, `token_type`, `user` | **VERIFIED** |
| **Auth Modal** | `AuthModal.tsx` | `oauthLogin()` | `POST` | `/api/v1/auth/oauth` | `Token` | `access_token`, `token_type`, `user` | **VERIFIED** |
| **Sidebar Signout**| `Sidebar.tsx` | `logoutUser()` | `POST` | `/api/v1/auth/logout` | `{"status", "message"}`| Cookie cleared | **VERIFIED** |
| **Dashboard** | `dashboard.tsx` | `getPapers()` | `GET` | `/api/v1/papers` | `PaperResponse[]` | `id`, `title`, `status`, `stage`, `page_count` | **VERIFIED** |
| **Paper Library**| `papers.tsx` | `getPapers()` | `GET` | `/api/v1/papers` | `PaperResponse[]` | Full paper array, filter & delete triggers | **VERIFIED** |
| **Upload Modal** | `UploadModal.tsx`| `uploadPaper()` | `POST` | `/api/v1/papers/upload`| `PaperUploadResponse` | `paper_id`, `file_name`, `status` | **VERIFIED** |
| **Upload Modal** | `UploadModal.tsx`| `getPaperStatus()`| `GET` | `/api/v1/papers/{id}/status`| `PaperStatusResponse` | `stage`, `progress`, `stages_detail` | **VERIFIED** |
| **Paper Workspace**| `paper.$id.tsx` | `getPaperDetail()`| `GET` | `/api/v1/papers/{id}` | `PaperResponse` | `title`, `authors`, `page_count`, `sections` | **VERIFIED** |
| **Paper Workspace**| `paper.$id.tsx` | `retryPaperPipeline()`| `POST`| `/api/v1/papers/{id}/retry`| `{"message", "paper_id", "status"}`| Status state reset to PROCESSING | **VERIFIED** |
| **Overview Tab** | `paper.$id.tsx` | `getPaperAnalysis()`| `GET` | `/api/v1/papers/{id}/analysis`| `PaperAnalysisResponse` | 10 structured fields | **VERIFIED** |
| **Methodology Tab**| `paper.$id.tsx`| `getPaperMethodology()`| `GET`| `/api/v1/papers/{id}/methodology`| `MethodologyExtractionResponse`| 8 structured components | **VERIFIED** |
| **Contributions Tab**| `paper.$id.tsx`| `getPaperContributions()`| `GET`| `/api/v1/papers/{id}/contributions`| `ContributionExtractionResponse`| Explicit & inferred claims | **VERIFIED** |
| **Grounded Q&A Tab**| `paper.$id.tsx`| `askPaperQuestion()`| `POST`| `/api/v1/papers/{id}/questions`| `QuestionAnsweringResponse`| `answer`, `abstained`, `support_score`, `sources` | **VERIFIED** |
| **Activity Feed** | `activity.tsx` | `getPapers()` | `GET` | `/api/v1/papers` | `PaperResponse[]` | Real event timeline generation | **VERIFIED** |
| **Admin Panel** | `AdminModal.tsx` | `getAdminStats()` | `GET` | `/api/v1/admin/stats` | `AdminStatsResponse` | `total_users`, `total_papers`, `total_questions` | **VERIFIED** |
| **Admin Panel** | `AdminModal.tsx` | `getAdminUsers()` | `GET` | `/api/v1/admin/users` | `User[]` | List of registered users | **VERIFIED** |
| **Admin Panel** | `AdminModal.tsx` | `deleteAdminUser()`| `DELETE`| `/api/v1/admin/users/{id}`| `204 No Content` | User deletion | **VERIFIED** |
| **Settings Page**| `settings.tsx` | `fetchHealth()` | `GET` | `/api/v1/health` | `HealthResponse` | System status & diagnostics | **VERIFIED** |

---

## 2. Contract Fidelity Verdict

- Total Frontend API calls audited: **20/20**
- Contract Mismatches Found: **0**
- Missing Endpoints: **0**
- Contract Integration Score: **100/100**
