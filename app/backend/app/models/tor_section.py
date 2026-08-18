"""TORSection ORM model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TORSection(Base):
    """A section of a TOR document within a project."""

    __tablename__ = "tor_sections"
    __table_args__ = (
        Index("idx_tor_sections_project", "project_id", "section_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    section_key: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # s1..s13
    sub_key: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # e.g. 4.1..4.14
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ai_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_findings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="tor_sections"
    )

    def __repr__(self) -> str:
        return (
            f"<TORSection(id={self.id}, project_id={self.project_id}, "
            f"section_key={self.section_key})>"
        )
