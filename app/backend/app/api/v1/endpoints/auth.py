"""Authentication API endpoints.

POST /auth/register — Create a new user account with password policy validation.
POST /auth/login — Authenticate user and return JWT token.
POST /auth/logout — Invalidate the current session.
GET /auth/me — Return current user profile from token.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_cookies import clear_access_cookie, extract_access_token, set_access_cookie
from app.config import get_settings
from app.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.auth_service import AuthService

logger = logging.getLogger("tor_app.auth")

router = APIRouter()


@router.post(
    "/register",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Validates password policy and checks email uniqueness.",
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Register a new user.

    Validates password against policy (min 8 chars, 1 upper, 1 lower, 1 digit, 1 special),
    checks email uniqueness, and creates the user with bcrypt-hashed password (12 rounds).
    """
    user = await AuthService.register_user(db, body)

    # Build response
    user_data = RegisterResponse.model_validate(user)
    request_id = getattr(request.state, "request_id", "unknown")

    response = SuccessResponse(
        ok=True,
        data=user_data.model_dump(mode="json"),
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    logger.info("User registered: %s (%s)", user.email, user.role)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response.model_dump(mode="json"),
    )


@router.post(
    "/login",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and receive JWT token",
    description="Authenticate with email and password. Returns JWT token with 24h expiry.",
)
async def login(
    request: Request,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[object, Depends(get_redis)],
) -> JSONResponse:
    """Authenticate user and return JWT token.

    Verifies credentials, generates JWT (HS256, 24h expiry),
    stores session in Redis, and returns token with user profile.
    """
    settings = get_settings()

    user, token = await AuthService.login(db, redis, body.email, body.password)

    # Build response
    user_data = UserResponse.model_validate(user)
    expires_in = settings.jwt_expiry_hours * 3600

    login_data = LoginResponse(
        token=token,
        user=user_data,
        expires_in=expires_in,
    )

    request_id = getattr(request.state, "request_id", "unknown")

    response = SuccessResponse(
        ok=True,
        data=login_data.model_dump(mode="json"),
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    logger.info("User logged in: %s", user.email)

    json_response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump(mode="json"),
    )
    set_access_cookie(json_response, token, expires_in)
    return json_response


@router.post(
    "/logout",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout and invalidate session",
    description="Invalidate the current JWT session in Redis.",
)
async def logout(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[object, Depends(get_redis)],
) -> JSONResponse:
    """Logout the current user by invalidating their session in Redis."""
    token = extract_access_token(request) or ""
    await AuthService.logout(redis, token)

    request_id = getattr(request.state, "request_id", "unknown")

    response = SuccessResponse(
        ok=True,
        data={"message": "ออกจากระบบเรียบร้อย"},
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    logger.info("User logged out: %s", current_user.email)

    json_response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump(mode="json"),
    )
    clear_access_cookie(json_response)
    return json_response


@router.get(
    "/me",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Return the authenticated user's profile from the JWT token.",
)
async def me(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Return the current authenticated user's profile."""
    user_data = UserResponse.model_validate(current_user)

    request_id = getattr(request.state, "request_id", "unknown")

    response = SuccessResponse(
        ok=True,
        data=user_data.model_dump(mode="json"),
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump(mode="json"),
    )
