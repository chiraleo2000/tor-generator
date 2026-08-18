"""ChatMessage ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ChatMessage(Base):
    """One message in a chat room."""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("idx_chat_messages_room", "room_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    room: Mapped["ChatRoom"] = relationship(  # noqa: F821
        "ChatRoom", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role})>"
