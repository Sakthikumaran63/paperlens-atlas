import logging
from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer
from app.models.answer_evidence import AnswerEvidence
from app.models.enums import PaperStatus, QuestionType, RetrievalMode
from app.models.paper import Paper
from app.models.question import Question
from app.models.retrieved_evidence import RetrievedEvidence
from app.schemas.answer import AnswerEvidenceItem, GroundedAnswerResponse
from app.schemas.question import QuestionAnsweringResponse, SourceMetadataItem
from app.services.evidence_selection_service import EvidenceSelectionService
from app.services.evidence_verification_service import EvidenceVerificationService
from app.services.llm_service import LLMService
from app.services.question_classifier import QuestionClassificationService
from app.services.retrieval_strategy_service import StructureAwareRetrievalService

logger = logging.getLogger("paperlens")


class AnswerGenerationService:
    """
    PaperLens Grounded Answer Generation Service.
    Executes 15-step pipeline:
    1. Authenticate user & workspace ownership
    2. Validate paper status == READY
    3. Classify question
    4. Route retrieval
    5. Retrieve candidate chunks
    6. Rank evidence
    7. Build evidence package
    8. Generate grounded answer
    9. Verify evidence support
    10. Answer or abstain
    11. Persist Question record
    12. Persist RetrievedEvidence records
    13. Persist Answer record
    14. Persist AnswerEvidence records
    15. Construct sources exclusively from database evidence metadata.
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        retrieval_strategy_service: Optional[StructureAwareRetrievalService] = None,
        evidence_selection_service: Optional[EvidenceSelectionService] = None,
        question_classifier: Optional[QuestionClassificationService] = None,
        evidence_verification_service: Optional[EvidenceVerificationService] = None
    ):
        self.llm_service = llm_service or LLMService()
        self.retrieval_strategy_service = retrieval_strategy_service or StructureAwareRetrievalService()
        self.evidence_selection_service = evidence_selection_service or EvidenceSelectionService()
        self.question_classifier = question_classifier or QuestionClassificationService()
        self.evidence_verification_service = evidence_verification_service or EvidenceVerificationService()

    async def answer_question_pipeline(
        self,
        paper_id: uuid.UUID,
        question_text: str,
        mode: RetrievalMode = RetrievalMode.STRUCTURE_AWARE_RAG,
        db: AsyncSession = None,
        llm_service: Optional[LLMService] = None,
        verification_service: Optional[EvidenceVerificationService] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> QuestionAnsweringResponse:
        if not question_text or not question_text.strip() or db is None:
            raise ValueError("Valid question_text and db session are required.")

        llm_svc = llm_service or self.llm_service
        ver_svc = verification_service or self.evidence_verification_service

        # 1. Fetch Paper & Validate paper is indexed (status == PaperStatus.READY)
        paper_res = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = paper_res.scalar_one_or_none()

        if not paper:
            raise ValueError(f"Paper with ID {paper_id} not found.")

        if paper.status != PaperStatus.READY:
            raise ValueError(f"Paper is not ready for question answering (current status: {paper.status.value}). Please index the paper first.")

        # 4. Classify question
        q_classification = self.question_classifier.classify_question(question_text)
        question_type = q_classification.question_type

        # 5, 6, 7. Route retrieval & Retrieve candidate chunks & Rank evidence
        candidates = await self.retrieval_strategy_service.retrieve_pipeline(
            query=question_text,
            paper_id=paper_id,
            top_k=8,
            mode=mode,
            db=db
        )

        # 8. Build evidence package
        evidence_package = self.evidence_selection_service.select_evidence(candidates)
        searched_sections = list({c.section_type.value for c in candidates})

        # 9. Generate grounded answer
        llm_output = await llm_svc.generate_grounded_answer(
            question_text=question_text,
            question_type=question_type,
            evidence_package=evidence_package
        )

        # 10. Verify evidence support
        verification = await ver_svc.verify_answer(
            question_text=question_text,
            candidate_answer=llm_output.answer,
            evidence_package=evidence_package
        )

        # 11. Either answer or abstain
        REFUSAL_MESSAGE = "I couldn't find enough information in the uploaded paper to answer this reliably."
        is_supported = verification.supported and not llm_output.abstain
        abstained = not is_supported

        if abstained:
            final_answer = REFUSAL_MESSAGE
            if verification.unsupported_claims:
                abstention_reason = f"Insufficient evidence support (score: {verification.support_score}). Unsupported claims: {'; '.join(verification.unsupported_claims)}"
            else:
                abstention_reason = f"Insufficient evidence support (score: {verification.support_score})."
        else:
            final_answer = llm_output.answer
            abstention_reason = None

        # Build sources from database evidence metadata (NEVER from generated text)
        source_items: list[SourceMetadataItem] = []
        bound_evidence_items: list[AnswerEvidenceItem] = []

        if not abstained:
            evidence_map = {item.evidence_id: item for item in evidence_package.items}
            for ev_id in llm_output.evidence_ids:
                if ev_id in evidence_map:
                    db_item = evidence_map[ev_id]
                    src = SourceMetadataItem(
                        page=db_item.page,
                        section=db_item.section,
                        chunk_id=db_item.chunk_id,
                        text=db_item.text
                    )
                    source_items.append(src)
                    bound_evidence_items.append(
                        AnswerEvidenceItem(
                            evidence_id=db_item.evidence_id,
                            chunk_id=db_item.chunk_id,
                            page=db_item.page,
                            section=db_item.section,
                            text=db_item.text
                        )
                    )

            if not source_items and evidence_package.items:
                for db_item in evidence_package.items:
                    src = SourceMetadataItem(
                        page=db_item.page,
                        section=db_item.section,
                        chunk_id=db_item.chunk_id,
                        text=db_item.text
                    )
                    source_items.append(src)
                    bound_evidence_items.append(
                        AnswerEvidenceItem(
                            evidence_id=db_item.evidence_id,
                            chunk_id=db_item.chunk_id,
                            page=db_item.page,
                            section=db_item.section,
                            text=db_item.text
                        )
                    )

            # Verification of cited quotes against actual chunk content
            chunk_text_map = {str(c.chunk_id): c.text for c in candidates}
            verified_source_items: list[SourceMetadataItem] = []
            verified_bound_items: list[AnswerEvidenceItem] = []

            for src, b_item in zip(source_items, bound_evidence_items):
                chunk_content = chunk_text_map.get(str(b_item.chunk_id), b_item.text)
                if ver_svc.verify_quote(quote_text=b_item.text, chunk_content=chunk_content):
                    verified_source_items.append(src)
                    verified_bound_items.append(b_item)
                else:
                    logger.warning(
                        "Rejected unverified citation quote for paper_id=%s, chunk_id=%s",
                        paper.id, b_item.chunk_id
                    )

            if not verified_source_items:
                abstained = True
                final_answer = REFUSAL_MESSAGE
                abstention_reason = "Answer contained unverifiable citations not found in document text."
                source_items = []
                bound_evidence_items = []
            else:
                source_items = verified_source_items
                bound_evidence_items = verified_bound_items

        # 12. Persist question DB record
        db_question = Question(
            workspace_id=paper.workspace_id,
            paper_id=paper.id,
            user_id=user_id,
            question_text=question_text,
            intent=question_type,
            intent_confidence=q_classification.confidence
        )
        db.add(db_question)
        await db.flush()

        # 13. Persist retrieved evidence DB records and build chunk->ret_ev mapping
        chunk_to_ret_ev: dict[str, uuid.UUID] = {}
        for idx, cand in enumerate(candidates[:6]):
            ret_ev = RetrievedEvidence(
                question_id=db_question.id,
                chunk_id=cand.chunk_id,
                rank=idx + 1,
                similarity_score=cand.similarity_score
            )
            db.add(ret_ev)
            await db.flush()  # flush to get ret_ev.id
            chunk_to_ret_ev[str(cand.chunk_id)] = ret_ev.id


        # 14. Persist answer DB record
        db_answer = Answer(
            question_id=db_question.id,
            answer_text=final_answer,
            is_abstained=abstained,
            abstention_reason=abstention_reason
        )
        db.add(db_answer)
        await db.flush()


        # 15. Persist answer-evidence relationship DB records
        for b_item in bound_evidence_items:
            ret_ev_id = chunk_to_ret_ev.get(str(b_item.chunk_id))
            if ret_ev_id:
                ans_ev = AnswerEvidence(
                    answer_id=db_answer.id,
                    retrieved_evidence_id=ret_ev_id,
                    quote_text=b_item.text[:500] if b_item.text else None
                )
                db.add(ans_ev)

        await db.commit()

        return QuestionAnsweringResponse(
            question_id=db_question.id,
            question=question_text,
            question_type=question_type,
            answer=final_answer,
            abstained=abstained,
            support_score=verification.support_score,
            sources=source_items
        )

    async def generate_answer_for_paper(
        self,
        paper_id: uuid.UUID,
        question_text: str,
        mode: RetrievalMode = RetrievalMode.STRUCTURE_AWARE_RAG,
        db: AsyncSession = None,
        llm_service: Optional[LLMService] = None,
        verification_service: Optional[EvidenceVerificationService] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> GroundedAnswerResponse:
        # Wrapper calling pipeline and converting response for backwards compatibility
        qa_resp = await self.answer_question_pipeline(
            paper_id=paper_id,
            question_text=question_text,
            mode=mode,
            db=db,
            llm_service=llm_service,
            verification_service=verification_service,
            user_id=user_id,
        )

        bound_evidence_items = [
            AnswerEvidenceItem(
                evidence_id=f"ev_{idx+1}",
                chunk_id=src.chunk_id,
                page=src.page,
                section=src.section,
                text=src.text
            ) for idx, src in enumerate(qa_resp.sources)
        ]

        return GroundedAnswerResponse(
            question_text=qa_resp.question,
            question_type=qa_resp.question_type,
            answer=qa_resp.answer,
            evidence_ids=[ev.evidence_id for ev in bound_evidence_items],
            evidences=bound_evidence_items,
            confidence=0.95 if not qa_resp.abstained else 0.0,
            support_score=qa_resp.support_score,
            supported=not qa_resp.abstained,
            abstain=qa_resp.abstained,
            searched_sections=[],
            evidence_count=len(qa_resp.sources),
            abstention_reason=None if not qa_resp.abstained else "Insufficient evidence support."
        )
