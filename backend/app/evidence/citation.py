"""
Citation Assembly & Lineage Module
----------------------------------
Binds answer statements to authoritative database chunk records.
"""
from typing import List
from app.models.paper_chunk import PaperChunk
from app.schemas.answer import SourceReference
from app.schemas.evidence import EvidencePackage


class CitationAssembler:
    """Assembles authoritative database source references for frontend display."""

    @staticmethod
    def build_source_references(evidence_package: EvidencePackage) -> List[SourceReference]:
        sources: List[SourceReference] = []
        for item in evidence_package.items:
            sources.append(
                SourceReference(
                    page=item.page,
                    section=item.section,
                    chunk_id=item.chunk_id,
                    text=item.text,
                )
            )
        return sources
