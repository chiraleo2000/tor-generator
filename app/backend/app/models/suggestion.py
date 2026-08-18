"""Suggestion ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Suggestion(Base):
    """AI-generated improvement suggestion for a TOR section."""

    __tablename__ = "suggestions"
    __table_args__ = (
        Index("idx_suggestions_project_status", "project_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    section_key: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # compliance|clarity|completeness|consistency
    current_text: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_score_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending|accepted|dismissed
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="suggestions"
    )

    def __repr__(self) -> str:
        return (
            f"<Suggestion(id={self.id}, project_id={self.project_id}, "
            f"category={self.category}, status={self.status})>"
        )
