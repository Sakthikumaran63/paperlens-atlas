"""Pydantic schemas for the /papers API surface.

ASSUMPTION: `PipelineStage` is the same granular stage enum the pipeline
orchestrator tracks (`PaperStage` in `app.services.pipeline_orchestrator`)
— PENDING/EXTRACTING/STRUCTURING/CHUNKING/EMBEDDING/ANALYZING/READY/FAILED.
`PaperStatus` below is a coarser, user-facing status derived from it, since
most clients (e.g. a polling UI) care about "is this done / in progress /
failed" more than the exact internal stage.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.enums import PaperStatus, PipelineStage


__all__ = [
    "PipelineStage",
    "PaperStatus",
    "derive_paper_status",
    "PaperUploadResponse",
    "PaperStatusResponse",
    "PaperRetryResponse",
    "PaperResponse",
    "RecommendedPaper",
    "PaperRecommendationsResponse",
]


from app.models.enums import PaperStatus



_IN_PROGRESS_STAGES = {
    PipelineStage.EXTRACTING,
    PipelineStage.STRUCTURING,
    PipelineStage.CHUNKING,
    PipelineStage.EMBEDDING,
    PipelineStage.ANALYZING,
}


def derive_paper_status(stage: PipelineStage) -> PaperStatus:
    """Collapse the granular pipeline stage into a coarse client-facing status."""
    if stage == PipelineStage.FAILED:
        return PaperStatus.FAILED
    if stage == PipelineStage.READY:
        return PaperStatus.READY
    if stage in _IN_PROGRESS_STAGES:
        return PaperStatus.PROCESSING
    return PaperStatus.UPLOADED



class PaperUploadResponse(BaseModel):
    paper_id: uuid.UUID
    file_name: Optional[str] = None
    filename: Optional[str] = None
    status: PaperStatus
    message: str = "Upload received. Processing has started."


class PaperStatusResponse(BaseModel):
    paper_id: uuid.UUID
    status: PaperStatus
    stage: PipelineStage
    progress: int = Field(ge=0, le=100)
    stages_detail: dict[str, Any] = Field(default_factory=dict)
    processing_error: Optional[str] = None


class PaperRetryResponse(BaseModel):
    paper_id: uuid.UUID
    status: PaperStatus
    message: str = "Retry has been scheduled."


class PaperResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    authors: Optional[str] = None
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    file_name: str
    file_path: Optional[str] = None
    file_size: int
    page_count: int = 0
    status: PaperStatus
    stage: PipelineStage
    progress: int = 0
    stage_details_json: Optional[dict[str, Any]] = None
    processing_error: Optional[str] = None

    class Config:
        from_attributes = True


class RecommendedPaper(BaseModel):
    title: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    url: Optional[str] = None


class PaperRecommendationsResponse(BaseModel):
    seed_paper_id: Optional[uuid.UUID] = None
    seed_title: str
    count: int
    recommendations: list[RecommendedPaper]


