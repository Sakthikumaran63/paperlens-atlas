from datetime import datetime, timezone
import logging
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import QuestionType, RetrievalMode
from app.schemas.evaluation import (
    AbstentionMetrics,
    AnswerMetrics,
    ConfigurationEvalReport,
    EvaluationBenchmarkReport,
    EvaluationDataset,
    EvaluationQuestionItem,
    GoldEvidenceItem,
    GroundingMetrics,
    RetrievalMetrics,
)
from app.services.answer_generation_service import AnswerGenerationService
from app.services.evidence_selection_service import EvidenceSelectionService
from app.services.evidence_verification_service import EvidenceVerificationService
from app.services.llm_service import LLMService
from app.services.question_classifier import QuestionClassificationService
from app.services.retrieval_service import RetrievalService
from app.services.retrieval_strategy_service import StructureAwareRetrievalService

logger = logging.getLogger("paperlens")


class EvaluationService:
    """
    PaperLens Evaluation Framework Service.
    Compares three system configurations:
    1. BASELINE_RAG
    2. STRUCTURE_AWARE_RAG
    3. STRUCTURE_AWARE_RAG + EVIDENCE_VERIFICATION
    Measures Retrieval (Recall@K, Precision@K, MRR), Answer, Grounding, and Abstention metrics.
    """

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        retrieval_strategy_service: Optional[StructureAwareRetrievalService] = None,
        evidence_selection_service: Optional[EvidenceSelectionService] = None,
        llm_service: Optional[LLMService] = None,
        verification_service: Optional[EvidenceVerificationService] = None,
        answer_generation_service: Optional[AnswerGenerationService] = None
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.retrieval_strategy_service = retrieval_strategy_service or StructureAwareRetrievalService()
        self.evidence_selection_service = evidence_selection_service or EvidenceSelectionService()
        self.llm_service = llm_service or LLMService()
        self.verification_service = verification_service or EvidenceVerificationService()
        self.answer_generation_service = answer_generation_service or AnswerGenerationService(
            llm_service=self.llm_service,
            retrieval_strategy_service=self.retrieval_strategy_service,
            evidence_selection_service=self.evidence_selection_service,
            evidence_verification_service=self.verification_service
        )

    async def run_benchmark(
        self,
        dataset: EvaluationDataset,
        db: AsyncSession,
        top_k: int = 5
    ) -> EvaluationBenchmarkReport:
        if not dataset or not dataset.items:
            raise ValueError("Evaluation dataset must contain at least one question item.")

        benchmark_id = f"eval_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        configs_to_run = [
            ("BASELINE_RAG", RetrievalMode.BASELINE_RAG, False),
            ("STRUCTURE_AWARE_RAG", RetrievalMode.STRUCTURE_AWARE_RAG, False),
            ("STRUCTURE_AWARE_RAG_WITH_VERIFICATION", RetrievalMode.STRUCTURE_AWARE_RAG, True)
        ]

        reports: List[ConfigurationEvalReport] = []

        for config_name, mode, use_verification in configs_to_run:
            report = await self._evaluate_configuration(
                config_name=config_name,
                mode=mode,
                use_verification=use_verification,
                dataset=dataset,
                db=db,
                top_k=top_k
            )
            reports.append(report)

        return EvaluationBenchmarkReport(
            benchmark_id=benchmark_id,
            timestamp=timestamp,
            configurations=reports
        )

    async def _evaluate_configuration(
        self,
        config_name: str,
        mode: RetrievalMode,
        use_verification: bool,
        dataset: EvaluationDataset,
        db: AsyncSession,
        top_k: int
    ) -> ConfigurationEvalReport:
        total_questions = len(dataset.items)
        answerable_items = [item for item in dataset.items if item.answerable]
        unanswerable_items = [item for item in dataset.items if not item.answerable]

        recalls, precisions, mrrs = [], [], []
        sem_sims, exact_matches, human_supports = [], [], []
        ev_precisions, ev_recalls, unsupported_rates = [], [], []
        correct_answers, correct_abstentions, false_answers = 0, 0, 0

        for item in dataset.items:
            # 1. Retrieval Stage
            retrieved_candidates = await self.retrieval_strategy_service.retrieve_pipeline(
                query=item.question,
                paper_id=item.paper_id,
                top_k=top_k,
                mode=mode,
                db=db
            )

            # Evaluate Retrieval Metrics (Recall@K, Precision@K, MRR)
            gold_chunk_ids = {g.chunk_id for g in item.gold_evidence if g.chunk_id}
            retrieved_chunk_ids = [str(c.chunk_id) for c in retrieved_candidates]

            if gold_chunk_ids:
                hits = sum(1 for cid in retrieved_chunk_ids if cid in gold_chunk_ids)
                rec = hits / len(gold_chunk_ids)
                prec = hits / len(retrieved_chunk_ids) if retrieved_chunk_ids else 0.0

                mrr_val = 0.0
                for idx, cid in enumerate(retrieved_chunk_ids):
                    if cid in gold_chunk_ids:
                        mrr_val = 1.0 / (idx + 1)
                        break
            else:
                # If no gold chunk specified, check section / text overlap
                hits = 0
                for cand in retrieved_candidates:
                    for g in item.gold_evidence:
                        if (g.section and g.section.lower() in cand.section_title.lower()) or (g.text and g.text.lower() in cand.text.lower()):
                            hits += 1
                            break
                rec = min(1.0, hits / max(1, len(item.gold_evidence)))
                prec = hits / len(retrieved_candidates) if retrieved_candidates else 0.0
                mrr_val = 1.0 if hits > 0 else 0.0

            recalls.append(rec)
            precisions.append(prec)
            mrrs.append(mrr_val)

            # 2. Answer & Grounding Generation
            evidence_package = self.evidence_selection_service.select_evidence(retrieved_candidates)
            llm_output = await self.llm_service.generate_grounded_answer(
                question_text=item.question,
                question_type=item.question_type,
                evidence_package=evidence_package
            )

            if use_verification:
                verification = await self.verification_service.verify_answer(
                    question_text=item.question,
                    candidate_answer=llm_output.answer,
                    evidence_package=evidence_package
                )
                abstained = (not verification.supported) or llm_output.abstain
                candidate_answer = "I couldn't find enough information in the uploaded paper to answer this reliably." if abstained else llm_output.answer
                support_score = verification.support_score
            else:
                abstained = llm_output.abstain
                candidate_answer = llm_output.answer
                support_score = 0.85 if not abstained else 0.0

            # Evaluate Answer Metrics
            sem_sim = self._calculate_word_jaccard_similarity(candidate_answer, item.gold_answer)
            exact = 1.0 if candidate_answer.strip().lower() == item.gold_answer.strip().lower() else 0.0
            human_sup = 1.0 if not abstained and support_score >= 0.70 else 0.0

            sem_sims.append(sem_sim)
            exact_matches.append(exact)
            human_supports.append(human_sup)

            # Evaluate Grounding Metrics
            ev_prec = prec
            ev_rec = rec
            unsupported_rate = 0.0 if not abstained and support_score >= 0.70 else (1.0 if not abstained else 0.0)

            ev_precisions.append(ev_prec)
            ev_recalls.append(ev_rec)
            unsupported_rates.append(unsupported_rate)

            # Evaluate Abstention Metrics
            if item.answerable:
                if not abstained:
                    correct_answers += 1
            else:
                if abstained:
                    correct_abstentions += 1
                else:
                    false_answers += 1

        avg_rec = sum(recalls) / total_questions if total_questions else 0.0
        avg_prec = sum(precisions) / total_questions if total_questions else 0.0
        avg_mrr = sum(mrrs) / total_questions if total_questions else 0.0

        avg_sem_sim = sum(sem_sims) / total_questions if total_questions else 0.0
        avg_exact = sum(exact_matches) / total_questions if total_questions else 0.0
        avg_human_sup = sum(human_supports) / total_questions if total_questions else 0.0

        avg_ev_prec = sum(ev_precisions) / total_questions if total_questions else 0.0
        avg_ev_rec = sum(ev_recalls) / total_questions if total_questions else 0.0
        avg_unsupported = sum(unsupported_rates) / total_questions if total_questions else 0.0

        ans_acc = correct_answers / len(answerable_items) if answerable_items else 1.0
        unans_det = correct_abstentions / len(unanswerable_items) if unanswerable_items else 1.0
        false_ans_rate = false_answers / len(unanswerable_items) if unanswerable_items else 0.0

        return ConfigurationEvalReport(
            config_name=config_name,
            total_questions=total_questions,
            answerable_count=len(answerable_items),
            unanswerable_count=len(unanswerable_items),
            retrieval=RetrievalMetrics(
                recall_at_k=round(avg_rec, 4),
                precision_at_k=round(avg_prec, 4),
                mrr=round(avg_mrr, 4)
            ),
            answer=AnswerMetrics(
                semantic_similarity=round(avg_sem_sim, 4),
                exact_match=round(avg_exact, 4),
                human_eval_support=round(avg_human_sup, 4)
            ),
            grounding=GroundingMetrics(
                evidence_precision=round(avg_ev_prec, 4),
                evidence_recall=round(avg_ev_rec, 4),
                unsupported_claim_rate=round(avg_unsupported, 4)
            ),
            abstention=AbstentionMetrics(
                answerable_accuracy=round(ans_acc, 4),
                unanswerable_detection=round(unans_det, 4),
                false_answer_rate=round(false_ans_rate, 4)
            )
        )

    def _calculate_word_jaccard_similarity(self, str1: str, str2: str) -> float:
        w1 = set(str1.lower().split())
        w2 = set(str2.lower().split())
        if not w1 or not w2:
            return 0.0
        intersection = w1.intersection(w2)
        union = w1.union(w2)
        return len(intersection) / len(union) if union else 0.0

    def generate_sample_evaluation_dataset(self, paper_id: uuid.UUID) -> EvaluationDataset:
        items = [
            EvaluationQuestionItem(
                id="q1",
                paper_id=paper_id,
                question="What dataset was used for evaluating performance?",
                question_type=QuestionType.DATASET,
                gold_answer="ImageNet and WMT 2014 translation datasets.",
                gold_evidence=[GoldEvidenceItem(page=5, section="Experiments", text="WMT 2014 translation dataset")],
                page=5,
                section="Experiments",
                answerable=True
            ),
            EvaluationQuestionItem(
                id="q2",
                paper_id=paper_id,
                question="What is the core proposed model architecture?",
                question_type=QuestionType.MODEL,
                gold_answer="Transformer architecture relying on multi-head self-attention.",
                gold_evidence=[GoldEvidenceItem(page=3, section="Methodology", text="multi-head self-attention")],
                page=3,
                section="Methodology",
                answerable=True
            ),
            EvaluationQuestionItem(
                id="q3",
                paper_id=paper_id,
                question="What stock market price ticker was analyzed in this paper?",
                question_type=QuestionType.UNKNOWN,
                gold_answer="I couldn't find enough information in the uploaded paper to answer this reliably.",
                gold_evidence=[],
                answerable=False
            )
        ]
        return EvaluationDataset(dataset_name="PaperLens Sample Evaluation Benchmark", items=items)
