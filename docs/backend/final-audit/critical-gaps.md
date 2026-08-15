# PaperLens Atlas — Critical Gaps & Risk Analysis

## 1. Risk & Gap Classification

| Priority | Issue Description | Location | Risk Assessment | Mitigation Implemented | Verification |
|---|---|---|---|---|---|
| **P0** (Critical) | Cross-tenant IDOR file/data probing | `papers.py` | High risk of unauthorized research paper access | `get_workspace_scoped_paper` returns 404 on cross-user queries | **VERIFIED (PASS)** |
| **P0** (Critical) | XSS session token theft | `localStorage` | High risk of credential theft | Replaced with `httpOnly`, `SameSite=Lax` cookie `paperlens_token` | **VERIFIED (PASS)** |
| **P1** (High) | Citation fabrication by LLMs | `answer_generation_service.py` | High risk of hallucinated research citations | Exact substring + RapidFuzz $\ge 90$ quote check before saving evidence | **VERIFIED (PASS)** |
| **P1** (High) | PDF prompt injection hijacking | `llm_service.py` | High risk of prompt extraction/jailbreak | Encapsulated in `<UNTRUSTED_DOCUMENT_CONTENT>` with strict passive directives | **VERIFIED (PASS)** |
| **P2** (Medium) | Stalled background processing jobs | `pipeline_orchestrator.py` | Medium risk of permanently stuck papers | `reconcile_stuck_papers` background reconciler + `/retry` endpoint | **VERIFIED (PASS)** |
| **P2** (Medium) | Brute-force / DoS on Q&A & Auth | `auth.py`, `papers.py` | Medium risk of API exhaustion | Slowapi sliding-window rate limiting (`/login` 20/min, `/questions` 30/min) | **VERIFIED (PASS)** |
| **P3** (Low) | Offline demo failure without OpenAI key | `offline_ai.py` | Low risk in production, high impact for local demo | Local extractive Q&A and deterministic pseudo-embeddings | **VERIFIED (PASS)** |

---

## 2. Unresolved Gaps

- **P0 Gaps**: **0**
- **P1 Gaps**: **0**
- **P2 Gaps**: **0**
- **P3 Gaps**: **0**

All identified vulnerabilities, performance risks, and architectural gaps have been resolved and verified with automated test suites.
