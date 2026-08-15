import app.db.sqlite_shim  # noqa: F401
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import subprocess

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger("paperlens")

_IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")


if _IS_SQLITE:
    import sqlalchemy.dialects.postgresql as _pg
    from sqlalchemy import String, JSON as _JSON

    class _UUIDCompat(String):
        """Drop-in for postgresql.UUID that works on SQLite (stored as TEXT)."""
        def __init__(self, as_uuid=True, length=36, **kw):
            kw.pop("length", None)
            super().__init__(length=36, **kw)

    _pg.UUID = _UUIDCompat  # type: ignore[attr-defined]

    # Patch JSONB → JSON
    _pg.JSONB = _JSON  # type: ignore[attr-defined]

    # Patch pgvector.Vector → JSON (embeddings stored as JSON array offline)
    try:
        import pgvector.sqlalchemy as _pv
        _pv.Vector = _JSON  # type: ignore[attr-defined]
    except ImportError:
        pass

    logger.info("SQLite mode: patched postgresql.UUID and pgvector.Vector for local development.")
# ─────────────────────────────────────────────────────────────────────────────

# Import router AFTER the shim so model classes pick up patched types
from app.api.router import api_router  # noqa: E402


def run_db_migrations():
    if _IS_SQLITE:
        return

    try:
        backend_dir = str(Path(__file__).parent.parent)
        subprocess.run(
            [sys.executable, "-m", "alembic", "stamp", "head"],
            cwd=backend_dir,
            capture_output=True,
            text=True
        )
        logger.info("Alembic revision stamped to head.")
    except Exception as e:
        logger.warning(f"Note on database migration stamp: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENV}] environment...")
    from app.db.session import engine
    from app.db.base import Base
    from sqlalchemy import text
    import app.models  # noqa: F401 - register all models

    async with engine.begin() as conn:
        if not _IS_SQLITE:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as ext_err:
                logger.warning(f"Note on vector extension: {ext_err}")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All database tables created/verified via create_all.")
    if not _IS_SQLITE:
        run_db_migrations()

    # Reconcile stalled pipeline jobs on startup
    try:
        from app.db.session import async_session_factory
        from app.services.pipeline_reconciler import reconcile_stuck_papers
        async with async_session_factory() as session:
            await reconcile_stuck_papers(session)
    except Exception as rec_err:
        logger.warning(f"Initial pipeline reconciliation skipped: {rec_err}")

    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")



from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware configuration
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error": str(exc) if settings.ENV == "development" else "Internal Server Error"
        }
    )


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "PaperLens FastAPI Backend Service",
        "status": "online",
        "health": "/health",
        "documentation": "/docs",
        "api_prefix": "/api/v1"
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}


app.include_router(api_router, prefix="/api/v1")

