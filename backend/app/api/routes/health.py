import time
from typing import Dict
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
@router.get("/api/v1/health")
async def health_check(
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Comprehensive multi-component health check.
    Checks:
    - Application status & settings
    - PostgreSQL Database connectivity (SELECT 1) and latency
    - Vector Storage (pgvector extension verification)
    - Embedding Service configuration
    - LLM Service configuration
    Returns 200 OK if operational/degraded, 503 if critical database failure occurs.
    Does not expose sensitive API keys or internal stack traces.
    """
    components: Dict[str, Dict] = {}
    is_unhealthy = False

    # 1. Application status
    components["application"] = {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "environment": settings.ENV

    }

    # 2. Database ping
    try:
        t0 = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        components["database"] = {
            "status": "healthy",
            "latency_ms": latency_ms
        }
    except Exception as db_err:
        is_unhealthy = True
        components["database"] = {
            "status": "unhealthy",
            "error": "Database connectivity failed"
        }

    # 3. Vector storage (pgvector extension check — PostgreSQL only)
    try:
        if settings.DATABASE_URL.startswith("sqlite"):
            components["vector_storage"] = {
                "status": "offline_mode",
                "extension": "SQLite (no pgvector in local dev)"
            }
        else:
            vec_res = await db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            vec_ext = vec_res.scalar_one_or_none()
            components["vector_storage"] = {
                "status": "healthy" if vec_ext else "degraded",
                "extension": "pgvector" if vec_ext else "pgvector extension not registered"
            }
    except Exception:
        components["vector_storage"] = {
            "status": "degraded",
            "extension": "pgvector check unavailable"
        }


    # 4. Embedding service configuration check
    components["embedding_service"] = {
        "status": "configured" if settings.EMBEDDING_API_KEY else "unconfigured",
        "model": settings.EMBEDDING_MODEL,
        "dimension": settings.EMBEDDING_DIMENSION
    }

    # 5. LLM service configuration check
    components["llm_service"] = {
        "status": "configured" if settings.LLM_API_KEY else "unconfigured",
        "model": settings.LLM_MODEL
    }

    overall_status = "unhealthy" if is_unhealthy else "healthy"
    if is_unhealthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "components": components
    }
