"""OpenAI embedding provider using text-embedding-3-small model.

This provider connects to the OpenAI API for generating embeddings in cloud
or hybrid deployment modes.
"""

import logging
from typing import Any

from openai import AsyncOpenAI

from app.providers.base import EmbeddingProvider
from app.providers.constants import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

# OpenAI embeddings API supports up to 2048 inputs per request
_MAX_BATCH_SIZE = 2048


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI's text-embedding-3-small model.

    Attributes:
        model: The OpenAI embedding model name.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        max_batch_size: int = _MAX_BATCH_SIZE,
        dimensions: int = EMBEDDING_DIMENSIONS,
        **client_kwargs: Any,
    ) -> None:
        """Initialize the OpenAI embedding provider.

        Args:
            api_key: OpenAI API key for authentication.
            model: Model identifier (default: text-embedding-3-small).
            max_batch_size: Maximum texts per API request (default: 2048).
            dimensions: Truncate embeddings to this size (default 768).
            **client_kwargs: Additional kwargs passed to AsyncOpenAI client
                (e.g. timeout, max_retries).
        """
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAIEmbeddingProvider")

        self._client = AsyncOpenAI(api_key=api_key, **client_kwargs)
        self.model = model
        self._max_batch_size = max_batch_size
        self.dimensions = dimensions

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text using OpenAI API.

        Args:
            text: The query string to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            openai.APIError: If the API returns an error response.
            openai.APIConnectionError: If unable to connect to OpenAI.
        """
        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
        )
        return response.data[0].embedding

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple document texts, chunking into batches if needed.

        Handles batch size limits by splitting into multiple API calls
        when the input exceeds the maximum batch size (2048 per request).

        Args:
            texts: A list of document strings to embed.

        Returns:
            A list of embedding vectors, one per input text.

        Raises:
            openai.APIError: If the API returns an error response.
            openai.APIConnectionError: If unable to connect to OpenAI.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Process in batches to respect API limits
        for i in range(0, len(texts), self._max_batch_size):
            batch = texts[i : i + self._max_batch_size]
            logger.debug(
                "Embedding batch %d-%d of %d texts",
                i,
                i + len(batch),
                len(texts),
            )
            response = await self._client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
            )
            # Ensure ordering matches input (API returns in order but sort to be safe)
            batch_embeddings = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in batch_embeddings])

        return all_embeddings
