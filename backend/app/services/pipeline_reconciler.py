"""
Pipeline Reconciler
-------------------
Identifies Paper records that have stalled in a non-terminal processing state
(e.g., due to server restart or unhandled worker termination) for longer than
STUCK_TIMEOUT_MINUTES and marks them as FAILED with an explicit actionable message.
"""
from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus
from app.models.paper import Paper

logger = logging.getLogger("paperlens")

STUCK_TIMEOUT_MINUTES = 15
NON_TERMINAL_STATUSES = [
    PaperStatus.UPLOADED,
    PaperStatus.PROCESSING,
]


async def reconcile_stuck_papers(db: AsyncSession, timeout_minutes: int = STUCK_TIMEOUT_MINUTES) -> int:
    """Finds all papers stalled in a non-terminal state and marks them FAILED."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    stmt = select(Paper).where(
        Paper.status.in_(NON_TERMINAL_STATUSES),
        Paper.updated_at < cutoff,
    )
    result = await db.execute(stmt)
    stuck_papers = result.scalars().all()

    if not stuck_papers:
        return 0

    count = 0
    for paper in stuck_papers:
        logger.warning(
            "Reconciler found stalled paper %s (stage: %s, updated_at: %s). Marking as FAILED.",
            paper.id, paper.stage, paper.updated_at
        )
        paper.status = PaperStatus.FAILED
        paper.processing_error = (
            f"Pipeline stalled at stage '{paper.stage}' for over {timeout_minutes} minutes. "
            "Click Retry to resume processing."
        )
        count += 1

    await db.commit()
    logger.info("Pipeline reconciler completed. Reconciled %d stalled paper(s).", count)
    return count
