import logging
import math
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.schemas.retrieval import RetrievedChunkCandidate
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("paperlens")


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class RetrievalService:
    """
    PaperLens Semantic Vector Retrieval Engine.
    Executes similarity searches using pgvector vector representations.
    Strictly enforces paper and workspace isolation.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or EmbeddingService()

    def _format_candidate(
        self,
        chunk: PaperChunk,
        section: Optional[PaperSection],
        sim_score: float
    ) -> RetrievedChunkCandidate:
        sec_type = SectionType.OTHER
        sec_title = "Document Text"
        sec_id = None

        if section:
            sec_type = section.section_type
            sec_title = section.title
            sec_id = section.id
        elif chunk.metadata_json and isinstance(chunk.metadata_json, dict):
            sec_type_val = chunk.metadata_json.get("section_type")
            if sec_type_val:
                try:
                    sec_type = SectionType(sec_type_val)
                except ValueError:
                    sec_type = SectionType.OTHER
            sec_title = chunk.metadata_json.get("section_title", "Document Text")
            sec_id = chunk.section_id

        return RetrievedChunkCandidate(
            chunk_id=chunk.id,
            paper_id=chunk.paper_id,
            page_number=chunk.page_number,
            section_id=sec_id or chunk.section_id,
            section_type=sec_type,
            section_title=sec_title,
            text=chunk.text,
            similarity_score=round(float(sim_score), 4)
        )

    async def retrieve(
        self,
        query: str,
        paper_id: uuid.UUID,
        top_k: int = 5,
        workspace_id: Optional[uuid.UUID] = None,
        db: AsyncSession = None
    ) -> List[RetrievedChunkCandidate]:
        """
        Retrieve top_k semantic evidence candidates for a query within a specific paper.
        Enforces strict paper and workspace isolation.
        """
        if not query or not query.strip() or top_k <= 0 or db is None:
            return []

        # 1. Generate query embedding vector
        query_vectors = await self.embedding_service.generate_embeddings([query])
        if not query_vectors:
            return []
        query_vector = query_vectors[0]

        # 2. Build isolated database query
        stmt = (
            select(PaperChunk, PaperSection)
            .outerjoin(PaperSection, PaperChunk.section_id == PaperSection.id)
            .join(Paper, PaperChunk.paper_id == Paper.id)
            .where(PaperChunk.paper_id == paper_id)
        )

        if workspace_id:
            stmt = stmt.where(Paper.workspace_id == workspace_id)

        # Execute query and compute similarity scores
        try:
            # Query using pgvector cosine distance if supported
            cos_dist = PaperChunk.embedding.cosine_distance(query_vector)
            sim_expr = (1 - cos_dist).label("similarity_score")
            pgvector_stmt = (
                select(PaperChunk, PaperSection, sim_expr)
                .outerjoin(PaperSection, PaperChunk.section_id == PaperSection.id)
                .join(Paper, PaperChunk.paper_id == Paper.id)
                .where(PaperChunk.paper_id == paper_id)
            )
            if workspace_id:
                pgvector_stmt = pgvector_stmt.where(Paper.workspace_id == workspace_id)

            pgvector_stmt = pgvector_stmt.order_by(cos_dist).limit(top_k)
            result = await db.execute(pgvector_stmt)
            rows = result.all()

            candidates = []
            for chunk, section, score in rows:
                candidates.append(self._format_candidate(chunk, section, score or 0.0))
            return candidates

        except Exception as e:
            # Fallback for mock in-memory database test environments where pgvector C extension is not compiled
            logger.debug(f"pgvector query fallback to Python cosine similarity: {e}")
            result = await db.execute(stmt)
            rows = result.all()

            scored_candidates = []
            for chunk, section in rows:
                if chunk.embedding:
                    score = cosine_similarity(query_vector, chunk.embedding)
                    candidate = self._format_candidate(chunk, section, score)
                    scored_candidates.append(candidate)

            # Sort descending by similarity score
            scored_candidates.sort(key=lambda c: c.similarity_score, reverse=True)
            return scored_candidates[:top_k]

    async def retrieve_by_section(
        self,
        query: str,
        paper_id: uuid.UUID,
        section_type: SectionType,
        top_k: int = 5,
        workspace_id: Optional[uuid.UUID] = None,
        db: AsyncSession = None
    ) -> List[RetrievedChunkCandidate]:
        """
        Retrieve evidence candidates restricted to a specific scientific section type (e.g. METHODOLOGY, RESULTS).
        """
        # Retrieve candidates
        all_candidates = await self.retrieve(
            query=query,
            paper_id=paper_id,
            top_k=top_k * 3,  # Fetch wider set before section filtering
            workspace_id=workspace_id,
            db=db
        )

        # Filter strictly by section_type
        section_candidates = [
            c for c in all_candidates if c.section_type == section_type
        ]

        return section_candidates[:top_k]
