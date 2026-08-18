"""Template ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Template(Base):
    """TOR template for different industry types."""

    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    industry: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # it|construction|consulting|general
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft"
    )  # draft|published
    section_structure: Mapped[dict] = mapped_column(JSONB, nullable=False)
    placeholder_guidance: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="templates"
    )
    versions: Mapped[list["TemplateVersion"]] = relationship(  # noqa: F821
        "TemplateVersion", back_populates="template", lazy="selectin"
    )
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="template", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name={self.name}, industry={self.industry})>"
