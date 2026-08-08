import re
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import RetrievalMode, SectionType
from app.schemas.retrieval import RetrievedChunkCandidate
from app.services.question_classifier import QuestionClassificationService
from app.services.retrieval_service import RetrievalService


class StructureAwareRetrievalService:
    """
    PaperLens Structure-Aware Retrieval Pipeline.
    Orchestrates Question Classification -> Retrieval Routing -> Semantic Vector Search -> Section-Aware & Keyword Scoring -> Final Ranking.
    Supports BASELINE_RAG (semantic only) and STRUCTURE_AWARE_RAG (combined weighted scoring).
    """

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        question_classifier: Optional[QuestionClassificationService] = None
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.question_classifier = question_classifier or QuestionClassificationService()

    def calculate_keyword_score(self, query: str, text: str) -> float:
        if not query or not text:
            return 0.0
        # Normalize and extract non-stopword query tokens (min length 3)
        query_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower()))
        text_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', text.lower()))

        if not query_words:
            return 0.0

        matches = query_words.intersection(text_words)
        overlap_ratio = len(matches) / len(query_words)
        return min(1.0, max(0.0, overlap_ratio))

    def calculate_section_score(self, chunk_sec_type: SectionType, priorities: List[SectionType]) -> float:
        if not priorities:
            return 0.50

        for rank_idx, priority_sec in enumerate(priorities):
            if chunk_sec_type == priority_sec:
                if rank_idx == 0:
                    return 1.0
                elif rank_idx == 1:
                    return 0.75
                elif rank_idx == 2:
                    return 0.50
                else:
                    return 0.30

        return 0.10

    async def retrieve_pipeline(
        self,
        query: str,
        paper_id: uuid.UUID,
        top_k: int = 5,
        mode: RetrievalMode = RetrievalMode.STRUCTURE_AWARE_RAG,
        section_type: Optional[SectionType] = None,
        workspace_id: Optional[uuid.UUID] = None,
        db: AsyncSession = None
    ) -> List[RetrievedChunkCandidate]:
        if not query or not query.strip() or db is None:
            return []

        # 1. Question Classification & Retrieval Routing
        classification = self.question_classifier.classify_question(query)
        priorities = classification.retrieval_priorities

        # 2. Semantic Candidate Retrieval
        fetch_k = top_k * 4 if mode == RetrievalMode.STRUCTURE_AWARE_RAG else top_k
        if section_type:
            raw_candidates = await self.retrieval_service.retrieve_by_section(
                query=query,
                paper_id=paper_id,
                section_type=section_type,
                top_k=fetch_k,
                workspace_id=workspace_id,
                db=db
            )
        else:
            raw_candidates = await self.retrieval_service.retrieve(
                query=query,
                paper_id=paper_id,
                top_k=fetch_k,
                workspace_id=workspace_id,
                db=db
            )

        processed_candidates: List[RetrievedChunkCandidate] = []

        # 3. Section-Aware & Keyword Scoring
        sem_weight = settings.RETRIEVAL_SEMANTIC_WEIGHT
        sec_weight = settings.RETRIEVAL_SECTION_WEIGHT
        kw_weight = settings.RETRIEVAL_KEYWORD_WEIGHT

        for cand in raw_candidates:
            sem_score = cand.similarity_score
            sec_score = self.calculate_section_score(cand.section_type, priorities)
            kw_score = self.calculate_keyword_score(query, cand.text)

            if mode == RetrievalMode.BASELINE_RAG:
                fin_score = sem_score
            else:
                fin_score = (sem_score * sem_weight) + (sec_score * sec_weight) + (kw_score * kw_weight)

            processed_cand = RetrievedChunkCandidate(
                chunk_id=cand.chunk_id,
                paper_id=cand.paper_id,
                page_number=cand.page_number,
                page=cand.page_number,
                section_id=cand.section_id,
                section_type=cand.section_type,
                section_title=cand.section_title,
                section=cand.section_title,
                text=cand.text,
                semantic_score=round(float(sem_score), 4),
                section_score=round(float(sec_score), 4),
                keyword_score=round(float(kw_score), 4),
                final_score=round(float(fin_score), 4),
                similarity_score=round(float(sem_score), 4)
            )
            processed_candidates.append(processed_cand)

        # 4. Final Ranking
        processed_candidates.sort(key=lambda c: c.final_score, reverse=True)
        return processed_candidates[:top_k]
