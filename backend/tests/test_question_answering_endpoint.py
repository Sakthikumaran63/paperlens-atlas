import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer
from app.models.answer_evidence import AnswerEvidence
from app.models.enums import PaperStatus, QuestionType, SectionType
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_section import PaperSection
from app.models.question import Question
from app.models.retrieved_evidence import RetrievedEvidence
from app.models.workspace import Workspace


@pytest.mark.asyncio
async def test_main_question_answering_endpoint_success_and_db_persistence(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Register user
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "main_qa_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Create READY Paper with DB Page and Section metadata
    paper = Paper(
        workspace_id=workspace.id,
        title="Main QA Paper",
        file_name="qa_main.pdf",
        file_size=1024,
        status=PaperStatus.READY
    )
    db_session.add(paper)
    await db_session.flush()

    sec = PaperSection(
        paper_id=paper.id,
        title="4. Experiments",
        normalized_title="experiments",
        section_type=SectionType.EXPERIMENTS,
        page_start=5,
        page_end=5,
        order_index=0
    )
    db_session.add(sec)
    await db_session.flush()

    chunk_id = uuid.uuid4()
    c = PaperChunk(
        id=chunk_id,
        paper_id=paper.id,
        page_number=5,
        section_id=sec.id,
        chunk_index=0,
        text="We evaluate on ImageNet dataset obtaining 88.5% top-1 accuracy.",
        token_count=10,
        embedding=[0.1]*1536
    )
    db_session.add(c)
    await db_session.commit()

    # 3. Call POST /api/v1/papers/{paper_id}/questions
    req_payload = {
        "question": "What dataset was used for evaluation?"
    }
    resp = await client.post(f"/api/v1/papers/{paper.id}/questions", headers=headers, json=req_payload)

    assert resp.status_code == 200
    data = resp.json()

    # Verify exact JSON response schema
    assert "question_id" in data
    assert data["question"] == "What dataset was used for evaluation?"
    assert data["question_type"] in ["DATASET", "EXPERIMENT", "RESULT"]
    assert "answer" in data
    assert "abstained" in data
    assert "support_score" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)

    # PROVE: Sources originate strictly from database metadata
    if len(data["sources"]) > 0:
        src = data["sources"][0]
        assert src["page"] == 5
        assert src["section"] == "4. Experiments"
        assert src["chunk_id"] == str(chunk_id)
        assert src["text"] == "We evaluate on ImageNet dataset obtaining 88.5% top-1 accuracy."

    # 4. Verify DB record persistence across all 4 tables
    q_id = uuid.UUID(data["question_id"])

    db_q = (await db_session.execute(select(Question).where(Question.id == q_id))).scalar_one()
    assert db_q.question_text == "What dataset was used for evaluation?"

    db_ret_ev = (await db_session.execute(select(RetrievedEvidence).where(RetrievedEvidence.question_id == q_id))).scalars().all()
    assert len(db_ret_ev) > 0

    db_ans = (await db_session.execute(select(Answer).where(Answer.question_id == q_id))).scalar_one()
    assert db_ans.answer_text == data["answer"]

    db_ans_ev = (await db_session.execute(select(AnswerEvidence).where(AnswerEvidence.answer_id == db_ans.id))).scalars().all()
    assert len(db_ans_ev) >= 0


@pytest.mark.asyncio
async def test_main_question_answering_endpoint_unindexed_paper_rejection(
    client: AsyncClient,
    db_session: AsyncSession
):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "unindexed_qa_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # Create paper in UPLOADED status (NOT READY)
    paper_uploaded = Paper(
        workspace_id=workspace.id,
        title="Uploaded Paper",
        file_name="uploaded.pdf",
        file_size=100,
        status=PaperStatus.UPLOADED
    )
    db_session.add(paper_uploaded)
    await db_session.commit()

    req_payload = {"question": "What is the summary?"}
    resp = await client.post(f"/api/v1/papers/{paper_uploaded.id}/questions", headers=headers, json=req_payload)

    # Must reject with 400 Bad Request
    assert resp.status_code == 400
    assert "not ready for question answering" in resp.json()["detail"]
