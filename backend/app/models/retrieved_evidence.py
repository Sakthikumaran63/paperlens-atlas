from datetime import datetime
import uuid
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.answer_evidence import AnswerEvidence
    from app.models.paper_chunk import PaperChunk
    from app.models.question import Question


class RetrievedEvidence(Base):
    __tablename__ = "retrieved_evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paper_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="retrieved_evidences")
    chunk: Mapped["PaperChunk"] = relationship("PaperChunk", back_populates="retrieved_evidences")
    answer_evidences: Mapped[List["AnswerEvidence"]] = relationship(
        "AnswerEvidence", back_populates="retrieved_evidence", cascade="all, delete-orphan"
    )
