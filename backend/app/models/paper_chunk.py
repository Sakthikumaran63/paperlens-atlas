from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Any, List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.paper import Paper
    from app.models.paper_section import PaperSection
    from app.models.retrieved_evidence import RetrievedEvidence


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paper_sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    metadata_json: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="chunks")
    section: Mapped[Optional["PaperSection"]] = relationship("PaperSection", back_populates="chunks")
    retrieved_evidences: Mapped[List["RetrievedEvidence"]] = relationship(
        "RetrievedEvidence", back_populates="chunk"
    )
