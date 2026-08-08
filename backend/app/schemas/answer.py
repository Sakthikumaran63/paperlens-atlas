import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.enums import QuestionType, RetrievalMode


class LLMAnswerOutput(BaseModel):
    answer: str
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    abstain: bool = Field(default=False)

    class Config:
        from_attributes = True


class AnswerEvidenceItem(BaseModel):
    evidence_id: str
    chunk_id: uuid.UUID
    page: int
    section: str
    text: str

    class Config:
        from_attributes = True


class GroundedAnswerResponse(BaseModel):
    question_text: str
    question_type: QuestionType
    answer: str
    evidence_ids: List[str]
    evidences: List[AnswerEvidenceItem]
    confidence: float
    support_score: float = 0.0
    supported: bool = True
    abstain: bool = False
    searched_sections: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    abstention_reason: Optional[str] = None

    class Config:
        from_attributes = True


class AskQuestionRequest(BaseModel):
    question_text: str
    mode: RetrievalMode = RetrievalMode.STRUCTURE_AWARE_RAG
