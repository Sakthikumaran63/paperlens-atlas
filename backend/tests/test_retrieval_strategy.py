import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, RetrievalMode, SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.retrieval_strategy_service import StructureAwareRetrievalService
from tests.test_embedding_service import MockHTTPClient


@pytest.mark.asyncio
async def test_baseline_rag_vs_structure_aware_rag_comparative_ranking(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "strategy_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Setup Paper
    paper = Paper(
        workspace_id=workspace.id,
        title="Comparative RAG Strategy Paper",
        file_name="rag_test.pdf",
        file_size=1024,
        status=PaperStatus.READY
    )
    db_session.add(paper)
    await db_session.flush()

    # Sections: INTRODUCTION vs DATASET
    sec_intro = PaperSection(
        paper_id=paper.id,
        title="1. Introduction",
        normalized_title="introduction",
        section_type=SectionType.INTRODUCTION,
        page_start=1,
        page_end=1,
        order_index=0,
        confidence=0.98
    )
    sec_dataset = PaperSection(
        paper_id=paper.id,
        title="2. Dataset and Benchmarks",
        normalized_title="dataset and benchmarks",
        section_type=SectionType.DATASET,
        page_start=2,
        page_end=2,
        order_index=1,
        confidence=0.95
    )
    db_session.add_all([sec_intro, sec_dataset])
    await db_session.flush()

    # Create mock vectors where Intro chunk has slightly higher semantic similarity [0.9]*1536
    # and Dataset chunk has slightly lower semantic similarity [0.8]*1536
    vec_intro = [0.9] * 1536
    vec_dataset = [0.8] * 1536

    chunk_intro = PaperChunk(
        paper_id=paper.id,
        page_number=1,
        section_id=sec_intro.id,
        chunk_index=0,
        text="Introduction mentioning generic training data overview.",
        token_count=10,
        embedding=vec_intro,
        metadata_json={"section_type": "INTRODUCTION", "section_title": "1. Introduction"}
    )
    chunk_dataset = PaperChunk(
        paper_id=paper.id,
        page_number=2,
        section_id=sec_dataset.id,
        chunk_index=1,
        text="We benchmark on ImageNet and COCO datasets with 100k samples.",
        token_count=12,
        embedding=vec_dataset,
        metadata_json={"section_type": "DATASET", "section_title": "2. Dataset and Benchmarks"}
    )
    db_session.add_all([chunk_intro, chunk_dataset])
    await db_session.commit()

    # 3. Setup Strategy Service with Mock HTTP client
    mock_emb_svc = EmbeddingService(http_client=MockHTTPClient(status_code=200))
    retrieval_base_svc = RetrievalService(embedding_service=mock_emb_svc)
    strategy_svc = StructureAwareRetrievalService(retrieval_service=retrieval_base_svc)

    query = "Which datasets were used for training?"

    # --- TEST MODE 1: BASELINE_RAG (semantic similarity only) ---
    baseline_candidates = await strategy_svc.retrieve_pipeline(
        query=query,
        paper_id=paper.id,
        top_k=2,
        mode=RetrievalMode.BASELINE_RAG,
        workspace_id=workspace.id,
        db=db_session
    )

    assert len(baseline_candidates) == 2
    # In BASELINE_RAG, final_score == semantic_score
    for cand in baseline_candidates:
        assert cand.final_score == cand.semantic_score

    # --- TEST MODE 2: STRUCTURE_AWARE_RAG (combined weighted scoring) ---
    structure_candidates = await strategy_svc.retrieve_pipeline(
        query=query,
        paper_id=paper.id,
        top_k=2,
        mode=RetrievalMode.STRUCTURE_AWARE_RAG,
        workspace_id=workspace.id,
        db=db_session
    )

    assert len(structure_candidates) == 2
    top_candidate = structure_candidates[0]

    # PROVE: Under STRUCTURE_AWARE_RAG, the DATASET section chunk gets higher ranking boost
    assert top_candidate.section_type == SectionType.DATASET
    assert top_candidate.chunk_id == chunk_dataset.id
    assert top_candidate.section_score == 1.0  # 1st priority section match
    assert top_candidate.final_score > top_candidate.semantic_score


def test_score_breakdowns_format():
    # Verify score breakdown fields
    from app.schemas.retrieval import RetrievedChunkCandidate
    cand = RetrievedChunkCandidate(
        chunk_id=uuid.uuid4(),
        paper_id=uuid.uuid4(),
        page_number=3,
        page=3,
        section_id=uuid.uuid4(),
        section_type=SectionType.DATASET,
        section_title="3. Dataset",
        section="3. Dataset",
        text="Dataset sample details.",
        semantic_score=0.85,
        section_score=1.0,
        keyword_score=0.50,
        final_score=0.835,
        similarity_score=0.85
    )
    assert cand.semantic_score == 0.85
    assert cand.section_score == 1.0
    assert cand.keyword_score == 0.50
    assert cand.final_score == 0.835
    assert cand.page == 3
    assert cand.section == "3. Dataset"
    assert cand.text == "Dataset sample details."


@pytest.mark.asyncio
async def test_retrieval_api_endpoint_modes(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "mode_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="API Mode Paper", file_name="mode.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="Sample text", token_count=5, embedding=[0.1]*1536)
    db_session.add(c)
    await db_session.commit()

    # Test BASELINE_RAG API request
    req_baseline = {"query": "Sample search", "top_k": 1, "mode": "BASELINE_RAG"}
    resp_b = await client.post(f"/api/v1/papers/{paper.id}/retrieve", headers=headers, json=req_baseline)
    assert resp_b.status_code == 200
    res_b_data = resp_b.json()
    assert len(res_b_data) > 0
    assert "semantic_score" in res_b_data[0]
    assert "final_score" in res_b_data[0]
    assert "page" in res_b_data[0]
    assert "section" in res_b_data[0]

    # Test STRUCTURE_AWARE_RAG API request
    req_struct = {"query": "Sample search", "top_k": 1, "mode": "STRUCTURE_AWARE_RAG"}
    resp_s = await client.post(f"/api/v1/papers/{paper.id}/retrieve", headers=headers, json=req_struct)
    assert resp_s.status_code == 200
    res_s_data = resp_s.json()
    assert len(res_s_data) > 0
    assert "section_score" in res_s_data[0]
    assert "keyword_score" in res_s_data[0]
