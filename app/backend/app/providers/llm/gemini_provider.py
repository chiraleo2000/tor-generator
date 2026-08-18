"""Gemini chat LLM provider via the public REST API (httpx)."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _to_gemini_contents(messages: list[dict]) -> tuple[str | None, list[dict]]:
    system: str | None = None
    contents: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        text = msg.get("content", "") or ""
        if role == "system":
            system = text
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})
    return system, contents


class GeminiLLMProvider(LLMProvider):
    """Google Gemini generateContent client."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required for GeminiLLMProvider")
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout

    def _url(self, action: str) -> str:
        return f"{_GEMINI_BASE}/models/{self._model_name}:{action}?key={self._api_key}"

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        system, contents = _to_gemini_contents(messages)
        body: dict = {"contents": contents}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        generation: dict = {}
        if "temperature" in kwargs:
            generation["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            generation["maxOutputTokens"] = kwargs["max_tokens"]
        if generation:
            body["generationConfig"] = generation
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url("generateContent"), json=body)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Gemini did not respond within {self._timeout}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise ConnectionError(f"Gemini endpoint unreachable: {exc}") from exc

        candidates = payload.get("candidates") or []
        text = ""
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(part.get("text") or "" for part in parts)
        usage_meta = payload.get("usageMetadata") or {}
        return LLMResponse(
            content=text,
            model=self._model_name,
            usage={
                "prompt_tokens": usage_meta.get("promptTokenCount") or 0,
                "completion_tokens": usage_meta.get("candidatesTokenCount") or 0,
                "total_tokens": usage_meta.get("totalTokenCount") or 0,
            },
            finish_reason=(candidates[0].get("finishReason") if candidates else "stop")
            or "stop",
        )

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        result = await self.invoke(messages, **kwargs)
        if result.content:
            yield result.content
