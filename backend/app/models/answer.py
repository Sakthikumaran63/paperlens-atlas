from datetime import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.answer_evidence import AnswerEvidence
    from app.models.question import Question


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_abstained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    abstention_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="answer")
    evidences: Mapped[List["AnswerEvidence"]] = relationship(
        "AnswerEvidence", back_populates="answer", cascade="all, delete-orphan"
    )
