"""
Job Worker Orchestrator
-----------------------
Manages background worker lifecycles.
"""
import logging
from app.jobs.tasks import run_paper_pipeline_task

logger = logging.getLogger("paperlens")


class PipelineWorker:
    """Worker handling document processing pipeline execution."""

    @staticmethod
    async def process_paper(paper_id, force_retry: bool = False):
        logger.info("PipelineWorker processing paper %s (force_retry=%s)", paper_id, force_retry)
        await run_paper_pipeline_task(paper_id=paper_id, force_retry=force_retry)
