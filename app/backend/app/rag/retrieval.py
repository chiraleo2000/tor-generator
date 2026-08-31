"""RAG retrieval module — embed query, similarity search, metadata filtering.

Implements the retrieval flow:
1. User query → embed with configured embedding provider
2. Cosine similarity search (top-K, default K=5)
3. Metadata filtering (document_type, legal_reference, section_relevance)
4. Return ranked chunks with source attribution

When fewer results than K are available, all matching chunks are returned
without error (Requirement 3.9).

Requirements: 3.4, 3.5, 3.9
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.providers.base import EmbeddingProvider, SearchResult, VectorStoreProvider

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5


def coerce_page_number(raw: Any) -> int | None:
    """Normalize MCP/vector metadata page numbers to int (Thai-safe, no bool)."""
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@dataclass
class RetrievalFilter:
    """Metadata filter criteria for RAG retrieval.

    All fields are optional. Only non-None fields are applied as filters.
    Multiple fields are combined with AND logic.

    Attributes:
        document_type: Filter by knowledge base category
            (e.g., "law", "regulation", "guideline", "manual", "example_tor").
        legal_reference: Filter by specific legal reference
            (e.g., "พ.ร.บ. 2560", "กฎกระทรวง").
        section_relevance: Filter by TOR section relevance
            (e.g., "s1", "s4", "budget", "qualifications").
    """

    document_type: str | None = None
    legal_reference: str | None = None
    section_relevance: str | None = None

    def to_filter_dict(self) -> dict | None:
        """Convert to a filter dictionary for the vector store provider.

        Returns:
            A dict with active filter criteria, or None if no filters are set.
        """
        filters: dict = {}

        if self.document_type is not None:
            filters["document_type"] = self.document_type
        if self.legal_reference is not None:
            filters["legal_reference"] = self.legal_reference
        if self.section_relevance is not None:
            filters["section_relevance"] = self.section_relevance

        return filters if filters else None


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the knowledge base with source attribution.

    Attributes:
        id: Unique chunk identifier.
        text: The chunk text content.
        score: Cosine similarity score (0.0–1.0, higher is more relevant).
        document_type: The type/category of the source document.
        legal_reference: Legal reference associated with this chunk (if any).
        section_relevance: TOR section this chunk is relevant to (if any).
        source_document: Name or ID of the source document.
        section_label: Section label within the source document.
        page_number: Page number in the source document.
        metadata: Full metadata dict from vector store.
    """

    id: str
    text: str
    score: float
    document_type: str | None = None
    legal_reference: str | None = None
    section_relevance: str | None = None
    source_document: str | None = None
    section_label: str | None = None
    page_number: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of a RAG retrieval operation.

    Attributes:
        chunks: List of retrieved chunks, ordered by descending similarity score.
        query: The original query text.
        top_k: The requested number of results.
        actual_count: The actual number of results returned (may be less than top_k).
        filter_applied: The metadata filter that was applied (if any).
    """

    chunks: list[RetrievedChunk]
    query: str
    top_k: int
    actual_count: int
    filter_applied: RetrievalFilter | None = None


class RAGRetriever:
    """Retrieves relevant knowledge base chunks for a given query.

    Uses the configured embedding provider to embed the query and the
    vector store provider to perform cosine similarity search with optional
    metadata filtering.

    Args:
        embedding_provider: Provider for generating query embeddings.
        vector_store_provider: Provider for vector similarity search.
        default_top_k: Default number of results to retrieve (default 5).
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store_provider: VectorStoreProvider,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store_provider = vector_store_provider
        self._default_top_k = default_top_k

    @property
    def default_top_k(self) -> int:
        """The default number of results to retrieve."""
        return self._default_top_k

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter: RetrievalFilter | None = None,
    ) -> RetrievalResult:
        """Retrieve the most relevant knowledge base chunks for a query.

        Embeds the query text, performs cosine similarity search in the vector store,
        applies any metadata filters, and returns ranked results.

        When fewer results than top_k are available, returns all matching chunks
        without error (Requirement 3.9).

        Args:
            query: The search query text (typically a TOR section description or question).
            top_k: Maximum number of results to return. Uses default_top_k if not specified.
            filter: Optional metadata filter to narrow the search scope.

        Returns:
            RetrievalResult with ranked chunks and metadata about the retrieval.

        Raises:
            ValueError: If query is empty or top_k is less than 1.
        """
        if not query or not query.strip():
            raise ValueError("Query text cannot be empty.")

        effective_top_k = top_k if top_k is not None else self._default_top_k

        if effective_top_k < 1:
            raise ValueError(f"top_k must be at least 1, got {effective_top_k}.")

        # Step 1: Embed the query
        logger.debug("Embedding query: %s...", query[:50])
        query_vector = await self._embedding_provider.embed_query(query)

        # Step 2: Build filter dict from RetrievalFilter
        filter_dict = filter.to_filter_dict() if filter else None

        # Step 3: Cosine similarity search in vector store
        logger.debug(
            "Searching vector store with top_k=%d, filter=%s",
            effective_top_k,
            filter_dict,
        )
        search_results: list[SearchResult] = await self._vector_store_provider.search(
            vector=query_vector,
            top_k=effective_top_k,
            filter=filter_dict,
        )

        # Step 4: Convert search results to RetrievedChunk objects
        # The vector store may return fewer results than top_k — this is expected (Req 3.9)
        chunks = [self._to_retrieved_chunk(result) for result in search_results]

        actual_count = len(chunks)
        if actual_count < effective_top_k:
            logger.info(
                "Retrieval returned %d results (fewer than requested top_k=%d). "
                "This is normal when the knowledge base has limited matching content.",
                actual_count,
                effective_top_k,
            )

        return RetrievalResult(
            chunks=chunks,
            query=query,
            top_k=effective_top_k,
            actual_count=actual_count,
            filter_applied=filter,
        )

    def _to_retrieved_chunk(self, result: SearchResult) -> RetrievedChunk:
        """Convert a SearchResult from the vector store into a RetrievedChunk.

        Extracts known metadata fields and includes the full metadata dict.

        Args:
            result: A SearchResult from the vector store provider.

        Returns:
            A RetrievedChunk with extracted metadata fields.
        """
        metadata = result.metadata or {}

        return RetrievedChunk(
            id=result.id,
            text=result.text,
            score=result.score,
            document_type=metadata.get("document_type"),
            legal_reference=metadata.get("legal_reference"),
            section_relevance=metadata.get("section_relevance"),
            source_document=metadata.get("source_document"),
            section_label=metadata.get("section_label"),
            page_number=metadata.get("page_number"),
            metadata=metadata,
        )
