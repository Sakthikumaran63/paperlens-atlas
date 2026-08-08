from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.paper import Paper


class PaperAnalysis(Base):
    __tablename__ = "paper_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_contributions: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="analysis")
