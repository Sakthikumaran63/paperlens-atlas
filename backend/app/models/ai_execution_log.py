"""
AI Execution Log Model
----------------------
Stores auditable metadata for every AI inference invocation (tokens, latency,
provider, model, fallback reasons) without recording confidential secrets.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.types import GUID


class AIExecutionLog(Base):
    __tablename__ = "ai_execution_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    question_id = Column(GUID(), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True)
    provider = Column(String(64), nullable=False)
    model_name = Column(String(128), nullable=False)
    model_version = Column(String(64), nullable=True)
    request_type = Column(String(64), nullable=False, default="QUESTION_ANSWERING")
    latency_ms = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=True)
    fallback_used = Column(Boolean, nullable=False, default=False)
    fallback_reason = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    question = relationship("Question", foreign_keys=[question_id])
