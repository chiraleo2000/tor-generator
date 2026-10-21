"""Load and append usage rows. Aggregation stays in ``aggregate``."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LlmPricingRate, LlmUsageEvent, UsageAlert
from app.usage.anomaly import (
    AlertDraft,
    detect_anomalies,
    limits_from_settings,
    sample_from_mapping,
)
from app.usage.cost import TokenRate, default_rates, estimate_cost_usd, merge_rates, pick_rate

logger = logging.getLogger(__name__)


def _uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _clip(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:limit]


async def fetch_usage_events(
    session: AsyncSession,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 5000,
) -> list[LlmUsageEvent]:
    stmt = select(LlmUsageEvent).order_by(LlmUsageEvent.created_at.desc())
    if since is not None:
        stmt = stmt.where(LlmUsageEvent.created_at >= since)
    if until is not None:
        stmt = stmt.where(LlmUsageEvent.created_at <= until)
    stmt = stmt.limit(max(1, min(limit, 20000)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def fetch_alerts(session: AsyncSession, *, limit: int = 200) -> list[UsageAlert]:
    stmt = select(UsageAlert).order_by(UsageAlert.created_at.desc()).limit(max(1, min(limit, 500)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


def sort_alerts(alerts: list[UsageAlert]) -> list[UsageAlert]:
    open_rows = [row for row in alerts if row.acknowledged_at is None]
    closed = [row for row in alerts if row.acknowledged_at is not None]
    open_rows.sort(key=lambda row: row.created_at, reverse=True)
    closed.sort(key=lambda row: row.created_at, reverse=True)
    return open_rows + closed[:20]


def open_alert_keys(alerts: list[UsageAlert]) -> set[tuple[str, str]]:
    return {
        (row.rule_id, row.subject_key)
        for row in alerts
        if row.acknowledged_at is None
    }


async def fetch_pricing_rows(session: AsyncSession) -> list[LlmPricingRate]:
    result = await session.execute(select(LlmPricingRate))
    return list(result.scalars().all())


def rates_from_rows(rows: list[LlmPricingRate]) -> list[TokenRate]:
    overrides = [
        TokenRate(
            provider=row.provider,
            model=row.model or "*",
            input_per_million=float(row.input_per_million or 0),
            output_per_million=float(row.output_per_million or 0),
            cache_write_per_million=float(row.cache_write_per_million or 0),
            cache_read_per_million=float(row.cache_read_per_million or 0),
        )
        for row in rows
    ]
    return merge_rates(default_rates(), overrides)


def _draft_row(draft: AlertDraft) -> UsageAlert:
    return UsageAlert(
        severity=draft.severity,
        rule_id=draft.rule_id,
        subject_key=draft.subject_key,
        title=draft.title,
        detail=draft.detail,
        window_start=draft.window_start,
        window_end=draft.window_end,
    )


async def evaluate_recent(
    session: AsyncSession, *, now: datetime | None = None
) -> list[UsageAlert]:
    """Run cheap usage rules against the last 7 days and insert new alerts."""
    current = now or datetime.now(timezone.utc)
    events = await fetch_usage_events(session, since=current - timedelta(days=7), until=current)
    alerts = await fetch_alerts(session)
    samples = [sample for row in events if (sample := sample_from_mapping(row)) is not None]
    drafts = detect_anomalies(
        samples,
        open_alert_keys(alerts),
        now=current,
        limits=limits_from_settings(),
    )
    created: list[UsageAlert] = []
    for draft in drafts:
        row = _draft_row(draft)
        session.add(row)
        created.append(row)
    return created


async def load_effective_rates(session: AsyncSession) -> list[TokenRate]:
    return rates_from_rows(await fetch_pricing_rows(session))


async def persist_llm_usage(
    *,
    user_id: str | None,
    request_id: str | None,
    task: str,
    provider: str,
    model: str,
    latency_ms: int,
    usage: dict[str, Any],
    status: str,
    error: str | None,
) -> LlmUsageEvent | None:
    """Insert one usage row. Failures are logged and never raised to the caller."""
    from app import infra

    factory = infra.session_factory
    if factory is None:
        return None
    try:
        async with factory() as session:
            rates = await load_effective_rates(session)
            rate = pick_rate(rates, provider, model)
            row = LlmUsageEvent(
                user_id=_uuid(user_id),
                request_id=_clip(request_id, 64),
                task=_clip(task, 40) or "chat",
                provider=_clip(provider, 40) or "",
                model=_clip(model, 200) or "",
                latency_ms=max(0, int(latency_ms)),
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                cache_creation_input_tokens=int(usage.get("cache_creation_input_tokens") or 0),
                cache_read_input_tokens=int(usage.get("cache_read_input_tokens") or 0),
                tokens_estimated=bool(usage.get("tokens_estimated")),
                cost_usd=estimate_cost_usd(usage, rate),
                status=_clip(status, 20) or "ok",
                error=_clip(error, 300) if error else None,
            )
            session.add(row)
            await session.flush()
            try:
                await evaluate_recent(session)
            except Exception:
                logger.exception("usage anomaly evaluation failed")
            await session.commit()
            return row
    except Exception:
        logger.exception("failed to persist llm usage")
        return None


async def replace_pricing_rates(session: AsyncSession, rates: list[TokenRate]) -> list[TokenRate]:
    await session.execute(delete(LlmPricingRate))
    for rate in rates:
        session.add(
            LlmPricingRate(
                provider=rate.provider[:40],
                model=(rate.model or "*")[:200],
                input_per_million=rate.input_per_million,
                output_per_million=rate.output_per_million,
                cache_write_per_million=rate.cache_write_per_million,
                cache_read_per_million=rate.cache_read_per_million,
            )
        )
    await session.commit()
    return rates
