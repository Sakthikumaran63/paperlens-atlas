from datetime import datetime, timezone
import logging
from typing import Optional
import uuid
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.enums import PaperStatus, PipelineStage
from app.models.paper import Paper
from app.models.paper_page import PaperPage
from app.models.paper_section import PaperSection
from app.services.chunking_engine import ChunkingEngine
from app.services.indexing_service import index_paper
from app.services.pdf_extractor import PDFExtractor
from app.services.section_detector import SectionDetector
from app.services.summary_service import SummaryService
from app.utils.storage import get_upload_dir

logger = logging.getLogger("paperlens")


class PaperPipelineOrchestrator:
    """
    PaperLens Asynchronous Paper-Analysis Pipeline Orchestrator.
    Executes stages sequentially in background:
    EXTRACTING -> STRUCTURING -> CHUNKING -> EMBEDDING -> ANALYZING -> READY.
    Tracks status, start_time, end_time, progress percentage, and error details per stage.
    """

    async def run_pipeline(self, paper_id: uuid.UUID, force_retry: bool = False) -> None:
        async with async_session_factory() as db:
            paper_res = await db.execute(select(Paper).where(Paper.id == paper_id))
            paper = paper_res.scalar_one_or_none()

            if not paper:
                logger.error(f"Pipeline error: Paper {paper_id} not found.")
                return

            if paper.status == PaperStatus.READY and not force_retry:
                logger.info(f"Paper {paper_id} is already in READY status. Skipping pipeline.")
                return

            # Initialize stage details tracking dictionary
            stage_details = paper.stage_details_json or {}
            paper.status = PaperStatus.PROCESSING
            paper.processing_error = None
            await db.commit()

            pdf_path = get_upload_dir() / paper.file_name

            # Helper to record stage transitions
            async def update_stage(stage: PipelineStage, progress: int, status_str: str, error_msg: Optional[str] = None):
                nonlocal stage_details
                stage_key = stage.value
                now_str = datetime.now(timezone.utc).isoformat()

                if stage_key not in stage_details:
                    stage_details[stage_key] = {"status": status_str, "start_time": now_str, "end_time": None, "error": None}
                else:
                    stage_details[stage_key]["status"] = status_str

                if status_str == "IN_PROGRESS":
                    stage_details[stage_key]["start_time"] = now_str
                elif status_str in ["COMPLETED", "FAILED"]:
                    stage_details[stage_key]["end_time"] = now_str

                if error_msg:
                    stage_details[stage_key]["error"] = error_msg

                paper.stage = stage
                paper.progress = progress
                paper.stage_details_json = dict(stage_details)
                await db.commit()

            try:
                # STAGE 1: EXTRACTING
                await update_stage(PipelineStage.EXTRACTING, 10, "IN_PROGRESS")
                extractor = PDFExtractor()
                doc_meta = await extractor.extract(pdf_path, paper_id, db)
                if doc_meta and doc_meta.get("page_count"):
                    paper.page_count = doc_meta["page_count"]
                    if doc_meta.get("title"):
                        paper.title = doc_meta["title"][:512]
                    if doc_meta.get("authors"):
                        paper.authors = ", ".join(doc_meta["authors"]) if isinstance(doc_meta["authors"], list) else str(doc_meta["authors"])
                await update_stage(PipelineStage.EXTRACTING, 20, "COMPLETED")

                # STAGE 2: STRUCTURING
                await update_stage(PipelineStage.STRUCTURING, 30, "IN_PROGRESS")
                pages_res = await db.execute(select(PaperPage).where(PaperPage.paper_id == paper_id).order_by(PaperPage.page_number))
                pages = pages_res.scalars().all()

                detector = SectionDetector()
                await detector.detect_and_save(paper_id, pages, db)
                await update_stage(PipelineStage.STRUCTURING, 40, "COMPLETED")

                # STAGE 3: CHUNKING
                await update_stage(PipelineStage.CHUNKING, 50, "IN_PROGRESS")
                sec_res = await db.execute(select(PaperSection).where(PaperSection.paper_id == paper_id).order_by(PaperSection.order_index))
                sections = sec_res.scalars().all()

                chunker = ChunkingEngine()
                await chunker.chunk_paper(paper_id, pages, sections, db)
                await update_stage(PipelineStage.CHUNKING, 60, "COMPLETED")

                # STAGE 4: EMBEDDING
                await update_stage(PipelineStage.EMBEDDING, 70, "IN_PROGRESS")
                await index_paper(paper_id, db, force_reindex=force_retry)
                await update_stage(PipelineStage.EMBEDDING, 80, "COMPLETED")

                # STAGE 5: ANALYZING
                await update_stage(PipelineStage.ANALYZING, 90, "IN_PROGRESS")
                summary_svc = SummaryService()
                await summary_svc.generate_structured_analysis(paper_id, db)
                await update_stage(PipelineStage.ANALYZING, 95, "COMPLETED")

                # STAGE 6: READY
                paper.status = PaperStatus.READY
                paper.stage = PipelineStage.READY
                paper.progress = 100
                paper.processing_error = None
                await db.commit()
                logger.info(f"Pipeline successfully completed for paper {paper_id}.")

            except Exception as e:
                logger.error(f"Pipeline failed at stage {paper.stage.value} for paper {paper_id}: {e}", exc_info=True)
                error_info = f"Failed during {paper.stage.value} stage: {str(e)}"
                await update_stage(paper.stage, paper.progress, "FAILED", error_msg=error_info)
                
                paper.status = PaperStatus.FAILED
                paper.stage = PipelineStage.FAILED
                paper.processing_error = "An error occurred during paper processing pipeline. Retry is available."
                await db.commit()
