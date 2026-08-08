import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, PipelineStage
from app.models.paper import Paper
from app.models.workspace import Workspace
from app.services.pipeline_orchestrator import PaperPipelineOrchestrator


@pytest.mark.asyncio
async def test_paper_pipeline_orchestrator_full_execution(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Register User & Workspace
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "pipeline_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    # 2. Create uploaded Paper record
    paper = Paper(
        workspace_id=workspace.id,
        title="Pipeline Test Paper",
        file_name="pipeline_test.pdf",
        file_size=512,
        status=PaperStatus.UPLOADED,
        stage=PipelineStage.UPLOADING,
        progress=0
    )
    db_session.add(paper)
    await db_session.commit()

    # 3. Execute Orchestrator run_pipeline directly
    orchestrator = PaperPipelineOrchestrator()
    await orchestrator.run_pipeline(paper.id)

    # 4. Verify Paper final status, stage, and progress
    updated_paper = (await db_session.execute(select(Paper).where(Paper.id == paper.id))).scalar_one()

    assert updated_paper.status == PaperStatus.READY
    assert updated_paper.stage == PipelineStage.READY
    assert updated_paper.progress == 100
    assert updated_paper.processing_error is None

    # Verify per-stage details tracking timestamps & status
    details = updated_paper.stage_details_json
    assert details is not None
    assert "EXTRACTING" in details
    assert details["EXTRACTING"]["status"] == "COMPLETED"
    assert "start_time" in details["EXTRACTING"]
    assert "end_time" in details["EXTRACTING"]

    assert "STRUCTURING" in details
    assert details["STRUCTURING"]["status"] == "COMPLETED"

    assert "CHUNKING" in details
    assert details["CHUNKING"]["status"] == "COMPLETED"

    assert "EMBEDDING" in details
    assert details["EMBEDDING"]["status"] == "COMPLETED"

    assert "ANALYZING" in details
    assert details["ANALYZING"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_get_paper_status_polling_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "status_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(
        workspace_id=workspace.id,
        title="Polling Paper",
        file_name="poll.pdf",
        file_size=100,
        status=PaperStatus.PROCESSING,
        stage=PipelineStage.EMBEDDING,
        progress=70,
        stage_details_json={
            "EXTRACTING": {"status": "COMPLETED", "start_time": "2026-08-08T23:00:00Z", "end_time": "2026-08-08T23:00:01Z"},
            "EMBEDDING": {"status": "IN_PROGRESS", "start_time": "2026-08-08T23:00:02Z", "end_time": None}
        }
    )
    db_session.add(paper)
    await db_session.commit()

    # Call GET /api/v1/papers/{paper_id}/status
    resp = await client.get(f"/api/v1/papers/{paper.id}/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["paper_id"] == str(paper.id)
    assert data["status"] == "PROCESSING"
    assert data["stage"] == "EMBEDDING"
    assert data["progress"] == 70
    assert "stages_detail" in data
    assert data["stages_detail"]["EXTRACTING"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_paper_pipeline_retry_endpoint(client: AsyncClient, db_session: AsyncSession):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "retry_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])

    ws_stmt = select(Workspace).where(Workspace.user_id == user_id)
    ws_res = await db_session.execute(ws_stmt)
    workspace = ws_res.scalar_one()

    paper = Paper(
        workspace_id=workspace.id,
        title="Failed Paper",
        file_name="failed.pdf",
        file_size=100,
        status=PaperStatus.FAILED,
        stage=PipelineStage.FAILED,
        progress=50,
        processing_error="Embedding service error"
    )
    db_session.add(paper)
    await db_session.commit()

    # Call POST /api/v1/papers/{paper_id}/retry
    resp = await client.post(f"/api/v1/papers/{paper.id}/retry", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "launched successfully" in data["message"]
    assert data["paper_id"] == str(paper.id)
    assert data["status"] == "PROCESSING"
