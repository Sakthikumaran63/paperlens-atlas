"""
Support Score Evaluation Module
-------------------------------
Computes answer support scores (0.0 to 1.0) and enforces the controlled
abstention guard (threshold >= 0.70).
"""
from typing import Tuple
from app.core.config import settings
from app.schemas.evidence import EvidencePackage
from app.services.evidence_verification_service import EvidenceVerificationService


class SupportEvaluator:
    """Evaluates factual support of generated answers against retrieved evidence."""

    def __init__(self, service: EvidenceVerificationService = None, threshold: float = 0.70):
        self.service = service or EvidenceVerificationService()
        self.threshold = getattr(settings, "SUPPORT_SCORE_THRESHOLD", threshold)

    def evaluate_support(
        self,
        answer_text: str,
        evidence_package: EvidencePackage,
    ) -> Tuple[float, bool]:
        """
        Returns (support_score, is_supported).
        """
        score = self.service.calculate_support_score(answer_text, evidence_package)
        is_supported = score >= self.threshold
        return score, is_supported
