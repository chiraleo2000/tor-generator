"""Property-based tests for Embedding Round-Trip Retrieval (Property 6).

Verifies that for any chunk text stored in the vector store, embedding the chunk
text and performing a similarity search with top-K=1 returns that same chunk as
the top result (self-retrieval property).

This uses deterministic mock providers:
- A hash-based embedding provider that always returns the same vector for the same text
- An in-memory vector store that performs actual cosine similarity search

**Validates: Requirements 3.4, 3.6**

# Feature: tor-drafting-review-app, Property 6: Embedding Round-Trip Retrieval
"""

from __future__ import annotations

import hashlib
import math
import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.providers.base import EmbeddingProvider, SearchResult, VectorStoreProvider
from app.rag.retrieval import RAGRetriever


# ---------------------------------------------------------------------------
# Deterministic Mock Embedding Provider
# ---------------------------------------------------------------------------


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """A mock embedding provider that produces deterministic vectors from text.

    Uses SHA-256 hash of the input text to generate a consistent embedding vector.
    The same text always produces the same vector, and different texts produce
    different vectors (with extremely high probability due to hash properties).

    The vector is normalized to unit length for proper cosine similarity behavior.
    """

    VECTOR_DIM = 64  # Smaller dimension for faster tests

    async def embed_query(self, text: str) -> list[float]:
        """Generate a deterministic embedding from text."""
        return self._text_to_vector(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic embeddings for multiple texts."""
        return [self._text_to_vector(t) for t in texts]

    def _text_to_vector(self, text: str) -> list[float]:
        """Convert text to a deterministic unit vector using SHA-256 hash.

        The hash bytes are expanded to fill the desired dimension, then
        normalized to unit length for cosine similarity.
        """
        # Generate enough hash bytes to fill the vector dimension
        raw_bytes = b""
        counter = 0
        while len(raw_bytes) < self.VECTOR_DIM * 4:
            data = f"{text}:{counter}".encode("utf-8")
            raw_bytes += hashlib.sha256(data).digest()
            counter += 1

        # Convert bytes to floats in [-1, 1]
        vector: list[float] = []
        for i in range(self.VECTOR_DIM):
            # Use 4 bytes per float
            byte_val = raw_bytes[i * 4 : (i + 1) * 4]
            int_val = int.from_bytes(byte_val, byteorder="big", signed=True)
            # Normalize to [-1, 1]
            vector.append(int_val / (2**31))

        # Normalize to unit vector
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector


# ---------------------------------------------------------------------------
# In-Memory Vector Store with Actual Cosine Similarity
# ---------------------------------------------------------------------------


class InMemoryVectorStore(VectorStoreProvider):
    """An in-memory vector store that performs actual cosine similarity search.

    Stores vectors in a dictionary and computes exact cosine similarity
    for search operations, matching the behavior of pgvector/Qdrant.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}  # id -> {"vector": [...], "metadata": {...}}

    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        """Store a vector with metadata."""
        self._store[id] = {"vector": vector, "metadata": metadata}

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[SearchResult]:
        """Search using cosine similarity."""
        if not self._store:
            return []

        results: list[tuple[str, float]] = []
        for entry_id, entry in self._store.items():
            # Apply metadata filter if provided
            if filter:
                entry_meta = entry["metadata"]
                if not all(entry_meta.get(k) == v for k, v in filter.items()):
                    continue

            score = self._cosine_similarity(vector, entry["vector"])
            results.append((entry_id, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results
        search_results: list[SearchResult] = []
        for entry_id, score in results[:top_k]:
            entry = self._store[entry_id]
            search_results.append(
                SearchResult(
                    id=entry_id,
                    text=entry["metadata"].get("chunk_text", ""),
                    score=score,
                    metadata=entry["metadata"],
                )
            )
        return search_results

    async def delete(self, id: str) -> None:
        """Remove a vector by ID."""
        self._store.pop(id, None)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot_product / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate non-empty chunk text (simulating Thai procurement document chunks)
chunk_text_strategy = st.text(
    alphabet=st.characters(
        categories=("L", "N", "P", "Z"),
        include_characters="กขคงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ"
        "ะาิีึืุูเแโใไ็่้๊๋์ํ๐๑๒๓๔๕๖๗๘๙",
    ),
    min_size=5,
    max_size=200,
).filter(lambda t: len(t.strip()) >= 3)

# Generate chunk IDs
chunk_id_strategy = st.uuids().map(str)

# Generate optional metadata
metadata_strategy = st.fixed_dictionaries(
    {},
    optional={
        "document_type": st.sampled_from(["law", "regulation", "guideline", "manual", "example_tor"]),
        "section_relevance": st.sampled_from(["s1", "s2", "s3", "s4", "s5", "s6"]),
        "source_document": st.text(min_size=3, max_size=30),
    },
)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestEmbeddingRoundTripRetrieval:
    """Property 6: Embedding Round-Trip Retrieval.

    For any document chunk stored in the vector store, embedding the chunk text
    and performing a similarity search with top-K=1 returns that same chunk as
    the top result (self-retrieval property).

    **Validates: Requirements 3.4, 3.6**
    """

    @given(
        chunk_text=chunk_text_strategy,
        chunk_id=chunk_id_strategy,
        extra_metadata=metadata_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 6: Embedding Round-Trip Retrieval
    def test_stored_chunk_is_top_1_when_searching_with_own_text(
        self,
        chunk_text: str,
        chunk_id: str,
        extra_metadata: dict,
    ):
        """A stored chunk is always the top-1 result when searching with its own text.

        This verifies the self-retrieval property: embedding a text produces a
        consistent vector, and searching with that same vector finds the stored
        entry with a perfect (or near-perfect) cosine similarity score.

        **Validates: Requirements 3.4, 3.6**
        """
        import asyncio

        asyncio.run(
            self._run_round_trip_test(chunk_text, chunk_id, extra_metadata)
        )

    async def _run_round_trip_test(
        self,
        chunk_text: str,
        chunk_id: str,
        extra_metadata: dict,
    ) -> None:
        """Execute the round-trip retrieval test asynchronously."""
        embedding_provider = DeterministicEmbeddingProvider()
        vector_store = InMemoryVectorStore()
        retriever = RAGRetriever(
            embedding_provider=embedding_provider,
            vector_store_provider=vector_store,
            default_top_k=1,
        )

        # Step 1: Embed the chunk text
        chunk_vector = await embedding_provider.embed_query(chunk_text)

        # Step 2: Store it in the vector store
        metadata = {"chunk_text": chunk_text, **extra_metadata}
        await vector_store.upsert(id=chunk_id, vector=chunk_vector, metadata=metadata)

        # Step 3: Retrieve with the same text (top_k=1)
        result = await retriever.retrieve(query=chunk_text, top_k=1)

        # Assert: The stored chunk is returned as the top-1 result
        assert result.actual_count == 1, (
            f"Expected 1 result but got {result.actual_count}"
        )
        assert result.chunks[0].id == chunk_id, (
            f"Expected chunk_id={chunk_id} but got {result.chunks[0].id}"
        )
        assert result.chunks[0].text == chunk_text, (
            f"Expected text to match stored chunk text"
        )
        # Cosine similarity of a vector with itself should be ~1.0
        assert result.chunks[0].score >= 0.99, (
            f"Expected near-perfect similarity score but got {result.chunks[0].score}"
        )

    @given(
        chunk_text=chunk_text_strategy,
        chunk_id=chunk_id_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 6: Embedding Round-Trip Retrieval
    def test_self_similarity_score_is_maximal(
        self,
        chunk_text: str,
        chunk_id: str,
    ):
        """Self-retrieval always yields the highest possible similarity score (~1.0).

        This ensures the embedding is deterministic — the same text always produces
        the same vector, so cosine similarity with itself is always 1.0.

        **Validates: Requirements 3.4, 3.6**
        """
        import asyncio

        asyncio.run(
            self._run_self_similarity_test(chunk_text, chunk_id)
        )

    async def _run_self_similarity_test(
        self,
        chunk_text: str,
        chunk_id: str,
    ) -> None:
        """Verify that the embedding of a text has cosine similarity 1.0 with itself."""
        embedding_provider = DeterministicEmbeddingProvider()

        # Embed the same text twice
        vector_1 = await embedding_provider.embed_query(chunk_text)
        vector_2 = await embedding_provider.embed_query(chunk_text)

        # Vectors must be identical (deterministic)
        assert vector_1 == vector_2, "Same text must produce identical embeddings"

        # Cosine similarity with itself must be ~1.0
        similarity = InMemoryVectorStore._cosine_similarity(vector_1, vector_2)
        assert abs(similarity - 1.0) < 1e-9, (
            f"Self-similarity should be 1.0, got {similarity}"
        )

    @given(
        chunk_texts=st.lists(
            chunk_text_strategy,
            min_size=2,
            max_size=10,
            unique=True,
        ),
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 6: Embedding Round-Trip Retrieval
    def test_target_chunk_beats_other_chunks_in_retrieval(
        self,
        chunk_texts: list[str],
    ):
        """When multiple chunks are stored, searching with one chunk's text
        returns that specific chunk as top-1, not any other chunk.

        This tests the discriminative property: the embedding must distinguish
        between different texts so the correct chunk is ranked first.

        **Validates: Requirements 3.4, 3.6**
        """
        import asyncio

        asyncio.run(
            self._run_multi_chunk_round_trip(chunk_texts)
        )

    async def _run_multi_chunk_round_trip(
        self,
        chunk_texts: list[str],
    ) -> None:
        """Store multiple chunks, query with one, verify it's top-1."""
        embedding_provider = DeterministicEmbeddingProvider()
        vector_store = InMemoryVectorStore()
        retriever = RAGRetriever(
            embedding_provider=embedding_provider,
            vector_store_provider=vector_store,
            default_top_k=1,
        )

        # Store all chunks
        chunk_ids = [str(uuid.uuid4()) for _ in chunk_texts]
        for chunk_id, chunk_text in zip(chunk_ids, chunk_texts):
            vector = await embedding_provider.embed_query(chunk_text)
            await vector_store.upsert(
                id=chunk_id,
                vector=vector,
                metadata={"chunk_text": chunk_text},
            )

        # For each chunk, verify self-retrieval
        target_text = chunk_texts[0]
        target_id = chunk_ids[0]

        result = await retriever.retrieve(query=target_text, top_k=1)

        assert result.actual_count >= 1, "Expected at least 1 result"
        assert result.chunks[0].id == target_id, (
            f"Expected target chunk {target_id} as top-1 but got {result.chunks[0].id}"
        )
        assert result.chunks[0].text == target_text, (
            f"Expected text '{target_text}' but got '{result.chunks[0].text}'"
        )
