import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.paper import Paper
from app.models.workspace import Workspace
from app.models.enums import PaperStatus


@pytest.mark.asyncio
async def test_workspace_isolation_and_unauthorized_paper_access(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Register User A
    user_a_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "usera@example.com", "password": "Password123!", "name": "User A"}
    )
    token_a = user_a_resp.json()["access_token"]
    user_a_id = uuid.UUID(user_a_resp.json()["user"]["id"])

    # 2. Register User B
    user_b_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "userb@example.com", "password": "Password123!", "name": "User B"}
    )
    token_b = user_b_resp.json()["access_token"]

    # Retrieve User A's default workspace from DB
    stmt_a = select(Workspace).where(Workspace.user_id == user_a_id)
    res_a = await db_session.execute(stmt_a)
    workspace_a = res_a.scalar_one()

    # Create a paper belonging to User A's workspace
    paper_a = Paper(
        workspace_id=workspace_a.id,
        title="User A Private Research Paper",
        file_name="usera_paper.pdf",
        file_size=2048,
        status=PaperStatus.READY
    )
    db_session.add(paper_a)
    await db_session.commit()
    await db_session.refresh(paper_a)

    # User A accesses User A's paper -> 200 OK
    headers_a = {"Authorization": f"Bearer {token_a}"}
    resp_a = await client.get(
        f"/api/v1/workspaces/{workspace_a.id}/papers/{paper_a.id}",
        headers=headers_a
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["title"] == "User A Private Research Paper"

    # User B attempts to access User A's paper in User A's workspace -> 404 / 403 Forbidden
    headers_b = {"Authorization": f"Bearer {token_b}"}
    resp_b = await client.get(
        f"/api/v1/workspaces/{workspace_a.id}/papers/{paper_a.id}",
        headers=headers_b
    )
    assert resp_b.status_code == 404
    assert resp_b.json()["detail"] == "Workspace not found or access denied."
