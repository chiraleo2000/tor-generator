"""Token-price table and USD estimate for one LLM call.

Rates are USD per 1,000,000 tokens. Local servers default to zero.
An unknown provider/model uses the conservative ``*`` / ``*`` row.
"""

from __future__ import annotations

from dataclasses import dataclass

LOCAL_PROVIDERS = frozenset({"lm_studio", "ollama", "llama_cpp", "sglang"})


@dataclass(frozen=True)
class TokenRate:
    provider: str
    model: str
    input_per_million: float
    output_per_million: float
    cache_write_per_million: float
    cache_read_per_million: float


def _rate(
    provider: str,
    model: str,
    input_rate: float,
    output_rate: float,
    cache_write: float,
    cache_read: float,
) -> TokenRate:
    return TokenRate(
        provider=provider,
        model=model,
        input_per_million=input_rate,
        output_per_million=output_rate,
        cache_write_per_million=cache_write,
        cache_read_per_million=cache_read,
    )


def default_rates() -> list[TokenRate]:
    """Built-in prices. Admin edits in the database override these."""
    zero = (0.0, 0.0, 0.0, 0.0)
    return [
        _rate("lm_studio", "*", *zero),
        _rate("ollama", "*", *zero),
        _rate("llama_cpp", "*", *zero),
        _rate("sglang", "*", *zero),
        _rate("claude", "*", 3.0, 15.0, 3.75, 0.30),
        _rate("bedrock", "*", 3.0, 15.0, 3.75, 0.30),
        _rate("gemini", "*", 0.10, 0.40, 0.0, 0.025),
        _rate("openai", "*", 0.15, 0.60, 0.0, 0.075),
        _rate("azure_foundry", "*", 0.15, 0.60, 0.0, 0.075),
        _rate("openai_compatible", "*", 0.15, 0.60, 0.0, 0.075),
        _rate("*", "*", 3.0, 15.0, 3.75, 0.30),
    ]


def merge_rates(base: list[TokenRate], overrides: list[TokenRate]) -> list[TokenRate]:
    merged = {(rate.provider, rate.model): rate for rate in base}
    for rate in overrides:
        merged[(rate.provider, rate.model)] = rate
    return list(merged.values())


def _matching_rate(rates: list[TokenRate], provider_id: str, model_id: str) -> TokenRate | None:
    for rate in rates:
        if rate.provider == provider_id and rate.model == model_id:
            return rate
    return None


def pick_rate(rates: list[TokenRate], provider: str, model: str) -> TokenRate:
    provider_id = (provider or "").strip().lower() or "*"
    model_id = (model or "").strip() or "*"
    exact = _matching_rate(rates, provider_id, model_id)
    if exact is not None:
        return exact
    starred = _matching_rate(rates, provider_id, "*")
    if starred is not None:
        return starred
    if provider_id in LOCAL_PROVIDERS:
        return _rate(provider_id, "*", 0.0, 0.0, 0.0, 0.0)
    fallback = _matching_rate(rates, "*", "*")
    if fallback is not None:
        return fallback
    return _rate("*", "*", 3.0, 15.0, 3.75, 0.30)


def _as_int(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def normalize_usage(raw: dict | None) -> dict[str, int | bool]:
    """Map provider usage payloads onto one token shape."""
    payload = raw or {}
    prompt = _as_int(payload.get("prompt_tokens"))
    completion = _as_int(payload.get("completion_tokens"))
    cache_read = _as_int(
        payload.get("cache_read_input_tokens")
        if payload.get("cache_read_input_tokens") is not None
        else payload.get("cached_tokens")
    )
    cache_write = _as_int(payload.get("cache_creation_input_tokens"))
    total = _as_int(payload.get("total_tokens")) or (prompt + completion)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "cache_creation_input_tokens": cache_write,
        "cache_read_input_tokens": cache_read,
        "tokens_estimated": bool(payload.get("tokens_estimated")),
    }


def estimate_cost_usd(usage: dict, rate: TokenRate) -> float:
    """Price fresh input, cache write, cache read, and output separately."""
    prompt = _as_int(usage.get("prompt_tokens"))
    completion = _as_int(usage.get("completion_tokens"))
    cache_read = min(_as_int(usage.get("cache_read_input_tokens")), prompt)
    cache_write = min(
        _as_int(usage.get("cache_creation_input_tokens")),
        max(0, prompt - cache_read),
    )
    fresh = max(0, prompt - cache_read - cache_write)
    cost = (
        fresh * rate.input_per_million
        + cache_write * rate.cache_write_per_million
        + cache_read * rate.cache_read_per_million
        + completion * rate.output_per_million
    ) / 1_000_000
    return round(cost, 6)


def rate_to_dict(rate: TokenRate) -> dict[str, float | str]:
    return {
        "provider": rate.provider,
        "model": rate.model,
        "input_per_million": rate.input_per_million,
        "output_per_million": rate.output_per_million,
        "cache_write_per_million": rate.cache_write_per_million,
        "cache_read_per_million": rate.cache_read_per_million,
    }
