"""Unit tests for Gemini chat and embedding providers (mocked HTTP)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.embedding.gemini_provider import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider


def test_gemini_llm_requires_key():
    with pytest.raises(ValueError, match="Gemini API key is required"):
        GeminiLLMProvider(api_key="")


def test_gemini_embedding_requires_key():
    with pytest.raises(ValueError, match="Gemini API key is required"):
        GeminiEmbeddingProvider(api_key="")


def test_gemini_embedding_fit_truncates_and_pads():
    provider = GeminiEmbeddingProvider(api_key="k", dimensions=4)
    assert provider._fit([1.0, 2.0, 3.0, 4.0, 5.0]) == [1.0, 2.0, 3.0, 4.0]
    assert provider._fit([1.0, 2.0]) == [1.0, 2.0, 0.0, 0.0]


def _async_client(response: MagicMock) -> MagicMock:
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_gemini_invoke_parses_text():
    provider = GeminiLLMProvider(api_key="fake", model_name="gemini-2.0-flash")
    http_response = MagicMock()
    http_response.raise_for_status = MagicMock()
    http_response.json.return_value = {
        "candidates": [
            {
                "content": {"parts": [{"text": "สวัสดี"}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 1,
            "candidatesTokenCount": 2,
            "totalTokenCount": 3,
        },
    }
    with patch(
        "app.providers.llm.gemini_provider.httpx.AsyncClient",
        return_value=_async_client(http_response),
    ):
        result = await provider.invoke([{"role": "user", "content": "hi"}])
    assert result.content == "สวัสดี"
    assert result.usage["total_tokens"] == 3


@pytest.mark.asyncio
async def test_gemini_embed_query_fits_768():
    provider = GeminiEmbeddingProvider(api_key="fake", dimensions=768)
    http_response = MagicMock()
    http_response.raise_for_status = MagicMock()
    http_response.json.return_value = {"embedding": {"values": [0.1, 0.2]}}
    with patch(
        "app.providers.embedding.gemini_provider.httpx.AsyncClient",
        return_value=_async_client(http_response),
    ):
        vector = await provider.embed_query("ทดสอบ")
    assert len(vector) == 768
    assert vector[0] == 0.1
    assert vector[1] == 0.2
    assert vector[-1] == 0.0


@pytest.mark.asyncio
async def test_gemini_invoke_system_generation_and_empty_candidates():
    provider = GeminiLLMProvider(api_key="fake", model_name="gemini-2.0-flash")
    http_response = MagicMock()
    http_response.raise_for_status = MagicMock()
    http_response.json.return_value = {"candidates": [], "usageMetadata": {}}
    captured = {}

    client = _async_client(http_response)

    async def capture_post(url, json=None):
        captured["url"] = url
        captured["json"] = json
        return http_response

    client.post = AsyncMock(side_effect=capture_post)
    with patch(
        "app.providers.llm.gemini_provider.httpx.AsyncClient",
        return_value=client,
    ):
        result = await provider.invoke(
            [
                {"role": "system", "content": "เป็นผู้ช่วย"},
                {"role": "assistant", "content": "ก่อนหน้า"},
                {"role": "user", "content": "ต่อ"},
            ],
            temperature=0.2,
            max_tokens=128,
        )
    assert result.content == ""
    assert captured["json"]["systemInstruction"]["parts"][0]["text"] == "เป็นผู้ช่วย"
    assert captured["json"]["generationConfig"]["temperature"] == 0.2
    assert captured["json"]["generationConfig"]["maxOutputTokens"] == 128


@pytest.mark.asyncio
async def test_gemini_timeout_http_error_and_stream():
    import httpx

    provider = GeminiLLMProvider(api_key="fake")
    timeout_client = AsyncMock()
    timeout_client.post = AsyncMock(side_effect=httpx.TimeoutException("slow"))
    timeout_client.__aenter__ = AsyncMock(return_value=timeout_client)
    timeout_client.__aexit__ = AsyncMock(return_value=None)
    with patch(
        "app.providers.llm.gemini_provider.httpx.AsyncClient",
        return_value=timeout_client,
    ):
        with pytest.raises(TimeoutError, match="did not respond"):
            await provider.invoke([{"role": "user", "content": "hi"}])

    err_client = AsyncMock()
    err_client.post = AsyncMock(side_effect=httpx.HTTPError("down"))
    err_client.__aenter__ = AsyncMock(return_value=err_client)
    err_client.__aexit__ = AsyncMock(return_value=None)
    with patch(
        "app.providers.llm.gemini_provider.httpx.AsyncClient",
        return_value=err_client,
    ):
        with pytest.raises(ConnectionError, match="unreachable"):
            await provider.invoke([{"role": "user", "content": "hi"}])

    http_response = MagicMock()
    http_response.raise_for_status = MagicMock()
    http_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "ชิ้นเดียว"}]}, "finishReason": "STOP"}],
        "usageMetadata": {},
    }
    with patch(
        "app.providers.llm.gemini_provider.httpx.AsyncClient",
        return_value=_async_client(http_response),
    ):
        chunks = [part async for part in provider.stream([{"role": "user", "content": "hi"}])]
    assert chunks == ["ชิ้นเดียว"]
