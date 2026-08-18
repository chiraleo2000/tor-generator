"""Unit tests for embedding providers (OpenAI and Qwen3 local).

Tests verify correct initialization, interface compliance, batching logic,
and error handling for both providers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import EmbeddingProvider
from app.providers.embedding import OpenAIEmbeddingProvider, Qwen3LocalEmbeddingProvider


# ---------------------------------------------------------------------------
# OpenAI Provider Tests
# ---------------------------------------------------------------------------


class TestOpenAIEmbeddingProviderInit:
    """Test OpenAIEmbeddingProvider initialization."""

    def test_raises_on_empty_api_key(self):
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIEmbeddingProvider(api_key="")

    def test_raises_on_none_api_key(self):
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIEmbeddingProvider(api_key=None)

    def test_default_model(self):
        provider = OpenAIEmbeddingProvider(api_key="sk-test-key")
        assert provider.model == "text-embedding-3-small"

    def test_custom_model(self):
        provider = OpenAIEmbeddingProvider(api_key="sk-test-key", model="text-embedding-3-large")
        assert provider.model == "text-embedding-3-large"

    def test_default_dimensions_768(self):
        provider = OpenAIEmbeddingProvider(api_key="sk-test-key")
        assert provider.dimensions == 768

    def test_implements_embedding_provider_interface(self):
        provider = OpenAIEmbeddingProvider(api_key="sk-test-key")
        assert isinstance(provider, EmbeddingProvider)


class TestOpenAIEmbedQuery:
    """Test OpenAIEmbeddingProvider.embed_query."""

    @pytest.fixture
    def provider(self):
        return OpenAIEmbeddingProvider(api_key="sk-test-key")

    @pytest.fixture
    def mock_embedding_response(self):
        """Create a mock response that mimics OpenAI's embeddings.create output."""
        embedding_obj = MagicMock()
        embedding_obj.embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding_obj.index = 0

        response = MagicMock()
        response.data = [embedding_obj]
        return response

    @pytest.mark.asyncio
    async def test_embed_query_returns_vector(self, provider, mock_embedding_response):
        provider._client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        result = await provider.embed_query("test query")

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        provider._client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="test query",
            dimensions=768,
        )

    @pytest.mark.asyncio
    async def test_embed_query_passes_model(self, mock_embedding_response):
        provider = OpenAIEmbeddingProvider(api_key="sk-test-key", model="text-embedding-3-large")
        provider._client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        await provider.embed_query("test")

        provider._client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-large",
            input="test",
            dimensions=768,
        )


class TestOpenAIEmbedDocuments:
    """Test OpenAIEmbeddingProvider.embed_documents."""

    @pytest.fixture
    def provider(self):
        return OpenAIEmbeddingProvider(api_key="sk-test-key", max_batch_size=3)

    def _make_response(self, embeddings: list[list[float]]):
        """Build a mock response with multiple embedding objects."""
        items = []
        for i, emb in enumerate(embeddings):
            item = MagicMock()
            item.embedding = emb
            item.index = i
            items.append(item)
        response = MagicMock()
        response.data = items
        return response

    @pytest.mark.asyncio
    async def test_embed_documents_empty_list(self, provider):
        result = await provider.embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_documents_single_batch(self, provider):
        expected = [[0.1, 0.2], [0.3, 0.4]]
        provider._client.embeddings.create = AsyncMock(
            return_value=self._make_response(expected)
        )

        result = await provider.embed_documents(["doc1", "doc2"])

        assert result == expected
        provider._client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_documents_multiple_batches(self, provider):
        """When texts exceed max_batch_size, splits into multiple requests."""
        batch1 = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        batch2 = [[0.7, 0.8], [0.9, 1.0]]

        provider._client.embeddings.create = AsyncMock(
            side_effect=[
                self._make_response(batch1),
                self._make_response(batch2),
            ]
        )

        result = await provider.embed_documents(["d1", "d2", "d3", "d4", "d5"])

        assert result == batch1 + batch2
        assert provider._client.embeddings.create.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_documents_preserves_order(self, provider):
        """Embeddings are returned sorted by index regardless of API order."""
        # Simulate API returning out-of-order
        item0 = MagicMock()
        item0.embedding = [0.1]
        item0.index = 0
        item1 = MagicMock()
        item1.embedding = [0.2]
        item1.index = 1

        response = MagicMock()
        response.data = [item1, item0]  # reversed order
        provider._client.embeddings.create = AsyncMock(return_value=response)

        result = await provider.embed_documents(["a", "b"])

        assert result == [[0.1], [0.2]]


# ---------------------------------------------------------------------------
# Qwen3 Local Provider Tests
# ---------------------------------------------------------------------------


class TestQwen3LocalEmbeddingProviderInit:
    """Test Qwen3LocalEmbeddingProvider initialization."""

    def test_raises_on_empty_base_url(self):
        with pytest.raises(ValueError, match="base_url is required"):
            Qwen3LocalEmbeddingProvider(base_url="")

    def test_raises_on_none_base_url(self):
        with pytest.raises(ValueError, match="base_url is required"):
            Qwen3LocalEmbeddingProvider(base_url=None)

    def test_default_model(self):
        provider = Qwen3LocalEmbeddingProvider(base_url="http://localhost:1234/v1")
        assert provider.model == "text-embedding-embeddinggemma-300m"

    def test_custom_model(self):
        provider = Qwen3LocalEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            model="custom-embedding-model",
        )
        assert provider.model == "custom-embedding-model"

    def test_implements_embedding_provider_interface(self):
        provider = Qwen3LocalEmbeddingProvider(base_url="http://localhost:1234/v1")
        assert isinstance(provider, EmbeddingProvider)

    def test_default_api_key_is_not_needed(self):
        """Local servers typically don't need authentication."""
        provider = Qwen3LocalEmbeddingProvider(base_url="http://localhost:1234/v1")
        # Should not raise - api_key defaults to "not-needed"
        assert provider is not None


class TestQwen3LocalEmbedQuery:
    """Test Qwen3LocalEmbeddingProvider.embed_query."""

    @pytest.fixture
    def provider(self):
        return Qwen3LocalEmbeddingProvider(base_url="http://localhost:1234/v1")

    @pytest.fixture
    def mock_embedding_response(self):
        embedding_obj = MagicMock()
        embedding_obj.embedding = [0.5, 0.6, 0.7]
        embedding_obj.index = 0

        response = MagicMock()
        response.data = [embedding_obj]
        return response

    @pytest.mark.asyncio
    async def test_embed_query_returns_vector(self, provider, mock_embedding_response):
        provider._client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        result = await provider.embed_query("ทดสอบข้อความภาษาไทย")

        assert result == [0.5, 0.6, 0.7]
        provider._client.embeddings.create.assert_called_once_with(
            model="text-embedding-embeddinggemma-300m",
            input="ทดสอบข้อความภาษาไทย",
        )


class TestQwen3LocalEmbedDocuments:
    """Test Qwen3LocalEmbeddingProvider.embed_documents."""

    @pytest.fixture
    def provider(self):
        return Qwen3LocalEmbeddingProvider(
            base_url="http://localhost:1234/v1",
            max_batch_size=2,
        )

    def _make_response(self, embeddings: list[list[float]]):
        items = []
        for i, emb in enumerate(embeddings):
            item = MagicMock()
            item.embedding = emb
            item.index = i
            items.append(item)
        response = MagicMock()
        response.data = items
        return response

    @pytest.mark.asyncio
    async def test_embed_documents_empty_list(self, provider):
        result = await provider.embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_documents_single_batch(self, provider):
        expected = [[0.1, 0.2], [0.3, 0.4]]
        provider._client.embeddings.create = AsyncMock(
            return_value=self._make_response(expected)
        )

        result = await provider.embed_documents(["doc1", "doc2"])
        assert result == expected

    @pytest.mark.asyncio
    async def test_embed_documents_multiple_batches(self, provider):
        """When texts exceed max_batch_size, splits into multiple requests."""
        batch1 = [[0.1, 0.2], [0.3, 0.4]]
        batch2 = [[0.5, 0.6]]

        provider._client.embeddings.create = AsyncMock(
            side_effect=[
                self._make_response(batch1),
                self._make_response(batch2),
            ]
        )

        result = await provider.embed_documents(["d1", "d2", "d3"])

        assert result == batch1 + batch2
        assert provider._client.embeddings.create.call_count == 2
