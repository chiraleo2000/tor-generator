"""AgentSession ORM model for conversational TOR drafting."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)


class AgentSession(Base):
    """Stateful agent workflow session linked to a Project and User."""

    __tablename__ = "agent_sessions"
    __table_args__ = (
        Index("idx_agent_sessions_user", "user_id", "phase"),
        Index("idx_agent_sessions_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    phase: Mapped[str] = mapped_column(String(30), nullable=False, default="idle")
    slot_map: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    gap_iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graph_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    messages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_expires_at
    )

    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="agent_sessions"
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="agent_sessions"
    )

    def __repr__(self) -> str:
        return f"<AgentSession(id={self.id}, phase={self.phase})>"
