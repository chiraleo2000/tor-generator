"""Unit tests for ClaudeSonnetProvider.

Tests cover:
- Constructor validation
- Message format conversion
- Circuit breaker state transitions
- invoke() error handling
- stream() error handling
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.llm.claude_provider import (
    CircuitBreaker,
    CircuitState,
    ClaudeSonnetProvider,
)


# ---------------------------------------------------------------------------
# CircuitBreaker unit tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_allows_requests_when_closed(self):
        cb = CircuitBreaker()
        assert cb.allow_request() is True

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_opens_at_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_transitions_to_half_open_after_recovery(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=0.1)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_success_closes_from_half_open(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=0.1)
        for _ in range(5):
            cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=0.1)
        for _ in range(5):
            cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        cb.record_success()
        # After reset, need 5 new failures to open
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# ClaudeSonnetProvider unit tests
# ---------------------------------------------------------------------------


class TestClaudeSonnetProviderInit:
    """Tests for provider initialization."""

    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="API key is required"):
            ClaudeSonnetProvider(api_key="")

    def test_default_model(self):
        provider = ClaudeSonnetProvider(api_key="test-key")
        assert provider._model == "claude-sonnet-4-20250514"

    def test_custom_model(self):
        provider = ClaudeSonnetProvider(api_key="test-key", model="claude-3-haiku-20240307")
        assert provider._model == "claude-3-haiku-20240307"

    def test_default_timeout(self):
        provider = ClaudeSonnetProvider(api_key="test-key")
        assert provider._timeout == 60.0

    def test_custom_timeout(self):
        provider = ClaudeSonnetProvider(api_key="test-key", timeout=120.0)
        assert provider._timeout == 120.0


class TestMessageConversion:
    """Tests for _convert_messages."""

    def setup_method(self):
        self.provider = ClaudeSonnetProvider(api_key="test-key")

    def test_extracts_system_message(self):
        messages = [
            {"role": "system", "content": "You are a helper."},
            {"role": "user", "content": "Hello"},
        ]
        system, msgs = self.provider._convert_messages(messages)
        assert system == "You are a helper."
        assert msgs == [{"role": "user", "content": "Hello"}]

    def test_no_system_message(self):
        messages = [{"role": "user", "content": "Hello"}]
        system, msgs = self.provider._convert_messages(messages)
        assert system is None
        assert msgs == [{"role": "user", "content": "Hello"}]

    def test_multi_turn_conversation(self):
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User 1"},
            {"role": "assistant", "content": "Assistant 1"},
            {"role": "user", "content": "User 2"},
        ]
        system, msgs = self.provider._convert_messages(messages)
        assert system == "System prompt"
        assert len(msgs) == 3
        assert msgs[0] == {"role": "user", "content": "User 1"}
        assert msgs[1] == {"role": "assistant", "content": "Assistant 1"}
        assert msgs[2] == {"role": "user", "content": "User 2"}


class TestSystemCacheBuilding:
    """Tests for _build_system_with_cache."""

    def setup_method(self):
        self.provider = ClaudeSonnetProvider(api_key="test-key")

    def test_returns_none_for_no_system(self):
        result = self.provider._build_system_with_cache(None)
        assert result is None

    def test_returns_cached_block(self):
        result = self.provider._build_system_with_cache("You are a helper.")
        assert result == [
            {
                "type": "text",
                "text": "You are a helper.",
                "cache_control": {"type": "ephemeral"},
            }
        ]


class TestInvoke:
    """Tests for the invoke() method."""

    def setup_method(self):
        self.provider = ClaudeSonnetProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self):
        # Force circuit breaker open
        for _ in range(5):
            self.provider._circuit_breaker.record_failure()

        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            await self.provider.invoke(messages=[{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_timeout_error_raises_timeout(self):
        import anthropic

        mock_create = AsyncMock(
            side_effect=anthropic.APITimeoutError(request=MagicMock())
        )
        self.provider._client.messages.create = mock_create

        with pytest.raises(TimeoutError, match="timed out"):
            await self.provider.invoke(messages=[{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_connection_error_raises_connection_error(self):
        import anthropic

        mock_create = AsyncMock(
            side_effect=anthropic.APIConnectionError(request=MagicMock())
        )
        self.provider._client.messages.create = mock_create

        with pytest.raises(ConnectionError, match="Failed to connect"):
            await self.provider.invoke(messages=[{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_successful_invocation(self):
        # Mock a successful response
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Generated content"

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage = mock_usage
        mock_response.stop_reason = "end_turn"

        mock_create = AsyncMock(return_value=mock_response)
        self.provider._client.messages.create = mock_create

        result = await self.provider.invoke(
            messages=[
                {"role": "system", "content": "You are a helper."},
                {"role": "user", "content": "Draft a section."},
            ],
            temperature=0.7,
        )

        assert result.content == "Generated content"
        assert result.model == "claude-sonnet-4-20250514"
        assert result.usage["prompt_tokens"] == 100
        assert result.usage["completion_tokens"] == 50
        assert result.usage["total_tokens"] == 150
        assert result.finish_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_records_success_after_invoke(self):
        mock_usage = MagicMock()
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 5

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "OK"

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage = mock_usage
        mock_response.stop_reason = "stop"

        self.provider._client.messages.create = AsyncMock(return_value=mock_response)

        # Record some failures first (but not enough to open)
        for _ in range(3):
            self.provider._circuit_breaker.record_failure()

        await self.provider.invoke(messages=[{"role": "user", "content": "test"}])
        assert self.provider._circuit_breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_records_failure_on_timeout(self):
        import anthropic

        self.provider._client.messages.create = AsyncMock(
            side_effect=anthropic.APITimeoutError(request=MagicMock())
        )

        with pytest.raises(TimeoutError):
            await self.provider.invoke(messages=[{"role": "user", "content": "test"}])

        assert self.provider._circuit_breaker._failure_count == 1


class TestStream:
    """Tests for the stream() method."""

    def setup_method(self):
        self.provider = ClaudeSonnetProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_stream_when_open(self):
        for _ in range(5):
            self.provider._circuit_breaker.record_failure()

        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            async for _ in self.provider.stream(
                messages=[{"role": "user", "content": "test"}]
            ):
                pass

    @pytest.mark.asyncio
    async def test_timeout_error_in_stream(self):
        import anthropic

        # Create an async context manager mock that raises on entry
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(
            side_effect=anthropic.APITimeoutError(request=MagicMock())
        )
        mock_stream_cm.__aexit__ = AsyncMock(return_value=False)

        self.provider._client.messages.stream = MagicMock(return_value=mock_stream_cm)

        with pytest.raises(TimeoutError, match="timed out"):
            async for _ in self.provider.stream(
                messages=[{"role": "user", "content": "test"}]
            ):
                pass
