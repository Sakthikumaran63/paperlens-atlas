from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import subprocess

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger("paperlens")


def run_db_migrations():
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

