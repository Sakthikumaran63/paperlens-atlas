from contextlib import asynccontextmanager
import logging
import sys
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import subprocess

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger("paperlens")

# ── SQLite compatibility shim ────────────────────────────────────────────────
# When DATABASE_URL is sqlite+aiosqlite, swap out PostgreSQL-specific types
# (postgresql.UUID and pgvector.Vector) with generic SQLAlchemy equivalents
# BEFORE any model modules are imported.
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
        # Handled asynchronously in lifespan; skip here.
        return

    try:
        logger.info("Applying database migrations via Alembic CLI...")
        res = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            logger.info(f"Database migrations applied successfully:\n{res.stdout}")
        else:
            logger.error(f"Database migration failed (code {res.returncode}):\n{res.stderr}")
    except Exception as e:
        logger.error(f"Error executing database migrations: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENV}] environment...")
    if _IS_SQLITE:
        from app.db.session import engine
        from app.db.base import Base
        import app.models  # noqa: F401 - register all models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite mode: all tables created via create_all.")
    else:
        run_db_migrations()
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")



app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

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

