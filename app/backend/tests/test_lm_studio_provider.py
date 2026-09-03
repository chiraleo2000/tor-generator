"""Unit tests for LMStudioLocalProvider.

Tests cover:
- Constructor configuration
- invoke() success and error handling
- stream() success and error handling
- Proper conversion of OpenAI-compatible responses to LLMResponse
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm_tokens import DEFAULT_MAX_TOKENS
from app.providers.base import LLMProvider, LLMResponse
from app.providers.llm.lm_studio_provider import LMStudioLocalProvider


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


class TestLMStudioProviderInit:
    """Tests for provider initialization."""

    def test_is_subclass_of_llm_provider(self):
        assert issubclass(LMStudioLocalProvider, LLMProvider)

    def test_default_values_from_config(self, monkeypatch):
        monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://host.docker.internal:1234/v1")
        monkeypatch.setenv("LM_STUDIO_MODEL", "google/gemma-4-e4b")
        monkeypatch.setenv("LM_STUDIO_TIMEOUT", "180")
        provider = LMStudioLocalProvider()
        assert provider._base_url == "http://host.docker.internal:1234/v1"
        assert provider._model_name == "google/gemma-4-e4b"
        assert provider._timeout == 180.0

    def test_custom_base_url(self):
        provider = LMStudioLocalProvider(base_url="http://localhost:5000/v1")
        assert provider._base_url == "http://localhost:5000/v1"

    def test_custom_model_name(self):
        provider = LMStudioLocalProvider(model_name="openthaichinda-4b")
        assert provider._model_name == "openthaichinda-4b"

    def test_custom_timeout(self):
        provider = LMStudioLocalProvider(timeout=120.0)
        assert provider._timeout == 120.0

    def test_client_uses_not_needed_api_key(self):
        provider = LMStudioLocalProvider(base_url="http://localhost:1234/v1")
        assert provider._client.api_key == "not-needed"
        assert provider._client.max_retries == 0

    def test_client_uses_provided_base_url(self):
        provider = LMStudioLocalProvider(base_url="http://my-server:8080/v1")
        assert str(provider._client.base_url) == "http://my-server:8080/v1/"

    def test_openai_compat_alias_is_same_class(self):
        from app.providers.llm.lm_studio_provider import OpenAICompatLLMProvider

        assert OpenAICompatLLMProvider is LMStudioLocalProvider


# ---------------------------------------------------------------------------
# invoke() tests
# ---------------------------------------------------------------------------


class TestInvoke:
    """Tests for the invoke() method."""

    def setup_method(self):
        self.provider = LMStudioLocalProvider(
            base_url="http://localhost:1234/v1",
            model_name="test-model",
            timeout=30.0,
        )

    @pytest.mark.asyncio
    async def test_successful_invocation(self):
        """Test that a normal response is correctly mapped to LLMResponse."""
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 120
        mock_usage.total_tokens = 170

        mock_message = MagicMock()
        mock_message.content = "Generated TOR section content"

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await self.provider.invoke(
            messages=[
                {"role": "system", "content": "You are a TOR drafting assistant."},
                {"role": "user", "content": "Draft background section."},
            ],
            temperature=0.7,
        )

        assert isinstance(result, LLMResponse)
        assert result.content == "Generated TOR section content"
        assert result.model == "test-model"
        assert result.usage == {
            "prompt_tokens": 50,
            "completion_tokens": 120,
            "total_tokens": 170,
        }
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_invocation_with_tools(self):
        """Test that tools are passed to the API when provided."""
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15

        mock_message = MagicMock()
        mock_message.content = "OK"

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage

        mock_create = AsyncMock(return_value=mock_response)
        self.provider._client.chat.completions.create = mock_create

        tools = [{"type": "function", "function": {"name": "get_budget"}}]
        await self.provider.invoke(
            messages=[{"role": "user", "content": "test"}],
            tools=tools,
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["tools"] == tools

    @pytest.mark.asyncio
    async def test_invocation_without_tools(self):
        """Test that tools key is omitted when no tools provided."""
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15

        mock_message = MagicMock()
        mock_message.content = "OK"

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage

        mock_create = AsyncMock(return_value=mock_response)
        self.provider._client.chat.completions.create = mock_create

        await self.provider.invoke(
            messages=[{"role": "user", "content": "test"}],
        )

        call_kwargs = mock_create.call_args[1]
        assert "tools" not in call_kwargs
        assert call_kwargs["max_tokens"] == DEFAULT_MAX_TOKENS

    @pytest.mark.asyncio
    async def test_handles_none_content(self):
        """Test that None content from model is converted to empty string."""
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 0
        mock_usage.total_tokens = 10

        mock_message = MagicMock()
        mock_message.content = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await self.provider.invoke(
            messages=[{"role": "user", "content": "test"}]
        )
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_handles_none_usage(self):
        """Test graceful handling when usage stats are None."""
        mock_message = MagicMock()
        mock_message.content = "Response"

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = None

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await self.provider.invoke(
            messages=[{"role": "user", "content": "test"}]
        )
        assert result.usage == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """Test that API timeout is converted to TimeoutError."""
        from openai import APITimeoutError

        self.provider._client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )

        with pytest.raises(TimeoutError, match="did not respond within"):
            await self.provider.invoke(
                messages=[{"role": "user", "content": "test"}]
            )

    @pytest.mark.asyncio
    async def test_connection_error_raises_connection_error(self):
        """Test that connection failure is converted to ConnectionError."""
        from openai import APIConnectionError

        self.provider._client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(ConnectionError, match="unreachable"):
            await self.provider.invoke(
                messages=[{"role": "user", "content": "test"}]
            )

    @pytest.mark.asyncio
    async def test_connection_error_retries_then_succeeds(self):
        from openai import APIConnectionError

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 1
        mock_usage.completion_tokens = 1
        mock_usage.total_tokens = 2
        mock_message = MagicMock()
        mock_message.content = "ok"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage
        self.provider._client.chat.completions.create = AsyncMock(
            side_effect=[APIConnectionError(request=MagicMock()), mock_response]
        )
        result = await self.provider.invoke(
            messages=[{"role": "user", "content": "test"}]
        )
        assert result.content == "ok"
        assert self.provider._client.chat.completions.create.await_count == 2

    @pytest.mark.asyncio
    async def test_other_exceptions_propagate(self):
        """Test that unexpected exceptions are re-raised."""
        self.provider._client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("Unexpected")
        )

        with pytest.raises(RuntimeError, match="Unexpected"):
            await self.provider.invoke(
                messages=[{"role": "user", "content": "test"}]
            )


# ---------------------------------------------------------------------------
# stream() tests
# ---------------------------------------------------------------------------


class TestStream:
    """Tests for the stream() method."""

    def setup_method(self):
        self.provider = LMStudioLocalProvider(
            base_url="http://localhost:1234/v1",
            model_name="test-model",
            timeout=30.0,
        )

    @pytest.mark.asyncio
    async def test_successful_stream(self):
        """Test streaming yields content deltas correctly."""

        # Build mock chunks
        def make_chunk(content):
            delta = MagicMock()
            delta.content = content
            choice = MagicMock()
            choice.delta = delta
            chunk = MagicMock()
            chunk.choices = [choice]
            return chunk

        chunks = [
            make_chunk("Hello"),
            make_chunk(" "),
            make_chunk("world"),
        ]

        # Create an async iterator from chunks
        async def mock_stream():
            for chunk in chunks:
                yield chunk

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )

        collected = []
        async for token in self.provider.stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            collected.append(token)

        assert "".join(collected) == "Hello world"
        assert (
            self.provider._client.chat.completions.create.call_args[1]["max_tokens"]
            == DEFAULT_MAX_TOKENS
        )

    @pytest.mark.asyncio
    async def test_stream_skips_empty_deltas(self):
        """Test that chunks with None or empty content are skipped."""

        def make_chunk(content):
            delta = MagicMock()
            delta.content = content
            choice = MagicMock()
            choice.delta = delta
            chunk = MagicMock()
            chunk.choices = [choice]
            return chunk

        chunks = [
            make_chunk("A"),
            make_chunk(None),
            make_chunk(""),
            make_chunk("B"),
        ]

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )

        collected = []
        async for token in self.provider.stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            collected.append(token)

        assert "".join(collected) == "AB"

    @pytest.mark.asyncio
    async def test_stream_skips_empty_choices(self):
        """Test that chunks with no choices are skipped."""
        def make_chunk_with_content(content):
            delta = MagicMock()
            delta.content = content
            choice = MagicMock()
            choice.delta = delta
            chunk = MagicMock()
            chunk.choices = [choice]
            return chunk

        empty_chunk = MagicMock()
        empty_chunk.choices = []

        chunks = [
            make_chunk_with_content("First"),
            empty_chunk,
            make_chunk_with_content("Second"),
        ]

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )

        collected = []
        async for token in self.provider.stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            collected.append(token)

        assert "".join(collected) == "FirstSecond"

    @pytest.mark.asyncio
    async def test_stream_timeout_raises_timeout_error(self):
        """Test that timeout during stream setup raises TimeoutError."""
        from openai import APITimeoutError

        self.provider._client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )

        with pytest.raises(TimeoutError, match="did not respond within"):
            async for _ in self.provider.stream(
                messages=[{"role": "user", "content": "test"}]
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_httpx_timeout_name_raises_timeout_error(self):
        class ReadTimeout(Exception):
            pass

        self.provider._client.chat.completions.create = AsyncMock(
            side_effect=ReadTimeout("read timed out")
        )
        with pytest.raises(TimeoutError, match="did not respond within"):
            async for _ in self.provider.stream(
                messages=[{"role": "user", "content": "test"}]
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_does_not_yield_reasoning_content(self):
        delta = MagicMock()
        delta.content = ""
        delta.reasoning_content = "Here's a thinking process"
        choice = MagicMock()
        choice.delta = delta
        chunk = MagicMock()
        chunk.choices = [choice]

        async def mock_stream():
            yield chunk

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )
        collected = [
            token
            async for token in self.provider.stream(
                messages=[{"role": "user", "content": "test"}]
            )
        ]
        assert collected == []

    @pytest.mark.asyncio
    async def test_stream_yields_thai_final_not_thinking(self):
        def make_chunk(content):
            delta = MagicMock()
            delta.content = content
            choice = MagicMock()
            choice.delta = delta
            chunk = MagicMock()
            chunk.choices = [choice]
            return chunk

        chunks = [
            make_chunk("Here's a thinking process to construct the answer:\n\n"),
            make_chunk("1. Analyze the Request.\n\n"),
            make_chunk("**Final Output Generation.**\n\n"),
            make_chunk("ตามระเบียบกระทรวงการคลัง งวดงานและการจ่ายเงินแบ่งเป็นสี่งวด"),
        ]

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )
        collected = [
            token
            async for token in self.provider.stream(
                messages=[{"role": "user", "content": "งวดจ่าย"}]
            )
        ]
        text = "".join(collected)
        assert "thinking process" not in text.lower()
        assert "Analyze the Request" not in text
        assert "ตามระเบียบกระทรวงการคลัง" in text

    @pytest.mark.asyncio
    async def test_stream_connection_error_raises_connection_error(self):
        """Test that connection failure during stream raises ConnectionError."""
        from openai import APIConnectionError

        self.provider._client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(ConnectionError, match="unreachable"):
            async for _ in self.provider.stream(
                messages=[{"role": "user", "content": "test"}]
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_passes_kwargs(self):
        """Test that extra kwargs are forwarded to the API call."""

        async def mock_stream():
            return
            yield  # Make it an async generator

        mock_create = AsyncMock(return_value=mock_stream())
        self.provider._client.chat.completions.create = mock_create

        async for _ in self.provider.stream(
            messages=[{"role": "user", "content": "test"}],
            temperature=0.5,
            max_tokens=500,
        ):
            pass

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["stream"] is True

    @pytest.mark.asyncio
    async def test_stream_retries_after_model_unload(self, monkeypatch):
        monkeypatch.setattr(
            "app.providers.llm.lm_studio_provider.asyncio.sleep",
            AsyncMock(),
        )

        def make_chunk(content):
            delta = MagicMock()
            delta.content = content
            choice = MagicMock()
            choice.delta = delta
            chunk = MagicMock()
            chunk.choices = [choice]
            return chunk

        async def mock_stream():
            yield make_chunk("กรมบัญชีกลาง")

        mock_create = AsyncMock(
            side_effect=[
                RuntimeError("Model unloaded by user or API request."),
                mock_stream(),
            ]
        )
        self.provider._client.chat.completions.create = mock_create
        collected: list[str] = []
        async for token in self.provider.stream(
            messages=[{"role": "user", "content": "test"}]
        ):
            collected.append(token)
        assert "".join(collected) == "กรมบัญชีกลาง"
        assert mock_create.await_count == 2


    @pytest.mark.asyncio
    async def test_disable_thinking_sets_extra_body(self):
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 1
        mock_usage.completion_tokens = 1
        mock_usage.total_tokens = 2
        mock_message = MagicMock()
        mock_message.content = "{}"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage
        mock_create = AsyncMock(return_value=mock_response)
        self.provider._client.chat.completions.create = mock_create

        await self.provider.invoke(
            messages=[{"role": "user", "content": "json"}],
            disable_thinking=True,
        )
        sent = mock_create.call_args.kwargs
        assert sent["extra_body"]["enable_thinking"] is False
        assert "disable_thinking" not in sent

    @pytest.mark.asyncio
    async def test_sglang_url_sends_guided_json(self):
        provider = LMStudioLocalProvider(
            base_url="http://sglang-llm:30000/v1",
            model_name="test-model",
            timeout=30.0,
        )
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 1
        mock_usage.completion_tokens = 1
        mock_usage.total_tokens = 2
        mock_message = MagicMock()
        mock_message.content = "{}"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage
        mock_create = AsyncMock(return_value=mock_response)
        provider._client.chat.completions.create = mock_create
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
        await provider.invoke(
            messages=[{"role": "user", "content": "json"}],
            json_schema=schema,
            json_schema_name="sample",
            disable_thinking=True,
        )
        sent = mock_create.call_args.kwargs
        assert sent["extra_body"]["guided_json"] == schema
        assert sent["response_format"]["type"] == "json_schema"
        assert "json_schema" not in sent

    @pytest.mark.asyncio
    async def test_uses_reasoning_content_when_message_empty(self):
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 1
        mock_usage.completion_tokens = 4
        mock_usage.total_tokens = 5
        mock_message = MagicMock()
        mock_message.content = ""
        mock_message.reasoning_content = '{"slot_map": {}}'
        mock_message.reasoning = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage
        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        result = await self.provider.invoke(
            messages=[{"role": "user", "content": "json"}]
        )
        assert result.content == '{"slot_map": {}}'

    @pytest.mark.asyncio
    async def test_invoke_strips_thinking_keeps_thai(self):
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30
        mock_message = MagicMock()
        mock_message.content = (
            "Here's a thinking process to construct the answer:\n"
            "1. **Analyze the Request:** extract งวดจ่าย.\n"
            "**Final Output Generation.**\n"
            "ตามระเบียบที่เกี่ยวข้อง งวดงานและการจ่ายเงินแบ่งเป็นสี่งวด"
        )
        mock_message.reasoning_content = None
        mock_message.reasoning = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage
        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        result = await self.provider.invoke(
            messages=[{"role": "user", "content": "งวดจ่าย"}]
        )
        assert "thinking process" not in result.content.lower()
        assert "ตามระเบียบที่เกี่ยวข้อง" in result.content

    @pytest.mark.asyncio
    async def test_invoke_drops_english_reasoning_not_json(self):
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 1
        mock_usage.completion_tokens = 4
        mock_usage.total_tokens = 5
        mock_message = MagicMock()
        mock_message.content = ""
        mock_message.reasoning_content = (
            "Here's a thinking process to construct the answer"
        )
        mock_message.reasoning = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage
        self.provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        result = await self.provider.invoke(
            messages=[{"role": "user", "content": "json"}]
        )
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_invoke_injects_output_contract_and_allows_thinking(self):
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 1
        mock_usage.completion_tokens = 1
        mock_usage.total_tokens = 2
        mock_message = MagicMock()
        mock_message.content = "ตามระเบียบ"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage
        mock_create = AsyncMock(return_value=mock_response)
        self.provider._client.chat.completions.create = mock_create
        await self.provider.invoke(messages=[{"role": "user", "content": "ถาม"}])
        sent = mock_create.call_args.kwargs
        assert sent["extra_body"]["enable_thinking"] is True
        assert sent["messages"][0]["role"] == "system"
        assert "ห้ามแสดงกระบวนการคิด" in sent["messages"][0]["content"]
