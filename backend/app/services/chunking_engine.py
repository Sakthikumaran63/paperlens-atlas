import math
import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.models.enums import SectionType
from app.models.paper_page import PaperPage
from app.models.paper_section import PaperSection


class ChunkConfig(BaseModel):
    target_tokens: int = 350
    max_tokens: int = 512
    min_tokens: int = 40
    overlap_tokens: int = 50


class GeneratedChunk(BaseModel):
    paper_id: uuid.UUID
    page_number: int
    section_id: Optional[uuid.UUID] = None
    section_type: SectionType
    section_title: str
    chunk_index: int
    text: str
    token_count: int
    metadata: Dict[str, Any] = {}


class ChunkingEngine:
    """
    PaperLens Structure-Aware Chunking Engine.
    Splits paper text along paragraph and section boundaries while enforcing token constraints,
    controlled overlap, special scientific section policies, and strict traceability (Paper -> Page -> Section -> Chunk).
    """

    @staticmethod
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        # Standard token approximation: ~1.3 tokens per word
        words = text.split()
        return max(1, math.ceil(len(words) * 1.3))

    def split_into_paragraphs(self, text: str) -> List[str]:
        if not text:
            return []
        # Split on double newlines or paragraph breaks
        raw_paras = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraphs = []
        for p in raw_paras:
            # If paragraph is very large, split into sentences
            if self.count_tokens(p) > 400:
                sentences = [s.strip() + '.' for s in re.split(r'\.\s+', p) if s.strip()]
                paragraphs.extend(sentences)
            else:
                paragraphs.append(p)
        return paragraphs

    def chunk_paper(
        self,
        paper_id: uuid.UUID,
        pages: List[PaperPage],
        sections: List[PaperSection],
        config: Optional[ChunkConfig] = None
    ) -> List[GeneratedChunk]:
        if not pages:
            return []

        cfg = config or ChunkConfig()
        chunks: List[GeneratedChunk] = []
        global_chunk_index = 0

        # Sort sections by order_index
        sorted_sections = sorted(sections, key=lambda s: s.order_index) if sections else []

        # If no sections detected, treat entire document as single default section
        if not sorted_sections:
            mock_section = PaperSection(
                id=uuid.uuid4(),
                paper_id=paper_id,
                title="Full Document",
                normalized_title="full document",
                section_type=SectionType.OTHER,
                page_start=pages[0].page_number,
                page_end=pages[-1].page_number,
                order_index=0,
                confidence=0.50
            )
            sorted_sections = [mock_section]

        # Map pages by page_number for fast lookup
        page_dict = {p.page_number: p for p in pages}

        for sec in sorted_sections:
            # Collect text belonging to this section across its page_start -> page_end
            sec_paragraphs_with_page: List[Tuple[str, int]] = []
            
            for p_num in range(sec.page_start, sec.page_end + 1):
                if p_num in page_dict:
                    p_obj = page_dict[p_num]
                    p_text = p_obj.cleaned_text or p_obj.raw_text or ""
                    paras = self.split_into_paragraphs(p_text)
                    for para in paras:
                        sec_paragraphs_with_page.append((para, p_num))

            if not sec_paragraphs_with_page:
                continue

            # Special Section Policy 1: ABSTRACT
            if sec.section_type == SectionType.ABSTRACT:
                combined_abstract = " ".join([p[0] for p in sec_paragraphs_with_page])
                tokens = self.count_tokens(combined_abstract)
                if tokens <= cfg.max_tokens:
                    # Single intact abstract chunk
                    chunks.append(
                        GeneratedChunk(
                            paper_id=paper_id,
                            page_number=sec_paragraphs_with_page[0][1],
                            section_id=sec.id,
                            section_type=sec.section_type,
                            section_title=sec.title,
                            chunk_index=global_chunk_index,
                            text=combined_abstract,
                            token_count=tokens,
                            metadata={
                                "section_type": sec.section_type.value,
                                "section_title": sec.title,
                                "page_number": sec_paragraphs_with_page[0][1],
                                "is_abstract": True
                            }
                        )
                    )
                    global_chunk_index += 1
                    continue

            # Section Chunking Loop with Paragraph Boundaries & Controlled Overlap
            current_chunk_paras: List[str] = []
            current_tokens = 0
            current_page_num = sec_paragraphs_with_page[0][1]

            for para_text, page_num in sec_paragraphs_with_page:
                para_tokens = self.count_tokens(para_text)

                # Check if adding paragraph exceeds max_tokens
                if current_chunk_paras and (current_tokens + para_tokens > cfg.target_tokens):
                    chunk_text = "\n\n".join(current_chunk_paras)
                    chunks.append(
                        GeneratedChunk(
                            paper_id=paper_id,
                            page_number=current_page_num,
                            section_id=sec.id,
                            section_type=sec.section_type,
                            section_title=sec.title,
                            chunk_index=global_chunk_index,
                            text=chunk_text,
                            token_count=current_tokens,
                            metadata={
                                "section_type": sec.section_type.value,
                                "section_title": sec.title,
                                "page_number": current_page_num
                            }
                        )
                    )
                    global_chunk_index += 1

                    # Compute controlled overlap within same section
                    overlap_paras: List[str] = []
                    overlap_tokens_count = 0
                    for prev_p in reversed(current_chunk_paras):
                        p_toks = self.count_tokens(prev_p)
                        if overlap_tokens_count + p_toks <= cfg.overlap_tokens:
                            overlap_paras.insert(0, prev_p)
                            overlap_tokens_count += p_toks
                        else:
                            break

                    current_chunk_paras = overlap_paras + [para_text]
                    current_tokens = overlap_tokens_count + para_tokens
                    current_page_num = page_num
                else:
                    if not current_chunk_paras:
                        current_page_num = page_num
                    current_chunk_paras.append(para_text)
                    current_tokens += para_tokens

            # Flush remaining chunk for section
            if current_chunk_paras:
                chunk_text = "\n\n".join(current_chunk_paras)
                chunks.append(
                    GeneratedChunk(
                        paper_id=paper_id,
                        page_number=current_page_num,
                        section_id=sec.id,
                        section_type=sec.section_type,
                        section_title=sec.title,
                        chunk_index=global_chunk_index,
                        text=chunk_text,
                        token_count=current_tokens,
                        metadata={
                            "section_type": sec.section_type.value,
                            "section_title": sec.title,
                            "page_number": current_page_num
                        }
                    )
                )
                global_chunk_index += 1

        return chunks
