"""Qdrant-based vector store provider using the async Qdrant client.

Provides an alternative to pgvector for vector similarity search,
particularly suited for cloud deployments or when Qdrant is preferred.
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.providers.base import SearchResult, VectorStoreProvider
from app.providers.constants import EMBEDDING_DIMENSIONS


class QdrantProvider(VectorStoreProvider):
    """Qdrant vector store provider using AsyncQdrantClient.

    Manages a single collection for knowledge base chunks.
    Handles collection creation on first use.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "tor_kb",
        vector_size: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        """Initialize the Qdrant provider.

        Args:
            host: Qdrant server host.
            port: Qdrant server port (gRPC/REST).
            collection_name: Name of the Qdrant collection to use.
            vector_size: Dimension of embedding vectors (default 768).
        """
        self._host = host
        self._port = port
        self._collection_name = collection_name
        self._vector_size = vector_size
        self._client = AsyncQdrantClient(host=host, port=port)
        self._collection_ensured = False

    async def _ensure_collection(self) -> None:
        """Create the collection if it doesn't already exist.

        Uses cosine distance metric to match the pgvector HNSW configuration.
        Only checks/creates once per provider instance lifecycle.
        """
        if self._collection_ensured:
            return

        collections = await self._client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self._collection_name not in collection_names:
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE,
                ),
            )

        self._collection_ensured = True

    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        """Insert or update a point in the Qdrant collection.

        The metadata is stored as the point payload. The chunk_text field
        is extracted from metadata and stored in the payload for retrieval.

        Args:
            id: Unique identifier for the point (UUID string).
            vector: The embedding vector.
            metadata: Associated metadata dict including chunk_text.
        """
        await self._ensure_collection()

        # Store all metadata as payload; Qdrant handles nested dicts
        payload = dict(metadata)

        point = PointStruct(
            id=id,
            vector=vector,
            payload=payload,
        )

        await self._client.upsert(
            collection_name=self._collection_name,
            points=[point],
        )

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors in the Qdrant collection.

        Uses cosine similarity with optional payload filtering.

        Args:
            vector: The query embedding vector.
            top_k: Maximum number of results to return.
            filter: Optional metadata filter dict. Each key-value pair
                becomes a FieldCondition with exact match.

        Returns:
            List of SearchResult objects ordered by descending similarity.
        """
        await self._ensure_collection()

        # Build Qdrant filter from the filter dict
        qdrant_filter: Filter | None = None
        if filter:
            conditions = [
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
                for key, value in filter.items()
            ]
            qdrant_filter = Filter(must=conditions)

        results = await self._client.search(
            collection_name=self._collection_name,
            query_vector=vector,
            limit=top_k,
            query_filter=qdrant_filter,
        )

        search_results: list[SearchResult] = []
        for point in results:
            payload = point.payload or {}
            chunk_text = payload.get("chunk_text", "")

            search_results.append(
                SearchResult(
                    id=str(point.id),
                    text=chunk_text,
                    score=point.score,
                    metadata=payload,
                )
            )

        return search_results

    async def delete(self, id: str) -> None:
        """Delete a point from the Qdrant collection by ID.

        Args:
            id: UUID string of the point to remove.
        """
        await self._ensure_collection()

        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=PointIdsList(points=[id]),
        )
