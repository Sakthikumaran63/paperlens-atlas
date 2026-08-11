import uuid
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import RetrievalMode, SectionType


class RetrievedChunkCandidate(BaseModel):
    chunk_id: uuid.UUID
    paper_id: uuid.UUID
    page_number: int = 1
    page: int = 1
    section_id: Optional[uuid.UUID] = None
    section_type: SectionType = SectionType.OTHER
    section_title: str = "Document Text"
    section: str = "Document Text"
    text: str = ""
    semantic_score: float = 0.0
    section_score: float = 0.0
    keyword_score: float = 0.0
    final_score: float = 0.0
    similarity_score: float = 0.0

    class Config:
        from_attributes = True


    class Config:
        from_attributes = True


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    mode: RetrievalMode = RetrievalMode.STRUCTURE_AWARE_RAG
    section_type: Optional[SectionType] = None
