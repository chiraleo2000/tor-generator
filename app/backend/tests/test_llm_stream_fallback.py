"""Shared stream_llm_tokens contract for every LLM provider class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.api.sse import SSE_HEADERS, sse_streaming_response
from app.providers.base import LLMProvider, LLMResponse
from app.providers.llm.stream_fallback import STREAM_FALLBACK_SLICE, stream_llm_tokens


class _FakeLLM(LLMProvider):
    def __init__(
        self,
        *,
        pieces: list[str] | None = None,
        invoke_text: str = "",
        stream_error: BaseException | None = None,
        invoke_error: BaseException | None = None,
    ) -> None:
        self.pieces = pieces
        self.invoke_text = invoke_text
        self.stream_error = stream_error
        self.invoke_error = invoke_error
        self.invoke_calls = 0

    async def invoke(self, messages, tools=None, **kwargs) -> LLMResponse:
        del messages, tools, kwargs
        self.invoke_calls += 1
        if self.invoke_error is not None:
            raise self.invoke_error
        return LLMResponse(content=self.invoke_text, model="fake", usage={})

    async def stream(self, messages, **kwargs):
        del messages, kwargs
        if self.stream_error is not None:
            raise self.stream_error
            yield ""  # pragma: no cover
        if self.pieces is None:
            return
        for piece in self.pieces:
            yield piece


@pytest.mark.asyncio
async def test_helper_yields_native_stream_tokens():
    llm = _FakeLLM(pieces=["ก", "ข"])
    parts = [piece async for piece in stream_llm_tokens(llm, [{"role": "user", "content": "hi"}])]
    assert parts == ["ก", "ข"]
    assert llm.invoke_calls == 0


@pytest.mark.asyncio
async def test_helper_slices_invoke_when_stream_is_empty():
    text = "x" * (STREAM_FALLBACK_SLICE + 15)
    llm = _FakeLLM(pieces=None, invoke_text=text)
    parts = [piece async for piece in stream_llm_tokens(llm, [{"role": "user", "content": "hi"}])]
    assert "".join(parts) == text
    assert parts[0] == "x" * STREAM_FALLBACK_SLICE
    assert llm.invoke_calls == 1


@pytest.mark.asyncio
async def test_helper_falls_back_when_stream_raises():
    llm = _FakeLLM(stream_error=TimeoutError("stream down"), invoke_text="จาก invoke")
    parts = [piece async for piece in stream_llm_tokens(llm, [{"role": "user", "content": "hi"}])]
    assert parts == ["จาก invoke"]


@pytest.mark.asyncio
async def test_helper_reraises_stream_error_when_invoke_has_no_text():
    llm = _FakeLLM(stream_error=RuntimeError("llm down"), invoke_text="")
    with pytest.raises(RuntimeError, match="llm down"):
        [piece async for piece in stream_llm_tokens(llm, [{"role": "user", "content": "hi"}])]


@pytest.mark.asyncio
async def test_helper_empty_stream_without_invoke_yields_nothing():
    class _StreamOnly:
        async def stream(self, _messages, **_kwargs):
            if False:
                yield ""

    parts = [
        piece
        async for piece in stream_llm_tokens(
            _StreamOnly(),  # type: ignore[arg-type]
            [{"role": "user", "content": "hi"}],
        )
    ]
    assert parts == []


@pytest.mark.asyncio
async def test_helper_reraises_stream_error_when_invoke_also_fails():
    llm = _FakeLLM(
        stream_error=TimeoutError("stream down"),
        invoke_error=ConnectionError("invoke down"),
    )
    with pytest.raises(TimeoutError, match="stream down"):
        [piece async for piece in stream_llm_tokens(llm, [{"role": "user", "content": "hi"}])]


def _openai():
    from app.providers.llm.openai_provider import OpenAILLMProvider

    return OpenAILLMProvider(api_key="sk-test")


def _azure():
    from app.providers.llm.azure_foundry_provider import AzureFoundryLLMProvider

    return AzureFoundryLLMProvider(
        api_key="k",
        endpoint="https://example.openai.azure.com",
        deployment="gpt-4o",
    )


def _compat():
    from app.providers.llm.lm_studio_provider import OpenAICompatLLMProvider

    return OpenAICompatLLMProvider(base_url="http://localhost:1234/v1", model_name="local")


def _gemini():
    from app.providers.llm.gemini_provider import GeminiLLMProvider

    return GeminiLLMProvider(api_key="fake")


def _claude():
    from app.providers.llm.claude_provider import ClaudeSonnetProvider

    return ClaudeSonnetProvider(api_key="sk-ant-test")


def _lm_studio():
    from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

    return LMStudioLocalProvider(base_url="http://localhost:1234/v1")


def _bedrock():
    from app.providers.llm.bedrock_provider import BedrockLLMProvider

    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client",
        return_value=MagicMock(),
    ):
        return BedrockLLMProvider(region="ap-southeast-1", model_id="anthropic.claude")


PROVIDER_FACTORIES = [
    ("openai", _openai),
    ("azure_foundry", _azure),
    ("openai_compatible", _compat),
    ("gemini", _gemini),
    ("claude", _claude),
    ("lm_studio", _lm_studio),
    ("bedrock", _bedrock),
]


@pytest.mark.parametrize("name,factory", PROVIDER_FACTORIES)
@pytest.mark.asyncio
async def test_every_provider_class_native_stream_terminates(name, factory):
    llm = factory()

    async def native(_messages, **_kwargs):
        yield f"{name}-token"

    llm.stream = native  # type: ignore[method-assign]
    parts = [piece async for piece in stream_llm_tokens(llm, [{"role": "user", "content": "hi"}])]
    assert parts == [f"{name}-token"]


@pytest.mark.parametrize("name,factory", PROVIDER_FACTORIES)
@pytest.mark.asyncio
async def test_every_provider_class_invoke_fallback_terminates(name, factory):
    llm = factory()

    async def empty(_messages, **_kwargs):
        if False:
            yield ""

    async def invoke(_messages, tools=None, **_kwargs):
        return LLMResponse(content=f"{name}-full", model=name, usage={})

    llm.stream = empty  # type: ignore[method-assign]
    llm.invoke = invoke  # type: ignore[method-assign]
    parts = [piece async for piece in stream_llm_tokens(llm, [{"role": "user", "content": "hi"}])]
    assert "".join(parts) == f"{name}-full"


def test_sse_headers_disable_proxy_buffering():
    assert SSE_HEADERS["Cache-Control"] == "no-cache"
    assert SSE_HEADERS["X-Accel-Buffering"] == "no"

    async def body():
        yield "event: done\ndata: {}\n\n"

    response = sse_streaming_response(body())
    assert response.media_type == "text/event-stream"
    assert response.headers["x-accel-buffering"] == "no"
    assert response.headers["cache-control"] == "no-cache"
