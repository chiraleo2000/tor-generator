"""Bedrock chat failover to Gemini on daily quota or throttle."""

from unittest.mock import patch

import pytest

from app.providers.base import LLMProvider, LLMResponse
from app.providers.llm.fallback_provider import (
    FallbackLLMProvider,
    fallback_circuit_open,
    reset_fallback_circuit,
)


class _ThrottlingException(Exception):
    pass


class _ValidationException(Exception):
    pass


class _AccessDeniedException(Exception):
    pass


def _chained(message: str, cause: BaseException) -> ConnectionError:
    exc = ConnectionError(message)
    exc.__cause__ = cause
    return exc


def _response(text: str) -> LLMResponse:
    return LLMResponse(content=text, model="m", usage={})


class _ScriptedLLM(LLMProvider):
    def __init__(
        self,
        *,
        content: str = "ok",
        error: BaseException | None = None,
        stream_parts: list[str] | None = None,
        stream_error: BaseException | None = None,
    ) -> None:
        self.content = content
        self.error = error
        self.stream_parts = stream_parts
        self.stream_error = stream_error
        self.invoke_calls = 0
        self.stream_calls = 0

    async def invoke(self, messages, tools=None, **kwargs):
        self.invoke_calls += 1
        if self.error is not None:
            raise self.error
        return _response(self.content)

    async def stream(self, messages, **kwargs):
        self.stream_calls += 1
        for part in self.stream_parts or []:
            yield part
        if self.stream_error is not None:
            raise self.stream_error
        if self.error is not None and not self.stream_parts:
            raise self.error


def _settings(**overrides):
    from app.config import Settings

    base = dict(
        deployment_mode="on_prem",
        llm_provider="bedrock",
        embedding_provider="local",
        gemini_api_key="gemini-test-key",
        gemini_model="gemini-3.5-flash-lite",
        llm_fallback_provider="",
        jwt_secret="changeme_jwt_secret_at_least_32_characters_long",
        lm_studio_base_url="http://127.0.0.1:1234/v1",
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture(autouse=True)
def _clear_circuit():
    reset_fallback_circuit()
    yield
    reset_fallback_circuit()


@pytest.mark.asyncio
async def test_daily_quota_opens_circuit_and_skips_primary():
    primary = _ScriptedLLM(
        error=_chained(
            "Bedrock endpoint unreachable: Too many tokens per day",
            _ThrottlingException("Too many tokens per day"),
        )
    )
    fallback = _ScriptedLLM(content="จากเจมิไน")
    provider = FallbackLLMProvider(primary, fallback)

    first = await provider.invoke([{"role": "user", "content": "ร่าง"}])
    second = await provider.invoke([{"role": "user", "content": "ร่างต่อ"}])

    assert first.content == "จากเจมิไน"
    assert second.content == "จากเจมิไน"
    assert primary.invoke_calls == 1
    assert fallback.invoke_calls == 2
    assert fallback_circuit_open()


@pytest.mark.asyncio
async def test_throttle_fails_over_once_then_tries_primary_again():
    primary = _ScriptedLLM(
        error=_chained(
            "Bedrock endpoint unreachable: Too many requests",
            _ThrottlingException("Too many requests"),
        )
    )
    fallback = _ScriptedLLM(content="สำรอง")
    provider = FallbackLLMProvider(primary, fallback)

    await provider.invoke([{"role": "user", "content": "หนึ่ง"}])
    await provider.invoke([{"role": "user", "content": "สอง"}])

    assert primary.invoke_calls == 2
    assert fallback.invoke_calls == 2
    assert not fallback_circuit_open()


@pytest.mark.asyncio
async def test_validation_and_timeout_do_not_fail_over():
    validation = _ScriptedLLM(
        error=_chained(
            "Bedrock endpoint unreachable: max tokens is too large",
            _ValidationException("max tokens is too large"),
        )
    )
    fallback = _ScriptedLLM(content="ไม่ควร")
    provider = FallbackLLMProvider(validation, fallback)
    with pytest.raises(ConnectionError):
        await provider.invoke([{"role": "user", "content": "x"}])
    assert fallback.invoke_calls == 0

    denied = _ScriptedLLM(
        error=_chained(
            "Bedrock endpoint unreachable: access denied",
            _AccessDeniedException("access denied"),
        )
    )
    provider = FallbackLLMProvider(denied, fallback)
    with pytest.raises(ConnectionError):
        await provider.invoke([{"role": "user", "content": "x"}])
    assert fallback.invoke_calls == 0

    timed_out = _ScriptedLLM(error=TimeoutError("Bedrock did not respond within 10800s"))
    provider = FallbackLLMProvider(timed_out, fallback)
    with pytest.raises(TimeoutError):
        await provider.invoke([{"role": "user", "content": "x"}])
    assert fallback.invoke_calls == 0


@pytest.mark.asyncio
async def test_success_does_not_call_fallback():
    primary = _ScriptedLLM(content="เบดร็อก")
    fallback = _ScriptedLLM(content="เจมิไน")
    provider = FallbackLLMProvider(primary, fallback)
    result = await provider.invoke([{"role": "user", "content": "hi"}])
    assert result.content == "เบดร็อก"
    assert fallback.invoke_calls == 0


@pytest.mark.asyncio
async def test_stream_fails_over_before_tokens_and_keeps_partial_output():
    quota = _chained(
        "Bedrock endpoint unreachable: Too many tokens per day",
        _ThrottlingException("Too many tokens per day"),
    )
    primary = _ScriptedLLM(error=quota)
    fallback = _ScriptedLLM(stream_parts=["ก", "ข"])
    provider = FallbackLLMProvider(primary, fallback)
    chunks = [part async for part in provider.stream([{"role": "user", "content": "hi"}])]
    assert chunks == ["ก", "ข"]
    assert fallback.stream_calls == 1

    reset_fallback_circuit()
    partial = _ScriptedLLM(stream_parts=["บางส่วน"], stream_error=quota)
    fallback = _ScriptedLLM(stream_parts=["ไม่ควร"])
    provider = FallbackLLMProvider(partial, fallback)
    with pytest.raises(ConnectionError):
        _ = [part async for part in provider.stream([{"role": "user", "content": "hi"}])]
    assert fallback.stream_calls == 0
    assert fallback_circuit_open()


def test_factory_wraps_only_bedrock_with_gemini_flag_and_key():
    from app.providers.factory import ProviderFactory
    from app.providers.llm.fallback_provider import FallbackLLMProvider
    from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

    created: list[str] = []

    def _create(self, kind: str):
        created.append(kind)
        return _ScriptedLLM(content=kind)

    with patch.object(ProviderFactory, "_create_cloud_llm_provider", _create):
        wrapped = ProviderFactory(
            settings=_settings(llm_fallback_provider="gemini")
        ).get_llm()
        assert isinstance(wrapped, FallbackLLMProvider)
        assert created == ["bedrock", "gemini"]

        created.clear()
        plain = ProviderFactory(
            settings=_settings(llm_fallback_provider="")
        ).get_llm()
        assert plain is not wrapped
        assert not isinstance(plain, FallbackLLMProvider)
        assert created == ["bedrock"]

        created.clear()
        missing_key = ProviderFactory(
            settings=_settings(llm_fallback_provider="gemini", gemini_api_key="")
        ).get_llm()
        assert not isinstance(missing_key, FallbackLLMProvider)
        assert created == ["bedrock"]

    with patch("app.providers.factory.probe_sglang_health_sync", return_value=False):
        local = ProviderFactory(
            settings=_settings(
                llm_provider="lm_studio",
                llm_fallback_provider="gemini",
                gemini_api_key="gemini-test-key",
            )
        ).get_llm()
    assert isinstance(local, LMStudioLocalProvider)
