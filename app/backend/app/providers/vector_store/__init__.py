"""Vector store provider implementations (pgvector, Qdrant).

Imports are lazy to avoid hard dependency on qdrant-client when not used.
"""

from app.providers.vector_store.pgvector_provider import PgVectorProvider

__all__ = ["PgVectorProvider", "QdrantProvider"]


def __getattr__(name: str):
    """Lazy import QdrantProvider to avoid requiring qdrant-client globally."""
    if name == "QdrantProvider":
        from app.providers.vector_store.qdrant_provider import QdrantProvider

        return QdrantProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
