import json
import logging
import re
from typing import List, Optional
import httpx

from app.core.config import settings
from app.schemas.evidence import EvidencePackage
from app.schemas.verification import VerificationResult

logger = logging.getLogger("paperlens")


class EvidenceVerificationService:
    """
    PaperLens Evidence Verification Layer.
    Evaluates whether proposed candidate answers are sufficiently supported by retrieved evidence package items.
    Enforces minimum support score thresholds and identifies unsupported claims.
    """

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self.client = http_client
        self.api_base = settings.LLM_API_BASE.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.threshold = settings.MIN_SUPPORT_SCORE_THRESHOLD

    def _fallback_keyword_overlap_support(self, candidate_answer: str, evidence_package: EvidencePackage) -> float:
        if not candidate_answer or not evidence_package.items:
            return 0.0

        ans_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', candidate_answer.lower()))
        if not ans_words:
            return 0.0

        all_evidence_text = " ".join([item.text.lower() for item in evidence_package.items])
        evidence_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', all_evidence_text))

        matches = ans_words.intersection(evidence_words)
        return min(1.0, max(0.0, len(matches) / len(ans_words)))

    async def verify_answer(
        self,
        question_text: str,
        candidate_answer: str,
        evidence_package: EvidencePackage,
        threshold: Optional[float] = None
    ) -> VerificationResult:
        thresh = threshold if threshold is not None else self.threshold

        if not candidate_answer or not evidence_package.items or evidence_package.total_items == 0:
            return VerificationResult(
                supported=False,
                support_score=0.0,
                unsupported_claims=["No evidence retrieved to support the candidate answer."]
            )

        # Check if candidate answer is an abstention response
        if "insufficient" in candidate_answer.lower() or "couldn't find" in candidate_answer.lower():
            return VerificationResult(
                supported=False,
                support_score=0.0,
                unsupported_claims=["Candidate answer explicitly indicated insufficient evidence."]
            )

        # If HTTP client is supplied or API key exists, call verification LLM / API
        if self.client is not None or self.api_key:
            try:
                url = f"{self.api_base}/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                evidence_str = "\n".join([f"[{it.evidence_id}]: {it.text}" for it in evidence_package.items])
                system_prompt = (
                    "You are a strict scientific evidence verifier.\n"
                    "Evaluate whether the proposed CANDIDATE ANSWER is factually supported by the SUPPLIED EVIDENCE.\n"
                    "Compute a support_score (0.0 to 1.0) reflecting the proportion of claims supported.\n"
                    "Identify any unsupported claims.\n"
                    "Output MUST strictly be JSON:\n"
                    '{\n  "support_score": 0.90,\n  "unsupported_claims": []\n}'
                )

                user_prompt = (
                    f"Question: {question_text}\n\n"
                    f"Candidate Answer: {candidate_answer}\n\n"
                    f"Supplied Evidence:\n{evidence_str}"
                )

                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }

                should_close = False
                client = self.client
                if client is None:
                    client = httpx.AsyncClient(timeout=30.0)
                    should_close = True

                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        data = json.loads(content)
                        score = float(data.get("support_score", 0.0))
                        claims = list(data.get("unsupported_claims", []))
                        is_supported = score >= thresh

                        if not is_supported and not claims:
                            claims = ["Candidate answer contains claims unsupported by evidence."]

                        return VerificationResult(
                            supported=is_supported,
                            support_score=round(score, 4),
                            unsupported_claims=claims
                        )
                finally:
                    if should_close and client:
                        await client.aclose()

            except Exception as e:
                logger.warning(f"LLM verification call failed ({e}). Falling back to word overlap verification.")

        # Heuristic word overlap verification fallback
        score = self._fallback_keyword_overlap_support(candidate_answer, evidence_package)
        is_supported = score >= thresh
        claims = [] if is_supported else ["Candidate answer contains unverified claims."]

        return VerificationResult(
            supported=is_supported,
            support_score=round(score, 4),
            unsupported_claims=claims
        )
