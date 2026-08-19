"""Property-based tests for Provider Factory Mode Resolution (Property 1).

Verifies that the ProviderFactory correctly resolves providers based on
DEPLOYMENT_MODE environment variable:
- For any valid mode (on_prem, cloud, hybrid), returns functioning providers
- For any invalid mode string, rejects with descriptive ValueError
- In hybrid mode, sub-provider combinations resolve to correct types

**Validates: Requirements 2.1, 2.8, 2.9**

# Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Mock qdrant_client if not installed (optional dependency)
if "qdrant_client" not in sys.modules:
    qdrant_mock = MagicMock()
    sys.modules["qdrant_client"] = qdrant_mock
    sys.modules["qdrant_client.models"] = qdrant_mock.models

from app.providers.base import EmbeddingProvider, LLMProvider, VectorStoreProvider
from app.providers.factory import (
    VALID_DEPLOYMENT_MODES,
    VALID_EMBEDDING_PROVIDERS,
    VALID_LLM_PROVIDERS,
    VALID_VECTOR_STORE_PROVIDERS,
    ProviderFactory,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

valid_mode_strategy = st.sampled_from(["on_prem", "cloud", "hybrid"])

invalid_mode_strategy = st.text(min_size=1, max_size=50).filter(
    lambda x: x not in VALID_DEPLOYMENT_MODES
)

valid_llm_provider_strategy = st.sampled_from(
    ["claude", "lm_studio", "ollama", "llama_cpp", "openai", "gemini"]
)
valid_embedding_provider_strategy = st.sampled_from(["openai", "qwen3", "local", "gemini"])
valid_vector_store_provider_strategy = st.sampled_from(["pgvector", "qdrant"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(
    deployment_mode: str = "on_prem",
    llm_provider: str = "lm_studio",
    embedding_provider: str = "qwen3",
    vector_store_provider: str = "pgvector",
    anthropic_api_key: str = "fake-anthropic-key-for-testing",
    openai_api_key: str = "fake-openai-key-for-testing",
    gemini_api_key: str = "fake-gemini-key-for-testing",
    lm_studio_base_url: str = "http://localhost:1234/v1",
    lm_studio_model: str = "test-model",
    lm_studio_embedding_model: str = "text-embedding-embeddinggemma-300m",
    lm_studio_timeout: float = 180.0,
    ollama_base_url: str = "http://host.docker.internal:11434/v1",
    llama_cpp_base_url: str = "http://host.docker.internal:8080/v1",
    openai_chat_model: str = "gpt-4o-mini",
    gemini_model: str = "gemini-2.0-flash",
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
):
    """Create a mock Settings object with specified values."""
    mock_settings = MagicMock()
    mock_settings.deployment_mode = deployment_mode
    mock_settings.llm_provider = llm_provider
    mock_settings.embedding_provider = embedding_provider
    mock_settings.vector_store_provider = vector_store_provider
    mock_settings.anthropic_api_key = anthropic_api_key
    mock_settings.openai_api_key = openai_api_key
    mock_settings.gemini_api_key = gemini_api_key
    mock_settings.lm_studio_base_url = lm_studio_base_url
    mock_settings.lm_studio_model = lm_studio_model
    mock_settings.lm_studio_embedding_model = lm_studio_embedding_model
    mock_settings.lm_studio_timeout = lm_studio_timeout
    mock_settings.ollama_base_url = ollama_base_url
    mock_settings.llama_cpp_base_url = llama_cpp_base_url
    mock_settings.local_embedding_server = "lm_studio"
    mock_settings.local_embedding_base_url = ""
    mock_settings.openai_embedding_model = "text-embedding-3-small"
    mock_settings.azure_foundry_api_key = ""
    mock_settings.azure_foundry_endpoint = ""
    mock_settings.azure_foundry_deployment = ""
    mock_settings.azure_foundry_embedding_deployment = ""
    mock_settings.azure_foundry_api_version = "2024-10-21"
    mock_settings.openai_compatible_base_url = ""
    mock_settings.openai_compatible_api_key = ""
    mock_settings.openai_compatible_model = ""
    mock_settings.openai_compatible_embedding_model = "text-embedding-3-small"
    mock_settings.bedrock_region = "ap-southeast-1"
    mock_settings.bedrock_model_id = ""
    mock_settings.bedrock_embedding_model_id = "amazon.titan-embed-text-v2:0"
    mock_settings.aws_access_key_id = ""
    mock_settings.aws_secret_access_key = ""
    mock_settings.openai_chat_model = openai_chat_model
    mock_settings.gemini_model = gemini_model
    mock_settings.gemini_embedding_model = "text-embedding-004"
    mock_settings.qdrant_host = qdrant_host
    mock_settings.qdrant_port = qdrant_port
    return mock_settings


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestProviderFactoryModeResolution:
    """Property 1: Provider Factory Mode Resolution.

    For any valid DEPLOYMENT_MODE value (on_prem, cloud, hybrid), the Provider
    Factory SHALL return a functioning LLM provider, embedding provider, and
    vector store provider without code modification — and for any invalid or
    missing value, it SHALL reject initialization with a descriptive error.
    """

    @given(mode=valid_mode_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_valid_mode_creates_factory_without_error(self, mode: str):
        """For any valid DEPLOYMENT_MODE, factory initializes without error.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(deployment_mode=mode)
        # Factory initialization should not raise for valid modes
        factory = ProviderFactory(settings=settings_obj)
        assert factory is not None

    @given(mode=invalid_mode_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_invalid_mode_rejects_with_descriptive_error(self, mode: str):
        """For any invalid DEPLOYMENT_MODE string, initialization raises ValueError.

        The error message must indicate the accepted values.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(deployment_mode=mode)

        with pytest.raises(ValueError) as exc_info:
            ProviderFactory(settings=settings_obj)

        error_msg = str(exc_info.value)
        # Error message should mention the invalid value
        assert mode in error_msg or "Invalid DEPLOYMENT_MODE" in error_msg
        # Error message should indicate accepted values
        assert "on_prem" in error_msg or "cloud" in error_msg or "hybrid" in error_msg

    @given(mode=valid_mode_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_valid_mode_returns_llm_provider_of_correct_type(self, mode: str):
        """For any valid mode, get_llm() returns an instance of LLMProvider.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(deployment_mode=mode)
        factory = ProviderFactory(settings=settings_obj)
        llm = factory.get_llm()
        assert isinstance(llm, LLMProvider)

    @given(mode=valid_mode_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_valid_mode_returns_embedding_provider_of_correct_type(self, mode: str):
        """For any valid mode, get_embedding() returns an instance of EmbeddingProvider.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(deployment_mode=mode)
        factory = ProviderFactory(settings=settings_obj)
        embedding = factory.get_embedding()
        assert isinstance(embedding, EmbeddingProvider)

    @given(mode=valid_mode_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_valid_mode_returns_vector_store_provider_of_correct_type(self, mode: str):
        """For any valid mode, get_vector_store() returns an instance of VectorStoreProvider.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(deployment_mode=mode)
        factory = ProviderFactory(settings=settings_obj)

        # pgvector requires a session_factory; qdrant does not
        mock_session_factory = MagicMock()
        vs = factory.get_vector_store(session_factory=mock_session_factory)
        assert isinstance(vs, VectorStoreProvider)

    @given(
        llm_choice=valid_llm_provider_strategy,
        emb_choice=valid_embedding_provider_strategy,
        vs_choice=valid_vector_store_provider_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_hybrid_mode_resolves_any_valid_sub_provider_combination(
        self, llm_choice: str, emb_choice: str, vs_choice: str
    ):
        """In hybrid mode, any combination of valid sub-providers resolves correctly.

        For any valid LLM_PROVIDER, EMBEDDING_PROVIDER, and VECTOR_STORE_PROVIDER
        values, the factory returns providers of the correct abstract types.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(
            deployment_mode="hybrid",
            llm_provider=llm_choice,
            embedding_provider=emb_choice,
            vector_store_provider=vs_choice,
        )
        factory = ProviderFactory(settings=settings_obj)

        # LLM provider resolves
        llm = factory.get_llm()
        assert isinstance(llm, LLMProvider)

        # Embedding provider resolves
        embedding = factory.get_embedding()
        assert isinstance(embedding, EmbeddingProvider)

        # Vector store provider resolves
        mock_session_factory = MagicMock()
        vs = factory.get_vector_store(session_factory=mock_session_factory)
        assert isinstance(vs, VectorStoreProvider)

    @given(
        llm_choice=valid_llm_provider_strategy,
        emb_choice=valid_embedding_provider_strategy,
        vs_choice=valid_vector_store_provider_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_hybrid_mode_llm_type_matches_selection(
        self, llm_choice: str, emb_choice: str, vs_choice: str
    ):
        """In hybrid mode, the LLM provider type matches the selected sub-provider.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        from app.providers.llm.claude_provider import ClaudeSonnetProvider
        from app.providers.llm.gemini_provider import GeminiLLMProvider
        from app.providers.llm.lm_studio_provider import LMStudioLocalProvider
        from app.providers.llm.openai_provider import OpenAILLMProvider

        settings_obj = _make_settings(
            deployment_mode="hybrid",
            llm_provider=llm_choice,
            embedding_provider=emb_choice,
            vector_store_provider=vs_choice,
        )
        factory = ProviderFactory(settings=settings_obj)
        llm = factory.get_llm()

        if llm_choice == "claude":
            assert isinstance(llm, ClaudeSonnetProvider)
        elif llm_choice == "openai":
            assert isinstance(llm, OpenAILLMProvider)
        elif llm_choice == "gemini":
            assert isinstance(llm, GeminiLLMProvider)
        else:
            assert isinstance(llm, LMStudioLocalProvider)

    @given(
        llm_choice=valid_llm_provider_strategy,
        emb_choice=valid_embedding_provider_strategy,
        vs_choice=valid_vector_store_provider_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_hybrid_mode_embedding_type_matches_selection(
        self, llm_choice: str, emb_choice: str, vs_choice: str
    ):
        """In hybrid mode, the embedding provider type matches the selected sub-provider.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        from app.providers.embedding.gemini_provider import GeminiEmbeddingProvider
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider
        from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider

        settings_obj = _make_settings(
            deployment_mode="hybrid",
            llm_provider=llm_choice,
            embedding_provider=emb_choice,
            vector_store_provider=vs_choice,
        )
        factory = ProviderFactory(settings=settings_obj)
        embedding = factory.get_embedding()

        if emb_choice == "openai":
            assert isinstance(embedding, OpenAIEmbeddingProvider)
        elif emb_choice == "gemini":
            assert isinstance(embedding, GeminiEmbeddingProvider)
        else:
            assert isinstance(embedding, Qwen3LocalEmbeddingProvider)

    @given(
        llm_choice=valid_llm_provider_strategy,
        emb_choice=valid_embedding_provider_strategy,
        vs_choice=valid_vector_store_provider_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_hybrid_mode_vector_store_type_matches_selection(
        self, llm_choice: str, emb_choice: str, vs_choice: str
    ):
        """In hybrid mode, the vector store provider type matches the selected sub-provider.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        from app.providers.vector_store.pgvector_provider import PgVectorProvider
        from app.providers.vector_store.qdrant_provider import QdrantProvider

        settings_obj = _make_settings(
            deployment_mode="hybrid",
            llm_provider=llm_choice,
            embedding_provider=emb_choice,
            vector_store_provider=vs_choice,
        )
        factory = ProviderFactory(settings=settings_obj)
        mock_session_factory = MagicMock()
        vs = factory.get_vector_store(session_factory=mock_session_factory)

        if vs_choice == "pgvector":
            assert isinstance(vs, PgVectorProvider)
        else:
            assert isinstance(vs, QdrantProvider)

    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_on_prem_mode_never_requires_cloud_api_keys(self):
        """On-prem mode works without any cloud API keys.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(
            deployment_mode="on_prem",
            anthropic_api_key="",
            openai_api_key="",
        )
        factory = ProviderFactory(settings=settings_obj)

        # LLM should work without cloud keys
        llm = factory.get_llm()
        assert isinstance(llm, LLMProvider)

        # Embedding should work without cloud keys
        embedding = factory.get_embedding()
        assert isinstance(embedding, EmbeddingProvider)

    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_cloud_mode_without_anthropic_key_raises_at_init(self):
        """Cloud mode without ANTHROPIC_API_KEY raises ValueError at initialization.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(
            deployment_mode="cloud",
            llm_provider="claude",
            embedding_provider="openai",
            anthropic_api_key="",
        )

        with pytest.raises(ValueError) as exc_info:
            ProviderFactory(settings=settings_obj)

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_cloud_mode_without_openai_key_raises_at_init(self):
        """Cloud mode without OPENAI_API_KEY raises ValueError at initialization.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(
            deployment_mode="cloud",
            llm_provider="claude",
            embedding_provider="openai",
            openai_api_key="",
        )

        with pytest.raises(ValueError) as exc_info:
            ProviderFactory(settings=settings_obj)

        assert "OPENAI_API_KEY" in str(exc_info.value)

    # Feature: tor-drafting-review-app, Property 1: Provider Factory Mode Resolution
    def test_pgvector_without_session_factory_raises(self):
        """PgVector provider without session_factory raises descriptive ValueError.

        **Validates: Requirements 2.1, 2.8, 2.9**
        """
        settings_obj = _make_settings(deployment_mode="on_prem")
        factory = ProviderFactory(settings=settings_obj)

        with pytest.raises(ValueError) as exc_info:
            factory.get_vector_store(session_factory=None)

        assert "session_factory" in str(exc_info.value)
