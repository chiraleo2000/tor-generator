"""Usage wrapper persistence, streams, and admission request binding."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import pytest

from app.llm_admission import admit
from app.providers.base import LLMProvider, LLMResponse
from app.providers.llm.usage_recording import UsageRecordingLLM, llm_core
from app.providers.structured_invoke import invoke_with_schema
from app.usage.context import bind_llm_request, current_request_id, usage_scope
from app.usage.store import persist_llm_usage

USER_ID = "11111111-1111-1111-1111-111111111111"


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _Session:
    def __init__(self, fail_flush: bool = False):
        self.added = []
        self.fail_flush = fail_flush

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        if self.fail_flush:
            raise RuntimeError("flush failed")

    async def commit(self):
        return None

    async def execute(self, _stmt):
        return _Rows([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


class _Factory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


class _BrokenFactory:
    def __call__(self):
        raise RuntimeError("db down")


class _Inner(LLMProvider):
    def __init__(
        self,
        *,
        content: str = "ok",
        usage: dict | None = None,
        error: Exception | None = None,
    ):
        self.content = content
        self.usage = usage or {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4}
        self.error = error
        self.last_usage = None
        self._model_name = "inner-model"

    async def invoke(self, messages, tools=None, **kwargs):
        if self.error:
            raise self.error
        return LLMResponse(content=self.content, model="inner-model", usage=self.usage)

    async def stream(self, messages, **kwargs):
        if self.error:
            raise self.error
        yield "ab"
        yield "cd"
        self.last_usage = {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}


def _events(session: _Session):
    from app.models.llm_usage import LlmUsageEvent

    return [row for row in session.added if isinstance(row, LlmUsageEvent)]


@pytest.fixture
def bound_factory(monkeypatch):
    session = _Session()
    monkeypatch.setattr("app.infra.session_factory", _Factory(session))
    return session


@pytest.mark.asyncio
async def test_invoke_persists_usage_with_context(bound_factory):
    wrapper = UsageRecordingLLM(_Inner(), provider_name="claude", task="draft")
    with usage_scope(user_id=USER_ID, request_id="req-9", task="review"):
        response = await wrapper.invoke([{"role": "user", "content": "สวัสดี"}])
    assert response.content == "ok"
    event = _events(bound_factory)[0]
    assert event.user_id == uuid.UUID(USER_ID)
    assert event.request_id == "req-9"
    assert event.task == "review"
    assert event.provider == "claude"
    assert event.prompt_tokens == 3
    assert event.status == "ok"
    assert event.tokens_estimated is False
    assert llm_core(wrapper) is wrapper.inner


@pytest.mark.asyncio
async def test_invoke_records_errors_and_ignores_a_down_database(monkeypatch):
    session = _Session()
    monkeypatch.setattr("app.infra.session_factory", _Factory(session))
    wrapper = UsageRecordingLLM(
        _Inner(error=ConnectionError("down")),
        provider_name="lm_studio",
        task="chat",
    )
    with pytest.raises(ConnectionError):
        await wrapper.invoke([{"role": "user", "content": "x"}])
    event = _events(session)[0]
    assert event.status == "error"
    assert event.tokens_estimated is True
    assert "down" in (event.error or "")

    monkeypatch.setattr("app.infra.session_factory", _BrokenFactory())
    healthy = UsageRecordingLLM(_Inner(content="still"), provider_name="gemini", task="chat")
    assert (await healthy.invoke([{"role": "user", "content": "x"}])).content == "still"


@pytest.mark.asyncio
async def test_stream_uses_provider_usage_or_an_estimate(bound_factory):
    measured = UsageRecordingLLM(_Inner(), provider_name="openai", task="chat")
    parts = [part async for part in measured.stream([{"role": "user", "content": "hi"}])]
    assert parts == ["ab", "cd"]
    event = _events(bound_factory)[-1]
    assert event.prompt_tokens == 5
    assert event.tokens_estimated is False

    estimated = UsageRecordingLLM(
        _Inner(error=RuntimeError("stream")),
        provider_name="openai",
        task="chat",
    )
    estimated.inner.error = None
    estimated.inner.last_usage = None

    async def _plain(messages, **kwargs):
        yield "สวัสดี"

    estimated.inner.stream = _plain  # type: ignore[method-assign]
    text = [
        part
        async for part in estimated.stream(
            [{"role": "user", "content": [{"text": "ถาม"}]}]
        )
    ]
    assert text == ["สวัสดี"]
    guessed = _events(bound_factory)[-1]
    assert guessed.tokens_estimated is True
    assert guessed.prompt_tokens >= 1


@pytest.mark.asyncio
async def test_structured_invoke_still_parses_after_the_wrapper_records(bound_factory):
    wrapper = UsageRecordingLLM(
        _Inner(
            content='{"ok": true}',
            usage={"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4},
        ),
        provider_name="gemini",
        task="structured",
    )
    parsed = await invoke_with_schema(
        wrapper,
        [{"role": "user", "content": "json"}],
        {"type": "object", "properties": {"ok": {"type": "boolean"}}},
        "probe",
    )
    assert parsed["ok"] is True
    assert _events(bound_factory)[0].task == "structured"


@pytest.mark.asyncio
async def test_admit_and_scope_bind_request_ids():
    with bind_llm_request("embedding", "skip-me"):
        assert current_request_id() is None
    async with admit(None, "llm", "req-123"):
        assert current_request_id() == "req-123"
    assert current_request_id() is None

    @asynccontextmanager
    async def _hold():
        async with admit(None, "llm", "outer"):
            async with admit(None, "llm", "inner"):
                yield current_request_id()

    async with _hold() as seen:
        assert seen == "inner"


@pytest.mark.asyncio
async def test_invalid_user_id_and_stream_errors_are_recorded(bound_factory):
    wrapper = UsageRecordingLLM(_Inner(), provider_name="ollama", task="")
    with usage_scope(user_id="not-a-uuid", request_id="r" * 80):
        await wrapper.invoke([{"role": "user", "content": "x"}])
    event = _events(bound_factory)[-1]
    assert event.user_id is None
    assert event.request_id is not None
    assert len(event.request_id) == 64
    assert event.task == "chat"

    failing = UsageRecordingLLM(_Inner(), provider_name="ollama", task="chat")

    async def _boom(messages, **kwargs):
        yield "บางส่วน"
        raise RuntimeError("cut")

    failing.inner.stream = _boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        _ = [part async for part in failing.stream([{"role": "user", "content": "x"}])]
    failed = _events(bound_factory)[-1]
    assert failed.status == "error"
    assert "cut" in (failed.error or "")


@pytest.mark.asyncio
async def test_persist_returns_none_without_a_factory(monkeypatch):
    monkeypatch.setattr("app.infra.session_factory", None)
    assert await persist_llm_usage(
        user_id="not-a-uuid",
        request_id="x" * 80,
        task="",
        provider="",
        model="",
        latency_ms=-1,
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        status="ok",
        error=None,
    ) is None
