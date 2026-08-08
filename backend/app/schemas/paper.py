from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel
from app.models.enums import PaperStatus, PipelineStage


class PaperUploadResponse(BaseModel):
    paper_id: uuid.UUID
    file_name: str
    status: PaperStatus

    class Config:
        from_attributes = True


class PaperResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    authors: Optional[str] = None
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    file_name: str
    file_size: int
    page_count: int
    status: PaperStatus
    stage: PipelineStage = PipelineStage.UPLOADING
    progress: int = 0
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperStatusResponse(BaseModel):
    paper_id: uuid.UUID
    status: PaperStatus
    stage: PipelineStage
    progress: int
    stages_detail: Optional[dict] = None
    processing_error: Optional[str] = None

    class Config:
        from_attributes = True
