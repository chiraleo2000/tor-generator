"""Provider/model capability table for the same Docker image on local VM and cloud.

LLM and embedding providers are selected with env (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`,
model ids). Do not hard-code Gemma's 131k window, thinking flags, or 768-d vectors.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.providers.constants import (
    CLOUD_LLM_PROVIDERS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    LOCAL_LLM_PROVIDERS,
)

# Gemma 4 E4B / local llama.cpp-class windows.
GEMMA_CONTEXT_WINDOW = 131_072
# Safe default when the model is unknown (OpenAI-compatible endpoint on a VM).
DEFAULT_CONTEXT_WINDOW = 32_768
DEFAULT_SECTION_COMPLETION = 16_384
DEFAULT_SCOPE_COMPLETION = 4_096
LOCAL_SECTION_COMPLETION = 32_768
LOCAL_SCOPE_COMPLETION = 8_192
CLOUD_SECTION_COMPLETION = 16_384
CLOUD_SCOPE_COMPLETION = 4_096

EMBEDDING_INPUT_GEMMA = 2_048
EMBEDDING_INPUT_OPENAI = 8_191
EMBEDDING_INPUT_COHERE = 4_096
EMBEDDING_DIM_GEMMA = 768
EMBEDDING_DIM_COHERE_V4 = 1_024
EMBEDDING_DIM_OPENAI_SMALL = 1_536
EMBEDDING_DIM_TITAN_V2 = 1_024

THINKING_PROVIDERS = frozenset(LOCAL_LLM_PROVIDERS)
LLM_PASSTHROUGH_KEYS = frozenset(
    {
        "temperature",
        "max_tokens",
        "top_p",
        "stop",
        "stop_sequences",
        "tools",
        "stream",
        "response_format",
        "extra_body",
        "json_schema",
        "json_schema_name",
        "_guided_json",
    }
)


@dataclass(frozen=True)
class ModelCapabilities:
    provider: str
    model: str
    context_window: int
    section_max_tokens: int
    scope_max_tokens: int
    thinking_supported: bool
    embedding_max_input: int
    embedding_dimensions: int


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return max(256, int(raw))
    except ValueError:
        return default


def _settings_or_none() -> Any:
    try:
        from app.config import get_settings

        return get_settings()
    except Exception:
        return None


def _llm_provider(settings: Any | None = None) -> str:
    env = (os.environ.get("LLM_PROVIDER") or "").strip()
    if env:
        return env
    if settings is not None:
        return str(getattr(settings, "llm_provider", "lm_studio") or "lm_studio")
    return "lm_studio"


def _embedding_provider(settings: Any | None = None) -> str:
    env = (os.environ.get("EMBEDDING_PROVIDER") or "").strip()
    if env:
        return env
    if settings is not None:
        return str(getattr(settings, "embedding_provider", "local") or "local")
    return "local"


def _chat_model(provider: str, settings: Any | None = None) -> str:
    if settings is None:
        return os.environ.get("LM_STUDIO_MODEL") or DEFAULT_CHAT_MODEL
    if provider == "openai":
        return str(getattr(settings, "openai_chat_model", "") or "gpt-4o-mini")
    if provider == "claude":
        return str(getattr(settings, "claude_model", "") or "claude-sonnet-4-20250514")
    if provider == "gemini":
        return str(getattr(settings, "gemini_model", "") or "")
    if provider == "bedrock":
        return str(getattr(settings, "bedrock_model_id", "") or "")
    if provider == "azure_foundry":
        return str(getattr(settings, "azure_foundry_deployment", "") or "")
    if provider == "openai_compatible":
        return str(getattr(settings, "openai_compatible_model", "") or "")
    if provider == "sglang":
        return str(
            getattr(settings, "sglang_model", "")
            or getattr(settings, "lm_studio_model", "")
            or DEFAULT_CHAT_MODEL
        )
    return str(getattr(settings, "lm_studio_model", "") or DEFAULT_CHAT_MODEL)


def _embedding_model(provider: str, settings: Any | None = None) -> str:
    env = (os.environ.get("BEDROCK_EMBEDDING_MODEL_ID") or "").strip()
    if provider == "bedrock" and env:
        return env
    if settings is None:
        return os.environ.get("LM_STUDIO_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL
    if provider == "openai":
        return str(getattr(settings, "openai_embedding_model", "") or "text-embedding-3-small")
    if provider == "gemini":
        return str(getattr(settings, "gemini_embedding_model", "") or "text-embedding-004")
    if provider == "bedrock":
        return str(getattr(settings, "bedrock_embedding_model_id", "") or "")
    if provider == "azure_foundry":
        return str(getattr(settings, "azure_foundry_embedding_deployment", "") or "")
    if provider == "openai_compatible":
        return str(getattr(settings, "openai_compatible_embedding_model", "") or "")
    return str(getattr(settings, "lm_studio_embedding_model", "") or DEFAULT_EMBEDDING_MODEL)


def _context_window(provider: str, model: str) -> int:
    lowered = f"{provider} {model}".lower()
    if "gemma" in lowered or provider in LOCAL_LLM_PROVIDERS:
        return GEMMA_CONTEXT_WINDOW
    if "gpt-4o" in lowered or "gpt-4.1" in lowered or "o3" in lowered or "o4" in lowered:
        return 128_000
    if "gpt-4" in lowered:
        return 128_000
    if "claude" in lowered or "anthropic" in lowered:
        return 200_000
    if "gemini" in lowered:
        return 128_000
    if provider == "bedrock":
        if "claude" in lowered:
            return 200_000
        return 128_000
    if provider in CLOUD_LLM_PROVIDERS:
        return 128_000
    return DEFAULT_CONTEXT_WINDOW


def _completion_caps(provider: str, context_window: int) -> tuple[int, int]:
    if provider in LOCAL_LLM_PROVIDERS:
        section = min(LOCAL_SECTION_COMPLETION, max(256, context_window - 4_096))
        scope = min(LOCAL_SCOPE_COMPLETION, section)
        return section, scope
    section = min(CLOUD_SECTION_COMPLETION, max(256, context_window - 4_096))
    scope = min(CLOUD_SCOPE_COMPLETION, section)
    return section, scope


def _embedding_limits(provider: str, model: str) -> tuple[int, int]:
    lowered = f"{provider} {model}".lower()
    if "cohere" in lowered or "embed-v4" in lowered:
        return EMBEDDING_INPUT_COHERE, EMBEDDING_DIM_COHERE_V4
    if "titan" in lowered:
        return EMBEDDING_INPUT_OPENAI, EMBEDDING_DIM_TITAN_V2
    if "text-embedding-3" in lowered or provider == "openai":
        dim = EMBEDDING_DIM_OPENAI_SMALL
        if "large" in lowered:
            dim = 3_072
        return EMBEDDING_INPUT_OPENAI, dim
    if "gemini" in lowered or provider == "gemini":
        return EMBEDDING_INPUT_GEMMA, 768
    if provider in {"local", "qwen3"} or "embeddinggemma" in lowered or "gemma" in lowered:
        return EMBEDDING_INPUT_GEMMA, EMBEDDING_DIM_GEMMA
    if provider == "bedrock":
        return EMBEDDING_INPUT_COHERE, EMBEDDING_DIM_COHERE_V4
    return EMBEDDING_INPUT_GEMMA, EMBEDDING_DIM_GEMMA


def thinking_supported(provider: str | None = None) -> bool:
    kind = provider or _llm_provider(_settings_or_none())
    return kind in THINKING_PROVIDERS


def compose_thinking_enabled(provider: str | None = None) -> bool:
    """Compose defaults off even when the model can think (empty-section bug)."""
    if not thinking_supported(provider):
        return False
    raw = (os.environ.get("TOR_COMPOSE_ENABLE_THINKING") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@lru_cache(maxsize=32)
def capabilities_for(
    llm_provider: str,
    chat_model: str,
    embedding_provider: str,
    embedding_model: str,
) -> ModelCapabilities:
    window = _int_env("TOR_CONTEXT_WINDOW", _context_window(llm_provider, chat_model))
    section_default, scope_default = _completion_caps(llm_provider, window)
    section = _int_env("TOR_SECTION_MAX_TOKENS", section_default)
    scope = _int_env("TOR_SCOPE_SUB_MAX_TOKENS", scope_default)
    embed_in, embed_dim = _embedding_limits(embedding_provider, embedding_model)
    embed_in = _int_env("EMBEDDING_MAX_TOKENS", embed_in)
    embed_dim = _int_env("EMBEDDING_DIMENSIONS", embed_dim)
    return ModelCapabilities(
        provider=llm_provider,
        model=chat_model,
        context_window=window,
        section_max_tokens=min(section, max(256, window - 256)),
        scope_max_tokens=min(scope, section),
        thinking_supported=thinking_supported(llm_provider),
        embedding_max_input=embed_in,
        embedding_dimensions=embed_dim,
    )


def current_capabilities() -> ModelCapabilities:
    settings = _settings_or_none()
    llm = _llm_provider(settings)
    embed = _embedding_provider(settings)
    return capabilities_for(
        llm,
        _chat_model(llm, settings),
        embed,
        _embedding_model(embed, settings),
    )


def context_window() -> int:
    return current_capabilities().context_window


def section_max_tokens() -> int:
    return current_capabilities().section_max_tokens


def scope_max_tokens() -> int:
    return current_capabilities().scope_max_tokens


def embedding_max_input() -> int:
    return current_capabilities().embedding_max_input


def embedding_dimensions() -> int:
    return current_capabilities().embedding_dimensions


def llm_call_kwargs(
    provider: str | None = None,
    *,
    thinking: bool | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Filter invoke/stream kwargs for the live provider (no thinking on cloud chat APIs)."""
    kind = provider or current_capabilities().provider
    payload = dict(kwargs)
    if thinking is None:
        payload["enable_thinking"] = thinking_supported(kind)
    else:
        payload["enable_thinking"] = bool(thinking)
    return filter_llm_kwargs(kind, payload)


def filter_llm_kwargs(provider: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Drop thinking/schema flags that cloud chat APIs reject."""
    payload = dict(kwargs)
    thinking = payload.pop("enable_thinking", None)
    payload.pop("disable_thinking", None)
    if not thinking_supported(provider):
        payload.pop("extra_body", None)
        cleaned = {
            key: value
            for key, value in payload.items()
            if key in LLM_PASSTHROUGH_KEYS
            and key not in {"json_schema", "json_schema_name", "_guided_json"}
        }
        return cleaned
    if thinking is not None:
        payload["enable_thinking"] = bool(thinking)
    return payload


def reset_capability_cache() -> None:
    capabilities_for.cache_clear()
