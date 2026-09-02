"""Amazon Bedrock LLM provider (Claude / other Bedrock chat models)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from typing import Any, AsyncIterator

from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_STREAM_END = object()
_BEDROCK_STREAM_ERRORS = (
    "internalServerException",
    "modelStreamErrorException",
    "throttlingException",
    "validationException",
    "serviceUnavailableException",
)


def _next_stream_event(events: Iterator[dict[str, Any]]) -> dict[str, Any] | object:
    """Read one blocking boto3 event without leaking StopIteration into asyncio."""
    try:
        return next(events)
    except StopIteration:
        return _STREAM_END


class BedrockLLMProvider(LLMProvider):
    """Calls Amazon Bedrock Runtime Converse / ConverseStream APIs.

    Empty AWS keys rely on the default boto3 credential chain (instance/task role).
    """

    def __init__(
        self,
        *,
        region: str,
        model_id: str,
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        timeout: float = 60.0,
    ) -> None:
        import boto3

        kwargs: dict[str, Any] = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            kwargs["aws_access_key_id"] = aws_access_key_id
            kwargs["aws_secret_access_key"] = aws_secret_access_key
        self._client = boto3.client("bedrock-runtime", **kwargs)
        self._model_id = model_id
        self._timeout = timeout

    def _build_request(self, messages: list[dict], **kwargs: Any) -> dict[str, Any]:
        system_parts: list[dict[str, str]] = []
        converse_messages: list[dict] = []
        for item in messages:
            role = item.get("role", "user")
            content = str(item.get("content") or "")
            if role == "system":
                system_parts.append({"text": content})
                continue
            mapped = "assistant" if role == "assistant" else "user"
            converse_messages.append({"role": mapped, "content": [{"text": content}]})
        request: dict[str, Any] = {
            "modelId": self._model_id,
            "messages": converse_messages or [{"role": "user", "content": [{"text": ""}]}],
        }
        if system_parts:
            request["system"] = system_parts
        inference: dict[str, Any] = {}
        if "max_tokens" in kwargs:
            inference["maxTokens"] = int(kwargs["max_tokens"])
        if "temperature" in kwargs:
            inference["temperature"] = float(kwargs["temperature"])
        if inference:
            request["inferenceConfig"] = inference
        return request

    def _converse(self, messages: list[dict], **kwargs: Any) -> dict:
        return self._client.converse(**self._build_request(messages, **kwargs))

    def _open_stream(self, messages: list[dict], **kwargs: Any) -> dict:
        return self._client.converse_stream(**self._build_request(messages, **kwargs))

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        del tools
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._converse, messages, **kwargs),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise TimeoutError(f"Bedrock did not respond within {self._timeout}s") from exc
        except Exception as exc:
            raise ConnectionError(f"Bedrock endpoint unreachable: {exc}") from exc
        chunks = response.get("output", {}).get("message", {}).get("content", [])
        text = "".join(part.get("text", "") for part in chunks if isinstance(part, dict))
        usage = response.get("usage") or {}
        return LLMResponse(
            content=text,
            model=self._model_id,
            usage={
                "prompt_tokens": int(usage.get("inputTokens") or 0),
                "completion_tokens": int(usage.get("outputTokens") or 0),
                "total_tokens": int(usage.get("totalTokens") or 0),
            },
            finish_reason=str(response.get("stopReason") or "stop"),
        )

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        event_stream: Any = None
        yielded = False
        try:
            async with asyncio.timeout(self._timeout):
                response = await asyncio.to_thread(self._open_stream, messages, **kwargs)
                event_stream = response.get("stream")
                if event_stream is None:
                    raise ConnectionError("Bedrock returned no response stream")
                events = iter(event_stream)
                while True:
                    event = await asyncio.to_thread(_next_stream_event, events)
                    if event is _STREAM_END:
                        break
                    if not isinstance(event, dict):
                        continue
                    for error_key in _BEDROCK_STREAM_ERRORS:
                        if error_key in event:
                            raise ConnectionError(
                                f"Bedrock stream error ({error_key}): {event[error_key]}"
                            )
                    delta = (event.get("contentBlockDelta") or {}).get("delta") or {}
                    text = delta.get("text")
                    if text:
                        yielded = True
                        yield str(text)
            return
        except TimeoutError as exc:
            stream_error: Exception = TimeoutError(
                f"Bedrock did not finish streaming within {self._timeout}s"
            )
            stream_error.__cause__ = exc
        except Exception as exc:
            stream_error = exc
        finally:
            close = getattr(event_stream, "close", None)
            if callable(close):
                try:
                    await asyncio.to_thread(close)
                except Exception:
                    logger.debug("Bedrock response stream close failed", exc_info=True)

        if yielded:
            raise ConnectionError(
                f"Bedrock stream stopped after sending part of the response: {stream_error}"
            ) from stream_error
        logger.warning(
            "Bedrock converse_stream failed before first token (%s); falling back to invoke",
            stream_error,
        )
        response = await self.invoke(messages, **kwargs)
        if response.content:
            yield response.content
