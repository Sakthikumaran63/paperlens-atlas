import uuid
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ContributionType, PaperStatus, SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.services.contribution_extraction_service import ContributionExtractionService
from app.services.llm_service import LLMService
import json as json_module


class MockContributionHTTPClient:
    """Mock HTTP client simulating LLM key contribution extraction."""

    def __init__(self, chunk_id_str: str):
        self.chunk_id_str = chunk_id_str

    async def post(self, url: str, json: dict = None, headers: dict = None):
        contrib_data = {
            "contributions": [
                {
                    "text": "We propose a novel multi-head self-attention architecture that replaces recurrent networks.",
                    "contribution_type": "EXPLICIT",
                    "chunk_id": self.chunk_id_str
                },
                {
                    "text": "Achieved state-of-the-art BLEU score on WMT 2014 English-to-German translation task.",
                    "contribution_type": "INFERRED",
                    "chunk_id": self.chunk_id_str
                }
            ]
        }
        content_str = json_module.dumps(contrib_data)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content_str}}]
        })


@pytest.mark.asyncio
async def test_contribution_extraction_service_and_type_distinction(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "contrib_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Setup Paper with Introduction & Contribution Section
    paper = Paper(
        workspace_id=workspace.id,
        title="Contribution Extraction Paper",
        file_name="contrib.pdf",
        file_size=1024,
        status=PaperStatus.READY
    )
    db_session.add(paper)
    await db_session.flush()

    sec_intro = PaperSection(
        paper_id=paper.id, title="1. Introduction", normalized_title="introduction",
        section_type=SectionType.INTRODUCTION, page_start=2, page_end=2, order_index=0
    )
    db_session.add(sec_intro)
    await db_session.flush()

    chunk_id = uuid.uuid4()
    c = PaperChunk(
        id=chunk_id, paper_id=paper.id, page_number=2, section_id=sec_intro.id, chunk_index=0,
        text="Our main contributions are: 1. We propose multi-head self-attention. 2. We achieve SOTA performance.", token_count=15
    )
    db_session.add(c)
    await db_session.commit()

    # 3. Test ContributionExtractionService
    mock_llm = LLMService(http_client=MockContributionHTTPClient(str(chunk_id)))
    contrib_svc = ContributionExtractionService(llm_service=mock_llm)

    resp = await contrib_svc.extract_contributions(paper_id=paper.id, db=db_session)

    assert resp is not None
    assert len(resp.contributions) == 2

    # Verify EXPLICIT vs INFERRED distinction
    c1 = resp.contributions[0]
    assert c1.contribution_type == ContributionType.EXPLICIT
    assert "multi-head self-attention" in c1.text
    assert c1.evidence.page == 2
    assert c1.evidence.section == "1. Introduction"
    assert c1.evidence.chunk_id == chunk_id

    c2 = resp.contributions[1]
    assert c2.contribution_type == ContributionType.INFERRED
    assert "BLEU score" in c2.text
    assert c2.evidence.chunk_id == chunk_id


@pytest.mark.asyncio
async def test_get_paper_contributions_api_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "contrib_api_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Contrib API Paper", file_name="c_api.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="Sample contribution text", token_count=5)
    db_session.add(c)
    await db_session.commit()

    # Call GET /api/v1/papers/{paper_id}/contributions
    resp = await client.get(f"/api/v1/papers/{paper.id}/contributions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "contributions" in data
    assert isinstance(data["contributions"], list)
    if len(data["contributions"]) > 0:
        contrib_obj = data["contributions"][0]
        assert "text" in contrib_obj
        assert "contribution_type" in contrib_obj
        assert "evidence" in contrib_obj
        assert "page" in contrib_obj["evidence"]
        assert "section" in contrib_obj["evidence"]
        assert "chunk_id" in contrib_obj["evidence"]
