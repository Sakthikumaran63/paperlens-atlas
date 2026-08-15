"""
Citation Quote Verification Module
----------------------------------
Verifies cited quotes against source chunk content using exact substring matching
and RapidFuzz partial ratio matching (threshold >= 90).
"""
from typing import Tuple
from app.services.evidence_verification_service import EvidenceVerificationService


class CitationVerifier:
    """Verifies that generated citation quotes exist in underlying chunk text."""

    def __init__(self, service: EvidenceVerificationService = None, threshold: float = 90.0):
        self.service = service or EvidenceVerificationService()
        self.threshold = threshold

    def verify_quote(self, quote: str, chunk_content: str) -> bool:
        return self.service.verify_quote(quote, chunk_content)

    def verify_citation(
        self,
        quote: str,
        chunk_content: str,
    ) -> Tuple[bool, str, float]:
        if not quote or not chunk_content:
            return False, "EMPTY", 0.0

        if quote.strip() in chunk_content:
            return True, "EXACT", 1.0

        try:
            from rapidfuzz import fuzz
            ratio = fuzz.partial_ratio(quote.strip().lower(), chunk_content.lower())
            if ratio >= self.threshold:
                return True, "RAPIDFUZZ_PARTIAL", ratio / 100.0
            return False, "RAPIDFUZZ_LOW_MATCH", ratio / 100.0
        except Exception:
            return False, "VERIFICATION_ERROR", 0.0
