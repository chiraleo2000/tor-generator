"""Persisted LLM usage, in-app alerts, and admin price overrides."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LlmUsageEvent(Base):
    """One LLM invocation (or a finished stream)."""

    __tablename__ = "llm_usage_events"
    __table_args__ = (
        Index("idx_llm_usage_events_created", "created_at"),
        Index("idx_llm_usage_events_user", "user_id", "created_at"),
        Index("idx_llm_usage_events_provider", "provider", "created_at"),
        Index("idx_llm_usage_events_task", "task", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task: Mapped[str] = mapped_column(String(40), nullable=False, default="chat")
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_creation_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)


class UsageAlert(Base):
    """Open or acknowledged anomaly shown only in the admin UI."""

    __tablename__ = "usage_alerts"
    __table_args__ = (
        Index("idx_usage_alerts_open", "rule_id", "subject_key", "acknowledged_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warn")
    rule_id: Mapped[str] = mapped_column(String(60), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class LlmPricingRate(Base):
    """Admin override of USD per 1,000,000 tokens for a provider and model."""

    __tablename__ = "llm_pricing_rates"
    __table_args__ = (UniqueConstraint("provider", "model", name="uq_llm_pricing_provider_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="*")
    input_per_million: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    output_per_million: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cache_write_per_million: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cache_read_per_million: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
