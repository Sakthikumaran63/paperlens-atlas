from datetime import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.answer_evidence import AnswerEvidence
    from app.models.question import Question


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("questions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_abstained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    abstention_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Documented in database-design.md §2.9 and Master Prompt §10 — AI telemetry fields
    support_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fallback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="answer")
    evidences: Mapped[List["AnswerEvidence"]] = relationship(
        "AnswerEvidence", back_populates="answer", cascade="all, delete-orphan"
    )
