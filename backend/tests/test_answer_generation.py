import json
import uuid
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, QuestionType, SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.schemas.evidence import EvidencePackage, SelectedEvidenceItem
from app.services.answer_generation_service import AnswerGenerationService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.retrieval_strategy_service import StructureAwareRetrievalService
from tests.test_embedding_service import MockHTTPClient


class MockLLMHTTPClient:
    """Mock HTTPX client simulating OpenAI-compatible chat completions API without external network calls."""

    def __init__(self, mock_response_data: dict = None, return_malformed_first: bool = False):
        self.mock_response_data = mock_response_data or {
            "answer": "The proposed self-attention mechanism uses QKV dot product matrix multiplication.",
            "evidence_ids": ["ev_1"],
            "confidence": 0.92,
            "abstain": False
        }
        self.return_malformed_first = return_malformed_first
        self.call_count = 0

    async def post(self, url: str, json: dict = None, headers: dict = None):
        self.call_count += 1
        if self.return_malformed_first and self.call_count == 1:
            # Return malformed non-JSON output on first call
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "This is invalid non-JSON output."}}]
            })

        # Return valid JSON response
        content_str = json_module.dumps(self.mock_response_data)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content_str}}]
        })


import json as json_module


@pytest.mark.asyncio
async def test_llm_service_grounded_answer_mock():
    mock_client = MockLLMHTTPClient()
    llm_svc = LLMService(http_client=mock_client)

    ev_item = SelectedEvidenceItem(
        evidence_id="ev_1",
        chunk_id=uuid.uuid4(),
        page=4,
        section="2. Methodology",
        text="QKV matrix multiplication details.",
        retrieval_score=0.90
    )
    pkg = EvidencePackage(items=[ev_item], total_tokens=10, total_items=1, package_hash="abc")

    output = await llm_svc.generate_grounded_answer(
        question_text="How does self-attention work?",
        question_type=QuestionType.METHODOLOGY,
        evidence_package=pkg
    )

    assert output.abstain is False
    assert output.confidence == 0.92
    assert "ev_1" in output.evidence_ids
    assert "QKV dot product" in output.answer


@pytest.mark.asyncio
async def test_llm_service_repair_prompt_retry():
    # Return malformed text on 1st call, then valid response on 2nd call
    mock_client = MockLLMHTTPClient(return_malformed_first=True)
    llm_svc = LLMService(http_client=mock_client)

    ev_item = SelectedEvidenceItem(
        evidence_id="ev_1",
        chunk_id=uuid.uuid4(),
        page=1,
        section="1. Introduction",
        text="Intro text.",
        retrieval_score=0.85
    )
    pkg = EvidencePackage(items=[ev_item], total_tokens=5, total_items=1, package_hash="def")

    output = await llm_svc.generate_grounded_answer(
        question_text="What is this paper about?",
        question_type=QuestionType.GENERAL,
        evidence_package=pkg
    )

    # Must make 2 calls (1st failed, 2nd repaired successfully)
    assert mock_client.call_count == 2
    assert output.abstain is False
    assert output.confidence == 0.92


@pytest.mark.asyncio
async def test_llm_service_explicit_abstention():
    abstain_data = {
        "answer": "The supplied evidence does not state the hyperparameter batch size.",
        "evidence_ids": [],
        "confidence": 0.0,
        "abstain": True
    }
    mock_client = MockLLMHTTPClient(mock_response_data=abstain_data)
    llm_svc = LLMService(http_client=mock_client)

    pkg = EvidencePackage(items=[], total_tokens=0, total_items=0, package_hash="empty")

    output = await llm_svc.generate_grounded_answer(
        question_text="What hyperparameter batch size was used?",
        question_type=QuestionType.EXPERIMENT,
        evidence_package=pkg
    )

    assert output.abstain is True
    assert output.confidence == 0.0
    assert output.evidence_ids == []


@pytest.mark.asyncio
async def test_answer_generation_db_metadata_binding(
    client: AsyncClient,
    db_session: AsyncSession
):
    # Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "answer_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # Setup Paper with Page 5 and Section "3. Methodology"
    paper = Paper(workspace_id=workspace.id, title="Binding Paper", file_name="bind.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    sec = PaperSection(paper_id=paper.id, title="3. Methodology", normalized_title="methodology", section_type=SectionType.METHODOLOGY, page_start=5, page_end=5, order_index=0)
    db_session.add(sec)
    await db_session.flush()

    chunk_id = uuid.uuid4()
    c = PaperChunk(
        id=chunk_id,
        paper_id=paper.id,
        page_number=5,
        section_id=sec.id,
        chunk_index=0,
        text="Algorithm step computing matrix multiplication on page 5.",
        token_count=10,
        embedding=[0.1]*1536
    )
    db_session.add(c)
    await db_session.commit()

    # Setup Services with Mocks
    mock_emb_svc = EmbeddingService(http_client=MockHTTPClient(status_code=200))
    retrieval_svc = RetrievalService(embedding_service=mock_emb_svc)
    strategy_svc = StructureAwareRetrievalService(retrieval_service=retrieval_svc)
    mock_llm_client = MockLLMHTTPClient()
    mock_llm_svc = LLMService(http_client=mock_llm_client)

    ans_svc = AnswerGenerationService(
        llm_service=mock_llm_svc,
        retrieval_strategy_service=strategy_svc
    )

    # Run answer generation
    resp = await ans_svc.generate_answer_for_paper(
        paper_id=paper.id,
        question_text="How is matrix multiplication computed?",
        db=db_session
    )

    assert resp.abstain is False
    assert resp.confidence == 0.92
    assert len(resp.evidences) == 1

    # PROVE: Page and section metadata come strictly from DB records, NOT generated text
    bound_ev = resp.evidences[0]
    assert bound_ev.chunk_id == chunk_id
    assert bound_ev.page == 5             # Exact page from DB PaperChunk/PaperPage record
    assert bound_ev.section == "3. Methodology" # Exact title from DB PaperSection record
    assert bound_ev.text == "Algorithm step computing matrix multiplication on page 5."


@pytest.mark.asyncio
async def test_ask_paper_question_api_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "ask_api_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Ask API Paper", file_name="ask.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="Ask API chunk text", token_count=5, embedding=[0.1]*1536)
    db_session.add(c)
    await db_session.commit()

    # Call POST /api/v1/papers/{paper_id}/ask
    req_body = {
        "question_text": "What is the chunk text?",
        "mode": "STRUCTURE_AWARE_RAG"
    }
    resp = await client.post(f"/api/v1/papers/{paper.id}/ask", headers=headers, json=req_body)
    assert resp.status_code == 200
    data = resp.json()

    assert "answer" in data
    assert "evidence_ids" in data
    assert "evidences" in data
    assert "confidence" in data
    assert "abstain" in data
