"""Request-scoped identifiers for LLM usage rows.

Values are set on the current asyncio task and read when a provider returns.
They are not reset inside ``get_current_user`` so they stay visible to the
endpoint that runs after authentication.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_user_id: ContextVar[str | None] = ContextVar("usage_user_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("usage_request_id", default=None)
_task: ContextVar[str | None] = ContextVar("usage_task", default=None)


def current_user_id() -> str | None:
    return _user_id.get()


def current_request_id() -> str | None:
    return _request_id.get()


def current_task() -> str | None:
    return _task.get()


def set_usage_actor(*, user_id: str | None = None, request_id: str | None = None) -> None:
    """Remember the signed-in user and HTTP request for later LLM calls."""
    if user_id:
        _user_id.set(str(user_id))
    if request_id:
        _request_id.set(str(request_id))


@contextmanager
def bind_llm_request(kind: str, request_id: str | None) -> Iterator[None]:
    """Attach an admission request id while an LLM slot is held."""
    if kind != "llm" or not request_id:
        yield
        return
    token = _request_id.set(str(request_id))
    try:
        yield
    finally:
        _request_id.reset(token)


@contextmanager
def usage_scope(
    *,
    user_id: str | None = None,
    request_id: str | None = None,
    task: str | None = None,
) -> Iterator[None]:
    """Temporarily override usage context. Resets on exit (for tests and jobs)."""
    tokens: list[tuple[ContextVar[str | None], Token[str | None]]] = []
    if user_id is not None:
        tokens.append((_user_id, _user_id.set(str(user_id))))
    if request_id is not None:
        tokens.append((_request_id, _request_id.set(str(request_id))))
    if task is not None:
        tokens.append((_task, _task.set(str(task))))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
