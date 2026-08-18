"""KBChunk ORM model with pgvector embedding column."""

import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.providers.constants import EMBEDDING_DIMENSIONS


class KBChunk(Base):
    """A chunk of text from a knowledge base document with its embedding vector."""

    __tablename__ = "kb_chunks"
    __table_args__ = (
        Index("idx_kb_chunks_document", "document_id", "chunk_index"),
        Index(
            "idx_kb_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_base_documents.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # Relationships
    document: Mapped["KnowledgeBaseDocument"] = relationship(  # noqa: F821
        "KnowledgeBaseDocument", back_populates="chunks"
    )

    def __repr__(self) -> str:
        return (
            f"<KBChunk(id={self.id}, document_id={self.document_id}, "
            f"chunk_index={self.chunk_index})>"
        )
