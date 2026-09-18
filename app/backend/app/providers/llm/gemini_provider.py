"""Gemini chat LLM provider via the public REST API (httpx)."""

from __future__ import annotations

import inspect
import json
import logging
from typing import AsyncIterator

import httpx

from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_FALLBACK_SLICE = 120


def gemini_sse_text_pieces(line: str) -> list[str]:
    """Parse one Gemini ``streamGenerateContent?alt=sse`` line into text chunks."""
    raw = (line or "").strip()
    if not raw or raw == "[DONE]":
        return []
    if raw.startswith("data:"):
        raw = raw[5:].strip()
    if not raw or raw == "[DONE]":
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    pieces: list[str] = []
    for candidate in payload.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        parts = (candidate.get("content") or {}).get("parts") or []
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text") or ""
            if text:
                pieces.append(str(text))
    return pieces


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
        model_name: str = "gemini-3.5-flash-lite",
        timeout: float = 300.0,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required for GeminiLLMProvider")
        self._api_key = api_key.strip()
        self._model_name = (model_name or "gemini-3.5-flash-lite").strip()
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
                raw_status = getattr(response, "status_code", 200)
                try:
                    status = int(raw_status)
                except (TypeError, ValueError):
                    status = 200
                if status >= 400:
                    detail = str(getattr(response, "text", "") or "")[:500]
                    raise ConnectionError(
                        f"Gemini HTTP {status}: {detail}"
                    )
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Gemini did not respond within {self._timeout}s"
            ) from exc
        except ConnectionError:
            raise
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

    def _generation_body(self, messages: list[dict], **kwargs) -> dict:
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
        return body

    async def _stream_sse(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        body = self._generation_body(messages, **kwargs)
        url = f"{self._url('streamGenerateContent')}&alt=sse"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            stream_ctx = client.stream("POST", url, json=body)
            if inspect.iscoroutine(stream_ctx):
                stream_ctx.close()
                raise TypeError("Gemini HTTP stream is unavailable")
            async with stream_ctx as response:
                raw_status = getattr(response, "status_code", 200)
                try:
                    status = int(raw_status)
                except (TypeError, ValueError):
                    status = 200
                if status >= 400:
                    detail = ""
                    try:
                        detail = (await response.aread()).decode("utf-8", errors="replace")[:500]
                    except Exception:
                        detail = str(getattr(response, "text", "") or "")[:500]
                    raise ConnectionError(f"Gemini HTTP {status}: {detail}")
                async for line in response.aiter_lines():
                    for piece in gemini_sse_text_pieces(line):
                        yield piece

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        streamed = False
        try:
            async for piece in self._stream_sse(messages, **kwargs):
                streamed = True
                yield piece
            if streamed:
                return
        except Exception as exc:  # noqa: BLE001 — fall back to a single generateContent call
            logger.info("Gemini SSE stream unavailable (%s); using generateContent", exc)
        result = await self.invoke(messages, **kwargs)
        text = result.content or ""
        if not text:
            return
        for index in range(0, len(text), _FALLBACK_SLICE):
            yield text[index : index + _FALLBACK_SLICE]
