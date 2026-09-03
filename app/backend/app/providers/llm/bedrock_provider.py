"""Amazon Bedrock LLM provider (Claude / other Bedrock chat models)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


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
        aws_bearer_token_bedrock: str = "",
    ) -> None:
        from app.providers.bedrock_client import bedrock_runtime_client

        self._client = bedrock_runtime_client(
            region=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            bearer_token=aws_bearer_token_bedrock,
        )
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

    def _collect_stream_tokens(self, messages: list[dict], **kwargs: Any) -> list[str]:
        response = self._client.converse_stream(**self._build_request(messages, **kwargs))
        tokens: list[str] = []
        for event in response.get("stream") or []:
            delta = (event.get("contentBlockDelta") or {}).get("delta") or {}
            text = delta.get("text")
            if text:
                tokens.append(str(text))
        return tokens

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
        try:
            tokens = await asyncio.wait_for(
                asyncio.to_thread(self._collect_stream_tokens, messages, **kwargs),
                timeout=self._timeout,
            )
            for token in tokens:
                yield token
            return
        except Exception as exc:
            logger.warning(
                "Bedrock converse_stream failed (%s); falling back to invoke",
                exc,
            )
        response = await self.invoke(messages, **kwargs)
        if response.content:
            yield response.content
