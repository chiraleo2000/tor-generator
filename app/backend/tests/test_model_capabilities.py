"""Model capability table — same Docker image, different env providers."""

from app.providers.model_capabilities import (
    EMBEDDING_DIM_COHERE_V4,
    EMBEDDING_DIM_GEMMA,
    GEMMA_CONTEXT_WINDOW,
    capabilities_for,
    compose_thinking_enabled,
    filter_llm_kwargs,
    llm_call_kwargs,
    reset_capability_cache,
    thinking_supported,
)


def setup_function() -> None:
    reset_capability_cache()


def test_local_gemma_uses_large_window_and_768d():
    caps = capabilities_for(
        "lm_studio",
        "google/gemma-4-e4b",
        "local",
        "text-embedding-embeddinggemma-300m",
    )
    assert caps.context_window == GEMMA_CONTEXT_WINDOW
    assert caps.section_max_tokens >= 8_192
    assert caps.thinking_supported is True
    assert caps.embedding_dimensions == EMBEDDING_DIM_GEMMA
    assert compose_thinking_enabled("lm_studio") is False


def test_bedrock_claude_and_cohere_on_same_image():
    caps = capabilities_for(
        "bedrock",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "bedrock",
        "cohere.embed-v4:0",
    )
    assert caps.context_window >= 128_000
    assert caps.section_max_tokens <= caps.context_window
    assert caps.thinking_supported is False
    assert caps.embedding_dimensions == EMBEDDING_DIM_COHERE_V4
    assert "enable_thinking" not in filter_llm_kwargs(
        "bedrock", {"temperature": 0.2, "enable_thinking": True, "max_tokens": 512}
    )


def test_openai_and_anthropic_strip_thinking_kwargs():
    openai_kwargs = filter_llm_kwargs(
        "openai",
        {"temperature": 0.3, "enable_thinking": True, "max_tokens": 1024, "foo": 1},
    )
    assert openai_kwargs == {"temperature": 0.3, "max_tokens": 1024}
    assert thinking_supported("claude") is False
    claude_kwargs = filter_llm_kwargs(
        "claude", {"max_tokens": 2048, "enable_thinking": False, "top_p": 0.9}
    )
    assert "enable_thinking" not in claude_kwargs
    assert claude_kwargs["max_tokens"] == 2048


def test_env_overrides_section_cap(monkeypatch):
    monkeypatch.setenv("TOR_SECTION_MAX_TOKENS", "4096")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")
    reset_capability_cache()
    caps = capabilities_for("openai", "gpt-4o-mini", "openai", "text-embedding-3-small")
    assert caps.section_max_tokens == 4096
    assert caps.embedding_dimensions == 1024


def test_llm_call_kwargs_keeps_thinking_only_for_local(monkeypatch):
    monkeypatch.delenv("TOR_COMPOSE_ENABLE_THINKING", raising=False)
    reset_capability_cache()
    local = llm_call_kwargs("lm_studio", thinking=False, temperature=0.2, max_tokens=128)
    assert local.get("enable_thinking") is False
    cloud = llm_call_kwargs("bedrock", thinking=True, temperature=0.2, max_tokens=128)
    assert "enable_thinking" not in cloud
    assert cloud["max_tokens"] == 128
