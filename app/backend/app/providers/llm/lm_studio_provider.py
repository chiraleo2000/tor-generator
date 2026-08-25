"""LM Studio local LLM provider (on-prem mode).

Uses the OpenAI-compatible API that LM Studio exposes locally.
No data leaves the organization — all inference runs on-premise.
"""

import logging
from typing import AsyncIterator

from httpx import Timeout
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI

from app.config import get_settings
from app.providers.base import LLMProvider, LLMResponse

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
    if not payload.pop("disable_thinking", False):
        return payload
    extra = dict(payload.get("extra_body") or {})
    extra["enable_thinking"] = False
    template = extra.get("chat_template_kwargs")
    merged = dict(template) if isinstance(template, dict) else {}
    merged["enable_thinking"] = False
    extra["chat_template_kwargs"] = merged
    payload["extra_body"] = extra
    return payload


def message_text(message: object) -> str:
    """Prefer visible content; Gemma 4 may put JSON only in reasoning fields."""
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    for attr in ("reasoning_content", "reasoning"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return content if isinstance(content, str) else ""


def delta_text(delta: object) -> str:
    content = getattr(delta, "content", None)
    if isinstance(content, str) and content:
        return content
    for attr in ("reasoning_content", "reasoning"):
        value = getattr(delta, attr, None)
        if isinstance(value, str) and value:
            return value
    return ""


def _timeout_error(exc: BaseException) -> bool:
    return isinstance(exc, (TimeoutError, APITimeoutError)) or "Timeout" in type(exc).__name__


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
            timeout: Request timeout in seconds. Defaults to config (180s for Gemma).
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
                "messages": messages,
                **thinking_request_kwargs(
                    {
                        **kwargs,
                        "_guided_json": endpoint_supports_guided_json(self._base_url),
                    }
                ),
            }
            request_kwargs.setdefault("max_tokens", 4096)
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
        try:
            stream = await self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                stream=True,
                **thinking_request_kwargs(kwargs),
            )

            async for chunk in stream:
                if not chunk.choices:
                    continue
                text = delta_text(chunk.choices[0].delta)
                if text:
                    yield text

        except APIConnectionError as exc:
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
            if _timeout_error(exc):
                logger.exception(
                    "LM Studio stream timed out after %.1fs",
                    self._timeout,
                )
                raise TimeoutError(
                    f"LM Studio did not respond within {self._timeout}s"
                ) from exc
            logger.exception("LM Studio stream failed")
            raise


# Alias: the same OpenAI-compatible client serves LM Studio, Ollama, and llama.cpp.
OpenAICompatLLMProvider = LMStudioLocalProvider
