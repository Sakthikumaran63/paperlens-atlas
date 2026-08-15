"""Orchestrates the end-to-end async paper analysis pipeline.

Stages (progress ranges are the *within-stage* bounds the orchestrator
reports while that stage is running; gaps between stages are intentional
buffer room for a stage's own internal sub-steps if it wants to report
finer-grained progress later):

    EXTRACTING   10-20%
    STRUCTURING  30-40%
    CHUNKING     50-60%
    EMBEDDING    70-80%
    ANALYZING    90-95%
    READY        100%
"""
from __future__ import annotations

import logging
import uuid
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.enums import PaperStatus, PipelineStage
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_page import PaperPage
from app.models.paper_section import PaperSection
from app.services.chunking_engine import ChunkingEngine
from app.services.indexing_service import index_paper
from app.services.pdf_extractor import PDFExtractor
from app.services.section_detector import SectionDetector
from app.services.summary_service import SummaryService
from app.utils.storage import get_upload_dir

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------

class PaperStage(str, Enum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    STRUCTURING = "STRUCTURING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    ANALYZING = "ANALYZING"
    READY = "READY"
    FAILED = "FAILED"


# (start_progress, end_progress) reported for each stage.
STAGE_PROGRESS: dict[PaperStage, tuple[int, int]] = {
    PaperStage.EXTRACTING: (10, 20),
    PaperStage.STRUCTURING: (30, 40),
    PaperStage.CHUNKING: (50, 60),
    PaperStage.EMBEDDING: (70, 80),
    PaperStage.ANALYZING: (90, 95),
    PaperStage.READY: (100, 100),
}

# Order stages run in.
STAGE_ORDER: list[PaperStage] = [
    PaperStage.EXTRACTING,
    PaperStage.STRUCTURING,
    PaperStage.CHUNKING,
    PaperStage.EMBEDDING,
    PaperStage.ANALYZING,
]


class PipelineError(Exception):
    """Raised when a stage fails; carries a user-friendly message."""

    def __init__(self, stage: PaperStage, user_message: str, *, cause: Optional[BaseException] = None):
        super().__init__(user_message)
        self.stage = stage
        self.user_message = user_message
        self.__cause__ = cause


# --------------------------------------------------------------------------
# Stage service interfaces
# --------------------------------------------------------------------------

class Extractor(Protocol):
    async def run(self, *, db: AsyncSession, paper: Any) -> None: ...


class Structurer(Protocol):
    async def run(self, *, db: AsyncSession, paper: Any) -> None: ...


class Chunker(Protocol):
    async def run(self, *, db: AsyncSession, paper: Any) -> None: ...


class Embedder(Protocol):
    async def run(self, *, db: AsyncSession, paper: Any) -> None: ...


class Analyzer(Protocol):
    async def run(self, *, db: AsyncSession, paper: Any) -> None: ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Default Stage Implementations mapped to PaperLens engine services
# --------------------------------------------------------------------------

class DefaultExtractor:
    async def run(self, *, db: AsyncSession, paper: Any) -> None:
        pdf_path = get_upload_dir() / (paper.file_path or paper.file_name)
        extractor = PDFExtractor()
        extracted_doc = extractor.extract(pdf_path)

        paper.page_count = extracted_doc.page_count
        if extracted_doc.title_candidate:
            paper.title = extracted_doc.title_candidate[:512]
        if extracted_doc.author_candidates:
            paper.authors = ", ".join(extracted_doc.author_candidates)

        await db.execute(delete(PaperPage).where(PaperPage.paper_id == paper.id))
        for page_data in extracted_doc.pages:
            page_record = PaperPage(
                paper_id=paper.id,
                page_number=page_data.page_number,
                raw_text=page_data.raw_text,
                cleaned_text=page_data.cleaned_text,
                character_count=page_data.character_count,
                word_count=page_data.word_count
            )
            db.add(page_record)
        await db.flush()


class DefaultStructurer:
    async def run(self, *, db: AsyncSession, paper: Any) -> None:
        pages_res = await db.execute(
            select(PaperPage).where(PaperPage.paper_id == paper.id).order_by(PaperPage.page_number)
        )
        pages = pages_res.scalars().all()

        await db.execute(delete(PaperSection).where(PaperSection.paper_id == paper.id))
        detector = SectionDetector()
        detected_sections = detector.detect_sections(pages)

        for ds in detected_sections:
            sec_record = PaperSection(
                paper_id=paper.id,
                title=ds.title,
                normalized_title=ds.normalized_title,
                section_type=ds.section_type,
                page_start=ds.page_start,
                page_end=ds.page_end,
                order_index=ds.order_index,
                confidence=ds.confidence
            )
            db.add(sec_record)
        await db.flush()


class DefaultChunker:
    async def run(self, *, db: AsyncSession, paper: Any) -> None:
        pages_res = await db.execute(
            select(PaperPage).where(PaperPage.paper_id == paper.id).order_by(PaperPage.page_number)
        )
        pages = pages_res.scalars().all()

        sec_res = await db.execute(
            select(PaperSection).where(PaperSection.paper_id == paper.id).order_by(PaperSection.order_index)
        )
        sections = sec_res.scalars().all()

        await db.execute(delete(PaperChunk).where(PaperChunk.paper_id == paper.id))
        chunker = ChunkingEngine()
        generated_chunks = chunker.chunk_paper(paper.id, pages, sections)

        for gc in generated_chunks:
            chunk_record = PaperChunk(
                paper_id=paper.id,
                page_number=gc.page_number,
                section_id=gc.section_id,
                chunk_index=gc.chunk_index,
                text=gc.text,
                token_count=gc.token_count,
                metadata_json=gc.metadata
            )
            db.add(chunk_record)
        await db.flush()


class DefaultEmbedder:
    async def run(self, *, db: AsyncSession, paper: Any) -> None:
        await index_paper(paper.id, db, force_reindex=True)


class DefaultAnalyzer:
    async def run(self, *, db: AsyncSession, paper: Any) -> None:
        summary_svc = SummaryService()
        await summary_svc.generate_structured_analysis(paper.id, db)


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

class PaperPipelineOrchestrator:
    """Drives a single paper through the full analysis pipeline."""

    def __init__(
        self,
        paper_id: Optional[uuid.UUID] = None,
        force_retry: bool = False,
        db: Optional[AsyncSession] = None,
        *,
        extractor: Optional[Extractor] = None,
        structurer: Optional[Structurer] = None,
        chunker: Optional[Chunker] = None,
        embedder: Optional[Embedder] = None,
        analyzer: Optional[Analyzer] = None,
    ) -> None:
        self.paper_id = paper_id
        self.force_retry = force_retry


        self._external_db = db
        self._owned_session_cm: Optional[AbstractAsyncContextManager[AsyncSession]] = None

        self._extractor = extractor
        self._structurer = structurer
        self._chunker = chunker
        self._embedder = embedder
        self._analyzer = analyzer

    # Backward compatibility entry point
    async def run_pipeline(self, paper_id: uuid.UUID, force_retry: bool = False, db: Optional[AsyncSession] = None) -> None:
        self.paper_id = paper_id
        self.force_retry = force_retry
        if db is not None:
            await self._run_with_session(db)
        else:
            from app.db.session import async_session_factory
            async with async_session_factory() as session:
                await self._run_with_session(session)

    # -- public API --------------------------------------------------

    async def run(self) -> Any:
        """Run the full pipeline for `self.paper_id` and return the Paper row."""
        if self._external_db is not None:
            return await self._run_with_session(self._external_db)

        from app.db.session import async_session_factory

        self._owned_session_cm = async_session_factory()
        async with self._owned_session_cm as session:
            return await self._run_with_session(session)

    # -- core flow -----------------------------------------------------

    async def _run_with_session(self, db: AsyncSession) -> Any:
        paper_res = await db.execute(select(Paper).where(Paper.id == self.paper_id))
        paper = paper_res.scalar_one_or_none()

        if paper is None:
            logger.error(f"Pipeline error: Paper {self.paper_id} not found.")
            return None


        current_status = getattr(paper, "status", None)
        current_stage = getattr(paper, "stage", None)
        is_ready = (current_status == PaperStatus.READY or current_stage == PaperStage.READY.value or current_stage == PipelineStage.READY)

        if is_ready and not self.force_retry:
            logger.info(f"Paper {self.paper_id} is already in READY status. Skipping pipeline.")
            return paper

        paper.status = PaperStatus.PROCESSING
        self._init_stage_details(paper)

        try:
            await self._clear_previous_artifacts(db, paper)

            services: dict[PaperStage, Any] = {
                PaperStage.EXTRACTING: self._extractor or DefaultExtractor(),
                PaperStage.STRUCTURING: self._structurer or DefaultStructurer(),
                PaperStage.CHUNKING: self._chunker or DefaultChunker(),
                PaperStage.EMBEDDING: self._embedder or DefaultEmbedder(),
                PaperStage.ANALYZING: self._analyzer or DefaultAnalyzer(),
            }

            for stage in STAGE_ORDER:
                await self._enter_stage(db, paper, stage)
                try:
                    await services[stage].run(db=db, paper=paper)
                except Exception as exc:
                    raise PipelineError(
                        stage,
                        self._friendly_error_message(stage, exc),
                        cause=exc,
                    ) from exc
                await self._complete_stage(db, paper, stage)

            await self._mark_ready(db, paper)
            await db.commit()
            return paper

        except PipelineError as pipeline_exc:
            await db.rollback()
            await self._mark_failed(db, paper, pipeline_exc.stage, pipeline_exc.user_message)
            await db.commit()
            raise
        except Exception as exc:
            logger.exception("Unexpected pipeline failure for paper %s", self.paper_id)
            await db.rollback()
            await self._mark_failed(
                db, paper, PaperStage(getattr(paper, "stage", PaperStage.PENDING.value)) if self._is_known_stage(paper) else PaperStage.PENDING,
                "An unexpected error occurred while processing this paper. Our team has been notified.",
            )
            await db.commit()
            raise

    @staticmethod
    def _is_known_stage(paper: Any) -> bool:
        try:
            PaperStage(getattr(paper, "stage", None))
            return True
        except ValueError:
            return False

    # -- idempotent cleanup ---------------------------------------------

    async def _clear_previous_artifacts(self, db: AsyncSession, paper: Any) -> None:
        """Delete any previously generated pages/sections/chunks/analysis."""
        from app.models.paper_analysis import PaperAnalysis
        for model in (PaperAnalysis, PaperChunk, PaperSection, PaperPage):
            await db.execute(delete(model).where(model.paper_id == paper.id))
        await db.flush()

    # -- stage bookkeeping -------------------------------------------------

    def _init_stage_details(self, paper: Any) -> None:
        details: dict[str, Any] = dict(getattr(paper, "stage_details_json", None) or {})
        details["start_time"] = _now_iso()
        details["end_time"] = None
        details["error"] = None
        details.setdefault("history", [])
        paper.stage_details_json = details
        paper.processing_error = None
        flag_modified(paper, "stage_details_json")

    async def _enter_stage(self, db: AsyncSession, paper: Any, stage: PaperStage) -> None:
        start_progress, _ = STAGE_PROGRESS[stage]
        # Map enum to model enum compatibility
        try:
            paper.stage = PipelineStage(stage.value)
        except ValueError:
            paper.stage = stage.value

        paper.progress = start_progress

        details = dict(paper.stage_details_json or {})
        details["current_stage"] = stage.value
        details["updated_at"] = _now_iso()

        stage_key = stage.value
        if stage_key not in details or not isinstance(details[stage_key], dict):
            details[stage_key] = {"status": "IN_PROGRESS", "start_time": _now_iso(), "end_time": None, "error": None}
        else:
            details[stage_key]["status"] = "IN_PROGRESS"
            details[stage_key]["start_time"] = _now_iso()

        history = list(details.get("history", []))
        history.append({
            "stage": stage.value,
            "status": "started",
            "started_at": _now_iso(),
            "progress_start": start_progress,
        })
        details["history"] = history
        paper.stage_details_json = details
        flag_modified(paper, "stage_details_json")

        db.add(paper)
        await db.commit()

    async def _complete_stage(self, db: AsyncSession, paper: Any, stage: PaperStage) -> None:
        _, end_progress = STAGE_PROGRESS[stage]
        paper.progress = end_progress

        details = dict(paper.stage_details_json or {})
        details["updated_at"] = _now_iso()

        stage_key = stage.value
        if stage_key in details and isinstance(details[stage_key], dict):
            details[stage_key]["status"] = "COMPLETED"
            details[stage_key]["end_time"] = _now_iso()

        history = list(details.get("history", []))
        if history and history[-1]["stage"] == stage.value and history[-1]["status"] == "started":
            history[-1]["status"] = "completed"
            history[-1]["ended_at"] = _now_iso()
            history[-1]["progress_end"] = end_progress
        details["history"] = history
        paper.stage_details_json = details
        flag_modified(paper, "stage_details_json")

        db.add(paper)
        await db.commit()


    async def _mark_ready(self, db: AsyncSession, paper: Any) -> None:
        paper.status = PaperStatus.READY
        try:
            paper.stage = PipelineStage.READY
        except ValueError:
            paper.stage = PaperStage.READY.value

        paper.progress = 100
        paper.processing_error = None

        details = dict(paper.stage_details_json or {})
        details["current_stage"] = PaperStage.READY.value
        details["end_time"] = _now_iso()
        details["updated_at"] = _now_iso()
        details["error"] = None
        paper.stage_details_json = details
        flag_modified(paper, "stage_details_json")

        db.add(paper)
        await db.commit()

    async def _mark_failed(self, db: AsyncSession, paper: Any, stage: PaperStage, user_message: str) -> None:
        paper.status = PaperStatus.FAILED
        try:
            paper.stage = PipelineStage.FAILED
        except ValueError:
            paper.stage = PaperStage.FAILED.value

        paper.processing_error = user_message

        details = dict(getattr(paper, "stage_details_json", None) or {})
        details["current_stage"] = PaperStage.FAILED.value
        details["end_time"] = _now_iso()
        details["updated_at"] = _now_iso()
        details["error"] = {
            "failed_stage": stage.value if isinstance(stage, PaperStage) else str(stage),
            "message": user_message,
            "occurred_at": _now_iso(),
        }
        history = list(details.get("history", []))
        if history and history[-1].get("status") == "started":
            history[-1]["status"] = "failed"
            history[-1]["ended_at"] = _now_iso()
        details["history"] = history
        paper.stage_details_json = details
        flag_modified(paper, "stage_details_json")

        db.add(paper)
        await db.commit()

    @staticmethod
    def _friendly_error_message(stage: PaperStage, exc: Exception) -> str:
        logger.exception("Pipeline stage %s failed", stage.value)
        stage_labels = {
            PaperStage.EXTRACTING: "extracting text from the PDF",
            PaperStage.STRUCTURING: "structuring the document",
            PaperStage.CHUNKING: "splitting the document into chunks",
            PaperStage.EMBEDDING: "generating embeddings",
            PaperStage.ANALYZING: "analyzing the paper",
        }
        label = stage_labels.get(stage, stage.value.lower())
        return f"Something went wrong while {label}. Please try again, or contact support if this keeps happening."
