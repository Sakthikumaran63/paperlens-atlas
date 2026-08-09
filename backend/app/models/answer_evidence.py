from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Text, func
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.answer import Answer
    from app.models.retrieved_evidence import RetrievedEvidence


class AnswerEvidence(Base):
    __tablename__ = "answer_evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    retrieved_evidence_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("retrieved_evidences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relevance_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quote_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    answer: Mapped["Answer"] = relationship("Answer", back_populates="evidences")
    retrieved_evidence: Mapped["RetrievedEvidence"] = relationship("RetrievedEvidence", back_populates="answer_evidences")
