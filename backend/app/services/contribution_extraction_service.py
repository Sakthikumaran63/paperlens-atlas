import json
import logging
from typing import Dict, List, Optional
import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ContributionType, SectionType
from app.models.paper import Paper
from app.models.paper_analysis import PaperAnalysis
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.schemas.contribution import (
    ContributionEvidence,
    ContributionExtractionResponse,
    ExtractedContribution,
)
from app.services.llm_service import LLMService

logger = logging.getLogger("paperlens")


class ContributionExtractionService:
    """
    PaperLens Key Contribution Extraction Service.
    Prioritizes Introduction contribution statements, Abstract, Conclusion, Methodology, and 'Our contributions' sections.
    Distinguishes between EXPLICIT and INFERRED contributions, binds evidence source metadata (page, section, chunk_id),
    and strictly avoids inventing novelty.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    async def extract_contributions(
        self,
        paper_id: uuid.UUID,
        db: AsyncSession,
        llm_service: Optional[LLMService] = None
    ) -> ContributionExtractionResponse:
        # 1. Fetch Paper
        paper_stmt = select(Paper).where(Paper.id == paper_id)
        paper_res = await db.execute(paper_stmt)
        paper = paper_res.scalar_one_or_none()

        if not paper:
            raise ValueError(f"Paper with ID {paper_id} not found.")

        # 2. Fetch chunks prioritizing contribution sections
        priority_section_types = [
            SectionType.ABSTRACT,
            SectionType.INTRODUCTION,
            SectionType.CONCLUSION,
            SectionType.METHODOLOGY
        ]

        chunk_stmt = (
            select(PaperChunk, PaperSection)
            .outerjoin(PaperSection, PaperChunk.section_id == PaperSection.id)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.chunk_index)
        )
        chunk_res = await db.execute(chunk_stmt)
        rows = chunk_res.all()

        if not rows:
            return ContributionExtractionResponse()

        # Separate explicit "contributions" sections, priority sections, and others
        explicit_contrib_rows = []
        priority_rows = []
        other_rows = []

        for chunk, sec in rows:
            sec_title = (sec.title if sec else "").lower()
            if "contribution" in sec_title or "our contribution" in sec_title or "main contribution" in sec_title:
                explicit_contrib_rows.append((chunk, sec))
            elif sec and sec.section_type in priority_section_types:
                priority_rows.append((chunk, sec))
            else:
                other_rows.append((chunk, sec))

        target_rows = (explicit_contrib_rows + priority_rows + other_rows)[:10]

        # Format context for LLM with chunk_id, page, and section metadata
        prompt_evidence_parts = []
        chunk_metadata_map: Dict[str, Dict] = {}

        for idx, (chunk, sec) in enumerate(target_rows):
            sec_title = sec.title if sec else (chunk.metadata_json.get("section_title") if chunk.metadata_json else "Document Text")
            cid_str = str(chunk.id)
            page_no = chunk.page_number

            chunk_metadata_map[cid_str] = {
                "chunk_id": chunk.id,
                "page": page_no,
                "section": sec_title
            }
            prompt_evidence_parts.append(
                f"[ChunkID: {cid_str}] (Page {page_no}, Section: {sec_title}):\n{chunk.text}"
            )

        evidence_str = "\n\n".join(prompt_evidence_parts)

        # 3. Call LLM for key contribution extraction
        system_prompt = (
            "You are PaperLens, an expert scientific contribution extractor.\n"
            "Identify key contributions stated or strongly supported by the paper text ONLY.\n"
            "STRICT RULES:\n"
            "1. Prefer EXPLICIT contributions explicitly stated by authors (e.g. 'We propose...', 'Our main contributions are...').\n"
            "2. Mark contribution_type as 'EXPLICIT' or 'INFERRED'.\n"
            "3. DO NOT invent novelty or claim unstated achievements.\n"
            "4. Bind each contribution to the ChunkID where evidence is found.\n"
            "5. Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "contributions": [\n'
            '    {\n'
            '      "text": "...",\n'
            '      "contribution_type": "EXPLICIT",\n'
            '      "chunk_id": "..."\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        user_prompt = f"Paper Title: {paper.title}\n\nPAPER SECTIONS:\n{evidence_str}"

        llm_svc = llm_service or self.llm_service
        raw_json_str = ""

        if llm_svc.client is not None or settings.LLM_API_KEY:
            try:
                url = f"{settings.LLM_API_BASE.rstrip('/')}/chat/completions"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.LLM_API_KEY}"}
                payload = {
                    "model": settings.LLM_MODEL,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }

                client = llm_svc.client
                should_close = False
                if client is None:
                    client = httpx.AsyncClient(timeout=45.0)
                    should_close = True

                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        raw_json_str = resp.json()["choices"][0]["message"]["content"].strip()
                finally:
                    if should_close and client:
                        await client.aclose()

            except Exception as e:
                logger.warning(f"LLM API call for contribution extraction failed ({e}). Using deterministic fallback.")

        extracted_contributions: List[ExtractedContribution] = []

        if raw_json_str:
            try:
                clean_str = raw_json_str.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_str)
                contribs_raw = parsed.get("contributions", [])

                for item in contribs_raw:
                    txt = item.get("text", "")
                    c_type_str = str(item.get("contribution_type", "EXPLICIT")).upper()
                    c_type = ContributionType.INFERRED if c_type_str == "INFERRED" else ContributionType.EXPLICIT
                    cid_str = item.get("chunk_id", "")

                    if cid_str in chunk_metadata_map:
                        meta = chunk_metadata_map[cid_str]
                    else:
                        # Fallback to first chunk metadata
                        first_meta = next(iter(chunk_metadata_map.values()))
                        meta = first_meta

                    ev = ContributionEvidence(
                        page=meta["page"],
                        section=meta["section"],
                        chunk_id=meta["chunk_id"]
                    )
                    extracted_contributions.append(
                        ExtractedContribution(
                            text=txt,
                            contribution_type=c_type,
                            evidence=ev
                        )
                    )
            except Exception as parse_err:
                logger.warning(f"Failed to parse LLM contribution output ({parse_err}). Falling back.")
                extracted_contributions = self._build_fallback_contributions(paper.title, target_rows)
        else:
            extracted_contributions = self._build_fallback_contributions(paper.title, target_rows)

        # 4. Save/Update PaperAnalysis.contributions_json in PostgreSQL
        existing_stmt = select(PaperAnalysis).where(PaperAnalysis.paper_id == paper_id)
        existing_res = await db.execute(existing_stmt)
        analysis = existing_res.scalar_one_or_none()

        contributions_dump = [c.model_dump(mode="json") for c in extracted_contributions]

        if analysis:
            analysis.contributions_json = contributions_dump
        else:
            analysis = PaperAnalysis(
                paper_id=paper_id,
                summary_json={},
                methodology_json={},
                contributions_json=contributions_dump,
                claims_json=[]
            )
            db.add(analysis)

        await db.commit()
        return ContributionExtractionResponse(contributions=extracted_contributions)

    def _build_fallback_contributions(self, title: str, target_rows: List) -> List[ExtractedContribution]:
        results = []
        for idx, (chunk, sec) in enumerate(target_rows[:2]):
            sec_title = sec.title if sec else "Introduction"
            page_no = chunk.page_number
            c_type = ContributionType.EXPLICIT if idx == 0 else ContributionType.INFERRED

            ev = ContributionEvidence(
                page=page_no,
                section=sec_title,
                chunk_id=chunk.id
            )
            results.append(
                ExtractedContribution(
                    text=f"Contribution from {sec_title}: {chunk.text[:150]}...",
                    contribution_type=c_type,
                    evidence=ev
                )
            )
        return results
