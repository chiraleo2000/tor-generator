"""Local Gemma needs a longer per-section timeout than cloud Claude."""

import pytest

from app.config import Settings


def test_mcp_rag_defaults_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_RAG_ENABLED", raising=False)
    monkeypatch.delenv("MCP_RAG_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("MCP_RAG_AUTH_VALUE", raising=False)
    settings = Settings(_env_file=None)
    assert settings.mcp_rag_enabled is False
    assert settings.mcp_rag_auth_header == "Authorization"
    assert settings.mcp_rag_auth_value == ""
    assert settings.mcp_rag_timeout_seconds == 20.0


def test_mcp_rag_env_maps_case_insensitively(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_RAG_ENABLED", "true")
    monkeypatch.setenv("MCP_RAG_TIMEOUT_SECONDS", "15")
    settings = Settings(_env_file=None)
    assert settings.mcp_rag_enabled is True
    assert settings.mcp_rag_timeout_seconds == 15.0
    settings = Settings(
        llm_provider="lm_studio",
        deployment_mode="on_prem",
        lm_studio_timeout=180.0,
    )
    assert settings.drafting_agent_timeout_seconds() == 180


def test_cloud_claude_timeout_is_60():
    settings = Settings(llm_provider="claude", deployment_mode="cloud")
    assert settings.drafting_agent_timeout_seconds() == 60


def test_on_prem_claude_uses_cloud_timeout():
    settings = Settings(llm_provider="claude", deployment_mode="on_prem")
    assert settings.drafting_agent_timeout_seconds() == 60


def test_timeout_is_clamped_to_1800():
    settings = Settings(
        llm_provider="lm_studio",
        deployment_mode="on_prem",
        lm_studio_timeout=9999.0,
    )
    assert settings.drafting_agent_timeout_seconds() == 1800


def test_ollama_on_prem_uses_local_timeout():
    settings = Settings(
        llm_provider="ollama",
        deployment_mode="on_prem",
        lm_studio_timeout=180.0,
    )
    assert settings.drafting_agent_timeout_seconds() == 180


def test_bedrock_uses_cloud_llm_timeout():
    settings = Settings(
        llm_provider="bedrock",
        deployment_mode="cloud",
        cloud_llm_timeout=300.0,
    )
    assert settings.drafting_agent_timeout_seconds() == 300


def test_on_prem_pin_rewrites_bedrock_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import (
        apply_on_prem_llm_pin,
        apply_runtime_overlay,
        clear_runtime_overlay,
        get_settings,
    )

    monkeypatch.setenv("PIN_ON_PREM_LLM", "true")
    monkeypatch.setenv("DEPLOYMENT_MODE", "on_prem")
    monkeypatch.setenv("LLM_PROVIDER", "lm_studio")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("MCP_RAG_ENABLED", "false")
    clear_runtime_overlay()
    apply_runtime_overlay(
        {
            "llm_provider": "bedrock",
            "deployment_mode": "cloud",
            "embedding_provider": "bedrock",
            "mcp_rag_enabled": True,
        }
    )
    try:
        pinned = apply_on_prem_llm_pin(
            Settings(
                _env_file=None,
                llm_provider="bedrock",
                deployment_mode="cloud",
                embedding_provider="bedrock",
                mcp_rag_enabled=True,
            )
        )
        assert pinned.llm_provider == "lm_studio"
        assert pinned.deployment_mode == "on_prem"
        assert pinned.embedding_provider == "local"
        assert pinned.mcp_rag_enabled is False
        settings = get_settings()
        assert settings.llm_provider == "lm_studio"
        assert settings.deployment_mode == "on_prem"
    finally:
        clear_runtime_overlay()


def test_on_prem_pin_enables_mcp_when_env_true(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import apply_on_prem_llm_pin, Settings as PinSettings

    monkeypatch.setenv("PIN_ON_PREM_LLM", "true")
    monkeypatch.setenv("DEPLOYMENT_MODE", "on_prem")
    monkeypatch.setenv("MCP_RAG_ENABLED", "true")
    pinned = apply_on_prem_llm_pin(
        PinSettings(
            _env_file=None,
            llm_provider="lm_studio",
            deployment_mode="on_prem",
            embedding_provider="local",
            mcp_rag_enabled=False,
        )
    )
    assert pinned.mcp_rag_enabled is True


def test_on_prem_pin_off_keeps_bedrock_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import apply_runtime_overlay, clear_runtime_overlay, get_settings

    monkeypatch.setenv("PIN_ON_PREM_LLM", "false")
    monkeypatch.setenv("DEPLOYMENT_MODE", "on_prem")
    clear_runtime_overlay()
    apply_runtime_overlay({"llm_provider": "bedrock", "deployment_mode": "cloud"})
    try:
        settings = get_settings()
        assert settings.llm_provider == "bedrock"
        assert settings.deployment_mode == "cloud"
    finally:
        clear_runtime_overlay()
    from app.config import apply_runtime_overlay, clear_runtime_overlay, get_settings

    clear_runtime_overlay()
    apply_runtime_overlay({"lm_studio_model": "overlay-only-model"})
    try:
        assert get_settings().lm_studio_model == "overlay-only-model"
    finally:
        clear_runtime_overlay()


def test_clear_runtime_overlay_restores_env_default():
    from app.config import apply_runtime_overlay, clear_runtime_overlay, get_settings

    apply_runtime_overlay({"lm_studio_timeout": 12.0})
    assert get_settings().lm_studio_timeout == 12.0
    clear_runtime_overlay()
    assert get_settings().lm_studio_timeout != 12.0


def test_redis_url_uses_tls_scheme_for_elasticache():
    settings = Settings(redis_tls=True, redis_host="cache.example", redis_password="s3cret")
    assert settings.redis_url.startswith("rediss://")
    assert "cache.example" in settings.redis_url


def test_redis_url_defaults_to_cleartext_for_compose():
    settings = Settings(redis_host="redis", redis_password="s3cret")
    assert settings.redis_url.startswith("redis://")
    assert not settings.redis_url.startswith("rediss://")
