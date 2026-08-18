"""Provider Factory — resolves LLM, embedding, and vector-store providers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.config import Settings, get_settings
from app.providers.base import EmbeddingProvider, LLMProvider, VectorStoreProvider
from app.providers.constants import (
    CLOUD_LLM_PROVIDERS,
    EMBEDDING_DIMENSIONS,
    LOCAL_EMBEDDING_PROVIDERS,
    LOCAL_LLM_DEFAULT_URLS,
    LOCAL_LLM_PROVIDERS,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

VALID_DEPLOYMENT_MODES = ("on_prem", "cloud", "hybrid")
VALID_LLM_PROVIDERS = (
    "claude",
    "lm_studio",
    "ollama",
    "llama_cpp",
    "openai",
    "gemini",
)
VALID_EMBEDDING_PROVIDERS = ("openai", "qwen3", "local", "gemini")
VALID_VECTOR_STORE_PROVIDERS = ("pgvector", "qdrant")


def _attr(settings: Any, name: str, default: Any = "") -> Any:
    return getattr(settings, name, default)


class ProviderFactory:
    """Factory that resolves providers from DEPLOYMENT_MODE and sub-provider ids."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        mode = self._settings.deployment_mode
        if mode not in VALID_DEPLOYMENT_MODES:
            raise ValueError(
                f"Invalid DEPLOYMENT_MODE: '{mode}'. "
                f"Accepted values are: {', '.join(VALID_DEPLOYMENT_MODES)}"
            )
        if mode == "cloud":
            self._validate_cloud_config()
        elif mode == "hybrid":
            self._validate_hybrid_config()

    def _resolved_cloud_llm(self) -> str:
        provider = _attr(self._settings, "llm_provider", "lm_studio")
        if provider in CLOUD_LLM_PROVIDERS:
            return provider
        return "claude"

    def _resolved_cloud_embedding(self) -> str:
        provider = _attr(self._settings, "embedding_provider", "local")
        if provider == "gemini":
            return "gemini"
        return "openai"

    def _validate_cloud_config(self) -> None:
        llm = self._resolved_cloud_llm()
        embedding = self._resolved_cloud_embedding()
        if llm == "claude" and not _attr(self._settings, "anthropic_api_key"):
            raise ValueError(
                "DEPLOYMENT_MODE is 'cloud' but ANTHROPIC_API_KEY is not set. "
                "Cloud mode requires a valid Anthropic API key for the LLM provider."
            )
        if llm == "openai" and not _attr(self._settings, "openai_api_key"):
            raise ValueError(
                "DEPLOYMENT_MODE is 'cloud' but OPENAI_API_KEY is not set. "
                "Cloud chat requires a valid OpenAI API key."
            )
        if llm == "gemini" and not _attr(self._settings, "gemini_api_key"):
            raise ValueError(
                "DEPLOYMENT_MODE is 'cloud' but GEMINI_API_KEY is not set. "
                "Cloud chat requires a valid Gemini API key."
            )
        if embedding == "openai" and not _attr(self._settings, "openai_api_key"):
            raise ValueError(
                "DEPLOYMENT_MODE is 'cloud' but OPENAI_API_KEY is not set. "
                "Cloud mode requires a valid OpenAI API key for the embedding provider."
            )
        if embedding == "gemini" and not _attr(self._settings, "gemini_api_key"):
            raise ValueError(
                "DEPLOYMENT_MODE is 'cloud' but GEMINI_API_KEY is not set. "
                "Gemini embeddings require a valid Gemini API key."
            )

    def _validate_hybrid_config(self) -> None:
        settings = self._settings
        if not settings.llm_provider:
            raise ValueError(
                "DEPLOYMENT_MODE is 'hybrid' but LLM_PROVIDER is not set. "
                f"Set LLM_PROVIDER to one of: {', '.join(VALID_LLM_PROVIDERS)}"
            )
        if settings.llm_provider not in VALID_LLM_PROVIDERS:
            raise ValueError(
                f"Invalid LLM_PROVIDER: '{settings.llm_provider}'. "
                f"Accepted values are: {', '.join(VALID_LLM_PROVIDERS)}"
            )
        if not settings.embedding_provider:
            raise ValueError(
                "DEPLOYMENT_MODE is 'hybrid' but EMBEDDING_PROVIDER is not set. "
                f"Set EMBEDDING_PROVIDER to one of: {', '.join(VALID_EMBEDDING_PROVIDERS)}"
            )
        if settings.embedding_provider not in VALID_EMBEDDING_PROVIDERS:
            raise ValueError(
                f"Invalid EMBEDDING_PROVIDER: '{settings.embedding_provider}'. "
                f"Accepted values are: {', '.join(VALID_EMBEDDING_PROVIDERS)}"
            )
        if not settings.vector_store_provider:
            raise ValueError(
                "DEPLOYMENT_MODE is 'hybrid' but VECTOR_STORE_PROVIDER is not set. "
                f"Set VECTOR_STORE_PROVIDER to one of: {', '.join(VALID_VECTOR_STORE_PROVIDERS)}"
            )
        if settings.vector_store_provider not in VALID_VECTOR_STORE_PROVIDERS:
            raise ValueError(
                f"Invalid VECTOR_STORE_PROVIDER: '{settings.vector_store_provider}'. "
                f"Accepted values are: {', '.join(VALID_VECTOR_STORE_PROVIDERS)}"
            )
        if settings.llm_provider == "claude" and not _attr(settings, "anthropic_api_key"):
            raise ValueError(
                "LLM_PROVIDER is 'claude' but ANTHROPIC_API_KEY is not set. "
                "Provide a valid Anthropic API key."
            )
        if settings.llm_provider == "openai" and not _attr(settings, "openai_api_key"):
            raise ValueError(
                "LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set. "
                "Provide a valid OpenAI API key."
            )
        if settings.llm_provider == "gemini" and not _attr(settings, "gemini_api_key"):
            raise ValueError(
                "LLM_PROVIDER is 'gemini' but GEMINI_API_KEY is not set. "
                "Provide a valid Gemini API key."
            )
        if settings.embedding_provider == "openai" and not _attr(settings, "openai_api_key"):
            raise ValueError(
                "EMBEDDING_PROVIDER is 'openai' but OPENAI_API_KEY is not set. "
                "Provide a valid OpenAI API key."
            )
        if settings.embedding_provider == "gemini" and not _attr(settings, "gemini_api_key"):
            raise ValueError(
                "EMBEDDING_PROVIDER is 'gemini' but GEMINI_API_KEY is not set. "
                "Provide a valid Gemini API key."
            )

    def get_llm(self) -> LLMProvider:
        mode = self._settings.deployment_mode
        if mode == "on_prem":
            return self._create_local_llm_provider()
        if mode == "cloud":
            return self._create_cloud_llm_provider(self._resolved_cloud_llm())
        if self._settings.llm_provider in LOCAL_LLM_PROVIDERS:
            return self._create_local_llm_provider()
        return self._create_cloud_llm_provider(self._settings.llm_provider)

    def get_embedding(self) -> EmbeddingProvider:
        mode = self._settings.deployment_mode
        if mode == "on_prem":
            return self._create_local_embedding_provider()
        if mode == "cloud":
            kind = self._resolved_cloud_embedding()
            if kind == "gemini":
                return self._create_gemini_embedding_provider()
            return self._create_openai_embedding_provider()
        if self._settings.embedding_provider in LOCAL_EMBEDDING_PROVIDERS:
            return self._create_local_embedding_provider()
        if self._settings.embedding_provider == "gemini":
            return self._create_gemini_embedding_provider()
        return self._create_openai_embedding_provider()

    def get_vector_store(
        self,
        session_factory: "async_sessionmaker[AsyncSession] | None" = None,
    ) -> VectorStoreProvider:
        use_qdrant = _attr(self._settings, "vector_store_provider", "pgvector") == "qdrant"
        if use_qdrant:
            return self._create_qdrant_provider()
        return self._create_pgvector_provider(session_factory)

    def _create_cloud_llm_provider(self, kind: str) -> LLMProvider:
        if kind == "openai":
            from app.providers.llm.openai_provider import OpenAILLMProvider

            return OpenAILLMProvider(
                api_key=_attr(self._settings, "openai_api_key"),
                model_name=_attr(self._settings, "openai_chat_model", "gpt-4o-mini"),
            )
        if kind == "gemini":
            from app.providers.llm.gemini_provider import GeminiLLMProvider

            return GeminiLLMProvider(
                api_key=_attr(self._settings, "gemini_api_key"),
                model_name=_attr(self._settings, "gemini_model", "gemini-2.0-flash"),
            )
        from app.providers.llm.claude_provider import ClaudeSonnetProvider

        return ClaudeSonnetProvider(api_key=_attr(self._settings, "anthropic_api_key"))

    def _create_local_llm_provider(self) -> LLMProvider:
        from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

        kind = _attr(self._settings, "llm_provider", "lm_studio")
        if kind not in LOCAL_LLM_PROVIDERS:
            kind = "lm_studio"
        if kind == "ollama":
            base_url = _attr(
                self._settings, "ollama_base_url", LOCAL_LLM_DEFAULT_URLS["ollama"]
            )
        elif kind == "llama_cpp":
            base_url = _attr(
                self._settings,
                "llama_cpp_base_url",
                LOCAL_LLM_DEFAULT_URLS["llama_cpp"],
            )
        else:
            base_url = _attr(
                self._settings,
                "lm_studio_base_url",
                LOCAL_LLM_DEFAULT_URLS["lm_studio"],
            )
        return LMStudioLocalProvider(
            base_url=base_url,
            model_name=_attr(self._settings, "lm_studio_model"),
            timeout=_attr(self._settings, "lm_studio_timeout", 180.0),
        )

    def _create_openai_embedding_provider(self) -> EmbeddingProvider:
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=_attr(self._settings, "openai_api_key"),
            dimensions=EMBEDDING_DIMENSIONS,
        )

    def _create_local_embedding_provider(self) -> EmbeddingProvider:
        from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider

        kind = _attr(self._settings, "llm_provider", "lm_studio")
        if kind == "ollama":
            base_url = _attr(
                self._settings, "ollama_base_url", LOCAL_LLM_DEFAULT_URLS["ollama"]
            )
        elif kind == "llama_cpp":
            base_url = _attr(
                self._settings,
                "llama_cpp_base_url",
                LOCAL_LLM_DEFAULT_URLS["llama_cpp"],
            )
        else:
            base_url = _attr(
                self._settings,
                "lm_studio_base_url",
                LOCAL_LLM_DEFAULT_URLS["lm_studio"],
            )
        return Qwen3LocalEmbeddingProvider(
            base_url=base_url,
            model=_attr(
                self._settings,
                "lm_studio_embedding_model",
                "text-embedding-embeddinggemma-300m",
            ),
        )

    def _create_gemini_embedding_provider(self) -> EmbeddingProvider:
        from app.providers.embedding.gemini_provider import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(
            api_key=_attr(self._settings, "gemini_api_key"),
            model=_attr(self._settings, "gemini_embedding_model", "text-embedding-004"),
        )

    def _create_pgvector_provider(
        self,
        session_factory: "async_sessionmaker[AsyncSession] | None",
    ) -> VectorStoreProvider:
        from app.providers.vector_store.pgvector_provider import PgVectorProvider

        if session_factory is None:
            raise ValueError(
                "PgVectorProvider requires a session_factory (SQLAlchemy async session maker). "
                "Pass session_factory to get_vector_store()."
            )
        return PgVectorProvider(session_factory=session_factory)

    def _create_qdrant_provider(self) -> VectorStoreProvider:
        from app.providers.vector_store.qdrant_provider import QdrantProvider

        return QdrantProvider(
            host=_attr(self._settings, "qdrant_host", "localhost"),
            port=_attr(self._settings, "qdrant_port", 6333),
            vector_size=EMBEDDING_DIMENSIONS,
        )
