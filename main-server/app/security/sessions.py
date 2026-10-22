"""Session management using opaque Redis tokens and HttpOnly cookies."""

import secrets
from typing import Any, Optional
from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.user import User
from app.db.session import get_db

SESSION_COOKIE_NAME = "codesec_session"


async def create_user_session(response: Response, user_id: str, org_id: str) -> str:
    settings = get_settings()
    session_id = secrets.token_urlsafe(32)
    session_data = {"user_id": user_id, "organization_id": org_id}

    redis_service = get_redis_service(settings.redis_url)
    await redis_service.set_session(session_id, session_data, ttl_seconds=86400 * 7)

    is_prod = settings.app_env == "production"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=86400 * 7,
        path="/",
    )
    return session_id


async def destroy_user_session(response: Response, session_id: Optional[str]) -> None:
    if session_id:
        settings = get_settings()
        redis_service = get_redis_service(settings.redis_url)
        await redis_service.delete_session(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


async def get_current_session(
    codesec_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    if not codesec_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    data = await redis_service.get_session(codesec_session)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return data


async def get_current_user(
    session: dict[str, Any] = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> User:
    stmt = select(User).where(User.id == session["user_id"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
