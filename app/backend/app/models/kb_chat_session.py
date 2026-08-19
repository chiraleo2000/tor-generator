"""KBChatSession ORM model for knowledge-base Q&A."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KBChatSession(Base):
    """Knowledge-base chat session owned by one user."""

    __tablename__ = "kb_chat_sessions"
    __table_args__ = (Index("idx_kb_chat_user", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="kb_chat_sessions"
    )

    def __repr__(self) -> str:
        return f"<KBChatSession(id={self.id}, user_id={self.user_id})>"
