"""UploadedFile ORM model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UploadedFile(Base):
    """A file uploaded by a user, stored in MinIO."""

    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending|completed|failed|timeout
    uploaded_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="uploaded_files"
    )
    uploader: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="uploaded_files", foreign_keys=[uploaded_by]
    )

    def __repr__(self) -> str:
        return (
            f"<UploadedFile(id={self.id}, original_name={self.original_name}, "
            f"ocr_status={self.ocr_status})>"
        )
