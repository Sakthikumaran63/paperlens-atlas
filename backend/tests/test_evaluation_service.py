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
from app.services.evaluation_service import EvaluationService


@pytest.mark.asyncio
async def test_evaluation_service_3_way_rag_benchmark(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Setup User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "eval_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Setup Paper with Section structure and Chunks
    paper = Paper(
        workspace_id=workspace.id,
        title="Evaluation Benchmark Paper",
        file_name="eval_test.pdf",
        file_size=1024,
        status=PaperStatus.READY
    )
    db_session.add(paper)
    await db_session.flush()

    sec_exp = PaperSection(
        paper_id=paper.id, title="5. Experiments", normalized_title="experiments",
        section_type=SectionType.EXPERIMENTS, page_start=5, page_end=5, order_index=0
    )
    db_session.add(sec_exp)
    await db_session.flush()

    c = PaperChunk(
        paper_id=paper.id, page_number=5, section_id=sec_exp.id, chunk_index=0,
        text="We evaluate on ImageNet obtaining 88.5% accuracy.", token_count=10,
        embedding=[0.1]*1536
    )
    db_session.add(c)
    await db_session.commit()

    # 3. Test EvaluationService
    eval_svc = EvaluationService()
    dataset = eval_svc.generate_sample_evaluation_dataset(paper.id)

    report = await eval_svc.run_benchmark(dataset=dataset, db=db_session, top_k=5)

    assert report is not None
    assert report.benchmark_id.startswith("eval_")
    assert len(report.configurations) == 3

    config_names = [cfg.config_name for cfg in report.configurations]
    assert "BASELINE_RAG" in config_names
    assert "STRUCTURE_AWARE_RAG" in config_names
    assert "STRUCTURE_AWARE_RAG_WITH_VERIFICATION" in config_names

    # Check metrics structure on verified config
    ver_cfg = next(cfg for cfg in report.configurations if cfg.config_name == "STRUCTURE_AWARE_RAG_WITH_VERIFICATION")
    assert ver_cfg.total_questions == 3
    assert ver_cfg.answerable_count == 2
    assert ver_cfg.unanswerable_count == 1

    # Verify metric attributes
    assert hasattr(ver_cfg.retrieval, "recall_at_k")
    assert hasattr(ver_cfg.retrieval, "precision_at_k")
    assert hasattr(ver_cfg.retrieval, "mrr")
    assert hasattr(ver_cfg.answer, "semantic_similarity")
    assert hasattr(ver_cfg.grounding, "evidence_precision")
    assert hasattr(ver_cfg.abstention, "unanswerable_detection")
    assert hasattr(ver_cfg.abstention, "false_answer_rate")


@pytest.mark.asyncio
async def test_evaluate_paper_api_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "eval_api_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(workspace_id=workspace.id, title="Eval API Paper", file_name="e_api.pdf", file_size=100, status=PaperStatus.READY)
    db_session.add(paper)
    await db_session.flush()

    c = PaperChunk(paper_id=paper.id, page_number=1, chunk_index=0, text="Eval sample text", token_count=5, embedding=[0.1]*1536)
    db_session.add(c)
    await db_session.commit()

    # Call POST /api/v1/papers/{paper_id}/evaluate
    resp = await client.post(f"/api/v1/papers/{paper.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "benchmark_id" in data
    assert "timestamp" in data
    assert "configurations" in data
    assert len(data["configurations"]) == 3
