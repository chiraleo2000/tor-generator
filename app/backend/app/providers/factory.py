"""Provider Factory — resolves LLM, embedding, and vector-store providers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.config import Settings, get_settings
from app.providers.base import EmbeddingProvider, LLMProvider, VectorStoreProvider
from app.providers.constants import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    LOCAL_EMBEDDING_PROVIDERS,
    LOCAL_EMBEDDING_SERVERS,
    LOCAL_LLM_DEFAULT_URLS,
    LOCAL_LLM_PROVIDERS,
    SGLANG_DEFAULT_EMBEDDING_URL,
)
from app.providers.sglang_health import probe_sglang_health_sync

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

VALID_DEPLOYMENT_MODES = ("on_prem", "cloud", "hybrid")
VALID_LLM_PROVIDERS = (
    "claude",
    "lm_studio",
    "ollama",
    "llama_cpp",
    "sglang",
    "openai",
    "gemini",
    "bedrock",
    "azure_foundry",
    "openai_compatible",
)
VALID_EMBEDDING_PROVIDERS = (
    "openai",
    "qwen3",
    "local",
    "gemini",
    "azure_foundry",
    "openai_compatible",
    "bedrock",
)
VALID_VECTOR_STORE_PROVIDERS = ("pgvector", "qdrant")


def _attr(settings: Any, name: str, default: Any = "") -> Any:
    value = getattr(settings, name, default)
    if isinstance(default, str) and not isinstance(value, str):
        return default
    return value


def _url_for_local_kind(settings: Any, kind: str) -> str:
    if kind == "ollama":
        return str(_attr(settings, "ollama_base_url", LOCAL_LLM_DEFAULT_URLS["ollama"]))
    if kind == "llama_cpp":
        return str(
            _attr(settings, "llama_cpp_base_url", LOCAL_LLM_DEFAULT_URLS["llama_cpp"])
        )
    if kind == "sglang":
        return str(_attr(settings, "sglang_base_url", LOCAL_LLM_DEFAULT_URLS["sglang"]))
    return str(_attr(settings, "lm_studio_base_url", LOCAL_LLM_DEFAULT_URLS["lm_studio"]))


def _local_chat_model(settings: Any, kind: str) -> str:
    if kind == "sglang":
        return str(
            _attr(settings, "sglang_model")
            or _attr(settings, "lm_studio_model", DEFAULT_CHAT_MODEL)
        )
    return str(_attr(settings, "lm_studio_model", DEFAULT_CHAT_MODEL))


class ProviderFactory:
    """Factory that resolves LLM and embeddings independently of each other."""

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
        self._validate_provider_ids()
        self._validate_llm_credentials()
        self._validate_embedding_credentials()

    def _validate_provider_ids(self) -> None:
        llm = _attr(self._settings, "llm_provider", "lm_studio")
        embedding = _attr(self._settings, "embedding_provider", "local")
        store = _attr(self._settings, "vector_store_provider", "pgvector")
        if not llm or llm not in VALID_LLM_PROVIDERS:
            raise ValueError(
                f"Invalid LLM_PROVIDER: '{llm}'. "
                f"Accepted values are: {', '.join(VALID_LLM_PROVIDERS)}"
            )
        if not embedding or embedding not in VALID_EMBEDDING_PROVIDERS:
            raise ValueError(
                f"Invalid EMBEDDING_PROVIDER: '{embedding}'. "
                f"Accepted values are: {', '.join(VALID_EMBEDDING_PROVIDERS)}"
            )
        if store and store not in VALID_VECTOR_STORE_PROVIDERS:
            raise ValueError(
                f"Invalid VECTOR_STORE_PROVIDER: '{store}'. "
                f"Accepted values are: {', '.join(VALID_VECTOR_STORE_PROVIDERS)}"
            )

    def _require_secret(self, attr: str, env_name: str, reason: str) -> None:
        if _attr(self._settings, attr):
            return
        raise ValueError(f"{env_name} is not set. {reason}")

    def _validate_llm_credentials(self) -> None:
        llm = _attr(self._settings, "llm_provider", "lm_studio")
        if llm in LOCAL_LLM_PROVIDERS:
            return
        if llm == "claude":
            self._require_secret(
                "anthropic_api_key",
                "ANTHROPIC_API_KEY",
                "LLM_PROVIDER is 'claude' and requires a valid Anthropic API key.",
            )
            return
        if llm == "openai":
            self._require_secret(
                "openai_api_key",
                "OPENAI_API_KEY",
                "LLM_PROVIDER is 'openai' and requires a valid OpenAI API key.",
            )
            return
        if llm == "gemini":
            self._require_secret(
                "gemini_api_key",
                "GEMINI_API_KEY",
                "LLM_PROVIDER is 'gemini' and requires a valid Gemini API key.",
            )
            return
        if llm == "azure_foundry":
            self._require_secret(
                "azure_foundry_api_key",
                "AZURE_FOUNDRY_API_KEY",
                "LLM_PROVIDER is 'azure_foundry' and requires a valid Azure API key.",
            )
            if not _attr(self._settings, "azure_foundry_endpoint"):
                raise ValueError(
                    "AZURE_FOUNDRY_ENDPOINT is not set. "
                    "Azure Foundry chat requires an endpoint URL."
                )
            return
        if llm == "openai_compatible" and not _attr(
            self._settings, "openai_compatible_base_url"
        ):
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL is not set. "
                "LLM_PROVIDER is 'openai_compatible' and requires a base URL."
            )

    def _validate_embedding_credentials(self) -> None:
        embedding = _attr(self._settings, "embedding_provider", "local")
        if embedding in LOCAL_EMBEDDING_PROVIDERS:
            return
        if embedding == "openai":
            self._require_secret(
                "openai_api_key",
                "OPENAI_API_KEY",
                "EMBEDDING_PROVIDER is 'openai' and requires a valid OpenAI API key.",
            )
            return
        if embedding == "gemini":
            self._require_secret(
                "gemini_api_key",
                "GEMINI_API_KEY",
                "EMBEDDING_PROVIDER is 'gemini' and requires a valid Gemini API key.",
            )
            return
        if embedding == "azure_foundry":
            self._require_secret(
                "azure_foundry_api_key",
                "AZURE_FOUNDRY_API_KEY",
                "EMBEDDING_PROVIDER is 'azure_foundry' and requires a valid Azure API key.",
            )
            if not _attr(self._settings, "azure_foundry_endpoint"):
                raise ValueError(
                    "AZURE_FOUNDRY_ENDPOINT is not set. "
                    "Azure Foundry embeddings require an endpoint URL."
                )
            return
        if embedding == "openai_compatible" and not _attr(
            self._settings, "openai_compatible_base_url"
        ):
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL is not set. "
                "EMBEDDING_PROVIDER is 'openai_compatible' and requires a base URL."
            )

    def get_llm(self, task: str = "chat") -> LLMProvider:
        """Return an LLM client for chat, draft, or structured JSON tasks.

        ``task`` selects local routing (LM Studio vs SGLang) when on-prem.
        Call as ``get_llm("draft")`` / ``get_llm("structured")``.
        """
        provider = _attr(self._settings, "llm_provider", "lm_studio")
        if provider in LOCAL_LLM_PROVIDERS:
            return self._create_local_llm_provider(self._local_kind_for_task(task))
        return self._create_cloud_llm_provider(provider)

    def _local_kind_for_task(self, task: str) -> str:
        configured = _attr(self._settings, "llm_provider", "lm_studio")
        if configured not in LOCAL_LLM_PROVIDERS:
            return "lm_studio"
        if configured == "sglang":
            return "sglang"
        if task not in {"chat", "draft", "structured"}:
            return configured
        sglang_url = _url_for_local_kind(self._settings, "sglang")
        if probe_sglang_health_sync(sglang_url):
            return "sglang"
        return configured

    def get_embedding(self) -> EmbeddingProvider:
        provider = _attr(self._settings, "embedding_provider", "local")
        if provider in LOCAL_EMBEDDING_PROVIDERS:
            return self._create_local_embedding_provider()
        return self._create_embedding_by_kind(provider)

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
        if kind == "bedrock":
            from app.providers.llm.bedrock_provider import BedrockLLMProvider

            return BedrockLLMProvider(
                region=_attr(self._settings, "bedrock_region", "ap-southeast-1"),
                model_id=_attr(self._settings, "bedrock_model_id"),
                aws_access_key_id=_attr(self._settings, "aws_access_key_id"),
                aws_secret_access_key=_attr(self._settings, "aws_secret_access_key"),
                aws_bearer_token_bedrock=_attr(
                    self._settings, "aws_bearer_token_bedrock"
                ),
                timeout=float(
                    _attr(self._settings, "cloud_llm_timeout", 300.0) or 300.0
                ),
            )
        if kind == "azure_foundry":
            from app.providers.llm.azure_foundry_provider import AzureFoundryLLMProvider

            return AzureFoundryLLMProvider(
                api_key=_attr(self._settings, "azure_foundry_api_key"),
                endpoint=_attr(self._settings, "azure_foundry_endpoint"),
                deployment=_attr(self._settings, "azure_foundry_deployment"),
                api_version=_attr(self._settings, "azure_foundry_api_version", "2024-10-21"),
            )
        if kind == "openai_compatible":
            from app.providers.llm.openai_provider import OpenAILLMProvider

            api_key = _attr(self._settings, "openai_compatible_api_key") or "not-needed"
            return OpenAILLMProvider(
                api_key=api_key,
                model_name=_attr(self._settings, "openai_compatible_model")
                or _attr(self._settings, "lm_studio_model"),
                base_url=_attr(self._settings, "openai_compatible_base_url"),
            )
        from app.providers.llm.claude_provider import ClaudeSonnetProvider

        return ClaudeSonnetProvider(api_key=_attr(self._settings, "anthropic_api_key"))

    def _create_embedding_by_kind(self, kind: str) -> EmbeddingProvider:
        if kind == "gemini":
            return self._create_gemini_embedding_provider()
        if kind == "bedrock":
            from app.providers.embedding.bedrock_provider import BedrockEmbeddingProvider

            return BedrockEmbeddingProvider(
                region=_attr(self._settings, "bedrock_region", "ap-southeast-1"),
                model_id=_attr(
                    self._settings,
                    "bedrock_embedding_model_id",
                    "amazon.titan-embed-text-v2:0",
                ),
                aws_access_key_id=_attr(self._settings, "aws_access_key_id"),
                aws_secret_access_key=_attr(self._settings, "aws_secret_access_key"),
                aws_bearer_token_bedrock=_attr(
                    self._settings, "aws_bearer_token_bedrock"
                ),
            )
        if kind == "azure_foundry":
            from httpx import Timeout
            from openai import AsyncAzureOpenAI

            from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

            provider = OpenAIEmbeddingProvider(
                api_key=_attr(self._settings, "azure_foundry_api_key"),
                model=_attr(self._settings, "azure_foundry_embedding_deployment")
                or _attr(self._settings, "azure_foundry_deployment")
                or "text-embedding-3-small",
                dimensions=EMBEDDING_DIMENSIONS,
            )
            provider._client = AsyncAzureOpenAI(
                api_key=_attr(self._settings, "azure_foundry_api_key"),
                azure_endpoint=_attr(self._settings, "azure_foundry_endpoint"),
                api_version=_attr(
                    self._settings, "azure_foundry_api_version", "2024-10-21"
                ),
                timeout=Timeout(60.0, connect=10.0),
            )
            return provider
        if kind == "openai_compatible":
            from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

            return OpenAIEmbeddingProvider(
                api_key=_attr(self._settings, "openai_compatible_api_key") or "not-needed",
                model=_attr(
                    self._settings,
                    "openai_compatible_embedding_model",
                    "text-embedding-3-small",
                ),
                dimensions=EMBEDDING_DIMENSIONS,
                base_url=_attr(self._settings, "openai_compatible_base_url"),
            )
        return self._create_openai_embedding_provider()

    def _create_local_llm_provider(self, kind: str | None = None) -> LLMProvider:
        from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

        resolved = kind or _attr(self._settings, "llm_provider", "lm_studio")
        if resolved not in LOCAL_LLM_PROVIDERS:
            resolved = "lm_studio"
        return LMStudioLocalProvider(
            base_url=_url_for_local_kind(self._settings, resolved),
            model_name=_local_chat_model(self._settings, resolved),
            timeout=_attr(self._settings, "lm_studio_timeout", 180.0),
        )

    def _create_openai_embedding_provider(self) -> EmbeddingProvider:
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=_attr(self._settings, "openai_api_key"),
            model=_attr(self._settings, "openai_embedding_model", "text-embedding-3-small"),
            dimensions=EMBEDDING_DIMENSIONS,
        )

    def _create_local_embedding_provider(self) -> EmbeddingProvider:
        from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider

        override = str(_attr(self._settings, "local_embedding_base_url", "") or "").strip()
        kind = _attr(self._settings, "local_embedding_server", "lm_studio")
        if kind not in LOCAL_EMBEDDING_SERVERS:
            kind = "lm_studio"
        if kind == "sglang":
            base_url = override or str(
                _attr(
                    self._settings,
                    "sglang_embedding_base_url",
                    SGLANG_DEFAULT_EMBEDDING_URL,
                )
            )
            model = str(
                _attr(self._settings, "sglang_embedding_model")
                or _attr(
                    self._settings,
                    "lm_studio_embedding_model",
                    DEFAULT_EMBEDDING_MODEL,
                )
            )
        else:
            base_url = override or _url_for_local_kind(self._settings, kind)
            model = str(
                _attr(
                    self._settings,
                    "lm_studio_embedding_model",
                    DEFAULT_EMBEDDING_MODEL,
                )
            )
        from httpx import Timeout

        return Qwen3LocalEmbeddingProvider(
            base_url=base_url,
            model=model,
            timeout=Timeout(60.0, connect=20.0),
            max_retries=2,
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
