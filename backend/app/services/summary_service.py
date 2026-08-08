import json
import logging
from typing import Dict, List, Optional
import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.paper import Paper
from app.models.paper_analysis import PaperAnalysis
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.schemas.analysis import ClaimWithSource, StructuredPaperSummary
from app.services.llm_service import LLMService

logger = logging.getLogger("paperlens")


class SummaryService:
    """
    PaperLens Structured Research-Paper Summarization Service.
    Leverages paper section structure to generate a 10-field structured analysis,
    tracks internal section/page source lineage for claims, and persists in PaperAnalysis.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    async def generate_structured_analysis(
        self,
        paper_id: uuid.UUID,
        db: AsyncSession,
        llm_service: Optional[LLMService] = None
    ) -> PaperAnalysis:
        # 1. Check if PaperAnalysis record already exists
        existing_stmt = select(PaperAnalysis).where(PaperAnalysis.paper_id == paper_id)
        existing_res = await db.execute(existing_stmt)
        existing_analysis = existing_res.scalar_one_or_none()

        if existing_analysis:
            return existing_analysis

        # 2. Fetch Paper, PaperSection, and PaperChunk records
        paper_stmt = select(Paper).where(Paper.id == paper_id)
        paper_res = await db.execute(paper_stmt)
        paper = paper_res.scalar_one_or_none()

        if not paper:
            raise ValueError(f"Paper with ID {paper_id} not found.")

        chunk_stmt = (
            select(PaperChunk, PaperSection)
            .outerjoin(PaperSection, PaperChunk.section_id == PaperSection.id)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.chunk_index)
        )
        chunk_res = await db.execute(chunk_stmt)
        rows = chunk_res.all()

        if not rows:
            # Fallback for paper without chunks
            empty_summary = StructuredPaperSummary(
                executive_summary="Paper text extraction pending or empty.",
                problem_statement="Not specified.",
                objective="Not specified.",
                methodology_summary="Not specified.",
                key_contributions=[],
                dataset="Not specified.",
                experimental_setup="Not specified.",
                key_results="Not specified.",
                limitations="Not specified.",
                conclusion="Not specified."
            )
            analysis = PaperAnalysis(
                paper_id=paper_id,
                summary_json=empty_summary.model_dump(),
                methodology_json={},
                contributions_json=[],
                claims_json=[]
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            return analysis

        # Group section context for LLM prompt
        sections_dict: Dict[str, List[str]] = {}
        section_page_map: Dict[str, int] = {}

        for chunk, sec in rows:
            sec_title = sec.title if sec else (chunk.metadata_json.get("section_title") if chunk.metadata_json else "Document Text")
            sec_type = sec.section_type.value if sec else "OTHER"
            
            if sec_title not in sections_dict:
                sections_dict[sec_title] = []
                section_page_map[sec_title] = chunk.page_number

            sections_dict[sec_title].append(chunk.text)

        # 3. Call LLM for 10-field structured summary extraction
        prompt_sections = []
        for sec_title, text_list in sections_dict.items():
            combined_sec_text = " ".join(text_list)[:1500]  # Limit length per section
            prompt_sections.append(f"Section [{sec_title}]:\n{combined_sec_text}")

        section_context_str = "\n\n".join(prompt_sections)[:6000]

        system_prompt = (
            "You are PaperLens, an expert scientific research summarizer.\n"
            "Analyze the paper's structured sections and extract ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "executive_summary": "...",\n'
            '  "problem_statement": "...",\n'
            '  "objective": "...",\n'
            '  "methodology_summary": "...",\n'
            '  "key_contributions": ["Contribution 1", "Contribution 2"],\n'
            '  "dataset": "...",\n'
            '  "experimental_setup": "...",\n'
            '  "key_results": "...",\n'
            '  "limitations": "...",\n'
            '  "conclusion": "..."\n'
            "}\n"
            "DO NOT include research-gap predictions or similar-paper recommendations."
        )

        user_prompt = f"Paper Title: {paper.title}\n\nSTRUCTURED SECTIONS:\n{section_context_str}"

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
                logger.warning(f"LLM API call for summarization failed ({e}). Using deterministic section fallback.")

        if raw_json_str:
            try:
                # Clean fences
                clean_str = raw_json_str.replace("```json", "").replace("```", "").strip()
                parsed_data = json.loads(clean_str)
                structured_summary = StructuredPaperSummary.model_validate(parsed_data)
            except Exception as parse_err:
                logger.warning(f"Failed to parse LLM structured summary output ({parse_err}). Falling back.")
                structured_summary = self._build_fallback_summary(paper.title, sections_dict)
        else:
            structured_summary = self._build_fallback_summary(paper.title, sections_dict)

        # 4. Generate internal claim lineage (claims_json with section & page tracking)
        claims_list: List[Dict] = []
        claim_counter = 1

        for sec_title, text_list in sections_dict.items():
            page_no = section_page_map.get(sec_title, 1)
            sample_text = " ".join(text_list)[:250]
            claims_list.append({
                "claim_id": f"claim_{claim_counter}",
                "claim_text": f"Fact from {sec_title}: {sample_text}",
                "section": sec_title,
                "page": page_no
            })
            claim_counter += 1

        # 5. Persist PaperAnalysis in PostgreSQL
        analysis = PaperAnalysis(
            paper_id=paper_id,
            summary_json=structured_summary.model_dump(),
            methodology_json={"summary": structured_summary.methodology_summary},
            contributions_json=structured_summary.key_contributions,
            claims_json=claims_list
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return analysis

    def _build_fallback_summary(self, title: str, sections_dict: Dict[str, List[str]]) -> StructuredPaperSummary:
        def get_sec_text(key_word: str) -> str:
            for title_name, text_list in sections_dict.items():
                if key_word.lower() in title_name.lower():
                    return " ".join(text_list)[:300]
            return f"Details extracted from research paper {title}."

        return StructuredPaperSummary(
            executive_summary=get_sec_text("abstract") or f"Executive summary of research paper: {title}.",
            problem_statement=get_sec_text("introduction") or "Research paper problem statement.",
            objective=get_sec_text("introduction") or "Primary research objective.",
            methodology_summary=get_sec_text("method") or "Proposed scientific methodology.",
            key_contributions=[
                f"Proposed novel approach in {title}.",
                "Demonstrated experimental performance across benchmarks."
            ],
            dataset=get_sec_text("data") or "Experimental dataset and benchmark evaluation corpora.",
            experimental_setup=get_sec_text("experiment") or "Experimental protocols and baselines.",
            key_results=get_sec_text("result") or "Quantitative results and performance metrics.",
            limitations=get_sec_text("limitation") or "Stated limitations and failure cases.",
            conclusion=get_sec_text("conclusion") or "Concluding remarks."
        )
