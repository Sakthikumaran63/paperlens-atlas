import difflib
import hashlib
import logging
from typing import List, Optional
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.evidence import EvidencePackage, SelectedEvidenceItem
from app.schemas.retrieval import RetrievedChunkCandidate
from app.services.chunking_engine import ChunkingEngine

logger = logging.getLogger("paperlens")


class EvidenceSelectionConfig(BaseModel):
    max_context_tokens: int = settings.MAX_EVIDENCE_CONTEXT_TOKENS
    max_items: int = 6
    dedup_threshold: float = settings.DEDUPLICATION_SIMILARITY_THRESHOLD


class EvidenceSelectionService:
    """
    PaperLens Evidence Selection Service.
    Transforms ranked retrieval candidates into a compact, deduplicated, token-budgeted, auditable evidence package for the LLM.
    Strictly preserves page numbers, section names, chunk IDs, and text immutability.
    """

    def is_near_duplicate(self, text: str, selected_texts: List[str], threshold: float) -> bool:
        if not selected_texts or not text:
            return False
        
        # Check text similarity ratio with previously selected evidence items
        for prev_text in selected_texts:
            ratio = difflib.SequenceMatcher(None, text, prev_text).ratio()
            if ratio >= threshold:
                return True
        return False

    def select_evidence(
        self,
        candidates: List[RetrievedChunkCandidate],
        config: Optional[EvidenceSelectionConfig] = None
    ) -> EvidencePackage:
        if not candidates:
            return EvidencePackage(items=[], total_tokens=0, total_items=0, package_hash=hashlib.sha256(b"empty").hexdigest())

        cfg = config or EvidenceSelectionConfig()
        
        # Sort candidates by final_score / similarity_score descending
        sorted_cands = sorted(candidates, key=lambda c: getattr(c, 'final_score', c.similarity_score), reverse=True)

        selected_items: List[SelectedEvidenceItem] = []
        selected_texts: List[str] = []
        accumulated_tokens = 0

        for cand in sorted_cands:
            if len(selected_items) >= cfg.max_items:
                break

            # 1. Near-duplicate removal check
            if self.is_near_duplicate(cand.text, selected_texts, cfg.dedup_threshold):
                logger.debug(f"Skipped near-duplicate chunk {cand.chunk_id}.")
                continue

            # 2. Token budget check
            cand_tokens = ChunkingEngine.count_tokens(cand.text)
            if accumulated_tokens + cand_tokens > cfg.max_context_tokens:
                # Token budget reached
                logger.debug(f"Evidence token budget reached ({accumulated_tokens}/{cfg.max_context_tokens}). Stopping selection.")
                break

            # 3. Create immutable evidence item maintaining full traceability
            evidence_id = f"ev_{len(selected_items) + 1}"
            retrieval_score = getattr(cand, 'final_score', cand.similarity_score)

            item = SelectedEvidenceItem(
                evidence_id=evidence_id,
                chunk_id=cand.chunk_id,
                page=cand.page if hasattr(cand, 'page') else cand.page_number,
                section=cand.section if hasattr(cand, 'section') else cand.section_title,
                text=cand.text,  # Text is NEVER modified or mutated
                retrieval_score=round(float(retrieval_score), 4)
            )

            selected_items.append(item)
            selected_texts.append(cand.text)
            accumulated_tokens += cand_tokens

        # 4. Generate SHA-256 package hash for auditability
        hash_input_parts = [
            f"{it.evidence_id}:{it.chunk_id}:{it.page}:{it.section}:{it.text}:{it.retrieval_score}"
            for it in selected_items
        ]
        hash_string = "||".join(hash_input_parts)
        package_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

        return EvidencePackage(
            items=selected_items,
            total_tokens=accumulated_tokens,
            total_items=len(selected_items),
            package_hash=package_hash
        )
