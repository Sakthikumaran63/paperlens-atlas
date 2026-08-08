from datetime import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.enums import QuestionType


class GoldEvidenceItem(BaseModel):
    page: Optional[int] = None
    section: Optional[str] = None
    text: Optional[str] = None
    chunk_id: Optional[str] = None

    class Config:
        from_attributes = True


class EvaluationQuestionItem(BaseModel):
    id: str
    paper_id: uuid.UUID
    question: str
    question_type: QuestionType = QuestionType.GENERAL
    gold_answer: str
    gold_evidence: List[GoldEvidenceItem] = Field(default_factory=list)
    page: Optional[int] = None
    section: Optional[str] = None
    answerable: bool = True

    class Config:
        from_attributes = True


class EvaluationDataset(BaseModel):
    dataset_name: str = "PaperLens Benchmark Dataset"
    items: List[EvaluationQuestionItem] = Field(default_factory=list)

    class Config:
        from_attributes = True


class RetrievalMetrics(BaseModel):
    recall_at_k: float = Field(description="Fraction of gold evidence chunks retrieved in Top-K candidates.")
    precision_at_k: float = Field(description="Fraction of retrieved Top-K candidates matching gold evidence.")
    mrr: float = Field(description="Mean Reciprocal Rank (1/rank) of first relevant gold evidence chunk.")


class AnswerMetrics(BaseModel):
    semantic_similarity: float = Field(description="Token overlap similarity between generated answer and gold answer.")
    exact_match: float = Field(description="Fraction of exact string matches.")
    human_eval_support: float = Field(description="Fraction of non-abstained, factual candidate answers.")


class GroundingMetrics(BaseModel):
    evidence_precision: float = Field(description="Fraction of cited evidence chunks matching gold evidence.")
    evidence_recall: float = Field(description="Fraction of gold evidence chunks cited in answer.")
    unsupported_claim_rate: float = Field(description="Fraction of generated claims lacking ground evidence support.")


class AbstentionMetrics(BaseModel):
    answerable_accuracy: float = Field(description="Fraction of answerable questions correctly answered.")
    unanswerable_detection: float = Field(description="Fraction of unanswerable questions correctly abstained (refused).")
    false_answer_rate: float = Field(description="Fraction of unanswerable questions incorrectly answered factually (hallucination rate).")


class ConfigurationEvalReport(BaseModel):
    config_name: str
    total_questions: int
    answerable_count: int
    unanswerable_count: int
    retrieval: RetrievalMetrics
    answer: AnswerMetrics
    grounding: GroundingMetrics
    abstention: AbstentionMetrics


class EvaluationBenchmarkReport(BaseModel):
    benchmark_id: str
    timestamp: str
    configurations: List[ConfigurationEvalReport]

    class Config:
        from_attributes = True
