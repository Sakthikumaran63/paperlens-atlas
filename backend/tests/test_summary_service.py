import uuid
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, SectionType
from app.models.paper import Paper
from app.models.paper_analysis import PaperAnalysis
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.services.llm_service import LLMService
from app.services.summary_service import SummaryService
from tests.test_answer_generation import MockLLMHTTPClient
import json as json_module


class MockSummaryHTTPClient:
    """Mock HTTP client simulating LLM structured summary extraction."""

    async def post(self, url: str, json: dict = None, headers: dict = None):
        summary_data = {
            "executive_summary": "Executive overview of multi-head self-attention.",
            "problem_statement": "High computational cost of recurrent sequence models.",
            "objective": "Design an architecture relying entirely on attention.",
            "methodology_summary": "Transformer model utilizing multi-head dot product attention.",
            "key_contributions": ["Multi-head attention mechanism", "Parallelizable architecture"],
            "dataset": "WMT 2014 English-to-German and English-to-French translation datasets.",
            "experimental_setup": "8 NVIDIA P100 GPUs trained for 3.5 days using Adam optimizer.",
            "key_results": "Achieved 28.4 BLEU score outperforming existing SOTA models.",
            "limitations": "Quadratic memory complexity with respect to sequence length.",
            "conclusion": "Attention mechanisms replace recurrent networks effectively."
        }
        content_str = json_module.dumps(summary_data)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content_str}}]
        })


@pytest.mark.asyncio
async def test_summary_service_10_field_generation_and_claim_lineage(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "summary_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Setup Paper with Section structure
    paper = Paper(
        workspace_id=workspace.id,
        title="Attention Is All You Need",
        file_name="attention.pdf",
        file_size=1024,
        status=PaperStatus.READY
    )
    db_session.add(paper)
    await db_session.flush()

    sec_intro = PaperSection(
        paper_id=paper.id, title="1. Introduction", normalized_title="introduction",
        section_type=SectionType.INTRODUCTION, page_start=1, page_end=1, order_index=0
    )
    sec_method = PaperSection(
        paper_id=paper.id, title="3. Model Architecture", normalized_title="model architecture",
        section_type=SectionType.METHODOLOGY, page_start=3, page_end=3, order_index=1
    )
    db_session.add_all([sec_intro, sec_method])
    await db_session.flush()

    c1 = PaperChunk(paper_id=paper.id, page_number=1, section_id=sec_intro.id, chunk_index=0, text="Intro text on attention.", token_count=5)
    c2 = PaperChunk(paper_id=paper.id, page_number=3, section_id=sec_method.id, chunk_index=1, text="Method text on multi-head attention.", token_count=5)
    db_session.add_all([c1, c2])
    await db_session.commit()

    # 3. Test SummaryService
    mock_llm = LLMService(http_client=MockSummaryHTTPClient())
    summary_svc = SummaryService(llm_service=mock_llm)

    analysis = await summary_svc.generate_structured_analysis(paper_id=paper.id, db=db_session)

    assert analysis is not None
    assert analysis.paper_id == paper.id

    # Verify presence of all 10 structured fields
    s_json = analysis.summary_json
    assert s_json["executive_summary"] == "Executive overview of multi-head self-attention."
    assert s_json["problem_statement"] == "High computational cost of recurrent sequence models."
    assert s_json["objective"] == "Design an architecture relying entirely on attention."
    assert s_json["methodology_summary"] == "Transformer model utilizing multi-head dot product attention."
    assert len(s_json["key_contributions"]) == 2
    assert s_json["dataset"] == "WMT 2014 English-to-German and English-to-French translation datasets."
    assert s_json["experimental_setup"] == "8 NVIDIA P100 GPUs trained for 3.5 days using Adam optimizer."
    assert s_json["key_results"] == "Achieved 28.4 BLEU score outperforming existing SOTA models."
    assert s_json["limitations"] == "Quadratic memory complexity with respect to sequence length."
    assert s_json["conclusion"] == "Attention mechanisms replace recurrent networks effectively."

    # Verify internal claim source lineage (claims_json)
    assert len(analysis.claims_json) >= 2
    claim_1 = analysis.claims_json[0]
    assert "section" in claim_1
    assert "page" in claim_1
    assert claim_1["page"] in [1, 3]


@pytest.mark.asyncio
async def test_get_paper_analysis_api_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "analysis_api_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Analysis Paper", file_name="ana.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="Analysis sample text", token_count=5)
    db_session.add(c)
    await db_session.commit()

    # Call GET /api/v1/papers/{paper_id}/analysis
    resp = await client.get(f"/api/v1/papers/{paper.id}/analysis", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "id" in data
    assert data["paper_id"] == str(paper.id)
    assert "summary" in data
    summary = data["summary"]

    assert "executive_summary" in summary
    assert "problem_statement" in summary
    assert "objective" in summary
    assert "methodology_summary" in summary
    assert "key_contributions" in summary
    assert "dataset" in summary
    assert "experimental_setup" in summary
    assert "key_results" in summary
    assert "limitations" in summary
    assert "conclusion" in summary
    assert "claims" in data
