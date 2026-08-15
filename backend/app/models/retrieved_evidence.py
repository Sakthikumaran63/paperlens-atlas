from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.paper_chunk import PaperChunk
    from app.models.question import Question


class RetrievedEvidence(Base):
    __tablename__ = "retrieved_evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("paper_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    # Documented in database-design.md §2.10 — composite retrieval scores
    semantic_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bm25_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    section_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="retrieved_evidences")
    chunk: Mapped[Optional["PaperChunk"]] = relationship("PaperChunk")
