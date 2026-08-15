# PaperLens Atlas — API Coverage Matrix

| Endpoint | HTTP Method | Frontend Uses | Backend Implemented | Auth Required | Tenant Isolated | Tested | Status |
|---|---|---|---|---|---|---|---|
| `/api/v1/auth/register` | `POST` | YES (`api.ts`) | YES (`auth.py`) | NO (Public) | Auto-workspace | YES | **COMPLETE** |
| `/api/v1/auth/login` | `POST` | YES (`api.ts`) | YES (`auth.py`) | NO (Rate limit) | N/A | YES | **COMPLETE** |
| `/api/v1/auth/oauth` | `POST` | YES (`api.ts`) | YES (`auth.py`) | NO (Public) | Auto-workspace | YES | **COMPLETE** |
| `/api/v1/auth/logout` | `POST` | YES (`api.ts`) | YES (`auth.py`) | YES (Cookie) | N/A | YES | **COMPLETE** |
| `/api/v1/auth/me` | `GET` | YES (`api.ts`) | YES (`auth.py`) | YES (Cookie/Bearer) | Current User | YES | **COMPLETE** |
| `/api/v1/papers/upload` | `POST` | YES (`api.ts`) | YES (`papers.py`) | YES | YES | YES | **COMPLETE** |
| `/api/v1/papers` | `GET` | YES (`api.ts`) | YES (`papers.py`) | YES | YES | YES | **COMPLETE** |
| `/api/v1/papers/{id}` | `GET` | YES (`api.ts`) | YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}` | `DELETE` | YES (`api.ts`) | YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}/status` | `GET` | YES (`api.ts`) | YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}/retry` | `POST` | YES (`api.ts`) | YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}/questions`| `POST`| YES (`api.ts`) | YES (`papers.py`) | YES (Rate limit) | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}/analysis` | `GET` | YES (`api.ts`) | YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}/methodology`| `GET`| YES (`api.ts`)| YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}/contributions`|`GET`| YES (`api.ts`)| YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/papers/{id}/evaluate`| `POST` | YES (`api.ts`) | YES (`papers.py`) | YES | YES (404 anti-IDOR)| YES | **COMPLETE** |
| `/api/v1/admin/stats` | `GET` | YES (`api.ts`) | YES (`admin.py`) | YES (Admin) | System-wide | YES | **COMPLETE** |
| `/api/v1/admin/users` | `GET` | YES (`api.ts`) | YES (`admin.py`) | YES (Admin) | System-wide | YES | **COMPLETE** |
| `/api/v1/admin/users/{id}` | `DELETE` | YES (`api.ts`)| YES (`admin.py`) | YES (Admin) | System-wide | YES | **COMPLETE** |
| `/api/v1/health` | `GET` | YES (`api.ts`) | YES (`health.py`) | NO | N/A | YES | **COMPLETE** |
