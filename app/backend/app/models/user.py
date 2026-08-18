"""User ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    """User account for procurement officers, reviewers, and administrators."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="officer"
    )  # officer|reviewer|admin
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="owner", lazy="selectin"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        "AuditLog", back_populates="user", lazy="selectin"
    )
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(  # noqa: F821
        "UploadedFile", back_populates="uploader", foreign_keys="UploadedFile.uploaded_by"
    )
    templates: Mapped[list["Template"]] = relationship(  # noqa: F821
        "Template", back_populates="creator", lazy="selectin"
    )
    chat_rooms: Mapped[list["ChatRoom"]] = relationship(  # noqa: F821
        "ChatRoom", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
