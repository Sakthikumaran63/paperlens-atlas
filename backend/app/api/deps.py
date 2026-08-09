import uuid
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.paper import Paper
from app.models.user import User
from app.models.workspace import Workspace

from typing import Optional

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(reusable_oauth2)
) -> User:
    if token:
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            try:
                user_id = uuid.UUID(payload.get("sub"))
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if user:
                    return user
            except ValueError:
                pass

    # Fallback demo/guest user for unauthenticated frontend browsing
    stmt = select(User).where(User.email == "demo@paperlens.ai")
    result = await db.execute(stmt)
    demo_user = result.scalar_one_or_none()

    if not demo_user:
        demo_id = str(uuid.UUID("00000000-0000-0000-0000-000000000001"))
        demo_user = User(
            id=demo_id,
            email="demo@paperlens.ai",
            hashed_password="demo_password_hash_unauthenticated",
            name="Research Scholar"
        )
        db.add(demo_user)
        await db.flush()

        ws_id = str(uuid.UUID("00000000-0000-0000-0000-000000000002"))
        default_workspace = Workspace(
            id=ws_id,
            user_id=demo_user.id,
            name="Default Workspace",
            description="Your default PaperLens research workspace."
        )
        db.add(default_workspace)
        await db.commit()
        await db.refresh(demo_user)

    return demo_user




async def get_current_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Workspace:
    stmt = select(Workspace).where(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id
    )
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return current_user



async def verify_paper_access(
    workspace_id: uuid.UUID,
    paper_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
) -> Paper:
    stmt = select(Paper).where(
        Paper.id == paper_id,
        Paper.workspace_id == workspace.id
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )
    return paper
