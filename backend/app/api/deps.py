import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.paper import Paper
from app.models.user import User
from app.models.workspace import Workspace

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _extract_token(request: Request, header_token: Optional[str]) -> Optional[str]:
    """Extract token from httpOnly cookie 'paperlens_token' first, falling back to Authorization header."""
    cookie_token = request.cookies.get("paperlens_token")
    if cookie_token:
        return cookie_token
    return header_token


async def get_current_user_strict(
    request: Request,
    db: AsyncSession = Depends(get_db),
    header_token: Optional[str] = Depends(reusable_oauth2)
) -> User:
    token = _extract_token(request, header_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = uuid.UUID(payload.get("sub"))
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            return user
    except ValueError:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    header_token: Optional[str] = Depends(reusable_oauth2)
) -> User:
    token = _extract_token(request, header_token)
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
        demo_user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="demo@paperlens.ai",
            hashed_password="demo_password_hash_unauthenticated",
            name="Research Scholar"
        )
        db.add(demo_user)
        await db.flush()

        default_workspace = Workspace(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
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
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied."
        )
    return workspace


async def require_admin(
    current_user: User = Depends(get_current_user_strict)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return current_user


async def get_workspace_scoped_paper(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Paper:
    """
    Enforces strict workspace isolation at the query level.
    Returns 404 (not 403) to prevent IDOR information disclosure of existence across workspaces.
    """
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(
            Paper.id == paper_id,
            Workspace.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    return paper

