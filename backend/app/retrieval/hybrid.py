"""
Hybrid Retrieval Orchestrator
-----------------------------
Coordinates dense vector search, BM25 scoring, section taxonomy routing,
and reranking.
"""
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RetrievalMode
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.reranker import IdentityReranker, Reranker
from app.retrieval.scoring import HybridScorer
from app.retrieval.section import SectionRouter
from app.retrieval.semantic import DenseRetriever
from app.schemas.retrieval import RetrievedChunkCandidate
from app.services.question_classifier import QuestionClassificationService


class HybridRetriever:
    """Orchestrates hybrid retrieval combining semantic vectors, BM25, and section routing."""

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        section_router: Optional[SectionRouter] = None,
        scorer: Optional[HybridScorer] = None,
        reranker: Optional[Reranker] = None,
        question_classifier: Optional[QuestionClassificationService] = None,
    ):
        self.dense = dense_retriever or DenseRetriever()
        self.bm25 = bm25_retriever or BM25Retriever()
        self.section_router = section_router or SectionRouter()
        self.scorer = scorer or HybridScorer()
        self.reranker = reranker or IdentityReranker()
        self.classifier = question_classifier or QuestionClassificationService()

    async def retrieve(
        self,
        query: str,
        paper_id: Optional[uuid.UUID] = None,
        top_k: int = 5,
        mode: RetrievalMode = RetrievalMode.STRUCTURE_AWARE_RAG,
        workspace_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[RetrievedChunkCandidate]:
        classification = self.classifier.classify_question(query)
        priorities = self.classifier.get_priority_sections(classification.question_type)

        fetch_k = top_k * 3 if mode == RetrievalMode.STRUCTURE_AWARE_RAG else top_k
        raw_candidates = await self.dense.retrieve(
            query=query,
            paper_id=paper_id,
            top_k=fetch_k,
            workspace_id=workspace_id,
            db=db,
        )

        if not raw_candidates:
            return []

        candidate_texts = [c.text for c in raw_candidates]
        bm25_scores = self.bm25.score_candidates(query, candidate_texts)

        processed: List[RetrievedChunkCandidate] = []
        for cand, kw_score in zip(raw_candidates, bm25_scores):
            sem_score = cand.similarity_score
            sec_score = self.section_router.calculate_section_score(cand.section_type, priorities)

            if mode == RetrievalMode.BASELINE_RAG:
                fin_score = sem_score
            else:
                fin_score = self.scorer.calculate_final_score(sem_score, sec_score, kw_score)

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
                similarity_score=round(float(sem_score), 4),
            )
            processed.append(processed_cand)

        reranked = await self.reranker.rerank(query, processed)
        return reranked[:top_k]
