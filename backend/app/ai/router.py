"""
PaperLens AI Unified Router
----------------------------
Coordinates local AI generation and manages seamless Gemini fallback according
to the central FallbackPolicy.
"""
import logging
from typing import Optional
from app.ai.base import AIProvider, GenerationResult
from app.ai.fallback_policy import FallbackPolicy
from app.ai.gemini_provider import GeminiProvider
from app.ai.local_provider import LocalModelProvider
from app.core.config import settings
from app.models.enums import QuestionType
from app.schemas.evidence import EvidencePackage

logger = logging.getLogger("paperlens")


class AIRouter:
    """
    Unified AI router implementing:
    Question -> Evidence -> Local Model -> Policy Check -> (Gemini Fallback if needed) -> Grounded Result
    """

    def __init__(
        self,
        local_provider: Optional[AIProvider] = None,
        fallback_provider: Optional[AIProvider] = None,
        fallback_policy: Optional[FallbackPolicy] = None,
    ):
        self.local_provider = local_provider or LocalModelProvider()
        self.fallback_provider = fallback_provider or GeminiProvider()
        self.fallback_policy = fallback_policy or FallbackPolicy(
            confidence_threshold=getattr(settings, "LOCAL_CONFIDENCE_THRESHOLD", 0.50),
            gemini_fallback_enabled=bool(getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "LLM_API_KEY", None)),
        )

    async def generate_grounded_answer(
        self,
        question_text: str,
        question_type: QuestionType,
        evidence_package: EvidencePackage,
    ) -> GenerationResult:
        """
        Executes local generation first.
        If policy demands fallback, runs Gemini with verified evidence constraints.
        """
        # Step 1: Execute primary local AI generation
        local_result = await self.local_provider.generate_answer(
            question_text=question_text,
            question_type=question_type,
            evidence_package=evidence_package,
        )

        # Step 2: Evaluate through central fallback policy
        decision = self.fallback_policy.evaluate(local_result, evidence_package)

        if not decision.use_fallback:
            logger.info("Local AI answer accepted (%s).", decision.reason)
            return local_result

        # Step 3: Execute Gemini fallback
        logger.info("Engaging Gemini fallback. Reason: %s", decision.reason)
        fallback_result = await self.fallback_provider.generate_answer(
            question_text=question_text,
            question_type=question_type,
            evidence_package=evidence_package,
        )
        fallback_result.fallback_used = True
        fallback_result.fallback_reason = decision.reason

        return fallback_result
