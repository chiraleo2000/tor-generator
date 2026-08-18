"""LM Studio local LLM provider (on-prem mode).

Uses the OpenAI-compatible API that LM Studio exposes locally.
No data leaves the organization — all inference runs on-premise.
"""

import logging
from typing import AsyncIterator

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI
from httpx import Timeout

from app.config import get_settings
from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


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
                **kwargs,
            }
            request_kwargs.setdefault("max_tokens", 4096)
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
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except APITimeoutError as exc:
            logger.exception(
                "LM Studio stream timed out after %.1fs",
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
            logger.exception("LM Studio stream failed")
            raise


# Alias: the same OpenAI-compatible client serves LM Studio, Ollama, and llama.cpp.
OpenAICompatLLMProvider = LMStudioLocalProvider
