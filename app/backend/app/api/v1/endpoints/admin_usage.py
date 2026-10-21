"""Admin usage monitor: tokens, cost, frequency, alerts, and infra snapshot."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.exceptions import NotFoundError, ValidationError
from app.models.llm_usage import LlmUsageEvent, UsageAlert
from app.models.user import User
from app.rbac import require_role
from app.schemas.responses import MetaInfo, SuccessResponse
from app.usage.aggregate import bucket_timeseries, filter_events, paginate, parse_range, summarize
from app.usage.cost import TokenRate, rate_to_dict
from app.usage.infra_status import infra_snapshot
from app.usage.store import (
    fetch_alerts,
    fetch_pricing_rows,
    fetch_usage_events,
    rates_from_rows,
    replace_pricing_rates,
    sort_alerts,
)

router = APIRouter()


class RateIn(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    model: str = Field(default="*", max_length=200)
    input_per_million: float = 0
    output_per_million: float = 0
    cache_write_per_million: float = 0
    cache_read_per_million: float = 0


class PricingUpdate(BaseModel):
    rates: list[RateIn] = Field(default_factory=list)


def _meta(request: Request) -> MetaInfo:
    return MetaInfo(
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _ok(request: Request, data: Any) -> JSONResponse:
    payload = SuccessResponse(ok=True, data=data, meta=_meta(request))
    return JSONResponse(content=payload.model_dump(mode="json"))


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def event_to_dict(event: LlmUsageEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "created_at": _iso(event.created_at),
        "user_id": str(event.user_id) if event.user_id else None,
        "request_id": event.request_id,
        "task": event.task,
        "provider": event.provider,
        "model": event.model,
        "latency_ms": event.latency_ms,
        "prompt_tokens": event.prompt_tokens,
        "completion_tokens": event.completion_tokens,
        "total_tokens": event.total_tokens,
        "cache_creation_input_tokens": event.cache_creation_input_tokens,
        "cache_read_input_tokens": event.cache_read_input_tokens,
        "tokens_estimated": event.tokens_estimated,
        "cost_usd": event.cost_usd,
        "status": event.status,
        "error": event.error,
    }


def alert_to_dict(alert: UsageAlert) -> dict[str, Any]:
    return {
        "id": str(alert.id),
        "created_at": _iso(alert.created_at),
        "severity": alert.severity,
        "rule_id": alert.rule_id,
        "subject_key": alert.subject_key,
        "title": alert.title,
        "detail": alert.detail or {},
        "window_start": _iso(alert.window_start),
        "window_end": _iso(alert.window_end),
        "acknowledged_at": _iso(alert.acknowledged_at),
        "open": alert.acknowledged_at is None,
    }


def _rate_or_raise(item: RateIn) -> TokenRate:
    numbers = (
        item.input_per_million,
        item.output_per_million,
        item.cache_write_per_million,
        item.cache_read_per_million,
    )
    if any(number < 0 for number in numbers):
        raise ValidationError(message="ราคาต่อโทเคนต้องไม่ติดลบ", field="rates")
    return TokenRate(
        provider=item.provider.strip().lower(),
        model=item.model.strip() or "*",
        input_per_million=item.input_per_million,
        output_per_million=item.output_per_million,
        cache_write_per_million=item.cache_write_per_million,
        cache_read_per_million=item.cache_read_per_million,
    )


async def _window_events(
    db: AsyncSession,
    start: str | None,
    end: str | None,
) -> tuple[list[LlmUsageEvent], datetime, datetime]:
    start_at, end_at = parse_range(start, end)
    rows = await fetch_usage_events(db, since=start_at, until=end_at)
    return filter_events(rows, start=start_at, end=end_at), start_at, end_at


@router.get("/summary")
async def usage_summary(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
    start: str | None = None,
    end: str | None = None,
) -> JSONResponse:
    events, start_at, end_at = await _window_events(db, start, end)
    data = summarize(events, start=start_at, end=end_at)
    data["start"] = start_at.isoformat()
    data["end"] = end_at.isoformat()
    return _ok(request, data)


@router.get("/timeseries")
async def usage_timeseries(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
    start: str | None = None,
    end: str | None = None,
    grain: str = "hour",
) -> JSONResponse:
    events, start_at, end_at = await _window_events(db, start, end)
    buckets = bucket_timeseries(events, start=start_at, end=end_at, grain=grain)
    return _ok(request, {"grain": "day" if grain == "day" else "hour", "buckets": buckets})


@router.get("/events")
async def usage_events(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    task: str | None = None,
    user_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
    start_at, end_at = parse_range(start, end)
    rows = await fetch_usage_events(db, since=start_at, until=end_at)
    selected = filter_events(
        rows,
        provider=provider,
        task=task,
        user_id=user_id,
        start=start_at,
        end=end_at,
    )
    page, total = paginate(selected, limit, offset)
    return _ok(
        request,
        {"total": total, "items": [event_to_dict(event) for event in page]},
    )


@router.get("/alerts")
async def usage_alerts(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    alerts = sort_alerts(await fetch_alerts(db))
    open_count = sum(1 for alert in alerts if alert.acknowledged_at is None)
    return _ok(
        request,
        {"open_count": open_count, "items": [alert_to_dict(alert) for alert in alerts]},
    )


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    alert = await db.get(UsageAlert, alert_id)
    if alert is None:
        raise NotFoundError(message="ไม่พบการแจ้งเตือน")
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = current_user.id
        await db.commit()
    return _ok(request, alert_to_dict(alert))


@router.get("/pricing")
async def get_pricing(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    rates = rates_from_rows(await fetch_pricing_rows(db))
    return _ok(request, {"rates": [rate_to_dict(rate) for rate in rates]})


@router.put("/pricing")
async def put_pricing(
    body: PricingUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    stored = await replace_pricing_rates(db, [_rate_or_raise(item) for item in body.rates])
    return _ok(request, {"rates": [rate_to_dict(rate) for rate in stored]})


@router.get("/infra")
async def usage_infra(
    request: Request,
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    return _ok(request, await infra_snapshot(request))
