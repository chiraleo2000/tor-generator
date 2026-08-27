"""Local Gemma needs a longer per-section timeout than cloud Claude."""

from app.config import Settings


def test_on_prem_lm_studio_timeout_is_180():
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


def test_runtime_overlay_changes_model_after_apply():
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
