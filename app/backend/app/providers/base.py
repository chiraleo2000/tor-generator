"""Abstract base interfaces for LLM, Embedding, and VectorStore providers.

This module defines the Strategy Pattern abstractions that allow the application
to switch between on-premise, cloud, and hybrid deployment modes without code changes.
The ProviderFactory instantiates concrete implementations based on environment variables.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class LLMResponse:
    """Structured response from an LLM provider invocation."""

    content: str
    model: str
    usage: dict  # {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    finish_reason: str = "stop"


@dataclass
class SearchResult:
    """A single result from a vector similarity search."""

    id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract interface for language model providers.

    Concrete implementations include ClaudeSonnetProvider (cloud)
    and LMStudioLocalProvider (on-prem).
    """

    @abstractmethod
    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send messages to the LLM and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            tools: Optional list of tool definitions for function calling.
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated content and usage metadata.

        Raises:
            TimeoutError: If the provider does not respond within the configured timeout.
            ConnectionError: If the provider endpoint is unreachable.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream tokens from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Yields:
            String tokens as they are generated.

        Raises:
            TimeoutError: If the provider does not respond within the configured timeout.
            ConnectionError: If the provider endpoint is unreachable.
        """
        ...


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers.

    Concrete implementations include OpenAIEmbeddingProvider (cloud)
    and Qwen3LocalEmbeddingProvider (on-prem).
    """

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text.

        Args:
            text: The query string to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple document texts.

        Args:
            texts: A list of document strings to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        ...


class VectorStoreProvider(ABC):
    """Abstract interface for vector store providers.

    Concrete implementations include PgVectorProvider (default)
    and QdrantProvider (optional).
    """

    @abstractmethod
    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        """Insert or update a vector with metadata.

        Args:
            id: Unique identifier for the vector entry.
            vector: The embedding vector to store.
            metadata: Associated metadata (source, section, page, etc.)
        """
        ...

    @abstractmethod
    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors using cosine similarity.

        Args:
            vector: The query embedding vector.
            top_k: Maximum number of results to return (default 5).
            filter: Optional metadata filter to narrow search scope.

        Returns:
            List of SearchResult objects ordered by descending similarity score.
        """
        ...

    @abstractmethod
    async def delete(self, id: str) -> None:
        """Delete a vector by ID.

        Args:
            id: The unique identifier of the vector entry to remove.
        """
        ...
