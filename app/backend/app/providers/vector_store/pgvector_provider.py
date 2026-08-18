"""PgVector-based vector store provider using SQLAlchemy and PostgreSQL pgvector extension.

Uses the kb_chunks table with HNSW index for cosine similarity search.
Supports metadata filtering via JSONB WHERE clauses.
"""

import uuid
from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.kb_chunk import KBChunk
from app.providers.base import SearchResult, VectorStoreProvider


class PgVectorProvider(VectorStoreProvider):
    """PostgreSQL + pgvector vector store provider.

    Uses SQLAlchemy async sessions and the pgvector extension's cosine distance
    operator (<=>) with HNSW indexing for sub-100ms retrieval.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize the PgVector provider.

        Args:
            session_factory: SQLAlchemy async session factory (from app.state).
        """
        self._session_factory = session_factory

    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        """Insert or update a kb_chunks row with embedding vector.

        Uses PostgreSQL ON CONFLICT DO UPDATE (upsert) to handle both
        new inserts and updates to existing vectors.

        Args:
            id: UUID string identifying the chunk.
            vector: The embedding vector (768 dimensions).
            metadata: Associated metadata dict. Expected keys include:
                - chunk_text: The text content of the chunk.
                - document_id: UUID of the source document.
                - chunk_index: Integer position within document.
                - section_label: Optional section name.
                - page_number: Optional page number.
        """
        chunk_id = uuid.UUID(id) if isinstance(id, str) else id

        # Extract known fields from metadata, remaining goes into chunk_metadata
        chunk_text = metadata.pop("chunk_text", "")
        document_id = metadata.pop("document_id", None)
        chunk_index = metadata.pop("chunk_index", 0)
        section_label = metadata.pop("section_label", None)
        page_number = metadata.pop("page_number", None)

        values: dict[str, Any] = {
            "id": chunk_id,
            "chunk_text": chunk_text,
            "embedding": vector,
            "chunk_index": chunk_index,
            "metadata": metadata,
        }

        if document_id is not None:
            values["document_id"] = (
                uuid.UUID(document_id) if isinstance(document_id, str) else document_id
            )

        if section_label is not None:
            values["section_label"] = section_label

        if page_number is not None:
            values["page_number"] = page_number

        # Insert against __table__: a column named "metadata" collides with
        # Table.metadata if we use the ORM class and stmt.excluded.metadata.
        table = KBChunk.__table__
        stmt = pg_insert(table).values(**values)
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=[table.c.id],
            set_={
                "chunk_text": excluded.chunk_text,
                "embedding": excluded.embedding,
                "chunk_index": excluded.chunk_index,
                "metadata": excluded["metadata"],
                "section_label": excluded.section_label,
                "page_number": excluded.page_number,
            },
        )

        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors using pgvector cosine distance.

        Uses the <=> operator (cosine distance) which leverages the HNSW index.
        Cosine distance = 1 - cosine_similarity, so lower is more similar.
        We convert to a similarity score (1 - distance) for the SearchResult.

        Args:
            vector: The query embedding vector.
            top_k: Maximum number of results to return.
            filter: Optional metadata filter dict. Keys are matched against
                the JSONB 'metadata' column using containment (@>).

        Returns:
            List of SearchResult objects ordered by descending similarity.
        """
        distance = KBChunk.embedding.cosine_distance(vector)
        stmt = (
            select(
                KBChunk.id,
                KBChunk.chunk_text,
                KBChunk.chunk_metadata,
                distance.label("distance"),
            )
            .where(KBChunk.embedding.is_not(None))
        )

        if filter:
            stmt = stmt.where(KBChunk.chunk_metadata.contains(filter))

        stmt = stmt.order_by(distance).limit(top_k)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = result.all()

        search_results: list[SearchResult] = []
        for row in rows:
            # Convert cosine distance to similarity score (1 - distance)
            distance = row.distance if row.distance is not None else 1.0
            similarity = 1.0 - distance

            search_results.append(
                SearchResult(
                    id=str(row.id),
                    text=row.chunk_text,
                    score=similarity,
                    metadata=row.chunk_metadata if row.chunk_metadata else {},
                )
            )

        return search_results

    async def delete(self, id: str) -> None:
        """Delete a vector entry by ID.

        Args:
            id: UUID string of the kb_chunk to remove.
        """
        chunk_id = uuid.UUID(id) if isinstance(id, str) else id

        stmt = sa_delete(KBChunk).where(KBChunk.id == chunk_id)

        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()
