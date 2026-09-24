"""Chat failover from a primary LLM to a backup when quota or throttle hits.

Bedrock daily token quotas open an in-process circuit until the next UTC
midnight so later calls skip the exhausted provider. A short throttle fails
over once and tries the primary again on the next call.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_DAILY_MARKERS = ("toomanytokensperday", "tokensperday", "servicequotaexceeded")
_THROTTLE_MARKERS = (
    "throttlingexception",
    "throttling",
    "toomanyrequests",
    "toomanytokens",
)
_BLOCKED_MARKERS = (
    "validationexception",
    "accessdenied",
    "unrecognizedclient",
    "expiredtoken",
)

_circuit_open_until: float | None = None


def reset_fallback_circuit() -> None:
    """Clear the in-process daily-quota circuit (tests)."""
    global _circuit_open_until
    _circuit_open_until = None


def fallback_circuit_open(now: float | None = None) -> bool:
    """True while a daily quota is still expected to be exhausted."""
    global _circuit_open_until
    if _circuit_open_until is None:
        return False
    current = datetime.now(timezone.utc).timestamp() if now is None else now
    if current >= _circuit_open_until:
        _circuit_open_until = None
        return False
    return True


def open_daily_quota_circuit(now: datetime | None = None) -> None:
    """Skip the primary provider until the next UTC midnight."""
    global _circuit_open_until
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    midnight = (current + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    _circuit_open_until = midnight.timestamp()


def _compact(text: str) -> str:
    return text.lower().replace("_", "").replace(" ", "")


def _error_blob(exc: BaseException) -> str:
    parts = [type(exc).__name__, str(exc)]
    cause = exc.__cause__
    seen = {id(exc)}
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        parts.append(type(cause).__name__)
        parts.append(str(cause))
        cause = cause.__cause__
    return _compact(" ".join(parts))


def _root_error_name(exc: BaseException) -> str:
    cause = exc
    seen = {id(exc)}
    while cause.__cause__ is not None and id(cause.__cause__) not in seen:
        cause = cause.__cause__
        seen.add(id(cause))
    return type(cause).__name__


def _blocked(blob: str) -> bool:
    return any(marker in blob for marker in _BLOCKED_MARKERS)


def is_daily_quota_error(exc: BaseException) -> bool:
    """Bedrock-style daily token quota. Timeouts and validation stay put."""
    if isinstance(exc, TimeoutError) or "didnotrespondwithin" in _error_blob(exc):
        return False
    blob = _error_blob(exc)
    if _blocked(blob):
        return False
    return any(marker in blob for marker in _DAILY_MARKERS)


def is_llm_failover_error(exc: BaseException) -> bool:
    """Quota or throttle after the primary provider has already retried."""
    if isinstance(exc, TimeoutError):
        return False
    blob = _error_blob(exc)
    if "didnotrespondwithin" in blob or _blocked(blob):
        return False
    if any(marker in blob for marker in _DAILY_MARKERS):
        return True
    return any(marker in blob for marker in _THROTTLE_MARKERS)


class FallbackLLMProvider(LLMProvider):
    """Try the primary chat model, then the backup on quota or throttle."""

    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider,
        *,
        primary_name: str = "bedrock",
        fallback_name: str = "gemini",
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_name = primary_name
        self._fallback_name = fallback_name

    def _note_failure(self, exc: BaseException) -> str:
        if is_daily_quota_error(exc):
            open_daily_quota_circuit()
            reason = "daily_quota"
        else:
            reason = "throttle"
        logger.warning(
            "LLM failover %s -> %s reason=%s error_class=%s",
            self._primary_name,
            self._fallback_name,
            reason,
            _root_error_name(exc),
        )
        return reason

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        if fallback_circuit_open():
            logger.warning("LLM circuit open; using %s", self._fallback_name)
            return await self._fallback.invoke(messages, tools=tools, **kwargs)
        try:
            return await self._primary.invoke(messages, tools=tools, **kwargs)
        except Exception as exc:
            if not is_llm_failover_error(exc):
                raise
            self._note_failure(exc)
            return await self._fallback.invoke(messages, tools=tools, **kwargs)

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        if fallback_circuit_open():
            logger.warning("LLM circuit open; using %s", self._fallback_name)
            async for piece in self._fallback.stream(messages, **kwargs):
                yield piece
            return
        yielded = False
        try:
            async for piece in self._primary.stream(messages, **kwargs):
                yielded = True
                yield piece
            return
        except Exception as exc:
            if yielded or not is_llm_failover_error(exc):
                if is_daily_quota_error(exc):
                    open_daily_quota_circuit()
                raise
            self._note_failure(exc)
        async for piece in self._fallback.stream(messages, **kwargs):
            yield piece
