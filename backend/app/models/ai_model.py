"""
AI Model Registry Model
-----------------------
Implements the AI Model Registry table specified in Master Implementation Prompt §15.
Tracks available AI providers, models, versions, active status, and capabilities.
"""
from datetime import datetime
import uuid
from typing import Any, Optional
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import GUID


class AIModel(Base):
    __tablename__ = "ai_models"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # LOCAL, GEMINI, etc.
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)  # GENERATOR, EMBEDDING, RERANKER, CLASSIFIER
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
