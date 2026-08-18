"""HttpOnly session cookie helpers."""

from __future__ import annotations

from fastapi import Request, Response

from app.config import get_settings

COOKIE_PATH = "/"


def cookie_name() -> str:
    return get_settings().auth_cookie_name


def extract_access_token(request: Request) -> str | None:
    """Prefer Authorization Bearer, then the HttpOnly session cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    cookie = request.cookies.get(cookie_name())
    if cookie:
        return cookie
    return None


def set_access_cookie(response: Response, token: str, max_age: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=cookie_name(),
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=COOKIE_PATH,
    )


def clear_access_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=cookie_name(),
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
