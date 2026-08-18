"""FastAPI dependency injection for shared resources.

Provides per-request access to:
- AsyncSession (from the application's async session factory with connection pooling)
- Redis client (for caching, rate limiting, session storage)
- MinIO client (for file/object storage)
- Current authenticated user (via JWT token validation)

Each dependency reads from app.state, which is populated by the lifespan handler
in main.py. If the underlying service is unavailable (None in app.state), the
dependency raises HTTP 503.
"""

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from minio import Minio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session from the application's session factory.

    The session auto-commits on success and rolls back on exception.
    Pool size is configured in the lifespan handler (default 20, max overflow 10).
    """
    session_factory = request.app.state.db_session_factory
    if session_factory is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available",
        )
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis(request: Request) -> Any:
    """Get the Redis client from app state.

    Used for session caching, rate limiting counters, and background job queues.
    """
    redis = request.app.state.redis
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not available",
        )
    return redis


def get_minio(request: Request) -> Minio:
    """Get the MinIO client from app state.

    Used for file storage (uploaded documents, exported DOCX/PDF).
    """
    minio = request.app.state.minio
    if minio is None:
        raise HTTPException(
            status_code=503,
            detail="MinIO not available",
        )
    return minio


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Extract and validate JWT from Authorization header, return the authenticated user.

    Looks for a Bearer token in the Authorization header, decodes it,
    validates the session exists in Redis (if Redis is available),
    and fetches the user from the database.

    Args:
        request: The incoming HTTP request.
        db: Async database session (injected).

    Returns:
        The authenticated User ORM instance.

    Raises:
        HTTPException 401: If the token is missing, invalid, expired,
                          session is invalidated, or user not found.
    """
    from app.auth_cookies import extract_access_token
    from app.services.auth_service import AuthService

    token = extract_access_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="กรุณาเข้าสู่ระบบ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and validate JWT
    try:
        payload = AuthService.decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="โทเค็นไม่ถูกต้องหรือหมดอายุ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="โทเค็นไม่ถูกต้อง",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check session validity in Redis (if available)
    redis = getattr(request.app.state, "redis", None)
    if redis is not None and jti is not None:
        session_key = f"session:{user_id}:{jti}"
        session_exists = await redis.exists(session_key)
        if not session_exists:
            raise HTTPException(
                status_code=401,
                detail="เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="ไม่พบผู้ใช้งาน",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
