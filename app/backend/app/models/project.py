"""Project ORM model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Project(Base):
    """TOR project owned by a procurement officer."""

    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_owner_status", "owner_id", "status"),
        Index("idx_projects_updated_at", "updated_at", postgresql_using="btree"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    ministry: Mapped[str] = mapped_column(String(255), nullable=False)
    budget: Mapped[int] = mapped_column(BigInteger, nullable=False)
    project_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general"
    )  # it|construction|consulting|general
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft"
    )  # draft|in_review|approved|rejected|archived
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1-8
    current_phase: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-4
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    extracted_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True
    )
    workflow_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="wizard"
    )  # wizard|agent
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="projects"
    )
    template: Mapped[Optional["Template"]] = relationship(  # noqa: F821
        "Template", back_populates="projects"
    )
    tor_sections: Mapped[list["TORSection"]] = relationship(  # noqa: F821
        "TORSection", back_populates="project", lazy="selectin"
    )
    versions: Mapped[list["ProjectVersion"]] = relationship(  # noqa: F821
        "ProjectVersion", back_populates="project", lazy="selectin"
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(  # noqa: F821
        "Suggestion", back_populates="project", lazy="selectin"
    )
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(  # noqa: F821
        "UploadedFile", back_populates="project", lazy="selectin"
    )
    agent_sessions: Mapped[list["AgentSession"]] = relationship(  # noqa: F821
        "AgentSession", back_populates="project", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
