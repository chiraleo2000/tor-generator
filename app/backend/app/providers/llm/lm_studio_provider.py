"""LM Studio local LLM provider (on-prem mode).

Uses the OpenAI-compatible API that LM Studio exposes locally.
No data leaves the organization — all inference runs on-premise.
"""

import asyncio
import logging
from typing import AsyncIterator

from httpx import Timeout
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI

from app.config import get_settings
from app.llm_tokens import DEFAULT_MAX_TOKENS
from app.providers.base import LLMProvider, LLMResponse
from app.providers.llm_output import (
    ThinkingStreamFilter,
    looks_like_json,
    messages_with_output_contract,
    strip_thinking,
)

logger = logging.getLogger(__name__)


def endpoint_supports_guided_json(base_url: str) -> bool:
    lower = (base_url or "").lower()
    return "sglang" in lower or ":30000" in lower


def thinking_request_kwargs(kwargs: dict) -> dict:
    """Strip local-only flags; attach SGLang guided_json when requested."""
    payload = dict(kwargs)
    schema = payload.pop("json_schema", None)
    schema_name = str(payload.pop("json_schema_name", "response") or "response")
    guided = bool(payload.pop("_guided_json", False))
    if isinstance(schema, dict) and guided:
        extra = dict(payload.get("extra_body") or {})
        extra["guided_json"] = schema
        extra["json_schema_name"] = schema_name
        payload["extra_body"] = extra
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema},
        }
    thinking_on = True
    enable_flag = payload.pop("enable_thinking", None)
    disable = payload.pop("disable_thinking", None)
    if disable is not None:
        thinking_on = not bool(disable)
    elif enable_flag is not None:
        thinking_on = bool(enable_flag)
    extra = dict(payload.get("extra_body") or {})
    extra["enable_thinking"] = thinking_on
    template = extra.get("chat_template_kwargs")
    merged = dict(template) if isinstance(template, dict) else {}
    merged["enable_thinking"] = thinking_on
    extra["chat_template_kwargs"] = merged
    payload["extra_body"] = extra
    return payload


def message_text(message: object) -> str:
    """Visible final answer only; JSON in reasoning is a structured-output fallback."""
    content = getattr(message, "content", None)
    visible = strip_thinking(content) if isinstance(content, str) else ""
    if visible:
        return visible
    for attr in ("reasoning_content", "reasoning"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip() and looks_like_json(value):
            return value.strip()
    return ""


def delta_text(delta: object) -> str:
    """Never stream reasoning/thinking tokens to the client."""
    content = getattr(delta, "content", None)
    return content if isinstance(content, str) else ""


def _timeout_error(exc: BaseException) -> bool:
    return isinstance(exc, (TimeoutError, APITimeoutError)) or "Timeout" in type(exc).__name__


def _transient_unload(exc: BaseException) -> bool:
    message = str(exc).lower()
    return "unloaded" in message or "model is not loaded" in message


class LMStudioLocalProvider(LLMProvider):
    """OpenAI-compatible client targeting a local LM Studio endpoint.

    LM Studio serves models via an OpenAI-compatible REST API, so we use
    the official openai Python SDK pointed at the local base_url.
    No API key is required for local inference.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialize the LM Studio provider.

        Args:
            base_url: LM Studio endpoint URL. Defaults to config value.
            model_name: Model identifier loaded in LM Studio. Defaults to config value.
            timeout: Request timeout in seconds. Defaults to config (600s for long Gemma Q&A).
        """
        settings = get_settings()
        self._base_url = base_url or settings.lm_studio_base_url
        self._model_name = model_name or settings.lm_studio_model
        self._timeout = settings.lm_studio_timeout if timeout is None else timeout

        self._client = AsyncOpenAI(
            base_url=self._base_url,
            api_key="not-needed",
            timeout=Timeout(self._timeout, connect=10.0),
            max_retries=0,
        )

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send messages to the local LM Studio model and return a response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            tools: Optional tool definitions (passed if the model supports function calling).
            **kwargs: Additional options forwarded to the completions API
                      (temperature, max_tokens, top_p, etc.)

        Returns:
            LLMResponse with generated content and usage metadata.

        Raises:
            TimeoutError: If LM Studio does not respond within the configured timeout.
            ConnectionError: If the LM Studio endpoint is unreachable.
        """
        try:
            request_kwargs: dict = {
                "model": self._model_name,
                "messages": messages_with_output_contract(messages),
                **thinking_request_kwargs(
                    {
                        **kwargs,
                        "_guided_json": endpoint_supports_guided_json(self._base_url),
                    }
                ),
            }
            request_kwargs.setdefault("max_tokens", DEFAULT_MAX_TOKENS)
            if tools:
                request_kwargs["tools"] = tools

            response = await self._client.chat.completions.create(**request_kwargs)

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=message_text(choice.message),
                model=response.model or self._model_name,
                usage={
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
                finish_reason=choice.finish_reason or "stop",
            )

        except APITimeoutError as exc:
            logger.exception(
                "LM Studio request timed out after %.1fs",
                self._timeout,
            )
            raise TimeoutError(
                f"LM Studio did not respond within {self._timeout}s"
            ) from exc

        except APIConnectionError as exc:
            logger.exception(
                "Cannot connect to LM Studio at %s",
                self._base_url,
            )
            raise ConnectionError(
                f"LM Studio endpoint unreachable at {self._base_url}"
            ) from exc

        except Exception:
            logger.exception("LM Studio invocation failed")
            raise

    async def stream(
        self,
        messages: list[dict],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream tokens from the local LM Studio model.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Additional options forwarded to the completions API
                      (temperature, max_tokens, top_p, etc.)

        Yields:
            String content deltas as they are generated.

        Raises:
            TimeoutError: If LM Studio does not respond within the configured timeout.
            ConnectionError: If the LM Studio endpoint is unreachable.
        """
        last_error: BaseException | None = None
        for attempt in range(3):
            try:
                async for visible in self._stream_once(messages, **kwargs):
                    yield visible
                return
            except APIConnectionError as exc:
                last_error = exc
                if _timeout_error(exc):
                    logger.exception(
                        "LM Studio stream timed out after %.1fs",
                        self._timeout,
                    )
                    raise TimeoutError(
                        f"LM Studio did not respond within {self._timeout}s"
                    ) from exc
                logger.exception(
                    "Cannot connect to LM Studio at %s",
                    self._base_url,
                )
                raise ConnectionError(
                    f"LM Studio endpoint unreachable at {self._base_url}"
                ) from exc
            except Exception as exc:
                last_error = exc
                if _timeout_error(exc):
                    logger.exception(
                        "LM Studio stream timed out after %.1fs",
                        self._timeout,
                    )
                    raise TimeoutError(
                        f"LM Studio did not respond within {self._timeout}s"
                    ) from exc
                if _transient_unload(exc) and attempt < 2:
                    logger.warning(
                        "LM Studio model unloaded; retry %s/2", attempt + 1
                    )
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                logger.exception("LM Studio stream failed")
                raise
        if last_error is not None:
            raise last_error

    async def _stream_once(
        self,
        messages: list[dict],
        **kwargs,
    ) -> AsyncIterator[str]:
        req_kwargs = thinking_request_kwargs(kwargs)
        req_kwargs.setdefault("max_tokens", DEFAULT_MAX_TOKENS)
        filter_out = ThinkingStreamFilter()
        stream = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages_with_output_contract(messages),
            stream=True,
            timeout=Timeout(
                connect=10.0,
                read=self._timeout,
                write=30.0,
                pool=10.0,
            ),
            **req_kwargs,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            text = delta_text(chunk.choices[0].delta)
            visible = filter_out.push(text) if text else ""
            if visible:
                yield visible
        tail = filter_out.flush()
        if tail:
            yield tail


# Alias: the same OpenAI-compatible client serves LM Studio, Ollama, and llama.cpp.
OpenAICompatLLMProvider = LMStudioLocalProvider
