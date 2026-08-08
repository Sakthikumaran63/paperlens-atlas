import logging
from pathlib import Path
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import PaperStatus
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_page import PaperPage
from app.models.paper_section import PaperSection
from app.services.chunking_engine import ChunkingEngine
from app.services.pdf_extractor import PDFExtractionError, PDFExtractor
from app.services.section_detector import SectionDetector
from app.utils.storage import get_upload_dir

logger = logging.getLogger("paperlens")


async def process_paper(paper_id: uuid.UUID, db: AsyncSession) -> Paper:
    """
    Process an uploaded paper by extracting text page by page using PDFExtractor.
    Updates paper status: UPLOADED -> PROCESSING -> READY (or FAILED).
    Ensures safe user-facing processing_error strings without exposing stack traces.
    """
    # 1. Fetch Paper record
    stmt = select(Paper).where(Paper.id == paper_id)
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise ValueError(f"Paper with ID {paper_id} not found.")

    # 2. Update status: UPLOADED -> PROCESSING
    paper.status = PaperStatus.PROCESSING
    paper.processing_error = None
    await db.commit()
    await db.refresh(paper)

    try:
        # Resolve file path
        upload_dir = get_upload_dir()
        # Find file in storage matching internal stored filename or paper title/file_name
        stored_file_path: Optional[Path] = None
        
        # Check files in storage matching uuid pattern or filename
        for p in upload_dir.glob("*.pdf"):
            if p.is_file():
                stored_file_path = p
                break

        if not stored_file_path or not stored_file_path.exists():
            raise PDFExtractionError("Uploaded PDF file not found in storage.")

        # 3. Perform PDF text extraction
        extractor = PDFExtractor()
        extracted_doc = extractor.extract(stored_file_path)

        # 4. Idempotently clear existing PaperPages if re-processed
        await db.execute(delete(PaperPage).where(PaperPage.paper_id == paper_id))

        # 5. Populate PaperPage database records
        db_pages = []
        for page_data in extracted_doc.pages:
            db_page = PaperPage(
                paper_id=paper.id,
                page_number=page_data.page_number,
                raw_text=page_data.raw_text,
                cleaned_text=page_data.cleaned_text,
                character_count=page_data.character_count,
                word_count=page_data.word_count
            )
            db.add(db_page)
            db_pages.append(db_page)
        
        await db.flush()

        # 6. Scientific section detection & persistence
        detector = SectionDetector()
        detected_sections = detector.detect_sections(db_pages)

        # Clear previous sections if re-processing
        await db.execute(delete(PaperSection).where(PaperSection.paper_id == paper_id))

        db_sections = []
        for sec in detected_sections:
            db_section = PaperSection(
                paper_id=paper.id,
                title=sec.title,
                normalized_title=sec.normalized_title,
                section_type=sec.section_type,
                page_start=sec.page_start,
                page_end=sec.page_end,
                order_index=sec.order_index,
                confidence=sec.confidence
            )
            db.add(db_section)
            db_sections.append(db_section)

        await db.flush()

        # 7. Structure-aware chunking & persistence
        chunker = ChunkingEngine()
        generated_chunks = chunker.chunk_paper(paper.id, db_pages, db_sections)

        # Clear previous chunks if re-processing
        await db.execute(delete(PaperChunk).where(PaperChunk.paper_id == paper_id))

        for chk in generated_chunks:
            db_chunk = PaperChunk(
                paper_id=paper.id,
                page_number=chk.page_number,
                section_id=chk.section_id,
                chunk_index=chk.chunk_index,
                text=chk.text,
                token_count=chk.token_count,
                metadata_json=chk.metadata
            )
            db.add(db_chunk)

        # 8. Update Paper metadata & status -> READY
        paper.page_count = extracted_doc.page_count
        if extracted_doc.title_candidate and (not paper.title or paper.title == paper.file_name):
            paper.title = extracted_doc.title_candidate
        if extracted_doc.author_candidates and not paper.authors:
            paper.authors = extracted_doc.author_candidates

        paper.status = PaperStatus.READY
        paper.processing_error = None
        await db.commit()
        await db.refresh(paper)
        logger.info(
            f"Successfully processed paper {paper.id} "
            f"({extracted_doc.page_count} pages, {len(db_sections)} sections, {len(generated_chunks)} chunks)."
        )
        return paper

    except Exception as e:
        logger.error(f"Error processing paper {paper_id}: {str(e)}", exc_info=True)
        # Transition -> FAILED with safe user-facing error message (no raw stack traces)
        paper.status = PaperStatus.FAILED
        if isinstance(e, PDFExtractionError):
            paper.processing_error = str(e)
        else:
            paper.processing_error = "An internal error occurred during text extraction. Please ensure the file is a valid PDF."
        
        await db.commit()
        await db.refresh(paper)
        return paper
