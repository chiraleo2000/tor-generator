"""Provider-agnostic token stream with invoke fallback.

Chat, intake, and draft SSE loops use this so OpenAI, Claude, Gemini, Bedrock,
Azure, and local LM Studio all terminate the same way: native tokens when the
vendor streams, otherwise invoke() sliced into paint-sized chunks.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)

STREAM_FALLBACK_SLICE = 120


async def stream_llm_tokens(
    llm: LLMProvider,
    messages: list[dict],
    **kwargs: Any,
) -> AsyncIterator[str]:
    """Yield LLM tokens, falling back to invoke() when stream is empty or fails."""
    streamed = False
    stream_error: BaseException | None = None
    try:
        async for piece in llm.stream(messages, **kwargs):
            if piece:
                streamed = True
                yield piece
        if streamed:
            return
    except Exception as exc:  # noqa: BLE001 — invoke() is the contract fallback
        stream_error = exc
        logger.info("LLM stream unavailable (%s); using invoke", exc)
    try:
        result = await llm.invoke(messages, **kwargs)
    except Exception:
        if stream_error is not None:
            raise stream_error
        return
    text = result.content if isinstance(getattr(result, "content", None), str) else ""
    if not text:
        if stream_error is not None:
            raise stream_error
        return
    for index in range(0, len(text), STREAM_FALLBACK_SLICE):
        yield text[index : index + STREAM_FALLBACK_SLICE]
