import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.enums import QuestionType, RetrievalMode


class QuestionClassificationRequest(BaseModel):
    question_text: str


class QuestionClassificationResponse(BaseModel):
    question_type: QuestionType
    confidence: float
    retrieval_priorities: List[str]

    class Config:
        from_attributes = True


class QuestionAnsweringRequest(BaseModel):
    question: str
    mode: Optional[RetrievalMode] = RetrievalMode.STRUCTURE_AWARE_RAG


class SourceMetadataItem(BaseModel):
    page: int
    section: str
    chunk_id: uuid.UUID
    text: str

    class Config:
        from_attributes = True


class QuestionAnsweringResponse(BaseModel):
    question_id: uuid.UUID
    question: str
    question_type: QuestionType
    answer: str
    abstained: bool
    support_score: float
    sources: List[SourceMetadataItem]

    class Config:
        from_attributes = True
