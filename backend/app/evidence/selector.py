"""
Evidence Selection & Budget Module
----------------------------------
Deduplicates candidate chunks and constructs a context package within token budget.
"""
from typing import List
from app.schemas.evidence import EvidenceItem, EvidencePackage
from app.schemas.retrieval import RetrievedChunkCandidate
from app.services.evidence_selection_service import EvidenceSelectionService


class EvidenceSelector:
    """Selects and deduplicates evidence chunks within token limits."""

    def __init__(self, service: EvidenceSelectionService = None):
        self.service = service or EvidenceSelectionService()

    def select_evidence(
        self,
        candidates: List[RetrievedChunkCandidate],
        max_tokens: int = 2000,
        max_chunks: int = 5,
    ) -> EvidencePackage:
        return self.service.select_evidence(
            candidates=candidates,
            max_tokens=max_tokens,
            max_chunks=max_chunks,
        )
