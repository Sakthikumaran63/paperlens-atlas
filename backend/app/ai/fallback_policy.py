"""
PaperLens AI Fallback Policy Engine
------------------------------------
Central decision engine that evaluates local model generation confidence,
evidence coverage, and completeness to determine if Google Gemini fallback
should be engaged.
"""
from dataclasses import dataclass
from typing import Optional
from app.ai.base import GenerationResult
from app.core.config import settings
from app.schemas.evidence import EvidencePackage


@dataclass
class FallbackDecision:
    use_fallback: bool
    reason: Optional[str] = None


class FallbackPolicy:
    """
    Evaluates generation outcomes to decide whether to accept the local answer,
    trigger Gemini fallback, or abstain.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.50,
        min_evidence_items: int = 1,
        gemini_fallback_enabled: bool = True,
    ):
        self.confidence_threshold = confidence_threshold
        self.min_evidence_items = min_evidence_items
        self.gemini_fallback_enabled = gemini_fallback_enabled

    def evaluate(
        self,
        local_result: GenerationResult,
        evidence_package: EvidencePackage,
    ) -> FallbackDecision:
        """
        Determines if local result is satisfactory or if Gemini fallback should be invoked.
        """
        if not self.gemini_fallback_enabled:
            return FallbackDecision(use_fallback=False, reason="FALLBACK_DISABLED_BY_CONFIG")

        # If local model explicitly abstained due to zero evidence, do not fallback
        if not evidence_package.items:
            return FallbackDecision(use_fallback=False, reason="ZERO_EVIDENCE_AVAILABLE")

        # If local model had an error or empty answer
        if not local_result.answer or len(local_result.answer.strip()) < 10:
            return FallbackDecision(use_fallback=True, reason="LOCAL_EMPTY_OR_INCOMPLETE")

        # If local confidence is below threshold
        if local_result.confidence < self.confidence_threshold:
            return FallbackDecision(use_fallback=True, reason="LOW_LOCAL_CONFIDENCE")

        # If local model produced answer with 0 evidence IDs attached
        if not local_result.evidence_ids and evidence_package.items:
            return FallbackDecision(use_fallback=True, reason="NO_EVIDENCE_IDS_ATTACHED")

        return FallbackDecision(use_fallback=False, reason="LOCAL_ACCEPTED")
