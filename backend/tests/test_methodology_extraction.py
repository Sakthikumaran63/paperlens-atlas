import uuid
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.services.llm_service import LLMService
from app.services.methodology_extraction_service import MethodologyExtractionService
import json as json_module


class MockMethodologyHTTPClient:
    """Mock HTTP client simulating LLM methodology extraction."""

    async def post(self, url: str, json: dict = None, headers: dict = None):
        methodology_data = {
            "approach": "Deep learning sequence-to-sequence transformation.",
            "model": "Transformer encoder-decoder with multi-head self-attention.",
            "algorithms": "Scaled dot-product attention calculation.",
            "dataset": "WMT 2014 English-to-German translation dataset.",
            "preprocessing": "Not specified in the paper",
            "training": "Adam optimizer with beta1=0.9, beta2=0.98, and warmup learning rate schedule.",
            "experimental_setup": "8 NVIDIA P100 GPUs trained for 100,000 steps.",
            "metrics": ["BLEU score", "Perplexity"]
        }
        content_str = json_module.dumps(methodology_data)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content_str}}]
        })


@pytest.mark.asyncio
async def test_methodology_extraction_service_and_source_lineage(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "methodology_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Setup Paper with Methodology Section
    paper = Paper(
        workspace_id=workspace.id,
        title="Methodology Extraction Paper",
        file_name="meth.pdf",
        file_size=1024,
        status=PaperStatus.READY
    )
    db_session.add(paper)
    await db_session.flush()

    sec_method = PaperSection(
        paper_id=paper.id, title="3. Methodology", normalized_title="methodology",
        section_type=SectionType.METHODOLOGY, page_start=4, page_end=4, order_index=0
    )
    db_session.add(sec_method)
    await db_session.flush()

    c = PaperChunk(
        paper_id=paper.id, page_number=4, section_id=sec_method.id, chunk_index=0,
        text="The Transformer model uses multi-head self-attention trained on 8 GPUs.", token_count=10
    )
    db_session.add(c)
    await db_session.commit()

    # 3. Test MethodologyExtractionService
    mock_llm = LLMService(http_client=MockMethodologyHTTPClient())
    meth_svc = MethodologyExtractionService(llm_service=mock_llm)

    resp = await meth_svc.extract_methodology(paper_id=paper.id, db=db_session)

    assert resp is not None
    assert resp.approach == "Deep learning sequence-to-sequence transformation."
    assert resp.model == "Transformer encoder-decoder with multi-head self-attention."
    assert resp.algorithms == "Scaled dot-product attention calculation."
    assert resp.dataset == "WMT 2014 English-to-German translation dataset."
    assert resp.preprocessing == "Not specified in the paper"  # Non-inference fallback
    assert resp.training == "Adam optimizer with beta1=0.9, beta2=0.98, and warmup learning rate schedule."
    assert resp.experimental_setup == "8 NVIDIA P100 GPUs trained for 100,000 steps."
    assert "BLEU score" in resp.metrics

    # Verify source lineage on evidence items
    assert len(resp.evidence) >= 1
    ev = resp.evidence[0]
    assert ev.section == "3. Methodology"
    assert ev.page == 4
    assert "Transformer model" in ev.text


@pytest.mark.asyncio
async def test_get_paper_methodology_api_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "meth_api_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Meth API Paper", file_name="m_api.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="Sample methodology text", token_count=5)
    db_session.add(c)
    await db_session.commit()

    # Call GET /api/v1/papers/{paper_id}/methodology
    resp = await client.get(f"/api/v1/papers/{paper.id}/methodology", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "approach" in data
    assert "model" in data
    assert "algorithms" in data
    assert "dataset" in data
    assert "preprocessing" in data
    assert "training" in data
    assert "experimental_setup" in data
    assert "metrics" in data
    assert "evidence" in data
