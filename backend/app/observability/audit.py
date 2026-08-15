"""
Audit Event Logging Module
--------------------------
Records auditable system and user actions to the database.
"""
import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity_log import ActivityLog

logger = logging.getLogger("paperlens")


class AuditLogger:
    """Logs workspace lifecycle and security events."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        event_type: str,
        entity_type: str,
        user_id: Optional[uuid.UUID] = None,
        entity_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            record = ActivityLog(
                workspace_id=workspace_id,
                user_id=user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
            db.add(record)
            await db.flush()
            logger.info("Audit logged: %s for %s (%s)", event_type, entity_type, entity_id)
        except Exception as err:
            logger.warning("Failed to record audit event: %s", err)
