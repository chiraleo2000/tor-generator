"""Amazon Bedrock LLM provider (Claude / other Bedrock chat models)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

from app.providers.base import LLMProvider, LLMResponse
from app.providers.bedrock_client import call_bedrock_with_retry

logger = logging.getLogger(__name__)


def _bedrock_tool_spec(tool: Any) -> dict[str, Any] | None:
    """Map one OpenAI-style tool, or a native toolSpec, to a Converse tool entry."""
    if not isinstance(tool, dict):
        return None
    if "toolSpec" in tool:
        return tool
    function = tool.get("function") if isinstance(tool.get("function"), dict) else tool
    name = str(function.get("name") or tool.get("name") or "").strip()
    if not name:
        return None
    description = str(function.get("description") or tool.get("description") or name)
    parameters = (
        function.get("parameters")
        or function.get("input_schema")
        or tool.get("parameters")
        or tool.get("input_schema")
        or {"type": "object", "properties": {}}
    )
    if isinstance(parameters, dict) and "json" in parameters and len(parameters) == 1:
        schema = parameters
    else:
        schema = {"json": parameters}
    return {
        "toolSpec": {
            "name": name,
            "description": description,
            "inputSchema": schema,
        }
    }


def openai_tools_to_bedrock_tool_config(
    tools: list[dict] | None,
) -> dict[str, Any] | None:
    """Map OpenAI-style tools (or Bedrock toolSpec) to Converse toolConfig."""
    if not tools:
        return None
    specs: list[dict[str, Any]] = []
    for tool in tools:
        spec = _bedrock_tool_spec(tool)
        if spec is None:
            continue
        specs.append(spec)
    if not specs:
        return None
    return {"tools": specs}


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

    def _build_request(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if tools is None:
            tools = kwargs.pop("tools", None)
        else:
            kwargs.pop("tools", None)
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
            # Keep input + maxTokens inside the model window (Bedrock ValidationException).
            try:
                from app.llm_tokens import clamp_max_tokens, estimate_tokens

                blob = "\n".join(
                    str(part.get("text") or "") for part in system_parts
                ) + "\n".join(
                    str((block.get("text") if isinstance(block, dict) else "") or "")
                    for msg in converse_messages
                    for block in (msg.get("content") or [])
                )
                inference["maxTokens"] = clamp_max_tokens(
                    blob, int(kwargs["max_tokens"])
                )
                # Extra guard when Thai estimate undercounts.
                used = estimate_tokens(blob)
                from app.llm_tokens import live_context_window

                room = max(256, live_context_window() - used - 512)
                inference["maxTokens"] = max(256, min(inference["maxTokens"], room))
            except Exception:  # noqa: BLE001 — never block the request on clamp helpers
                inference["maxTokens"] = int(kwargs["max_tokens"])
        if "temperature" in kwargs:
            inference["temperature"] = float(kwargs["temperature"])
        if inference:
            request["inferenceConfig"] = inference
        tool_config = openai_tools_to_bedrock_tool_config(tools)
        if tool_config:
            request["toolConfig"] = tool_config
        return request

    def _converse(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> dict:
        request = self._build_request(messages, tools=tools, **kwargs)
        return call_bedrock_with_retry(
            lambda: self._client.converse(**request),
            model_id=self._model_id,
            op="converse",
        )

    def _collect_stream_tokens(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        request = self._build_request(messages, tools=tools, **kwargs)
        response = call_bedrock_with_retry(
            lambda: self._client.converse_stream(**request),
            model_id=self._model_id,
            op="converse_stream",
        )
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
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._converse, messages, tools, **kwargs),
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
        tools = kwargs.pop("tools", None)
        try:
            tokens = await asyncio.wait_for(
                asyncio.to_thread(self._collect_stream_tokens, messages, tools, **kwargs),
                timeout=self._timeout,
            )
            for token in tokens:
                yield token
            return
        except Exception as exc:
            logger.warning(
                "Bedrock converse_stream failed (%s); falling back to invoke",
                type(exc).__name__,
            )
        response = await self.invoke(messages, tools=tools, **kwargs)
        if response.content:
            yield response.content
