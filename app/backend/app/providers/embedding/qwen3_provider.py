"""Qwen3 local embedding provider via OpenAI-compatible API.

This provider connects to a locally-hosted Qwen3-Embedding-4B model
served via an OpenAI-compatible endpoint (e.g., LM Studio, vLLM, Ollama).
Used in on-prem and hybrid deployment modes.
"""

import logging
from typing import Any

from openai import AsyncOpenAI

from app.providers.base import EmbeddingProvider
from app.providers.constants import DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Local servers may have lower batch limits; default conservatively
_DEFAULT_MAX_BATCH_SIZE = 512


class Qwen3LocalEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using a locally-hosted Qwen3-Embedding-4B model.

    Connects to an OpenAI-compatible embedding endpoint (e.g., LM Studio
    or vLLM serving Qwen3-Embedding-4B locally).

    Attributes:
        model: The model name as registered on the local server.
    """

    def __init__(
        self,
        base_url: str,
        model: str = DEFAULT_EMBEDDING_MODEL,
        api_key: str = "not-needed",
        max_batch_size: int = _DEFAULT_MAX_BATCH_SIZE,
        **client_kwargs: Any,
    ) -> None:
        """Initialize the Qwen3 local embedding provider.

        Args:
            base_url: Base URL for the local embedding server
                (e.g., "http://localhost:1234/v1").
            model: Model identifier on the local server
                (default: EmbeddingGemma-300M).
            api_key: API key for the local server (default: "not-needed"
                since most local servers don't require authentication).
            max_batch_size: Maximum texts per request (default: 512).
            **client_kwargs: Additional kwargs passed to AsyncOpenAI client
                (e.g. timeout, max_retries).
        """
        if not base_url:
            raise ValueError(
                "base_url is required for Qwen3LocalEmbeddingProvider "
                "(e.g., 'http://localhost:1234/v1')"
            )

        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            **client_kwargs,
        )
        self.model = model
        self._max_batch_size = max_batch_size

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text using the local Qwen3 model.

        Args:
            text: The query string to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            openai.APIConnectionError: If the local server is unreachable.
            openai.APIError: If the server returns an error response.
        """
        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple document texts, chunking into batches if needed.

        Handles batch size limits by splitting into multiple requests
        when the input exceeds the configured maximum batch size.

        Args:
            texts: A list of document strings to embed.

        Returns:
            A list of embedding vectors, one per input text.

        Raises:
            openai.APIConnectionError: If the local server is unreachable.
            openai.APIError: If the server returns an error response.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Process in batches to respect local server limits
        for i in range(0, len(texts), self._max_batch_size):
            batch = texts[i : i + self._max_batch_size]
            logger.debug(
                "Embedding batch %d-%d of %d texts (local Qwen3)",
                i,
                i + len(batch),
                len(texts),
            )
            response = await self._client.embeddings.create(
                model=self.model,
                input=batch,
            )
            # Ensure ordering matches input
            batch_embeddings = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in batch_embeddings])

        return all_embeddings
