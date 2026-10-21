"""Pricing math and provider usage-field normalization."""

from app.providers.llm.bedrock_provider import _bedrock_usage
from app.providers.llm.gemini_provider import _usage_counts
from app.providers.llm.openai_provider import _openai_usage
from app.usage.cost import (
    TokenRate,
    default_rates,
    estimate_cost_usd,
    merge_rates,
    normalize_usage,
    pick_rate,
)


def test_fresh_and_cache_tokens_are_priced_separately():
    rate = pick_rate(default_rates(), "claude", "claude-sonnet")
    usage = normalize_usage(
        {
            "prompt_tokens": 1_000_000,
            "completion_tokens": 1_000_000,
            "cache_creation_input_tokens": 200_000,
            "cache_read_input_tokens": 300_000,
        }
    )
    # 500k fresh * $3 + 200k write * $3.75 + 300k read * $0.30 + 1M out * $15
    assert estimate_cost_usd(usage, rate) == 17.34


def test_local_models_are_free_and_unknown_models_use_fallback():
    rates = default_rates()
    local = pick_rate(rates, "lm_studio", "google/gemma-4-e4b")
    assert estimate_cost_usd(
        normalize_usage({"prompt_tokens": 5000, "completion_tokens": 500}),
        local,
    ) == 0
    unknown_model = pick_rate(rates, "gemini", "some-new-model")
    assert unknown_model.model == "*"
    assert unknown_model.input_per_million == 0.10
    fallback = pick_rate(rates, "acme", "mystery")
    assert fallback.provider == "*"
    assert estimate_cost_usd(
        normalize_usage({"prompt_tokens": 1_000_000, "completion_tokens": 0}),
        fallback,
    ) == 3.0


def test_override_replaces_the_matching_rate_only():
    merged = merge_rates(
        default_rates(),
        [TokenRate("claude", "*", 1, 2, 3, 4)],
    )
    claude = pick_rate(merged, "claude", "claude-sonnet")
    assert claude.input_per_million == 1
    assert pick_rate(merged, "openai", "gpt-4o-mini").input_per_million == 0.15


def test_normalize_ignores_bad_numbers_and_reads_cache_alias():
    usage = normalize_usage(
        {
            "prompt_tokens": "nope",
            "completion_tokens": None,
            "cached_tokens": 12,
            "tokens_estimated": True,
        }
    )
    assert usage["prompt_tokens"] == 0
    assert usage["cache_read_input_tokens"] == 12
    assert usage["tokens_estimated"] is True
    capped = estimate_cost_usd(
        normalize_usage(
            {
                "prompt_tokens": 10,
                "cache_read_input_tokens": 50,
                "cache_creation_input_tokens": 50,
                "completion_tokens": 0,
            }
        ),
        pick_rate(default_rates(), "claude", "*"),
    )
    assert capped == 0.000003


def test_provider_usage_helpers_keep_cache_tokens():
    gemini = _usage_counts(
        {
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 2,
                "totalTokenCount": 12,
                "cachedContentTokenCount": 4,
            }
        }
    )
    assert gemini["cache_read_input_tokens"] == 4
    bedrock = _bedrock_usage(
        {
            "inputTokens": 8,
            "outputTokens": 1,
            "totalTokens": 9,
            "cacheWriteInputTokens": 3,
            "cacheReadInputTokens": 2,
        }
    )
    assert bedrock["cache_creation_input_tokens"] == 3
    assert bedrock["cache_read_input_tokens"] == 2
    assert _bedrock_usage(None)["prompt_tokens"] == 0

    class _Details:
        cached_tokens = 6

    class _Usage:
        prompt_tokens = 9
        completion_tokens = 1
        total_tokens = 10
        prompt_tokens_details = _Details()

    openai = _openai_usage(_Usage())
    assert openai["cache_read_input_tokens"] == 6
    assert _openai_usage(None)["total_tokens"] == 0
    dict_usage = _openai_usage({"prompt_tokens_details": {"cached_tokens": 2}})
    assert dict_usage["cache_read_input_tokens"] == 2
