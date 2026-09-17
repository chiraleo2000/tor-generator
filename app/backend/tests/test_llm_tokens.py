"""Shared LLM token budgets."""

import pytest

from app.llm_tokens import (
    CHAT_MAX_TOKENS,
    CHAT_MIN_TOKENS,
    DRAFT_MAX_TOKENS,
    DRAFT_MIN_TOKENS,
    EMBEDDING_MAX_TOKENS,
    GEMMA_CONTEXT_WINDOW,
    REVIEW_ANALYZE_MAX_TOKENS,
    REVIEW_CONTEXT_WINDOW,
    REVIEW_MAX_TOKENS,
    REVIEW_SUGGESTION_MAX_TOKENS,
    chars_for_tokens,
    clamp_max_tokens,
    estimate_tokens,
    live_context_window,
    live_section_max_tokens,
    truncate_for_embedding,
)
from app.providers.model_capabilities import (
    DEFAULT_CONTEXT_WINDOW,
    reset_capability_cache,
)


def test_draft_and_chat_budgets(monkeypatch):
    monkeypatch.delenv("TOR_CONTEXT_WINDOW", raising=False)
    monkeypatch.delenv("TOR_SECTION_MAX_TOKENS", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "lm_studio")
    monkeypatch.setenv("LM_STUDIO_MODEL", "typhoon2.5-qwen3-4b")
    reset_capability_cache()
    assert GEMMA_CONTEXT_WINDOW == 131_072
    assert EMBEDDING_MAX_TOKENS == 2_048
    assert DRAFT_MAX_TOKENS >= 8_192
    assert DRAFT_MIN_TOKENS == 192
    assert CHAT_MAX_TOKENS == 32_768
    assert CHAT_MIN_TOKENS == 0
    assert REVIEW_MAX_TOKENS == DEFAULT_CONTEXT_WINDOW
    assert REVIEW_ANALYZE_MAX_TOKENS == 16_384
    assert REVIEW_SUGGESTION_MAX_TOKENS == 8_192
    assert REVIEW_CONTEXT_WINDOW == DEFAULT_CONTEXT_WINDOW
    assert chars_for_tokens(DRAFT_MIN_TOKENS) == 384
    assert live_context_window() == DEFAULT_CONTEXT_WINDOW
    assert live_section_max_tokens() <= live_context_window()
    capped = clamp_max_tokens(
        "x",
        DRAFT_MAX_TOKENS,
        context_window=live_context_window(),
    )
    assert 256 <= capped <= live_context_window() - 256


def test_env_tor_context_window_overrides(monkeypatch):
    monkeypatch.setenv("TOR_CONTEXT_WINDOW", "32768")
    monkeypatch.setenv("TOR_SECTION_MAX_TOKENS", "4096")
    monkeypatch.setenv("TOR_CHAT_MAX_TOKENS", "2048")
    monkeypatch.setenv("EMBEDDING_MAX_TOKENS", "1024")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    monkeypatch.setenv("LLM_PROVIDER", "lm_studio")
    monkeypatch.setenv("LM_STUDIO_MODEL", "google/gemma-4-e4b")
    reset_capability_cache()
    assert live_context_window() == 32_768
    assert live_section_max_tokens() == 4_096
    from app.llm_tokens import live_chat_max_tokens, live_embedding_max_tokens
    from app.providers.model_capabilities import embedding_dimensions

    assert live_chat_max_tokens() == 2_048
    assert live_embedding_max_tokens() == 1_024
    assert embedding_dimensions() == 768


def test_clamp_max_tokens_leaves_room_for_the_prompt():
    prompt = "ก" * 10_000
    window = REVIEW_CONTEXT_WINDOW
    capped = clamp_max_tokens(
        prompt,
        REVIEW_MAX_TOKENS,
        context_window=window,
        system="sys",
    )
    used = estimate_tokens("sys") + estimate_tokens(prompt)
    assert capped <= window - used - 256
    assert capped >= 256


def test_truncate_for_embedding_caps_at_requested_tokens():
    short = "สั้น"
    assert truncate_for_embedding(short) == short
    long_text = "ก" * (chars_for_tokens(EMBEDDING_MAX_TOKENS) + 50)
    clipped = truncate_for_embedding(long_text, max_tokens=EMBEDDING_MAX_TOKENS)
    assert len(clipped) == chars_for_tokens(EMBEDDING_MAX_TOKENS)
    assert estimate_tokens(clipped) <= EMBEDDING_MAX_TOKENS


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("lm_studio", "google/gemma-4-e4b"),
        ("openai", "gpt-4o-mini"),
        ("claude", "claude-sonnet-4-20250514"),
        ("bedrock", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    ],
)
def test_clamp_uses_provider_window(provider, model, monkeypatch):
    from app.providers.model_capabilities import capabilities_for

    monkeypatch.delenv("TOR_CONTEXT_WINDOW", raising=False)
    reset_capability_cache()
    caps = capabilities_for(provider, model, "local", "text-embedding-embeddinggemma-300m")
    capped = clamp_max_tokens("ก" * 200, 999_999, context_window=caps.context_window)
    assert 256 <= capped < caps.context_window
