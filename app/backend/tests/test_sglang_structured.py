"""Tests for SGLang health probe and guided JSON request kwargs."""

from unittest.mock import patch

from app.providers.llm.lm_studio_provider import (
    endpoint_supports_guided_json,
    thinking_request_kwargs,
)
from app.providers.sglang_health import (
    clear_sglang_health_cache,
    health_url_from_openai_base,
    probe_sglang_health_sync,
)
from app.schemas.llm_structured import IntakeAnalyzeResult, json_schema_for


def test_health_url_strips_v1():
    assert (
        health_url_from_openai_base("http://sglang-llm:30000/v1")
        == "http://sglang-llm:30000/health"
    )


def test_endpoint_supports_guided_json():
    assert endpoint_supports_guided_json("http://sglang-llm:30000/v1") is True
    assert endpoint_supports_guided_json("http://host.docker.internal:1234/v1") is False


def test_guided_json_attached_for_sglang_kwargs():
    schema = json_schema_for(IntakeAnalyzeResult)
    payload = thinking_request_kwargs(
        {
            "temperature": 0.1,
            "json_schema": schema,
            "json_schema_name": "intake_analyze",
            "_guided_json": True,
            "disable_thinking": True,
        }
    )
    assert payload["extra_body"]["guided_json"] == schema
    assert payload["extra_body"]["enable_thinking"] is False
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "intake_analyze"
    assert "json_schema" not in payload
    assert payload["temperature"] == 0.1


def test_guided_json_omitted_without_flag():
    payload = thinking_request_kwargs(
        {"json_schema": {"type": "object"}, "_guided_json": False}
    )
    assert "extra_body" not in payload or "guided_json" not in payload.get("extra_body", {})


def test_probe_sglang_health_uses_cache(monkeypatch):
    clear_sglang_health_cache()
    calls = {"n": 0}

    class FakeResponse:
        status_code = 200

    def fake_get(_url, timeout=1.0):
        calls["n"] += 1
        return FakeResponse()

    monkeypatch.setattr("httpx.get", fake_get)
    assert probe_sglang_health_sync("http://sglang-llm:30000/v1") is True
    assert probe_sglang_health_sync("http://sglang-llm:30000/v1") is True
    assert calls["n"] == 1
    clear_sglang_health_cache()


def test_factory_promotes_sglang_when_healthy():
    from app.config import Settings
    from app.providers.factory import ProviderFactory

    settings = Settings(llm_provider="lm_studio", embedding_provider="local")
    with patch("app.providers.factory.probe_sglang_health_sync", return_value=True):
        llm = ProviderFactory(settings=settings).get_llm("structured")
    assert "sglang" in llm._base_url or ":30000" in llm._base_url
