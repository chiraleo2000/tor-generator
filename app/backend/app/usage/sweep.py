"""Periodic anomaly sweep. Started from the FastAPI lifespan."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.usage.anomaly import (
    detect_anomalies,
    detect_infra_anomalies,
    limits_from_settings,
    sample_from_mapping,
)
from app.usage.infra_status import collect_waiting_ms, probe_process_services
from app.usage.store import _draft_row, fetch_alerts, fetch_usage_events, open_alert_keys

logger = logging.getLogger(__name__)


def _interval_seconds() -> float:
    from app.config import get_settings

    raw = getattr(get_settings(), "usage_sweep_seconds", 300)
    try:
        return max(5.0, float(raw))
    except (TypeError, ValueError):
        return 300.0


async def run_usage_sweep_once() -> int:
    """Re-check the last 7 days plus dependency health. Returns alerts created."""
    from app import infra

    factory = infra.session_factory
    if factory is None:
        return 0
    now = datetime.now(timezone.utc)
    async with factory() as session:
        events = await fetch_usage_events(session, since=now - timedelta(days=7), until=now)
        alerts = await fetch_alerts(session)
        keys = open_alert_keys(alerts)
        samples = [sample for row in events if (sample := sample_from_mapping(row)) is not None]
        limits = limits_from_settings()
        drafts = detect_anomalies(samples, keys, now=now, limits=limits)
        services = await probe_process_services()
        waits = await collect_waiting_ms(infra.redis_client)
        drafts.extend(detect_infra_anomalies(services, waits, keys, now=now, limits=limits))
        for draft in drafts:
            session.add(_draft_row(draft))
        await session.commit()
        return len(drafts)


async def usage_sweep_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await run_usage_sweep_once()
        except Exception:
            logger.exception("usage sweep failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=_interval_seconds())
        except TimeoutError:
            continue
