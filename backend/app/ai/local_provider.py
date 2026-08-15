"""
PaperLens Local AI Provider
----------------------------
Implements local, deterministic, zero-dependency extractive answer generation
and confidence estimation using heuristic text algorithms.
"""
import time
from typing import List
from app.ai.base import AIProvider, GenerationResult
from app.models.enums import QuestionType
from app.schemas.evidence import EvidencePackage
from app.services.offline_ai import generate_offline_answer


class LocalModelProvider(AIProvider):
    """
    Primary local AI provider.
    Generates evidence-grounded answers without calling external cloud APIs.
    """

    def __init__(self, model_name: str = "paperlens-local-extractive", model_version: str = "1.0.0"):
        self.model_name = model_name
        self.model_version = model_version

    async def generate_answer(
        self,
        question_text: str,
        question_type: QuestionType,
        evidence_package: EvidencePackage,
    ) -> GenerationResult:
        start_time = time.perf_counter()

        if not evidence_package.items:
            return GenerationResult(
                answer="I couldn't find enough information in the uploaded paper to answer this reliably.",
                evidence_ids=[],
                confidence=0.0,
                abstain=True,
                provider="LOCAL",
                model_name=self.model_name,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Run local extractive Q&A heuristic
        offline_out = generate_offline_answer(
            question_text=question_text,
            evidence_package=evidence_package,
            question_type=question_type,
        )

        latency = int((time.perf_counter() - start_time) * 1000)
        return GenerationResult(
            answer=offline_out.answer,
            evidence_ids=offline_out.evidence_ids,
            confidence=offline_out.confidence,
            abstain=offline_out.abstain,
            provider="LOCAL",
            model_name=self.model_name,
            fallback_used=False,
            fallback_reason=None,
            latency_ms=latency,
        )

    async def estimate_confidence(
        self,
        question_text: str,
        evidence_package: EvidencePackage,
        candidate_answer: str,
    ) -> float:
        if not candidate_answer or not evidence_package.items:
            return 0.0
        q_tokens = set(question_text.lower().split())
        ans_tokens = set(candidate_answer.lower().split())
        overlap = len(q_tokens.intersection(ans_tokens)) / max(len(q_tokens), 1)
        return min(max(overlap * 1.5, 0.2), 1.0)
