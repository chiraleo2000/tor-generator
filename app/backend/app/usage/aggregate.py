"""Pure summaries over usage rows already loaded from the database."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_range(
    start: str | None,
    end: str | None,
    *,
    now: datetime | None = None,
    default_hours: int = 24,
) -> tuple[datetime, datetime]:
    current = _aware(now or datetime.now(timezone.utc))
    end_at = _parse_dt(end) or current
    start_at = _parse_dt(start) or (end_at - timedelta(hours=max(1, default_hours)))
    if start_at > end_at:
        start_at, end_at = end_at, start_at
    return start_at, end_at


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return _aware(parsed)


def _created(row: Any) -> datetime | None:
    created = getattr(row, "created_at", None)
    if isinstance(created, datetime):
        return _aware(created)
    return None


def _inside_window(created: datetime | None, start: datetime | None, end: datetime | None) -> bool:
    if start is not None and (created is None or created < start):
        return False
    if end is not None and (created is None or created > end):
        return False
    return True


def _label_matches(event: Any, provider: str | None, task: str | None, user_id: str | None) -> bool:
    if provider and str(getattr(event, "provider", "")) != provider:
        return False
    if task and str(getattr(event, "task", "")) != task:
        return False
    if user_id and str(getattr(event, "user_id", "") or "") != user_id:
        return False
    return True


def filter_events(
    events: list[Any],
    *,
    provider: str | None = None,
    task: str | None = None,
    user_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Any]:
    selected: list[Any] = []
    for event in events:
        if not _inside_window(_created(event), start, end):
            continue
        if _label_matches(event, provider, task, user_id):
            selected.append(event)
    return selected


def paginate(items: list[Any], limit: int, offset: int) -> tuple[list[Any], int]:
    safe_limit = max(1, min(int(limit or 50), 200))
    safe_offset = max(0, int(offset or 0))
    return items[safe_offset : safe_offset + safe_limit], len(items)


def _num(row: Any, name: str) -> float:
    try:
        return float(getattr(row, name, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def summarize(events: list[Any], *, start: datetime, end: datetime) -> dict[str, Any]:
    prompt = completion = cache_write = cache_read = total = 0
    cost = 0.0
    by_provider: dict[str, dict[str, float]] = defaultdict(_bucket)
    by_model: dict[str, dict[str, float]] = defaultdict(_bucket)
    by_task: dict[str, dict[str, float]] = defaultdict(_bucket)
    by_user: dict[str, dict[str, float]] = defaultdict(_bucket)
    for event in events:
        prompt += int(_num(event, "prompt_tokens"))
        completion += int(_num(event, "completion_tokens"))
        cache_write += int(_num(event, "cache_creation_input_tokens"))
        cache_read += int(_num(event, "cache_read_input_tokens"))
        total += int(_num(event, "total_tokens"))
        event_cost = _num(event, "cost_usd")
        cost += event_cost
        _add(by_provider[str(getattr(event, "provider", "") or "unknown")], event, event_cost)
        _add(by_model[str(getattr(event, "model", "") or "unknown")], event, event_cost)
        _add(by_task[str(getattr(event, "task", "") or "unknown")], event, event_cost)
        user = str(getattr(event, "user_id", "") or "") or "anonymous"
        _add(by_user[user], event, event_cost)
    hours = max((end - start).total_seconds() / 3600, 1 / 60)
    return {
        "requests": len(events),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cache_creation_input_tokens": cache_write,
        "cache_read_input_tokens": cache_read,
        "total_tokens": total,
        "cost_usd": round(cost, 6),
        "calls_per_hour": round(len(events) / hours, 2),
        "by_provider": _top(by_provider),
        "by_model": _top(by_model),
        "by_task": _top(by_task),
        "by_user": _top(by_user),
    }


def _bucket() -> dict[str, float]:
    return {"requests": 0, "tokens": 0, "cost_usd": 0.0}


def _add(bucket: dict[str, float], event: Any, cost: float) -> None:
    bucket["requests"] += 1
    bucket["tokens"] += _num(event, "total_tokens")
    bucket["cost_usd"] = round(bucket["cost_usd"] + cost, 6)


def _top(groups: dict[str, dict[str, float]], limit: int = 10) -> list[dict[str, Any]]:
    ranked = sorted(groups.items(), key=lambda item: item[1]["tokens"], reverse=True)
    return [{"key": key, **values} for key, values in ranked[:limit]]


def _floor(moment: datetime, grain: str) -> datetime:
    moment = _aware(moment)
    if grain == "day":
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)
    return moment.replace(minute=0, second=0, microsecond=0)


def _step(grain: str) -> timedelta:
    return timedelta(days=1) if grain == "day" else timedelta(hours=1)


def bucket_timeseries(
    events: list[Any],
    *,
    start: datetime,
    end: datetime,
    grain: str,
) -> list[dict[str, Any]]:
    unit = "day" if grain == "day" else "hour"
    cursor = _floor(start, unit)
    finish = _floor(end, unit)
    buckets: dict[datetime, dict[str, float]] = {}
    guard = 0
    while cursor <= finish and guard < 400:
        buckets[cursor] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
        cursor = cursor + _step(unit)
        guard += 1
    for event in events:
        created = _created(event)
        if created is None:
            continue
        slot = _floor(created, unit)
        if slot not in buckets:
            continue
        buckets[slot]["requests"] += 1
        buckets[slot]["tokens"] += _num(event, "total_tokens")
        buckets[slot]["cost_usd"] = round(buckets[slot]["cost_usd"] + _num(event, "cost_usd"), 6)
    return [
        {
            "start": slot.isoformat(),
            "requests": int(values["requests"]),
            "tokens": int(values["tokens"]),
            "cost_usd": values["cost_usd"],
        }
        for slot, values in buckets.items()
    ]
