"""Focused Bedrock provider tests (mocked Runtime client, no live AWS)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.providers.bedrock_client import (
    call_bedrock_with_retry,
    is_bedrock_retryable,
    is_bedrock_short_timeout,
    is_bedrock_throttle,
)
from app.providers.constants import EMBEDDING_DIMENSIONS
from app.providers.embedding.bedrock_provider import (
    BedrockEmbeddingProvider,
    _cohere_body,
    _fit_dimensions,
    _is_cohere_model,
    _request_output_dimension,
    _titan_body,
)
from app.providers.llm.bedrock_provider import (
    BedrockLLMProvider,
    openai_tools_to_bedrock_tool_config,
)


class _ClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class ReadTimeoutError(Exception):
    pass


class ConnectTimeoutError(Exception):
    pass
    def __init__(self) -> None:
        super().__init__("Read timeout on endpoint")


def _json_body(payload: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(payload).encode()
    return body


def _embedding_provider(client: MagicMock, model_id: str) -> BedrockEmbeddingProvider:
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ):
        return BedrockEmbeddingProvider(region="ap-southeast-1", model_id=model_id)


def _llm_provider(client: MagicMock, **kwargs) -> BedrockLLMProvider:
    with patch(
        "app.providers.bedrock_client.bedrock_runtime_client", return_value=client
    ):
        return BedrockLLMProvider(
            region="ap-southeast-1",
            model_id=kwargs.pop("model_id", "anthropic.claude"),
            **kwargs,
        )


def _converse_ok(text: str = "ok") -> dict:
    return {
        "output": {"message": {"content": [{"text": text}]}},
        "usage": {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3},
        "stopReason": "end_turn",
    }


def test_cohere_model_id_detection() -> None:
    assert _is_cohere_model("cohere.embed-v4:0")
    assert _is_cohere_model("us.cohere.embed-english-v3")
    assert not _is_cohere_model("amazon.titan-embed-text-v2:0")
    assert not _is_cohere_model("titan")


def test_titan_body_keeps_input_text_and_dimensions() -> None:
    body = _titan_body("วงเงิน", "amazon.titan-embed-text-v2:0")
    assert body["inputText"] == "วงเงิน"
    assert "dimensions" in body
    assert body["dimensions"] in (256, 512, 1024)
    if EMBEDDING_DIMENSIONS == 768:
        assert body["dimensions"] == 1024


def test_cohere_body_matches_pn_rag_shape() -> None:
    body = _cohere_body(
        ["เอกสารหนึ่ง", "เอกสารสอง"],
        "search_document",
        "cohere.embed-v4:0",
    )
    assert body == {
        "texts": ["เอกสารหนึ่ง", "เอกสารสอง"],
        "input_type": "search_document",
        "embedding_types": ["float"],
        "output_dimension": _request_output_dimension("cohere.embed-v4:0"),
        "truncate": "RIGHT",
    }
    assert "inputText" not in body
    if EMBEDDING_DIMENSIONS == 768:
        assert body["output_dimension"] == 1024


def test_fit_dimensions_supports_1024_and_keeps_768() -> None:
    truncated = _fit_dimensions([0.1] * 1024, size=768)
    assert len(truncated) == 768
    kept = _fit_dimensions([0.2] * 1024, size=1024)
    assert kept == [0.2] * 1024
    padded = _fit_dimensions([1.0, 2.0], size=768)
    assert len(padded) == 768
    assert padded[:2] == [1.0, 2.0]


@pytest.mark.asyncio
async def test_titan_embed_query_sends_input_text_and_fits_768() -> None:
    client = MagicMock()
    client.invoke_model.return_value = {"body": _json_body({"embedding": [0.3] * 1024})}
    provider = _embedding_provider(client, "amazon.titan-embed-text-v2:0")

    vector = await provider.embed_query("สเปก")

    sent = json.loads(client.invoke_model.call_args.kwargs["body"])
    assert sent["inputText"] == "สเปก"
    assert "dimensions" in sent
    assert len(vector) == EMBEDDING_DIMENSIONS
    if EMBEDDING_DIMENSIONS == 768:
        assert len(vector) == 768


@pytest.mark.asyncio
async def test_cohere_embed_uses_texts_input_type_and_fits_1024() -> None:
    client = MagicMock()
    client.invoke_model.return_value = {
        "body": _json_body({"embeddings": {"float": [[0.4] * 1024, [0.5] * 1024]}})
    }
    provider = _embedding_provider(client, "cohere.embed-v4:0")

    rows = await provider.embed_documents(["ก", "ข"])

    sent = json.loads(client.invoke_model.call_args.kwargs["body"])
    assert sent["texts"] == ["ก", "ข"]
    assert sent["input_type"] == "search_document"
    assert sent["embedding_types"] == ["float"]
    assert sent["truncate"] == "RIGHT"
    assert "output_dimension" in sent
    assert "inputText" not in sent
    assert len(rows) == 2
    assert all(len(row) == EMBEDDING_DIMENSIONS for row in rows)


@pytest.mark.asyncio
async def test_cohere_embed_query_uses_search_query() -> None:
    client = MagicMock()
    client.invoke_model.return_value = {
        "body": _json_body({"embeddings": [[0.9] * 1024]})
    }
    provider = _embedding_provider(client, "cohere.embed-v4:0")

    vector = await provider.embed_query("วงเงินเท่าไร")

    sent = json.loads(client.invoke_model.call_args.kwargs["body"])
    assert sent["texts"] == ["วงเงินเท่าไร"]
    assert sent["input_type"] == "search_query"
    assert len(vector) == EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_embed_keeps_1024_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.providers.embedding.bedrock_provider._target_dimensions",
        lambda: 1024,
    )
    client = MagicMock()
    client.invoke_model.return_value = {
        "body": _json_body({"embeddings": {"float": [[0.1] * 1024]}})
    }
    provider = _embedding_provider(client, "cohere.embed-v4:0")
    vector = await provider.embed_query("keep")
    assert len(vector) == 1024


def test_openai_tools_map_to_bedrock_tool_config() -> None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "ค้นเว็บ",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]
    config = openai_tools_to_bedrock_tool_config(tools)
    assert config == {
        "tools": [
            {
                "toolSpec": {
                    "name": "web_search",
                    "description": "ค้นเว็บ",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        }
                    },
                }
            }
        ]
    }
    assert openai_tools_to_bedrock_tool_config(None) is None
    assert openai_tools_to_bedrock_tool_config([]) is None


def test_tool_config_passthrough_for_bedrock_spec() -> None:
    native = [{"toolSpec": {"name": "lookup", "description": "x", "inputSchema": {"json": {}}}}]
    assert openai_tools_to_bedrock_tool_config(native) == {"tools": native}


def test_build_request_omits_tool_config_without_tools() -> None:
    client = MagicMock()
    provider = _llm_provider(client)
    request = provider._build_request([{"role": "user", "content": "hi"}])
    assert "toolConfig" not in request


def test_build_request_adds_tool_config_when_tools_present() -> None:
    client = MagicMock()
    provider = _llm_provider(client)
    tools = [{"type": "function", "function": {"name": "lookup"}}]
    request = provider._build_request(
        [{"role": "user", "content": "hi"}],
        tools=tools,
        max_tokens=32,
    )
    assert request["toolConfig"]["tools"][0]["toolSpec"]["name"] == "lookup"
    assert request["inferenceConfig"]["maxTokens"] == 32


@pytest.mark.asyncio
async def test_invoke_and_stream_pass_tool_config() -> None:
    client = MagicMock()
    client.converse.return_value = _converse_ok("พร้อมเครื่องมือ")
    client.converse_stream.return_value = {
        "stream": [{"contentBlockDelta": {"delta": {"text": "สตรีม"}}}]
    }
    provider = _llm_provider(client)
    tools = [{"type": "function", "function": {"name": "web_search"}}]

    response = await provider.invoke(
        [{"role": "user", "content": "hi"}],
        tools=tools,
    )
    tokens = [
        token
        async for token in provider.stream(
            [{"role": "user", "content": "hi"}],
            tools=tools,
        )
    ]

    assert response.content == "พร้อมเครื่องมือ"
    assert tokens == ["สตรีม"]
    invoke_kwargs = client.converse.call_args.kwargs
    stream_kwargs = client.converse_stream.call_args.kwargs
    assert invoke_kwargs["toolConfig"]["tools"][0]["toolSpec"]["name"] == "web_search"
    assert stream_kwargs["toolConfig"]["tools"][0]["toolSpec"]["name"] == "web_search"


def test_retryable_throttle_and_short_timeout() -> None:
    assert is_bedrock_throttle(_ClientError("ThrottlingException"))
    assert is_bedrock_throttle(_ClientError("TooManyRequestsException"))
    assert is_bedrock_retryable(_ClientError("TooManyRequests"))
    assert not is_bedrock_short_timeout(ReadTimeoutError())
    assert not is_bedrock_retryable(ReadTimeoutError())
    assert not is_bedrock_retryable(RuntimeError("offline"))
    assert not is_bedrock_retryable(TimeoutError("app wait_for"))


def test_retry_helper_retries_throttle_then_succeeds(caplog: pytest.LogCaptureFixture) -> None:
    calls = {"n": 0}

    def _op() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise _ClientError("ThrottlingException")
        return "ok"

    with patch("app.providers.bedrock_client.time.sleep") as sleep:
        with caplog.at_level("WARNING"):
            assert (
                call_bedrock_with_retry(
                    _op,
                    model_id="global.anthropic.claude-sonnet-4-5",
                    op="converse",
                )
                == "ok"
            )
    sleep.assert_called_once()
    text = caplog.text
    assert "global.anthropic.claude-sonnet-4-5" in text
    assert "ClientError" in text or "ThrottlingException" in text
    assert "sk-" not in text
    assert "Bearer" not in text
    assert "bedrock-api-key" not in text


def test_retry_helper_retries_too_many_requests_and_timeout() -> None:
    sequence: list[BaseException | str] = [
        _ClientError("TooManyRequestsException"),
        ConnectTimeoutError(),
        "done",
    ]

    def _op() -> str:
        item = sequence.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    with patch("app.providers.bedrock_client.time.sleep"):
        assert (
            call_bedrock_with_retry(
                _op, model_id="cohere.embed-v4:0", op="invoke_model"
            )
            == "done"
        )


def test_retry_helper_does_not_retry_non_throttle() -> None:
    def _op() -> None:
        raise RuntimeError("ValidationException")

    with patch("app.providers.bedrock_client.time.sleep") as sleep:
        with pytest.raises(RuntimeError, match="ValidationException"):
            call_bedrock_with_retry(_op, model_id="m", op="converse")
    sleep.assert_not_called()


@pytest.mark.asyncio
async def test_invoke_retries_throttle_then_returns(caplog: pytest.LogCaptureFixture) -> None:
    client = MagicMock()
    client.converse.side_effect = [
        _ClientError("ThrottlingException"),
        _converse_ok("หลังรอ"),
    ]
    provider = _llm_provider(client, model_id="anthropic.claude-sonnet")
    with patch("app.providers.bedrock_client.time.sleep"):
        with caplog.at_level("WARNING"):
            result = await provider.invoke([{"role": "user", "content": "hi"}])
    assert result.content == "หลังรอ"
    assert client.converse.call_count == 2
    assert "anthropic.claude-sonnet" in caplog.text
    assert "lm_studio" not in caplog.text.lower()
    assert "sk-" not in caplog.text


@pytest.mark.asyncio
async def test_embed_retries_too_many_requests() -> None:
    client = MagicMock()
    client.invoke_model.side_effect = [
        _ClientError("TooManyRequestsException"),
        {"body": _json_body({"embedding": [0.2] * 4})},
    ]
    provider = _embedding_provider(client, "amazon.titan-embed-text-v2:0")
    with patch("app.providers.bedrock_client.time.sleep"):
        vector = await provider.embed_query("retry")
    assert len(vector) == EMBEDDING_DIMENSIONS
    assert client.invoke_model.call_count == 2


@pytest.mark.asyncio
async def test_stream_failure_falls_back_to_bedrock_invoke_not_lm_studio() -> None:
    client = MagicMock()
    client.converse_stream.side_effect = RuntimeError("no stream")
    client.converse.return_value = _converse_ok("จาก converse")
    provider = _llm_provider(client)
    with patch(
        "app.providers.llm.lm_studio_provider.LMStudioLocalProvider"
    ) as lm_studio:
        tokens = [
            token async for token in provider.stream([{"role": "user", "content": "x"}])
        ]
    assert tokens == ["จาก converse"]
    lm_studio.assert_not_called()
    client.converse.assert_called_once()


@pytest.mark.asyncio
async def test_exhausted_throttle_becomes_connection_error() -> None:
    client = MagicMock()
    client.converse.side_effect = _ClientError("ThrottlingException")
    provider = _llm_provider(client, timeout=5.0)
    with patch("app.providers.bedrock_client.time.sleep"):
        with pytest.raises(ConnectionError, match="unreachable"):
            await provider.invoke([{"role": "user", "content": "x"}])
    assert client.converse.call_count == 3
