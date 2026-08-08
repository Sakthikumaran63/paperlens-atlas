import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.workspace import Workspace
from app.schemas.retrieval import RetrievedChunkCandidate
from app.services.evidence_selection_service import (
    EvidenceSelectionConfig,
    EvidenceSelectionService,
)


def create_mock_candidate(
    text: str,
    score: float,
    page: int = 1,
    section: str = "1. Introduction",
    chunk_id: uuid.UUID = None
) -> RetrievedChunkCandidate:
    cid = chunk_id or uuid.uuid4()
    pid = uuid.uuid4()
    return RetrievedChunkCandidate(
        chunk_id=cid,
        paper_id=pid,
        page_number=page,
        page=page,
        section_id=uuid.uuid4(),
        section_type=SectionType.INTRODUCTION,
        section_title=section,
        section=section,
        text=text,
        semantic_score=score,
        section_score=1.0,
        keyword_score=0.5,
        final_score=score,
        similarity_score=score
    )


def test_evidence_selection_duplicate_removal():
    svc = EvidenceSelectionService()

    # Candidate 1 and Candidate 2 have near-identical text (> 85% overlap)
    text1 = "This paper proposes a novel self-attention mechanism for neural machine translation."
    text2 = "This paper proposes a novel self-attention mechanism for neural machine translation in NLP."
    text3 = "We conduct comprehensive experiments on ImageNet benchmark datasets."

    c1 = create_mock_candidate(text1, score=0.95)
    c2 = create_mock_candidate(text2, score=0.90)
    c3 = create_mock_candidate(text3, score=0.80)

    config = EvidenceSelectionConfig(dedup_threshold=0.80, max_context_tokens=1000)
    package = svc.select_evidence([c1, c2, c3], config=config)

    # c2 should be removed as near-duplicate of c1
    assert package.total_items == 2
    selected_texts = [it.text for it in package.items]
    assert text1 in selected_texts
    assert text2 not in selected_texts
    assert text3 in selected_texts


def test_evidence_selection_context_limits():
    svc = EvidenceSelectionService()

    # Create 3 distinct candidates with long texts (~15 tokens each)
    t1 = "First chunk paragraph text with substantial detailed context information for testing budget limits."
    t2 = "Second chunk paragraph text detailing experimental methodologies and model hyperparameter settings."
    t3 = "Third chunk paragraph text presenting quantitative metric comparisons across all benchmark datasets."

    c1 = create_mock_candidate(t1, score=0.90)
    c2 = create_mock_candidate(t2, score=0.85)
    c3 = create_mock_candidate(t3, score=0.80)

    # Set strict token limit of 25 tokens -> Should only accept c1
    config = EvidenceSelectionConfig(max_context_tokens=25, dedup_threshold=0.90)
    package = svc.select_evidence([c1, c2, c3], config=config)

    assert package.total_items == 1
    assert package.items[0].text == t1
    assert package.total_tokens <= 25


def test_evidence_selection_page_section_and_text_immutability():
    svc = EvidenceSelectionService()

    c_id = uuid.uuid4()
    exact_text = "Exact un-mutated scientific text string preserving exact phrasing and syntax."
    page_no = 7
    section_name = "4. Experimental Results"

    cand = create_mock_candidate(text=exact_text, score=0.92, page=page_no, section=section_name, chunk_id=c_id)
    package = svc.select_evidence([cand])

    assert package.total_items == 1
    item = package.items[0]

    # Verify exact preservation
    assert item.chunk_id == c_id
    assert item.page == page_no
    assert item.section == section_name
    assert item.text == exact_text  # Immutable check
    assert item.retrieval_score == 0.92
    assert item.evidence_id == "ev_1"


def test_evidence_selection_auditability():
    svc = EvidenceSelectionService()

    cand1 = create_mock_candidate("Scientific evidence chunk 1 text.", score=0.88)
    cand2 = create_mock_candidate("Scientific evidence chunk 2 text.", score=0.78)

    package1 = svc.select_evidence([cand1, cand2])
    package2 = svc.select_evidence([cand1, cand2])

    # SHA256 audit hash must be deterministic and non-empty
    assert len(package1.package_hash) == 64
    assert package1.package_hash == package2.package_hash


@pytest.mark.asyncio
async def test_evidence_api_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "evidence_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Evidence Paper", file_name="ev.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    sec = PaperSection(paper_id=paper.id, title="2. Methods", normalized_title="methods", section_type=SectionType.METHODOLOGY, page_start=2, page_end=2, order_index=0)
    db_session.add(sec)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=2, section_id=sec.id, chunk_index=0, text="Evidence API test text", token_count=5, embedding=[0.1]*1536)
    db_session.add(c)
    await db_session.commit()

    # Call POST /api/v1/papers/{paper_id}/evidence
    req_body = {"query": "Evidence API search", "top_k": 3}
    resp = await client.post(f"/api/v1/papers/{paper.id}/evidence", headers=headers, json=req_body)
    assert resp.status_code == 200
    pkg_data = resp.json()

    assert "items" in pkg_data
    assert "total_tokens" in pkg_data
    assert "total_items" in pkg_data
    assert "package_hash" in pkg_data
    if pkg_data["total_items"] > 0:
        item = pkg_data["items"][0]
        assert item["page"] == 2
        assert item["section"] == "2. Methods"
        assert item["text"] == "Evidence API test text"
        assert item["retrieval_score"] > 0.0
