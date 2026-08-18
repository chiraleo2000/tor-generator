"""ChatRoom ORM model — per-user KB Q&A or draft intake rooms."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ChatRoom(Base):
    """A conversation owned by one user (KB Q&A or project intake)."""

    __tablename__ = "chat_rooms"
    __table_args__ = (
        Index("idx_chat_rooms_user_kind", "user_id", "kind", "updated_at"),
        Index("idx_chat_rooms_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # kb | draft_intake
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="ห้องใหม่")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="chat_rooms"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        "ChatMessage",
        back_populates="room",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatRoom(id={self.id}, kind={self.kind}, title={self.title})>"
