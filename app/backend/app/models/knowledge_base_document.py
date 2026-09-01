"""KnowledgeBaseDocument ORM model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KnowledgeBaseDocument(Base):
    """A document ingested into the knowledge base for RAG retrieval."""

    __tablename__ = "knowledge_base_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # law|regulation|guideline|circular|price_announcement|manual|example_tor|template|other
    file_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # pdf|docx|txt
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending|processing|completed|failed
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    mongo_gridfs_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="baseline")
    corpus_group: Mapped[str] = mapped_column(
        String(40), nullable=False, default="mandatory_raw"
    )
    content_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    chunks: Mapped[list["KBChunk"]] = relationship(  # noqa: F821
        "KBChunk", back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBaseDocument(id={self.id}, name={self.name}, "
            f"status={self.processing_status})>"
        )
