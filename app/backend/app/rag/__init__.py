"""RAG pipeline package.

Provides document ingestion (extraction, chunking, embedding) and retrieval functionality
for the TOR Drafting and Review Application knowledge base.
"""

from app.rag.retrieval import (
    DEFAULT_TOP_K,
    RAGRetriever,
    RetrievalFilter,
    RetrievalResult,
    RetrievedChunk,
)

__all__ = [
    "DEFAULT_TOP_K",
    "RAGRetriever",
    "RetrievalFilter",
    "RetrievalResult",
    "RetrievedChunk",
]
