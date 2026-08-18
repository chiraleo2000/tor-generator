"""OpenAI chat LLM provider for cloud deployment."""

from __future__ import annotations

import logging
from typing import AsyncIterator

from httpx import Timeout
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI

from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """Cloud OpenAI chat completions client."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        timeout: float = 60.0,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAILLMProvider")
        self._model_name = model_name
        self._timeout = timeout
        client_kwargs: dict = {
            "api_key": api_key,
            "timeout": Timeout(timeout, connect=10.0),
        }
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        try:
            request_kwargs: dict = {
                "model": self._model_name,
                "messages": messages,
                **kwargs,
            }
            if tools:
                request_kwargs["tools"] = tools
            response = await self._client.chat.completions.create(**request_kwargs)
            choice = response.choices[0]
            usage = response.usage
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model or self._model_name,
                usage={
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
                finish_reason=choice.finish_reason or "stop",
            )
        except APITimeoutError as exc:
            raise TimeoutError(
                f"OpenAI did not respond within {self._timeout}s"
            ) from exc
        except APIConnectionError as exc:
            raise ConnectionError("OpenAI endpoint unreachable") from exc

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except APITimeoutError as exc:
            raise TimeoutError(
                f"OpenAI stream did not respond within {self._timeout}s"
            ) from exc
        except APIConnectionError as exc:
            raise ConnectionError("OpenAI endpoint unreachable") from exc
