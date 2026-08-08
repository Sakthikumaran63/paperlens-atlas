import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

# Add Backend root directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.paper import Paper
from app.services.evaluation_service import EvaluationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paperlens")


async def main():
    async with async_session_factory() as db:
        # Select first available READY paper
        stmt = select(Paper).limit(1)
        res = await db.execute(stmt)
        paper = res.scalar_one_or_none()

        if not paper:
            logger.error("No papers found in database to evaluate. Please upload and index a paper first.")
            return

        logger.info(f"Starting evaluation benchmark for paper ID: {paper.id} (Title: {paper.title})")

        eval_svc = EvaluationService()
        dataset = eval_svc.generate_sample_evaluation_dataset(paper.id)

        report = await eval_svc.run_benchmark(dataset=dataset, db=db, top_k=5)

        out_path = backend_dir / "evaluation_results.json"
        report_json = report.model_dump(mode="json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2)

        logger.info(f"Evaluation benchmark report successfully saved to {out_path}")
        print("\n" + "="*80)
        print(f"  PAPERLENS EVALUATION BENCHMARK REPORT ({report.benchmark_id})")
        print("="*80)
        for cfg in report.configurations:
            print(f"\n--- Configuration: {cfg.config_name} ---")
            print(f"  Questions Evaluated : Total {cfg.total_questions} (Answerable: {cfg.answerable_count}, Unanswerable: {cfg.unanswerable_count})")
            print(f"  Retrieval Metrics   : Recall@K={cfg.retrieval.recall_at_k:.4f} | Precision@K={cfg.retrieval.precision_at_k:.4f} | MRR={cfg.retrieval.mrr:.4f}")
            print(f"  Answer Quality      : SemSim={cfg.answer.semantic_similarity:.4f} | ExactMatch={cfg.answer.exact_match:.4f} | Support={cfg.answer.human_eval_support:.4f}")
            print(f"  Grounding Metrics   : EvPrec={cfg.grounding.evidence_precision:.4f} | EvRec={cfg.grounding.evidence_recall:.4f} | UnsupportedRate={cfg.grounding.unsupported_claim_rate:.4f}")
            print(f"  Abstention Metrics  : AnsAcc={cfg.abstention.answerable_accuracy:.4f} | UnansDetect={cfg.abstention.unanswerable_detection:.4f} | FalseAnsRate={cfg.abstention.false_answer_rate:.4f}")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
