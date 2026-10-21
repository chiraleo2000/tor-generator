"""Wrap any LLM provider and append a usage row after invoke or stream."""

from __future__ import annotations

import logging
import time
from typing import AsyncIterator

from app.llm_tokens import estimate_tokens
from app.providers.base import LLMProvider, LLMResponse
from app.usage.context import current_request_id, current_task, current_user_id
from app.usage.cost import normalize_usage
from app.usage.store import persist_llm_usage

logger = logging.getLogger(__name__)


def llm_core(provider: LLMProvider) -> LLMProvider:
    """Return the concrete provider inside a usage wrapper, if any."""
    inner = getattr(provider, "inner", None)
    if isinstance(inner, LLMProvider):
        return inner
    return provider


def _text_pieces(content: object) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return [] if content is None else [str(content)]
    pieces: list[str] = []
    for block in content:
        if isinstance(block, str):
            pieces.append(block)
        elif isinstance(block, dict):
            pieces.append(str(block.get("text") or ""))
    return pieces


def _message_text(messages: list[dict] | None) -> str:
    parts: list[str] = []
    for message in messages or []:
        content = message.get("content") if isinstance(message, dict) else ""
        parts.extend(_text_pieces(content))
    return "\n".join(parts)


def _estimated(messages: list[dict], output_text: str) -> dict:
    prompt = estimate_tokens(_message_text(messages))
    completion = estimate_tokens(output_text) if output_text else 0
    return normalize_usage(
        {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "tokens_estimated": True,
        }
    )


class UsageRecordingLLM(LLMProvider):
    """Delegates to ``inner`` and records tokens, cost, and latency."""

    def __init__(self, inner: LLMProvider, *, provider_name: str, task: str) -> None:
        self.inner = inner
        self.provider_name = provider_name or "unknown"
        self.task = task or "chat"

    def __getattr__(self, name: str):
        return getattr(self.inner, name)

    def _resolved_task(self) -> str:
        return current_task() or self.task or "chat"

    async def _record(
        self,
        *,
        model: str,
        usage: dict,
        started: float,
        status: str,
        error: str | None,
    ) -> None:
        try:
            await persist_llm_usage(
                user_id=current_user_id(),
                request_id=current_request_id(),
                task=self._resolved_task(),
                provider=self.provider_name,
                model=model or "unknown",
                latency_ms=int((time.perf_counter() - started) * 1000),
                usage=usage,
                status=status,
                error=error,
            )
        except Exception:
            logger.exception("usage recorder failed")

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        started = time.perf_counter()
        try:
            response = await self.inner.invoke(messages, tools, **kwargs)
        except Exception as exc:
            await self._record(
                model=str(getattr(self.inner, "_model_name", "") or self.provider_name),
                usage=_estimated(messages, ""),
                started=started,
                status="error",
                error=str(exc)[:300],
            )
            raise
        await self._record(
            model=response.model or self.provider_name,
            usage=normalize_usage(response.usage),
            started=started,
            status="ok",
            error=None,
        )
        return response

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        started = time.perf_counter()
        parts: list[str] = []
        error: str | None = None
        try:
            async for part in self.inner.stream(messages, **kwargs):
                parts.append(str(part))
                yield str(part)
        except Exception as exc:
            error = str(exc)[:300]
            raise
        finally:
            output = "".join(parts)
            raw = getattr(self.inner, "last_usage", None)
            if isinstance(raw, dict) and raw:
                usage = normalize_usage(raw)
                usage["tokens_estimated"] = False
            else:
                usage = _estimated(messages, output)
            await self._record(
                model=str(
                    getattr(self.inner, "_model_name", "")
                    or getattr(self.inner, "model", "")
                    or self.provider_name
                ),
                usage=usage,
                started=started,
                status="error" if error else "ok",
                error=error,
            )
