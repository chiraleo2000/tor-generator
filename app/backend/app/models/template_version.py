"""TemplateVersion ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TemplateVersion(Base):
    """Versioned snapshot of a template's structure and guidance."""

    __tablename__ = "template_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_structure: Mapped[dict] = mapped_column(JSONB, nullable=False)
    placeholder_guidance: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    template: Mapped["Template"] = relationship(  # noqa: F821
        "Template", back_populates="versions"
    )

    def __repr__(self) -> str:
        return (
            f"<TemplateVersion(id={self.id}, template_id={self.template_id}, "
            f"version={self.version_number})>"
        )
