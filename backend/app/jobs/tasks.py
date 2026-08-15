"""
Background Pipeline Tasks
-------------------------
Executable task wrappers for paper ingestion and analysis stages.
"""
import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.pipeline_orchestrator import PaperPipelineOrchestrator

logger = logging.getLogger("paperlens")


async def run_paper_pipeline_task(
    paper_id: uuid.UUID,
    force_retry: bool = False,
    db: Optional[AsyncSession] = None,
) -> None:
    """Executes the 5-stage document processing pipeline."""
    orchestrator = PaperPipelineOrchestrator()
    await orchestrator.run_pipeline(paper_id=paper_id, force_retry=force_retry, db=db)
