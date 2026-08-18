"""Unit tests for ProviderFactory deployment mode resolution.

Tests cover:
- on_prem mode: returns all local providers
- cloud mode: returns all cloud providers
- hybrid mode: per-component provider selection
- Error handling: invalid DEPLOYMENT_MODE, missing sub-provider vars, missing API keys
"""

from unittest.mock import MagicMock, patch
import sys

import pytest

# Stub qdrant-client so QdrantProvider can be constructed without the package.
if "qdrant_client" not in sys.modules:
    qdrant_mock = MagicMock()
    sys.modules["qdrant_client"] = qdrant_mock
    sys.modules["qdrant_client.models"] = qdrant_mock.models

from app.config import Settings
from app.providers.factory import (
    ProviderFactory,
    VALID_DEPLOYMENT_MODES,
    VALID_EMBEDDING_PROVIDERS,
    VALID_LLM_PROVIDERS,
    VALID_VECTOR_STORE_PROVIDERS,
)


# ---------------------------------------------------------------------------
# Helper: create Settings instances with overrides
# ---------------------------------------------------------------------------


def make_settings(**overrides) -> Settings:
    """Create a Settings instance with sensible defaults for testing.

    Bypasses .env file loading by setting _env_file to None.
    """
    defaults = {
        "deployment_mode": "on_prem",
        "anthropic_api_key": "",
        "openai_api_key": "",
        "gemini_api_key": "",
        "lm_studio_base_url": "http://localhost:1234/v1",
        "lm_studio_model": "test-model",
        "lm_studio_embedding_model": "text-embedding-embeddinggemma-300m",
        "lm_studio_timeout": 180.0,
        "ollama_base_url": "http://host.docker.internal:11434/v1",
        "llama_cpp_base_url": "http://host.docker.internal:8080/v1",
        "openai_chat_model": "gpt-4o-mini",
        "gemini_model": "gemini-2.0-flash",
        "llm_provider": "lm_studio",
        "embedding_provider": "qwen3",
        "vector_store_provider": "pgvector",
        "qdrant_host": "localhost",
        "qdrant_port": 6333,
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_db": "test_db",
        "postgres_user": "test_user",
        "postgres_password": "test_pass",
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_password": "test_redis",
        "minio_endpoint": "localhost:9000",
        "minio_access_key": "minioadmin",
        "minio_secret_key": "minioadmin123",
        "minio_bucket": "test-bucket",
        "jwt_secret": "test_jwt_secret_at_least_32_characters_long!!",
        "jwt_expiry_hours": 24,
        "rate_limit_requests_per_minute": 100,
        "rate_limit_uploads_per_minute": 10,
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# on_prem mode tests
# ---------------------------------------------------------------------------


class TestOnPremMode:
    """Tests for on_prem deployment mode."""

    def test_factory_creates_successfully(self):
        """on_prem mode should initialize without API keys."""
        settings = make_settings(deployment_mode="on_prem")
        factory = ProviderFactory(settings=settings)
        assert factory is not None

    def test_get_llm_returns_lm_studio_provider(self):
        """on_prem mode should return LMStudioLocalProvider."""
        from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

        settings = make_settings(deployment_mode="on_prem")
        factory = ProviderFactory(settings=settings)
        llm = factory.get_llm()
        assert isinstance(llm, LMStudioLocalProvider)

    def test_get_embedding_returns_qwen3_provider(self):
        """on_prem mode should return Qwen3LocalEmbeddingProvider."""
        from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider

        settings = make_settings(deployment_mode="on_prem")
        factory = ProviderFactory(settings=settings)
        embedding = factory.get_embedding()
        assert isinstance(embedding, Qwen3LocalEmbeddingProvider)

    def test_get_vector_store_returns_pgvector_provider(self):
        """on_prem mode should return PgVectorProvider when session_factory provided."""
        from app.providers.vector_store.pgvector_provider import PgVectorProvider

        settings = make_settings(deployment_mode="on_prem")
        factory = ProviderFactory(settings=settings)
        mock_session_factory = MagicMock()
        vs = factory.get_vector_store(session_factory=mock_session_factory)
        assert isinstance(vs, PgVectorProvider)

    def test_get_vector_store_raises_without_session_factory(self):
        """on_prem mode should raise ValueError if no session_factory for PgVector."""
        settings = make_settings(deployment_mode="on_prem")
        factory = ProviderFactory(settings=settings)
        with pytest.raises(ValueError, match="session_factory"):
            factory.get_vector_store(session_factory=None)

    def test_get_vector_store_honors_qdrant_on_prem(self):
        from app.providers.vector_store.qdrant_provider import QdrantProvider

        settings = make_settings(
            deployment_mode="on_prem",
            vector_store_provider="qdrant",
        )
        vs = ProviderFactory(settings=settings).get_vector_store()
        assert isinstance(vs, QdrantProvider)


# ---------------------------------------------------------------------------
# cloud mode tests
# ---------------------------------------------------------------------------


class TestCloudMode:
    """Tests for cloud deployment mode."""

    def test_factory_creates_with_valid_keys(self):
        """cloud mode should initialize with both API keys."""
        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="sk-ant-test-key",
            openai_api_key="sk-openai-test-key",
        )
        factory = ProviderFactory(settings=settings)
        assert factory is not None

    def test_factory_rejects_missing_anthropic_key(self):
        """cloud mode should reject missing ANTHROPIC_API_KEY."""
        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="",
            openai_api_key="sk-openai-test-key",
        )
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            ProviderFactory(settings=settings)

    def test_factory_rejects_missing_openai_key(self):
        """cloud mode should reject missing OPENAI_API_KEY."""
        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="sk-ant-test-key",
            openai_api_key="",
        )
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            ProviderFactory(settings=settings)

    def test_get_llm_returns_claude_provider(self):
        """cloud mode should return ClaudeSonnetProvider."""
        from app.providers.llm.claude_provider import ClaudeSonnetProvider

        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="sk-ant-test-key",
            openai_api_key="sk-openai-test-key",
        )
        factory = ProviderFactory(settings=settings)
        llm = factory.get_llm()
        assert isinstance(llm, ClaudeSonnetProvider)

    def test_get_embedding_returns_openai_provider(self):
        """cloud mode should return OpenAIEmbeddingProvider."""
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="sk-ant-test-key",
            openai_api_key="sk-openai-test-key",
        )
        factory = ProviderFactory(settings=settings)
        embedding = factory.get_embedding()
        assert isinstance(embedding, OpenAIEmbeddingProvider)

    def test_get_vector_store_default_pgvector(self):
        """cloud mode should default to PgVectorProvider."""
        from app.providers.vector_store.pgvector_provider import PgVectorProvider

        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="sk-ant-test-key",
            openai_api_key="sk-openai-test-key",
            vector_store_provider="pgvector",
        )
        factory = ProviderFactory(settings=settings)
        mock_session_factory = MagicMock()
        vs = factory.get_vector_store(session_factory=mock_session_factory)
        assert isinstance(vs, PgVectorProvider)

    def test_get_vector_store_qdrant_when_configured(self):
        """cloud mode should use QdrantProvider if vector_store_provider is 'qdrant'."""
        from app.providers.vector_store.qdrant_provider import QdrantProvider

        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="sk-ant-test-key",
            openai_api_key="sk-openai-test-key",
            vector_store_provider="qdrant",
        )
        factory = ProviderFactory(settings=settings)
        vs = factory.get_vector_store()
        assert isinstance(vs, QdrantProvider)


# ---------------------------------------------------------------------------
# hybrid mode tests
# ---------------------------------------------------------------------------


class TestHybridMode:
    """Tests for hybrid deployment mode."""

    def test_hybrid_claude_openai_pgvector(self):
        """hybrid mode with claude + openai + pgvector should work."""
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider
        from app.providers.llm.claude_provider import ClaudeSonnetProvider
        from app.providers.vector_store.pgvector_provider import PgVectorProvider

        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="claude",
            embedding_provider="openai",
            vector_store_provider="pgvector",
            anthropic_api_key="sk-ant-test-key",
            openai_api_key="sk-openai-test-key",
        )
        factory = ProviderFactory(settings=settings)

        assert isinstance(factory.get_llm(), ClaudeSonnetProvider)
        assert isinstance(factory.get_embedding(), OpenAIEmbeddingProvider)
        mock_session = MagicMock()
        assert isinstance(factory.get_vector_store(mock_session), PgVectorProvider)

    def test_hybrid_lm_studio_qwen3_qdrant(self):
        """hybrid mode with lm_studio + qwen3 + qdrant should work."""
        from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider
        from app.providers.llm.lm_studio_provider import LMStudioLocalProvider
        from app.providers.vector_store.qdrant_provider import QdrantProvider

        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="lm_studio",
            embedding_provider="qwen3",
            vector_store_provider="qdrant",
        )
        factory = ProviderFactory(settings=settings)

        assert isinstance(factory.get_llm(), LMStudioLocalProvider)
        assert isinstance(factory.get_embedding(), Qwen3LocalEmbeddingProvider)
        assert isinstance(factory.get_vector_store(), QdrantProvider)

    def test_hybrid_mixed_cloud_local(self):
        """hybrid mode can mix cloud LLM with local embedding."""
        from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider
        from app.providers.llm.claude_provider import ClaudeSonnetProvider

        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="claude",
            embedding_provider="qwen3",
            vector_store_provider="pgvector",
            anthropic_api_key="sk-ant-test-key",
        )
        factory = ProviderFactory(settings=settings)

        assert isinstance(factory.get_llm(), ClaudeSonnetProvider)
        assert isinstance(factory.get_embedding(), Qwen3LocalEmbeddingProvider)

    def test_hybrid_rejects_missing_anthropic_key_for_claude(self):
        """hybrid mode with claude LLM should reject missing ANTHROPIC_API_KEY."""
        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="claude",
            embedding_provider="qwen3",
            vector_store_provider="pgvector",
            anthropic_api_key="",
        )
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            ProviderFactory(settings=settings)

    def test_hybrid_rejects_missing_openai_key_for_openai_embedding(self):
        """hybrid mode with openai embedding should reject missing OPENAI_API_KEY."""
        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="lm_studio",
            embedding_provider="openai",
            vector_store_provider="pgvector",
            openai_api_key="",
        )
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            ProviderFactory(settings=settings)

    def test_hybrid_local_providers_dont_need_api_keys(self):
        """hybrid mode with all local providers shouldn't require any API keys."""
        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="lm_studio",
            embedding_provider="qwen3",
            vector_store_provider="pgvector",
            anthropic_api_key="",
            openai_api_key="",
        )
        factory = ProviderFactory(settings=settings)
        assert factory is not None


class TestExpandedProviders:
    """Ollama, llama.cpp, OpenAI chat, Gemini, and local embedding id."""

    def test_on_prem_ollama_uses_11434(self):
        from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

        settings = make_settings(
            deployment_mode="on_prem",
            llm_provider="ollama",
            ollama_base_url="http://host.docker.internal:11434/v1",
        )
        llm = ProviderFactory(settings=settings).get_llm()
        assert isinstance(llm, LMStudioLocalProvider)
        assert llm._base_url == "http://host.docker.internal:11434/v1"

    def test_on_prem_llama_cpp_uses_8080(self):
        settings = make_settings(
            deployment_mode="on_prem",
            llm_provider="llama_cpp",
            llama_cpp_base_url="http://host.docker.internal:8080/v1",
        )
        llm = ProviderFactory(settings=settings).get_llm()
        assert llm._base_url == "http://host.docker.internal:8080/v1"

    def test_on_prem_local_embedding_alias(self):
        from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider

        settings = make_settings(
            deployment_mode="on_prem",
            embedding_provider="local",
        )
        embedding = ProviderFactory(settings=settings).get_embedding()
        assert isinstance(embedding, Qwen3LocalEmbeddingProvider)
        assert embedding.model == "text-embedding-embeddinggemma-300m"

    def test_hybrid_openai_chat(self):
        from app.providers.llm.openai_provider import OpenAILLMProvider

        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="openai",
            embedding_provider="local",
            openai_api_key="sk-openai-test-key",
        )
        assert isinstance(ProviderFactory(settings=settings).get_llm(), OpenAILLMProvider)

    def test_hybrid_gemini_chat_and_embeddings(self):
        from app.providers.embedding.gemini_provider import GeminiEmbeddingProvider
        from app.providers.llm.gemini_provider import GeminiLLMProvider

        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="gemini",
            embedding_provider="gemini",
            gemini_api_key="gem-test-key",
        )
        factory = ProviderFactory(settings=settings)
        assert isinstance(factory.get_llm(), GeminiLLMProvider)
        assert isinstance(factory.get_embedding(), GeminiEmbeddingProvider)

    def test_cloud_openai_does_not_need_anthropic(self):
        from app.providers.llm.openai_provider import OpenAILLMProvider

        settings = make_settings(
            deployment_mode="cloud",
            llm_provider="openai",
            embedding_provider="openai",
            anthropic_api_key="",
            openai_api_key="sk-openai-test-key",
        )
        factory = ProviderFactory(settings=settings)
        assert isinstance(factory.get_llm(), OpenAILLMProvider)

    def test_cloud_gemini_does_not_need_openai_when_embeddings_are_gemini(self):
        from app.providers.llm.gemini_provider import GeminiLLMProvider

        settings = make_settings(
            deployment_mode="cloud",
            llm_provider="gemini",
            embedding_provider="gemini",
            gemini_api_key="gem-test-key",
            openai_api_key="",
            anthropic_api_key="",
        )
        factory = ProviderFactory(settings=settings)
        assert isinstance(factory.get_llm(), GeminiLLMProvider)

    def test_cloud_gemini_rejects_missing_gemini_key(self):
        settings = make_settings(
            deployment_mode="cloud",
            llm_provider="gemini",
            embedding_provider="gemini",
            gemini_api_key="",
            openai_api_key="",
            anthropic_api_key="",
        )
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            ProviderFactory(settings=settings)

    def test_hybrid_rejects_missing_openai_key_for_openai_chat(self):
        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="openai",
            embedding_provider="local",
            openai_api_key="",
        )
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            ProviderFactory(settings=settings)

    def test_cloud_openai_rejects_missing_openai_key_when_selected(self):
        settings = make_settings(
            deployment_mode="cloud",
            llm_provider="openai",
            embedding_provider="openai",
            anthropic_api_key="",
            openai_api_key="",
            gemini_api_key="",
        )
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            ProviderFactory(settings=settings)

    def test_factory_reads_in_process_overlay_url(self):
        from app.config import apply_runtime_overlay
        from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

        apply_runtime_overlay(
            {
                "deployment_mode": "on_prem",
                "llm_provider": "ollama",
                "embedding_provider": "local",
                "ollama_base_url": "http://127.0.0.1:11434/v1",
                "lm_studio_model": "overlay-chat",
                "lm_studio_embedding_model": "text-embedding-embeddinggemma-300m",
            }
        )
        llm = ProviderFactory().get_llm()
        assert isinstance(llm, LMStudioLocalProvider)
        assert llm._base_url == "http://127.0.0.1:11434/v1"

    def test_qdrant_vector_size_is_768(self):
        from app.providers.constants import EMBEDDING_DIMENSIONS

        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="lm_studio",
            embedding_provider="local",
            vector_store_provider="qdrant",
        )
        vs = ProviderFactory(settings=settings).get_vector_store()
        assert vs._vector_size == EMBEDDING_DIMENSIONS
        assert EMBEDDING_DIMENSIONS == 768


class TestErrorHandling:
    """Tests for error cases in ProviderFactory."""

    def test_invalid_deployment_mode_rejected(self):
        """Invalid DEPLOYMENT_MODE should raise ValueError with valid options."""
        # Bypass Pydantic's Literal validation to test factory logic
        settings = make_settings(deployment_mode="on_prem")
        object.__setattr__(settings, "deployment_mode", "invalid_mode")

        with pytest.raises(ValueError, match="Invalid DEPLOYMENT_MODE"):
            ProviderFactory(settings=settings)

    def test_error_message_lists_valid_modes(self):
        """Error message should list all valid deployment modes."""
        settings = make_settings(deployment_mode="on_prem")
        object.__setattr__(settings, "deployment_mode", "bad_value")

        with pytest.raises(ValueError) as exc_info:
            ProviderFactory(settings=settings)

        error_msg = str(exc_info.value)
        for mode in VALID_DEPLOYMENT_MODES:
            assert mode in error_msg

    def test_cloud_mode_error_messages_are_descriptive(self):
        """Cloud mode errors should specify which API key is missing."""
        settings = make_settings(
            deployment_mode="cloud",
            anthropic_api_key="",
            openai_api_key="",
        )
        with pytest.raises(ValueError) as exc_info:
            ProviderFactory(settings=settings)

        # Should mention the first missing key found (anthropic checked first)
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_pgvector_without_session_factory_raises(self):
        """PgVector provider without session_factory should raise ValueError."""
        settings = make_settings(
            deployment_mode="hybrid",
            llm_provider="lm_studio",
            embedding_provider="qwen3",
            vector_store_provider="pgvector",
        )
        factory = ProviderFactory(settings=settings)

        with pytest.raises(ValueError, match="session_factory"):
            factory.get_vector_store(session_factory=None)


# ---------------------------------------------------------------------------
# Constants validation tests
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests verifying factory constants are aligned with configuration."""

    def test_valid_deployment_modes(self):
        """Factory should recognize on_prem, cloud, and hybrid."""
        assert "on_prem" in VALID_DEPLOYMENT_MODES
        assert "cloud" in VALID_DEPLOYMENT_MODES
        assert "hybrid" in VALID_DEPLOYMENT_MODES

    def test_valid_llm_providers(self):
        """Factory should recognize local OpenAI-compat and cloud LLM ids."""
        assert "claude" in VALID_LLM_PROVIDERS
        assert "lm_studio" in VALID_LLM_PROVIDERS
        assert "ollama" in VALID_LLM_PROVIDERS
        assert "llama_cpp" in VALID_LLM_PROVIDERS
        assert "openai" in VALID_LLM_PROVIDERS
        assert "gemini" in VALID_LLM_PROVIDERS

    def test_valid_embedding_providers(self):
        """Factory should recognize openai, local/qwen3 alias, and gemini."""
        assert "openai" in VALID_EMBEDDING_PROVIDERS
        assert "qwen3" in VALID_EMBEDDING_PROVIDERS
        assert "local" in VALID_EMBEDDING_PROVIDERS
        assert "gemini" in VALID_EMBEDDING_PROVIDERS

    def test_valid_vector_store_providers(self):
        """Factory should recognize pgvector and qdrant vector store providers."""
        assert "pgvector" in VALID_VECTOR_STORE_PROVIDERS
        assert "qdrant" in VALID_VECTOR_STORE_PROVIDERS
