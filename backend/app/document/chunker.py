"""
Document Chunking Module
------------------------
Generates ~400 token semantic chunks respecting section and page boundaries.
"""
from typing import List
from app.services.chunking_engine import ChunkingEngine, GeneratedChunk


class DocumentChunker:
    """Chunks paper text into semantic chunks without crossing section boundaries."""

    def __init__(self, engine: ChunkingEngine = None):
        self.engine = engine or ChunkingEngine()

    def chunk_paper(self, pages: List[any], sections: List[any]) -> List[GeneratedChunk]:
        return self.engine.chunk_paper(pages, sections)
