# PaperLens Atlas — Repository Inventory

## 1. Directory Structure

```text
paperlens-atlas/
├── backend/
│   ├── app/
│   │   ├── ai/                     # AI providers (base, local_provider, gemini_provider, fallback_policy, router)
│   │   ├── api/
│   │   │   ├── routes/             # auth.py, papers.py, questions.py, health.py, admin.py
│   │   │   ├── deps.py             # Auth extraction & get_workspace_scoped_paper
│   │   │   └── router.py           # Master API router
│   │   ├── core/                   # config.py, limiter.py, logging.py, security.py
│   │   ├── db/                     # base.py, session.py, sqlite_shim.py, types.py
│   │   ├── models/                 # 13 SQLAlchemy models
│   │   ├── repositories/           # Data access layers
│   │   ├── schemas/                # Pydantic validation models
│   │   ├── services/               # Ingestion, RAG, verification, offline AI, reconciler
│   │   ├── utils/                  # storage.py (path traversal safe upload storage)
│   │   └── main.py                 # FastAPI app entry point, CORS, Slowapi limiter & lifespan
│   ├── Data/base paper/            # 6 base research papers (.pdf)
│   ├── scripts/                    # ingest_qasper_benchmark.py
│   ├── tests/                      # 24 pytest test suites
│   ├── alembic/                    # Database migrations
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/app/         # AuthModal, AdminModal, Sidebar, Header, etc.
│   │   ├── components/ui/          # Radix & Tailwind design system
│   │   ├── lib/                    # api.ts, utils.ts
│   │   ├── routes/                 # TanStack Router file-based pages
│   │   └── index.css               # Design tokens
│   └── package.json                # Frontend dependencies
├── docs/                           # Architecture, API, Security, Testing, Research docs
├── scratch/                        # test_improvements.py, test_full_pipeline.py
├── run_offline.ps1                 # Local execution script
├── DOCUMENTATION.md                # Master technical documentation
└── README.md                       # Comprehensive project README
```

---

## 2. Key Components & Entry Points

- **Backend Application Entry Point**: `backend/app/main.py:app` (Uvicorn on port 8000).
- **Frontend Entry Point**: `frontend/src/routes/__root.tsx` (Vite on port 8080 / 5173).
- **Centralized Frontend API Client**: `frontend/src/lib/api.ts`.
- **Database Engine & Shims**: `backend/app/db/session.py`, `backend/app/db/sqlite_shim.py`.
- **AI Architecture**: `backend/app/ai/router.py` (LocalModelProvider primary, GeminiProvider fallback).
- **Verification Engine**: `backend/app/services/evidence_verification_service.py` (RapidFuzz $S \ge 90$).
- **Background Pipeline Reconciler**: `backend/app/services/pipeline_reconciler.py`.
