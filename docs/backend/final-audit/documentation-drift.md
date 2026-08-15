# PaperLens Atlas — Documentation Drift Audit

## 1. Audit Analysis

An audit was conducted across the root `README.md`, `DOCUMENTATION.md`, `docs/`, and actual codebase implementation:

| Documentation Claim | Implementation Reality | Drift Level | Resolution Status |
|---|---|---|---|
| **Cookie Authentication** | Implemented via `paperlens_token` `httpOnly`, `SameSite=Lax` cookie in `auth.py` and `deps.py`. | **Zero Drift** | Documented accurately |
| **Workspace Isolation (Anti-IDOR)** | Implemented via `get_workspace_scoped_paper` returning `404 Not Found`. | **Zero Drift** | Documented accurately |
| **Citation Verification Threshold** | RapidFuzz partial ratio $S \ge 90$ enforced in `evidence_verification_service.py`. | **Zero Drift** | Documented accurately |
| **Retrieval Scoring Formula** | Weighted formula ($0.60 \times \text{sem} + 0.25 \times \text{sec} + 0.15 \times \text{BM25}$) active in `retrieval_strategy_service.py`. | **Zero Drift** | Documented accurately |
| **AI Provider Hierarchy** | Local-First (`LocalModelProvider`) primary with policy-driven Gemini fallback in `app/ai/`. | **Zero Drift** | Documented accurately |
| **Rate Limiting** | Slowapi sliding-window limiter on `/auth/login` (20/min), `/auth/register` (10/min), `/papers/{id}/questions` (30/min). | **Zero Drift** | Documented accurately |
| **Pipeline Reconciler** | Startup task `reconcile_stuck_papers` and `/retry` endpoint active. | **Zero Drift** | Documented accurately |

---

## 2. Conclusion

The documentation suite in `docs/`, `DOCUMENTATION.md`, and `README.md` is **100% synchronized** with the actual running codebase. No documentation drift or obsolete claims were discovered.
