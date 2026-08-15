from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.answer import Answer
    from app.models.paper_chunk import PaperChunk


class AnswerEvidence(Base):
    __tablename__ = "answer_evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("paper_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quote_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Documented in database-design.md §2.11 — citation verification fields
    verification_method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # EXACT | RAPIDFUZZ_PARTIAL
    verification_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relevance_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    answer: Mapped["Answer"] = relationship("Answer", back_populates="evidences")
    chunk: Mapped[Optional["PaperChunk"]] = relationship("PaperChunk")
