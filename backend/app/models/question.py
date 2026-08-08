from datetime import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QuestionType

if TYPE_CHECKING:
    from app.models.answer import Answer
    from app.models.paper import Paper
    from app.models.retrieved_evidence import RetrievedEvidence
    from app.models.workspace import Workspace


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type_enum"), default=QuestionType.GENERAL, nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="questions")
    paper: Mapped[Optional["Paper"]] = relationship("Paper")
    retrieved_evidences: Mapped[List["RetrievedEvidence"]] = relationship(
        "RetrievedEvidence", back_populates="question", cascade="all, delete-orphan", order_by="RetrievedEvidence.rank"
    )
    answer: Mapped[Optional["Answer"]] = relationship(
        "Answer", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )
