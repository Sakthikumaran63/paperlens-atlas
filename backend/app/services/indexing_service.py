import logging
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import PaperStatus
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.embedding_service import EmbeddingGenerationError, EmbeddingService

logger = logging.getLogger("paperlens")


async def index_paper(
    paper_id: uuid.UUID,
    db: AsyncSession,
    force_reindex: bool = False,
    embedding_service: Optional[EmbeddingService] = None
) -> Paper:
    """
    Generate and store vector embeddings for PaperChunk.text in PostgreSQL pgvector.
    Batches chunk vector generation, skips already embedded chunks unless force_reindex=True,
    and updates paper status: UPLOADED/FAILED -> PROCESSING -> READY (or FAILED with retry capability).
    """
    # 1. Fetch Paper record
    stmt = select(Paper).where(Paper.id == paper_id)
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise ValueError(f"Paper with ID {paper_id} not found.")

    # 2. Transition status -> PROCESSING
    paper.status = PaperStatus.PROCESSING
    paper.processing_error = None
    await db.commit()
    await db.refresh(paper)

    try:
        # 3. Load PaperChunk records
        chunk_stmt = select(PaperChunk).where(PaperChunk.paper_id == paper_id).order_by(PaperChunk.chunk_index)
        chunk_res = await db.execute(chunk_stmt)
        chunks: List[PaperChunk] = chunk_res.scalars().all()

        if not chunks:
            # Paper has no chunks yet, set READY
            paper.status = PaperStatus.READY
            paper.processing_error = None
            await db.commit()
            await db.refresh(paper)
            return paper

        # Filter chunks that require embedding
        if force_reindex:
            target_chunks = chunks
        else:
            target_chunks = [c for c in chunks if c.embedding is None]

        if not target_chunks:
            # All chunks already indexed
            logger.info(f"Paper {paper_id} chunks are already fully indexed. Skipping vector regeneration.")
            paper.status = PaperStatus.READY
            paper.processing_error = None
            await db.commit()
            await db.refresh(paper)
            return paper

        # 4. Batch vector generation
        emb_service = embedding_service or EmbeddingService()
        batch_size = settings.EMBEDDING_BATCH_SIZE

        for i in range(0, len(target_chunks), batch_size):
            batch = target_chunks[i:i + batch_size]
            batch_texts = [c.text for c in batch]

            vectors = await emb_service.generate_embeddings(batch_texts)

            for chunk, vector in zip(batch, vectors):
                chunk.embedding = vector

            await db.flush()

        # 5. Transition status -> READY on success
        paper.status = PaperStatus.READY
        paper.processing_error = None
        await db.commit()
        await db.refresh(paper)

        logger.info(f"Successfully generated and stored vector embeddings for {len(target_chunks)} chunks of paper {paper_id}.")
        return paper

    except Exception as e:
        logger.error(f"Failed to generate embeddings for paper {paper_id}: {str(e)}", exc_info=True)
        # Transition status -> FAILED with safe error description (no raw stack traces)
        paper.status = PaperStatus.FAILED
        if isinstance(e, EmbeddingGenerationError):
            paper.processing_error = f"Embedding indexing failed: {str(e)}"
        else:
            paper.processing_error = "An error occurred during vector embedding generation. Indexing can be retried."

        await db.commit()
        await db.refresh(paper)
        return paper
