import json
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
from app.schemas.evidence import EvidencePackage, SelectedEvidenceItem
from app.services.answer_generation_service import AnswerGenerationService
from app.services.embedding_service import EmbeddingService
from app.services.evidence_verification_service import EvidenceVerificationService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.retrieval_strategy_service import StructureAwareRetrievalService
from tests.test_answer_generation import MockLLMHTTPClient
from tests.test_embedding_service import MockHTTPClient


class MockVerificationHTTPClient:
    """Mock HTTP client simulating Evidence Verification LLM API calls."""
    def __init__(self, support_score: float = 0.95, claims: list = None):
        self.support_score = support_score
        self.claims = claims or []

    async def post(self, url: str, json: dict = None, headers: dict = None):
        res_data = {
            "support_score": self.support_score,
            "unsupported_claims": self.claims
        }
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json_module.dumps(res_data)}}]
        })


import json as json_module


@pytest.mark.asyncio
async def test_evidence_verification_fully_supported():
    mock_client = MockVerificationHTTPClient(support_score=0.92, claims=[])
    ver_svc = EvidenceVerificationService(http_client=mock_client)

    ev = SelectedEvidenceItem(
        evidence_id="ev_1",
        chunk_id=uuid.uuid4(),
        page=2,
        section="2. Methodology",
        text="The model uses multi-head self-attention with 8 attention heads.",
        retrieval_score=0.90
    )
    pkg = EvidencePackage(items=[ev], total_tokens=10, total_items=1, package_hash="a")

    res = await ver_svc.verify_answer(
        question_text="How many attention heads are used?",
        candidate_answer="The model uses 8 attention heads.",
        evidence_package=pkg,
        threshold=0.70
    )

    assert res.supported is True
    assert res.support_score == 0.92
    assert res.unsupported_claims == []


@pytest.mark.asyncio
async def test_evidence_verification_partially_supported():
    # Support score 0.45 (< 0.70 threshold) with unsupported claims
    claims = ["Claim about 100x speedup is unsupported by methodology text."]
    mock_client = MockVerificationHTTPClient(support_score=0.45, claims=claims)
    ver_svc = EvidenceVerificationService(http_client=mock_client)

    ev = SelectedEvidenceItem(
        evidence_id="ev_1",
        chunk_id=uuid.uuid4(),
        page=2,
        section="2. Methodology",
        text="The model achieves moderate acceleration.",
        retrieval_score=0.75
    )
    pkg = EvidencePackage(items=[ev], total_tokens=5, total_items=1, package_hash="b")

    res = await ver_svc.verify_answer(
        question_text="What speedup is achieved?",
        candidate_answer="The model achieves a 100x speedup over baselines.",
        evidence_package=pkg,
        threshold=0.70
    )

    assert res.supported is False
    assert res.support_score == 0.45
    assert len(res.unsupported_claims) == 1
    assert "100x speedup" in res.unsupported_claims[0]


@pytest.mark.asyncio
async def test_evidence_verification_unsupported_answer_refusal_override(
    client: AsyncClient,
    db_session: AsyncSession
):
    # Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "refusal_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Refusal Paper", file_name="ref.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    sec = PaperSection(paper_id=paper.id, title="1. Introduction", normalized_title="introduction", section_type=SectionType.INTRODUCTION, page_start=1, page_end=1, order_index=0)
    db_session.add(sec)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, section_id=sec.id, chunk_index=0, text="General intro text.", token_count=5, embedding=[0.1]*1536)
    db_session.add(c)
    await db_session.commit()

    # Mocks
    mock_emb_svc = EmbeddingService(http_client=MockHTTPClient(status_code=200))
    retrieval_svc = RetrievalService(embedding_service=mock_emb_svc)
    strategy_svc = StructureAwareRetrievalService(retrieval_service=retrieval_svc)

    # LLM outputs a candidate answer, but Verification Service returns support_score=0.30 (< 0.70)
    candidate_answer_data = {
        "answer": "Unfounded hallucinated claim about medical diagnostic performance.",
        "evidence_ids": ["ev_1"],
        "confidence": 0.80,
        "abstain": False
    }
    mock_llm = LLMService(http_client=MockLLMHTTPClient(mock_response_data=candidate_answer_data))
    mock_ver = EvidenceVerificationService(http_client=MockVerificationHTTPClient(support_score=0.30, claims=["Medical claims unsupported."]))

    ans_svc = AnswerGenerationService(
        llm_service=mock_llm,
        retrieval_strategy_service=strategy_svc,
        evidence_verification_service=mock_ver
    )

    resp = await ans_svc.generate_answer_for_paper(
        paper_id=paper.id,
        question_text="What are the clinical trial results?",
        db=db_session
    )

    # MUST REFUSE answer and return EXACT statement
    EXPECTED_REFUSAL = "I couldn't find enough information in the uploaded paper to answer this reliably."
    assert resp.answer == EXPECTED_REFUSAL
    assert resp.supported is False
    assert resp.abstain is True
    assert resp.support_score == 0.30
    assert len(resp.searched_sections) > 0
    assert resp.evidence_count >= 1
    assert resp.abstention_reason is not None


@pytest.mark.asyncio
async def test_evidence_verification_completely_unrelated_question(
    client: AsyncClient,
    db_session: AsyncSession
):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "unrelated_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Unrelated Paper", file_name="unrelated.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    # Paper contains computer science chunk
    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="Convolutional neural network image classification.", token_count=5, embedding=[0.1]*1536)
    db_session.add(c)
    await db_session.commit()

    # Query completely unrelated question (e.g. recipe / gardening)
    mock_emb_svc = EmbeddingService(http_client=MockHTTPClient(status_code=200))
    retrieval_svc = RetrievalService(embedding_service=mock_emb_svc)
    strategy_svc = StructureAwareRetrievalService(retrieval_service=retrieval_svc)

    abstain_llm_data = {
        "answer": "Insufficient evidence.",
        "evidence_ids": [],
        "confidence": 0.0,
        "abstain": True
    }
    mock_llm = LLMService(http_client=MockLLMHTTPClient(mock_response_data=abstain_llm_data))
    ver_svc = EvidenceVerificationService(http_client=MockVerificationHTTPClient(support_score=0.0, claims=["Unrelated domain."]))

    ans_svc = AnswerGenerationService(
        llm_service=mock_llm,
        retrieval_strategy_service=strategy_svc,
        evidence_verification_service=ver_svc
    )

    resp = await ans_svc.generate_answer_for_paper(
        paper_id=paper.id,
        question_text="How do you make a chocolate cake?",
        db=db_session
    )

    assert resp.answer == "I couldn't find enough information in the uploaded paper to answer this reliably."
    assert resp.supported is False
    assert resp.abstain is True
    assert resp.support_score == 0.0
