"""Persisted admin AI provider settings (single-row overlay)."""

from datetime import datetime

from sqlalchemy import Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AiRuntimeSettings(Base):
    """Singleton row of admin-selected AI provider configuration."""

    __tablename__ = "ai_runtime_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
