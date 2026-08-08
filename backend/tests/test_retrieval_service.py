import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from tests.test_embedding_service import MockHTTPClient


@pytest.mark.asyncio
async def test_retrieval_service_semantic_search_and_section_filter(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "retrieval_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    # Fetch default workspace
    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Setup Paper A
    paper_a = Paper(
        workspace_id=workspace.id,
        title="Attention Mechanism Paper",
        file_name="paper_a.pdf",
        file_size=1024,
        status=PaperStatus.READY
    )
    db_session.add(paper_a)
    await db_session.flush()

    # Sections for Paper A
    sec_intro = PaperSection(
        paper_id=paper_a.id,
        title="1. Introduction",
        normalized_title="introduction",
        section_type=SectionType.INTRODUCTION,
        page_start=1,
        page_end=1,
        order_index=0,
        confidence=0.98
    )
    sec_method = PaperSection(
        paper_id=paper_a.id,
        title="2. Methodology",
        normalized_title="methodology",
        section_type=SectionType.METHODOLOGY,
        page_start=2,
        page_end=2,
        order_index=1,
        confidence=0.98
    )
    db_session.add_all([sec_intro, sec_method])
    await db_session.flush()

    # Chunks for Paper A with deterministic mock vector embeddings (1536 dims)
    # Vector for Intro chunk matches query mock index 0 [0.1]*1536
    # Vector for Method chunk matches query mock index 1 [1.1]*1536
    vec_intro = [0.1] * 1536
    vec_method = [1.1] * 1536

    chunk_a1 = PaperChunk(
        paper_id=paper_a.id,
        page_number=1,
        section_id=sec_intro.id,
        chunk_index=0,
        text="Introduction text explaining neural self-attention.",
        token_count=10,
        embedding=vec_intro,
        metadata_json={"section_type": "INTRODUCTION", "section_title": "1. Introduction"}
    )
    chunk_a2 = PaperChunk(
        paper_id=paper_a.id,
        page_number=2,
        section_id=sec_method.id,
        chunk_index=1,
        text="Methodology algorithm computing QKV matrix multiplication.",
        token_count=12,
        embedding=vec_method,
        metadata_json={"section_type": "METHODOLOGY", "section_title": "2. Methodology"}
    )
    db_session.add_all([chunk_a1, chunk_a2])
    await db_session.commit()

    # 3. Test RetrievalService.retrieve using MockHTTPClient
    mock_emb_svc = EmbeddingService(http_client=MockHTTPClient(status_code=200))
    retrieval_svc = RetrievalService(embedding_service=mock_emb_svc)

    candidates = await retrieval_svc.retrieve(
        query="How is QKV matrix multiplication computed?",
        paper_id=paper_a.id,
        top_k=5,
        workspace_id=workspace.id,
        db=db_session
    )

    assert len(candidates) >= 1
    # Check mandatory candidate attributes
    top_cand = candidates[0]
    assert top_cand.paper_id == paper_a.id
    assert top_cand.chunk_id in [chunk_a1.id, chunk_a2.id]
    assert top_cand.page_number in [1, 2]
    assert top_cand.section_id in [sec_intro.id, sec_method.id]
    assert top_cand.section_type in [SectionType.INTRODUCTION, SectionType.METHODOLOGY]
    assert top_cand.section_title != ""
    assert top_cand.text != ""
    assert top_cand.similarity_score > 0.0

    # 4. Test retrieve_by_section (filtering strictly to METHODOLOGY)
    method_candidates = await retrieval_svc.retrieve_by_section(
        query="Explain algorithm",
        paper_id=paper_a.id,
        section_type=SectionType.METHODOLOGY,
        top_k=5,
        workspace_id=workspace.id,
        db=db_session
    )

    assert len(method_candidates) == 1
    assert method_candidates[0].section_type == SectionType.METHODOLOGY
    assert method_candidates[0].section_id == sec_method.id
    assert "Methodology algorithm" in method_candidates[0].text


@pytest.mark.asyncio
async def test_paper_isolation_in_retrieval(
    client: AsyncClient,
    db_session: AsyncSession
):
    # Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "isolation_retrieval@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # Create Paper 1 & Paper 2
    paper_1 = Paper(workspace_id=workspace.id, title="Paper 1", file_name="p1.pdf", file_size=100, status=PaperStatus.READY)
    paper_2 = Paper(workspace_id=workspace.id, title="Paper 2", file_name="p2.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add_all([paper_1, paper_2])
    await db_session.flush()

    vec_shared = [0.5] * 1536
    c1 = PaperChunk(paper_id=paper_1.id, page_number=1, chunk_index=0, text="Secret Paper 1 text", token_count=5, embedding=vec_shared)
    c2 = PaperChunk(paper_id=paper_2.id, page_number=1, chunk_index=0, text="Secret Paper 2 text", token_count=5, embedding=vec_shared)
    db_session.add_all([c1, c2])
    await db_session.commit()

    mock_emb_svc = EmbeddingService(http_client=MockHTTPClient(status_code=200))
    retrieval_svc = RetrievalService(embedding_service=mock_emb_svc)

    # Query Paper 1 -> MUST NEVER return chunks from Paper 2
    candidates_1 = await retrieval_svc.retrieve(query="Secret text", paper_id=paper_1.id, top_k=10, workspace_id=workspace.id, db=db_session)
    assert len(candidates_1) == 1
    assert candidates_1[0].paper_id == paper_1.id
    assert candidates_1[0].chunk_id == c1.id
    assert "Paper 1" in candidates_1[0].text
    assert "Paper 2" not in candidates_1[0].text

    # Query Paper 2 -> MUST NEVER return chunks from Paper 1
    candidates_2 = await retrieval_svc.retrieve(query="Secret text", paper_id=paper_2.id, top_k=10, workspace_id=workspace.id, db=db_session)
    assert len(candidates_2) == 1
    assert candidates_2[0].paper_id == paper_2.id
    assert candidates_2[0].chunk_id == c2.id
    assert "Paper 2" in candidates_2[0].text
    assert "Paper 1" not in candidates_2[0].text


@pytest.mark.asyncio
async def test_retrieval_api_endpoint(
    client: AsyncClient,
    db_session: AsyncSession
):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "endpoint_retrieval@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="API Paper", file_name="api.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="API chunk text", token_count=5, embedding=[0.2]*1536)
    db_session.add(c)
    await db_session.commit()

    # Call POST /api/v1/papers/{paper_id}/retrieve
    req_body = {
        "query": "API chunk search",
        "top_k": 3
    }
    resp = await client.post(f"/api/v1/papers/{paper.id}/retrieve", headers=headers, json=req_body)
    assert resp.status_code == 200
    candidates = resp.json()
    assert isinstance(candidates, list)
    if len(candidates) > 0:
        assert candidates[0]["paper_id"] == str(paper.id)
        assert candidates[0]["chunk_id"] == str(c.id)
