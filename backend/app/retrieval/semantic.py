"""
Semantic Vector Retrieval Module
---------------------------------
Executes dense embedding nearest-neighbor similarity search against paper chunks.
"""
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.retrieval import RetrievedChunkCandidate
from app.services.retrieval_service import RetrievalService


class DenseRetriever:
    """Retrieves paper chunks using vector cosine similarity search."""

    def __init__(self, retrieval_service: Optional[RetrievalService] = None):
        self.service = retrieval_service or RetrievalService()

    async def retrieve(
        self,
        query: str,
        paper_id: Optional[uuid.UUID] = None,
        top_k: int = 10,
        workspace_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[RetrievedChunkCandidate]:
        return await self.service.retrieve(
            query=query,
            paper_id=paper_id,
            top_k=top_k,
            workspace_id=workspace_id,
            db=db,
        )
