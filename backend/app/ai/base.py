"""
PaperLens Atlas AI Provider Base Interfaces
---------------------------------------------
Defines the Protocol for all AI providers (Local extractive, Gemini, OpenAI)
and common generation result dataclasses.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Protocol
from app.models.enums import QuestionType
from app.schemas.evidence import EvidencePackage


@dataclass
class GenerationResult:
    answer: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    abstain: bool = False
    provider: str = "LOCAL"
    model_name: str = "offline-extractive"
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    latency_ms: int = 0


class AIProvider(Protocol):
    """Protocol for PaperLens LLM and generation providers."""

    async def generate_answer(
        self,
        question_text: str,
        question_type: QuestionType,
        evidence_package: EvidencePackage,
    ) -> GenerationResult:
        ...

    async def estimate_confidence(
        self,
        question_text: str,
        evidence_package: EvidencePackage,
        candidate_answer: str,
    ) -> float:
        ...
