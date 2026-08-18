"""Unit tests for OpenAI chat LLM provider."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.base import LLMProvider, LLMResponse
from app.providers.llm.openai_provider import OpenAILLMProvider


def test_requires_api_key():
    with pytest.raises(ValueError, match="OpenAI API key is required"):
        OpenAILLMProvider(api_key="")


def test_implements_llm_provider():
    assert isinstance(OpenAILLMProvider(api_key="sk-test"), LLMProvider)


@pytest.mark.asyncio
async def test_invoke_maps_response():
    provider = OpenAILLMProvider(api_key="sk-test", model_name="gpt-4o-mini")
    usage = MagicMock(prompt_tokens=3, completion_tokens=4, total_tokens=7)
    message = MagicMock(content="ok")
    choice = MagicMock(message=message, finish_reason="stop")
    response = MagicMock(choices=[choice], model="gpt-4o-mini", usage=usage)
    provider._client.chat.completions.create = AsyncMock(return_value=response)

    result = await provider.invoke([{"role": "user", "content": "hi"}])
    assert isinstance(result, LLMResponse)
    assert result.content == "ok"
    assert result.usage["total_tokens"] == 7


@pytest.mark.asyncio
async def test_invoke_passes_tools_and_handles_missing_usage():
    provider = OpenAILLMProvider(api_key="sk-test", model_name="gpt-4o-mini")
    message = MagicMock(content=None)
    choice = MagicMock(message=message, finish_reason=None)
    response = MagicMock(choices=[choice], model=None, usage=None)
    provider._client.chat.completions.create = AsyncMock(return_value=response)

    result = await provider.invoke(
        [{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "lookup"}}],
    )
    assert result.content == ""
    assert result.usage["total_tokens"] == 0
    kwargs = provider._client.chat.completions.create.await_args.kwargs
    assert "tools" in kwargs


@pytest.mark.asyncio
async def test_invoke_timeout_and_connection():
    from openai import APIConnectionError, APITimeoutError

    provider = OpenAILLMProvider(api_key="sk-test")
    provider._client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=MagicMock())
    )
    with pytest.raises(TimeoutError, match="did not respond within"):
        await provider.invoke([{"role": "user", "content": "hi"}])

    provider._client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )
    with pytest.raises(ConnectionError, match="unreachable"):
        await provider.invoke([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_stream_yields_delta_and_errors():
    from openai import APIConnectionError, APITimeoutError

    provider = OpenAILLMProvider(api_key="sk-test")
    chunk = MagicMock()
    chunk.choices = [MagicMock(delta=MagicMock(content="สวัสดี"))]

    class _Stream:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._chunks:
                raise StopAsyncIteration
            return self._chunks.pop(0)

    provider._client.chat.completions.create = AsyncMock(return_value=_Stream([chunk]))
    parts = [part async for part in provider.stream([{"role": "user", "content": "hi"}])]
    assert parts == ["สวัสดี"]

    provider._client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=MagicMock())
    )
    with pytest.raises(TimeoutError):
        async for _ in provider.stream([{"role": "user", "content": "hi"}]):
            pass

    provider._client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )
    with pytest.raises(ConnectionError):
        async for _ in provider.stream([{"role": "user", "content": "hi"}]):
            pass
