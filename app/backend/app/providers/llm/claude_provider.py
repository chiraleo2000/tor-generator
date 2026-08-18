"""Claude Sonnet LLM provider implementation for cloud deployment mode.

Uses the Anthropic Python SDK (AsyncAnthropic) with prompt caching support.
Implements circuit breaker pattern (5 consecutive failures → 30s open state).
"""

import time
from enum import Enum
from typing import AsyncIterator

import anthropic

from app.providers.base import LLMProvider, LLMResponse


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for protecting against cascading LLM failures.

    - Closed: Normal operation, all requests pass through.
    - Open: After `failure_threshold` consecutive failures, reject immediately for `recovery_timeout` seconds.
    - Half-Open: After recovery timeout, allow one probe request. If it succeeds, close; if it fails, reopen.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, accounting for recovery timeout transitions."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Check whether a request should be allowed through."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Record a successful request, resetting the circuit to closed."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed request; trip the circuit if threshold is reached."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN


class ClaudeSonnetProvider(LLMProvider):
    """Anthropic Claude Sonnet LLM provider with prompt caching and circuit breaker.

    Args:
        api_key: Anthropic API key.
        model: Model identifier (default: claude-sonnet-4-20250514).
        timeout: Request timeout in seconds (default: 60).
        max_tokens: Default maximum tokens for responses (default: 4096).
        failure_threshold: Consecutive failures before circuit opens (default: 5).
        recovery_timeout: Seconds to wait before allowing a probe request (default: 30).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        timeout: float = 60.0,
        max_tokens: int = 4096,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        if not api_key:
            raise ValueError("Anthropic API key is required for ClaudeSonnetProvider")

        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout,
        )
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def _convert_messages(
        self, messages: list[dict]
    ) -> tuple[str | None, list[dict]]:
        """Convert generic message format to Anthropic's expected format.

        Extracts system message (if present) and formats user/assistant messages.
        Applies prompt caching headers to system message and the last user message
        to maximize cache hit rates.

        Returns:
            Tuple of (system_prompt_or_None, anthropic_messages_list).
        """
        system: str | None = None
        anthropic_messages: list[dict] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system = content
            elif role in ("user", "assistant"):
                anthropic_messages.append({"role": role, "content": content})

        return system, anthropic_messages

    def _build_system_with_cache(self, system: str | None) -> list[dict] | None:
        """Build system parameter with prompt caching enabled.

        Uses cache_control on the system block to enable Anthropic prompt caching,
        reducing latency and cost for repeated system prompts.
        """
        if not system:
            return None
        return [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send messages to Claude and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            tools: Optional tool definitions (not yet implemented).
            **kwargs: Additional options: temperature, max_tokens, etc.

        Returns:
            LLMResponse with content, model, and usage metadata.

        Raises:
            TimeoutError: If the request times out.
            ConnectionError: If the API endpoint is unreachable.
            RuntimeError: If the circuit breaker is open.
        """
        if not self._circuit_breaker.allow_request():
            raise RuntimeError(
                "Circuit breaker is open: Claude API has experienced repeated failures. "
                "Requests will be retried automatically after the recovery period."
            )

        system, anthropic_messages = self._convert_messages(messages)

        # Build request parameters
        request_kwargs: dict = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }

        # Add system with prompt caching
        system_blocks = self._build_system_with_cache(system)
        if system_blocks:
            request_kwargs["system"] = system_blocks

        # Optional parameters
        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            request_kwargs["top_p"] = kwargs["top_p"]
        if "stop_sequences" in kwargs:
            request_kwargs["stop_sequences"] = kwargs["stop_sequences"]

        try:
            response = await self._client.messages.create(**request_kwargs)
            self._circuit_breaker.record_success()

            # Extract text content from response blocks
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            # Build usage dict
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": (
                    response.usage.input_tokens + response.usage.output_tokens
                ),
            }

            # Include cache usage info if available
            if hasattr(response.usage, "cache_creation_input_tokens"):
                usage["cache_creation_input_tokens"] = (
                    response.usage.cache_creation_input_tokens
                )
            if hasattr(response.usage, "cache_read_input_tokens"):
                usage["cache_read_input_tokens"] = (
                    response.usage.cache_read_input_tokens
                )

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason or "stop",
            )

        except anthropic.APITimeoutError as e:
            self._circuit_breaker.record_failure()
            raise TimeoutError(
                f"Claude API request timed out after {self._timeout}s: {e}"
            ) from e

        except anthropic.APIConnectionError as e:
            self._circuit_breaker.record_failure()
            raise ConnectionError(
                f"Failed to connect to Claude API: {e}"
            ) from e

        except anthropic.RateLimitError as e:
            self._circuit_breaker.record_failure()
            raise RuntimeError(
                f"Claude API rate limit exceeded: {e}"
            ) from e

        except anthropic.APIStatusError as e:
            self._circuit_breaker.record_failure()
            raise RuntimeError(
                f"Claude API error (status {e.status_code}): {e.message}"
            ) from e

    async def stream(
        self,
        messages: list[dict],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream tokens from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Additional options: temperature, max_tokens, etc.

        Yields:
            String tokens as they are generated.

        Raises:
            TimeoutError: If the request times out.
            ConnectionError: If the API endpoint is unreachable.
            RuntimeError: If the circuit breaker is open.
        """
        if not self._circuit_breaker.allow_request():
            raise RuntimeError(
                "Circuit breaker is open: Claude API has experienced repeated failures. "
                "Requests will be retried automatically after the recovery period."
            )

        system, anthropic_messages = self._convert_messages(messages)

        # Build request parameters
        request_kwargs: dict = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }

        # Add system with prompt caching
        system_blocks = self._build_system_with_cache(system)
        if system_blocks:
            request_kwargs["system"] = system_blocks

        # Optional parameters
        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            request_kwargs["top_p"] = kwargs["top_p"]
        if "stop_sequences" in kwargs:
            request_kwargs["stop_sequences"] = kwargs["stop_sequences"]

        try:
            async with self._client.messages.stream(**request_kwargs) as stream:
                self._circuit_breaker.record_success()
                async for text in stream.text_stream:
                    yield text

        except anthropic.APITimeoutError as e:
            self._circuit_breaker.record_failure()
            raise TimeoutError(
                f"Claude API stream timed out after {self._timeout}s: {e}"
            ) from e

        except anthropic.APIConnectionError as e:
            self._circuit_breaker.record_failure()
            raise ConnectionError(
                f"Failed to connect to Claude API for streaming: {e}"
            ) from e

        except anthropic.RateLimitError as e:
            self._circuit_breaker.record_failure()
            raise RuntimeError(
                f"Claude API rate limit exceeded during streaming: {e}"
            ) from e

        except anthropic.APIStatusError as e:
            self._circuit_breaker.record_failure()
            raise RuntimeError(
                f"Claude API streaming error (status {e.status_code}): {e.message}"
            ) from e
