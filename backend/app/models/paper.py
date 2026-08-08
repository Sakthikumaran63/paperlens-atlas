from datetime import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaperStatus, PipelineStage

if TYPE_CHECKING:
    from app.models.paper_analysis import PaperAnalysis
    from app.models.paper_chunk import PaperChunk
    from app.models.paper_page import PaperPage
    from app.models.paper_section import PaperSection
    from app.models.workspace import Workspace


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[PaperStatus] = mapped_column(
        Enum(PaperStatus, name="paper_status_enum"), default=PaperStatus.UPLOADED, nullable=False
    )
    stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage, name="pipeline_stage_enum"), default=PipelineStage.UPLOADING, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage_details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="papers")
    pages: Mapped[List["PaperPage"]] = relationship(
        "PaperPage", back_populates="paper", cascade="all, delete-orphan", order_by="PaperPage.page_number"
    )
    sections: Mapped[List["PaperSection"]] = relationship(
        "PaperSection", back_populates="paper", cascade="all, delete-orphan", order_by="PaperSection.order_index"
    )
    chunks: Mapped[List["PaperChunk"]] = relationship(
        "PaperChunk", back_populates="paper", cascade="all, delete-orphan", order_by="PaperChunk.chunk_index"
    )
    analysis: Mapped[Optional["PaperAnalysis"]] = relationship(
        "PaperAnalysis", back_populates="paper", uselist=False, cascade="all, delete-orphan"
    )
