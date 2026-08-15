"""
Reranker Interface & Implementations
------------------------------------
Defines the Reranker Protocol and pass-through/scoring rerankers.
"""
from typing import List, Protocol
from app.schemas.retrieval import RetrievedChunkCandidate


class Reranker(Protocol):
    """Protocol for candidate chunk reranking models."""

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunkCandidate],
    ) -> List[RetrievedChunkCandidate]:
        ...


class IdentityReranker:
    """Pass-through reranker maintaining hybrid score order."""

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunkCandidate],
    ) -> List[RetrievedChunkCandidate]:
        candidates.sort(key=lambda c: c.final_score, reverse=True)
        return candidates
