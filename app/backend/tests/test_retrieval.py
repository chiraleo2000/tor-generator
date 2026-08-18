"""Unit tests for the RAG retrieval module.

Tests cover:
- Query embedding and vector search integration
- Metadata filtering (document_type, legal_reference, section_relevance)
- Graceful handling of fewer results than K (Requirement 3.9)
- Input validation (empty query, invalid top_k)
- RetrievalFilter to_filter_dict conversion
- RetrievedChunk metadata extraction from SearchResult
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.providers.base import EmbeddingProvider, SearchResult, VectorStoreProvider
from app.rag.retrieval import (
    DEFAULT_TOP_K,
    RAGRetriever,
    RetrievalFilter,
    RetrievalResult,
    RetrievedChunk,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_embedding_provider() -> AsyncMock:
    """Create a mock embedding provider that returns a fixed vector."""
    provider = AsyncMock(spec=EmbeddingProvider)
    provider.embed_query.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    return provider


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Create a mock vector store provider."""
    provider = AsyncMock(spec=VectorStoreProvider)
    provider.search.return_value = []
    return provider


@pytest.fixture
def retriever(mock_embedding_provider: AsyncMock, mock_vector_store: AsyncMock) -> RAGRetriever:
    """Create a RAGRetriever with mocked providers."""
    return RAGRetriever(
        embedding_provider=mock_embedding_provider,
        vector_store_provider=mock_vector_store,
    )


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Sample search results simulating vector store output."""
    return [
        SearchResult(
            id="chunk-001",
            text="มาตรา 56 การจัดซื้อจัดจ้างพัสดุ",
            score=0.95,
            metadata={
                "document_type": "law",
                "legal_reference": "พ.ร.บ. 2560",
                "section_relevance": "s4",
                "source_document": "พระราชบัญญัติการจัดซื้อจัดจ้าง",
                "section_label": "หมวด 6",
                "page_number": 12,
            },
        ),
        SearchResult(
            id="chunk-002",
            text="ข้อ 22 ให้หน่วยงานของรัฐจัดทำแผนการจัดซื้อจัดจ้าง",
            score=0.88,
            metadata={
                "document_type": "regulation",
                "legal_reference": "ระเบียบกระทรวงการคลัง 2560",
                "section_relevance": "s4",
                "source_document": "ระเบียบกระทรวงการคลัง",
                "section_label": "ส่วนที่ 3",
                "page_number": 5,
            },
        ),
        SearchResult(
            id="chunk-003",
            text="การกำหนดขอบเขตของงานควรประกอบด้วย",
            score=0.82,
            metadata={
                "document_type": "guideline",
                "section_relevance": "s4",
                "source_document": "คู่มือปฏิบัติงาน",
            },
        ),
    ]


# ---------------------------------------------------------------------------
# RetrievalFilter Tests
# ---------------------------------------------------------------------------


class TestRetrievalFilter:
    """Tests for RetrievalFilter data class."""

    def test_empty_filter_returns_none(self):
        """An empty filter produces None (no filtering)."""
        f = RetrievalFilter()
        assert f.to_filter_dict() is None

    def test_single_document_type_filter(self):
        """A filter with only document_type returns single-key dict."""
        f = RetrievalFilter(document_type="law")
        assert f.to_filter_dict() == {"document_type": "law"}

    def test_single_legal_reference_filter(self):
        """A filter with only legal_reference returns single-key dict."""
        f = RetrievalFilter(legal_reference="พ.ร.บ. 2560")
        assert f.to_filter_dict() == {"legal_reference": "พ.ร.บ. 2560"}

    def test_single_section_relevance_filter(self):
        """A filter with only section_relevance returns single-key dict."""
        f = RetrievalFilter(section_relevance="s4")
        assert f.to_filter_dict() == {"section_relevance": "s4"}

    def test_multiple_filters_combined(self):
        """Multiple filter fields are combined into a single dict."""
        f = RetrievalFilter(
            document_type="regulation",
            legal_reference="ระเบียบกระทรวงการคลัง 2560",
            section_relevance="s6",
        )
        result = f.to_filter_dict()
        assert result == {
            "document_type": "regulation",
            "legal_reference": "ระเบียบกระทรวงการคลัง 2560",
            "section_relevance": "s6",
        }

    def test_partial_filters(self):
        """Only non-None fields appear in the filter dict."""
        f = RetrievalFilter(document_type="law", section_relevance="s1")
        result = f.to_filter_dict()
        assert result == {"document_type": "law", "section_relevance": "s1"}
        assert "legal_reference" not in result


# ---------------------------------------------------------------------------
# RAGRetriever Tests — Query Embedding
# ---------------------------------------------------------------------------


class TestRAGRetrieverEmbedding:
    """Tests for query embedding behavior."""

    @pytest.mark.asyncio
    async def test_embeds_query_text(
        self, retriever: RAGRetriever, mock_embedding_provider: AsyncMock, mock_vector_store: AsyncMock
    ):
        """The retriever embeds the query using the embedding provider."""
        await retriever.retrieve("ขอบเขตของงาน")
        mock_embedding_provider.embed_query.assert_called_once_with("ขอบเขตของงาน")

    @pytest.mark.asyncio
    async def test_passes_embedding_to_vector_store(
        self, retriever: RAGRetriever, mock_embedding_provider: AsyncMock, mock_vector_store: AsyncMock
    ):
        """The embedded vector is passed to the vector store search."""
        mock_embedding_provider.embed_query.return_value = [1.0, 2.0, 3.0]
        await retriever.retrieve("test query")
        mock_vector_store.search.assert_called_once_with(
            vector=[1.0, 2.0, 3.0],
            top_k=DEFAULT_TOP_K,
            filter=None,
        )


# ---------------------------------------------------------------------------
# RAGRetriever Tests — Search and Results
# ---------------------------------------------------------------------------


class TestRAGRetrieverSearch:
    """Tests for search behavior and result handling."""

    @pytest.mark.asyncio
    async def test_returns_results_from_vector_store(
        self,
        retriever: RAGRetriever,
        mock_vector_store: AsyncMock,
        sample_search_results: list[SearchResult],
    ):
        """Results from vector store are converted to RetrievedChunks."""
        mock_vector_store.search.return_value = sample_search_results
        result = await retriever.retrieve("ขอบเขตของงาน")

        assert isinstance(result, RetrievalResult)
        assert len(result.chunks) == 3
        assert result.actual_count == 3
        assert result.top_k == DEFAULT_TOP_K
        assert result.query == "ขอบเขตของงาน"

    @pytest.mark.asyncio
    async def test_chunks_ordered_by_score(
        self,
        retriever: RAGRetriever,
        mock_vector_store: AsyncMock,
        sample_search_results: list[SearchResult],
    ):
        """Results maintain the order from the vector store (descending score)."""
        mock_vector_store.search.return_value = sample_search_results
        result = await retriever.retrieve("test")

        scores = [chunk.score for chunk in result.chunks]
        assert scores == [0.95, 0.88, 0.82]

    @pytest.mark.asyncio
    async def test_custom_top_k(
        self, retriever: RAGRetriever, mock_vector_store: AsyncMock
    ):
        """Custom top_k is passed to vector store search."""
        await retriever.retrieve("test", top_k=10)
        mock_vector_store.search.assert_called_once_with(
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            top_k=10,
            filter=None,
        )

    @pytest.mark.asyncio
    async def test_default_top_k_configurable(
        self, mock_embedding_provider: AsyncMock, mock_vector_store: AsyncMock
    ):
        """The default_top_k can be configured at construction."""
        retriever = RAGRetriever(
            embedding_provider=mock_embedding_provider,
            vector_store_provider=mock_vector_store,
            default_top_k=10,
        )
        assert retriever.default_top_k == 10
        await retriever.retrieve("test")
        mock_vector_store.search.assert_called_once_with(
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            top_k=10,
            filter=None,
        )


# ---------------------------------------------------------------------------
# RAGRetriever Tests — Metadata Filtering
# ---------------------------------------------------------------------------


class TestRAGRetrieverFiltering:
    """Tests for metadata filtering behavior."""

    @pytest.mark.asyncio
    async def test_filter_passed_to_vector_store(
        self, retriever: RAGRetriever, mock_vector_store: AsyncMock
    ):
        """RetrievalFilter is converted and passed to vector store search."""
        filter = RetrievalFilter(document_type="law")
        await retriever.retrieve("test", filter=filter)
        mock_vector_store.search.assert_called_once_with(
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            top_k=DEFAULT_TOP_K,
            filter={"document_type": "law"},
        )

    @pytest.mark.asyncio
    async def test_combined_filter_passed(
        self, retriever: RAGRetriever, mock_vector_store: AsyncMock
    ):
        """Multiple filter criteria are combined and passed."""
        filter = RetrievalFilter(
            document_type="regulation",
            legal_reference="พ.ร.บ. 2560",
            section_relevance="s4",
        )
        await retriever.retrieve("test", filter=filter)
        mock_vector_store.search.assert_called_once_with(
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            top_k=DEFAULT_TOP_K,
            filter={
                "document_type": "regulation",
                "legal_reference": "พ.ร.บ. 2560",
                "section_relevance": "s4",
            },
        )

    @pytest.mark.asyncio
    async def test_empty_filter_passes_none(
        self, retriever: RAGRetriever, mock_vector_store: AsyncMock
    ):
        """An empty RetrievalFilter (all None) passes filter=None to vector store."""
        filter = RetrievalFilter()
        await retriever.retrieve("test", filter=filter)
        mock_vector_store.search.assert_called_once_with(
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            top_k=DEFAULT_TOP_K,
            filter=None,
        )

    @pytest.mark.asyncio
    async def test_filter_stored_in_result(
        self, retriever: RAGRetriever, mock_vector_store: AsyncMock
    ):
        """The applied filter is recorded in the RetrievalResult."""
        filter = RetrievalFilter(document_type="guideline")
        result = await retriever.retrieve("test", filter=filter)
        assert result.filter_applied is filter
        assert result.filter_applied.document_type == "guideline"


# ---------------------------------------------------------------------------
# RAGRetriever Tests — Graceful Handling of Fewer Results (Req 3.9)
# ---------------------------------------------------------------------------


class TestRAGRetrieverFewerResults:
    """Tests for graceful handling when fewer results than K are available."""

    @pytest.mark.asyncio
    async def test_fewer_results_than_top_k(
        self, retriever: RAGRetriever, mock_vector_store: AsyncMock
    ):
        """Returns all available results without error when fewer than top_k."""
        mock_vector_store.search.return_value = [
            SearchResult(id="chunk-1", text="only one result", score=0.7, metadata={}),
        ]
        result = await retriever.retrieve("test", top_k=5)

        assert result.actual_count == 1
        assert result.top_k == 5
        assert len(result.chunks) == 1
        assert result.chunks[0].text == "only one result"

    @pytest.mark.asyncio
    async def test_zero_results(
        self, retriever: RAGRetriever, mock_vector_store: AsyncMock
    ):
        """Returns empty list without error when no results match."""
        mock_vector_store.search.return_value = []
        result = await retriever.retrieve("obscure query with no matches", top_k=5)

        assert result.actual_count == 0
        assert result.top_k == 5
        assert result.chunks == []

    @pytest.mark.asyncio
    async def test_exact_top_k_results(
        self,
        retriever: RAGRetriever,
        mock_vector_store: AsyncMock,
        sample_search_results: list[SearchResult],
    ):
        """Returns exactly top_k results when that many are available."""
        mock_vector_store.search.return_value = sample_search_results[:3]
        result = await retriever.retrieve("test", top_k=3)

        assert result.actual_count == 3
        assert result.top_k == 3


# ---------------------------------------------------------------------------
# RAGRetriever Tests — Input Validation
# ---------------------------------------------------------------------------


class TestRAGRetrieverValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_empty_query_raises_value_error(self, retriever: RAGRetriever):
        """An empty query string raises ValueError."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await retriever.retrieve("")

    @pytest.mark.asyncio
    async def test_whitespace_only_query_raises_value_error(self, retriever: RAGRetriever):
        """A whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await retriever.retrieve("   ")

    @pytest.mark.asyncio
    async def test_top_k_zero_raises_value_error(self, retriever: RAGRetriever):
        """top_k=0 raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be at least 1"):
            await retriever.retrieve("test", top_k=0)

    @pytest.mark.asyncio
    async def test_negative_top_k_raises_value_error(self, retriever: RAGRetriever):
        """Negative top_k raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be at least 1"):
            await retriever.retrieve("test", top_k=-1)


# ---------------------------------------------------------------------------
# RAGRetriever Tests — Metadata Extraction
# ---------------------------------------------------------------------------


class TestRetrievedChunkMetadata:
    """Tests for metadata extraction into RetrievedChunk fields."""

    @pytest.mark.asyncio
    async def test_full_metadata_extracted(
        self,
        retriever: RAGRetriever,
        mock_vector_store: AsyncMock,
    ):
        """All metadata fields are correctly extracted into RetrievedChunk."""
        mock_vector_store.search.return_value = [
            SearchResult(
                id="chunk-full",
                text="full metadata chunk",
                score=0.92,
                metadata={
                    "document_type": "law",
                    "legal_reference": "พ.ร.บ. 2560",
                    "section_relevance": "s3",
                    "source_document": "พระราชบัญญัติการจัดซื้อจัดจ้าง",
                    "section_label": "มาตรา 56",
                    "page_number": 15,
                },
            )
        ]
        result = await retriever.retrieve("test")
        chunk = result.chunks[0]

        assert chunk.id == "chunk-full"
        assert chunk.text == "full metadata chunk"
        assert chunk.score == 0.92
        assert chunk.document_type == "law"
        assert chunk.legal_reference == "พ.ร.บ. 2560"
        assert chunk.section_relevance == "s3"
        assert chunk.source_document == "พระราชบัญญัติการจัดซื้อจัดจ้าง"
        assert chunk.section_label == "มาตรา 56"
        assert chunk.page_number == 15

    @pytest.mark.asyncio
    async def test_partial_metadata_handled(
        self,
        retriever: RAGRetriever,
        mock_vector_store: AsyncMock,
    ):
        """Missing metadata fields default to None."""
        mock_vector_store.search.return_value = [
            SearchResult(
                id="chunk-partial",
                text="partial metadata",
                score=0.75,
                metadata={"document_type": "guideline"},
            )
        ]
        result = await retriever.retrieve("test")
        chunk = result.chunks[0]

        assert chunk.document_type == "guideline"
        assert chunk.legal_reference is None
        assert chunk.section_relevance is None
        assert chunk.source_document is None
        assert chunk.section_label is None
        assert chunk.page_number is None

    @pytest.mark.asyncio
    async def test_empty_metadata_handled(
        self,
        retriever: RAGRetriever,
        mock_vector_store: AsyncMock,
    ):
        """Empty metadata dict results in all None fields."""
        mock_vector_store.search.return_value = [
            SearchResult(
                id="chunk-empty",
                text="no metadata",
                score=0.60,
                metadata={},
            )
        ]
        result = await retriever.retrieve("test")
        chunk = result.chunks[0]

        assert chunk.document_type is None
        assert chunk.legal_reference is None
        assert chunk.section_relevance is None
        assert chunk.metadata == {}

    @pytest.mark.asyncio
    async def test_none_metadata_handled(
        self,
        retriever: RAGRetriever,
        mock_vector_store: AsyncMock,
    ):
        """SearchResult with metadata=None (from default_factory) is handled."""
        # SearchResult has default_factory=dict, but test defensive handling
        result_item = SearchResult(id="chunk-none", text="null meta", score=0.5, metadata={})
        mock_vector_store.search.return_value = [result_item]
        result = await retriever.retrieve("test")
        chunk = result.chunks[0]

        assert chunk.document_type is None
        assert chunk.metadata == {}
