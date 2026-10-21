"""In-app anomaly rules over recent LLM usage samples.

Rules emit a draft only when no open alert already exists for the same
``(rule_id, subject_key)``. Infrastructure checks are separate so a single
LLM call does not ping Postgres and Neo4j.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

_CACHE_PROVIDERS = frozenset({"claude", "bedrock"})


@dataclass(frozen=True)
class AnomalyLimits:
    spike_multiplier: float = 5.0
    spike_floor_tokens: int = 100_000
    burst_requests: int = 40
    burst_window_minutes: int = 15
    daily_cost_usd: float = 25.0
    cache_miss_prompt_tokens: int = 8_000
    admission_wait_p95_ms: int = 120_000


@dataclass(frozen=True)
class UsageSample:
    created_at: datetime
    user_id: str | None
    provider: str
    prompt_tokens: int
    total_tokens: int
    cache_read_input_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class AlertDraft:
    severity: str
    rule_id: str
    subject_key: str
    title: str
    detail: dict[str, Any]
    window_start: datetime
    window_end: datetime


def limits_from_settings(settings: Any | None = None) -> AnomalyLimits:
    if settings is None:
        from app.config import get_settings

        settings = get_settings()
    return AnomalyLimits(
        spike_multiplier=float(getattr(settings, "usage_spike_multiplier", 5) or 5),
        spike_floor_tokens=int(getattr(settings, "usage_spike_floor_tokens", 100_000) or 0),
        burst_requests=int(getattr(settings, "usage_burst_requests", 40) or 1),
        burst_window_minutes=int(getattr(settings, "usage_burst_window_minutes", 15) or 1),
        daily_cost_usd=float(getattr(settings, "usage_daily_cost_usd_limit", 25) or 0),
        cache_miss_prompt_tokens=int(
            getattr(settings, "usage_cache_miss_prompt_tokens", 8_000) or 0
        ),
        admission_wait_p95_ms=int(
            getattr(settings, "usage_admission_wait_p95_ms", 120_000) or 0
        ),
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def percentile(values: list[int], percent: float = 95) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, int(round((percent / 100) * (len(ordered) - 1)))))
    return int(ordered[rank])


def _subject(user_id: str | None) -> str:
    return user_id or "anonymous"


def _hour_bucket(moment: datetime) -> datetime:
    moment = _aware(moment)
    return moment.replace(minute=0, second=0, microsecond=0)


def _accept(
    draft: AlertDraft | None,
    open_keys: set[tuple[str, str]],
    seen: set[tuple[str, str]],
) -> AlertDraft | None:
    if draft is None:
        return None
    key = (draft.rule_id, draft.subject_key)
    if key in open_keys or key in seen:
        return None
    seen.add(key)
    return draft


def _hourly_history(
    own: list[UsageSample], *, hour_ago: datetime, week_ago: datetime
) -> dict[datetime, int]:
    history: dict[datetime, int] = {}
    for sample in own:
        moment = _aware(sample.created_at)
        if moment >= hour_ago or moment < week_ago:
            continue
        bucket = _hour_bucket(moment)
        history[bucket] = history.get(bucket, 0) + sample.total_tokens
    return history


def _spike_alert(
    own: list[UsageSample],
    user: str,
    *,
    current: datetime,
    hour_ago: datetime,
    week_ago: datetime,
    rules: AnomalyLimits,
) -> AlertDraft | None:
    hour_tokens = sum(
        sample.total_tokens for sample in own if _aware(sample.created_at) >= hour_ago
    )
    history = _hourly_history(own, hour_ago=hour_ago, week_ago=week_ago)
    baseline = median(list(history.values()))
    threshold = max(rules.spike_floor_tokens, rules.spike_multiplier * baseline)
    if hour_tokens <= threshold or hour_tokens < rules.spike_floor_tokens:
        return None
    return AlertDraft(
        severity="critical",
        rule_id="user_token_spike",
        subject_key=user,
        title="การใช้โทเคนสูงผิดปกติ",
        detail={
            "tokens_last_hour": hour_tokens,
            "threshold": threshold,
            "baseline_hours": len(history),
        },
        window_start=hour_ago,
        window_end=current,
    )


def _burst_alert(
    own: list[UsageSample],
    user: str,
    *,
    current: datetime,
    burst_start: datetime,
    rules: AnomalyLimits,
) -> AlertDraft | None:
    burst = sum(1 for sample in own if _aware(sample.created_at) >= burst_start)
    if burst <= rules.burst_requests:
        return None
    return AlertDraft(
        severity="warn",
        rule_id="user_request_burst",
        subject_key=user,
        title="เรียกใช้โมเดลถี่ผิดปกติ",
        detail={
            "requests": burst,
            "window_minutes": rules.burst_window_minutes,
            "limit": rules.burst_requests,
        },
        window_start=burst_start,
        window_end=current,
    )


def _cache_alert(
    own: list[UsageSample],
    user: str,
    *,
    current: datetime,
    hour_ago: datetime,
    rules: AnomalyLimits,
) -> AlertDraft | None:
    recent = [
        sample
        for sample in own
        if _is_cache_miss(sample, hour_ago=hour_ago, rules=rules)
    ]
    prior_hits = [
        sample
        for sample in own
        if sample.cache_read_input_tokens > 0 and _aware(sample.created_at) < hour_ago
    ]
    if not recent or not prior_hits:
        return None
    sample = max(recent, key=lambda item: item.prompt_tokens)
    return AlertDraft(
        severity="warn",
        rule_id="cache_miss_waste",
        subject_key=user,
        title="พรอมต์ยาวโดยไม่โดนแคช",
        detail={
            "provider": sample.provider,
            "prompt_tokens": sample.prompt_tokens,
            "prior_cache_hits": len(prior_hits),
        },
        window_start=hour_ago,
        window_end=current,
    )


def _is_cache_miss(sample: UsageSample, *, hour_ago: datetime, rules: AnomalyLimits) -> bool:
    if _aware(sample.created_at) < hour_ago:
        return False
    if sample.provider not in _CACHE_PROVIDERS:
        return False
    if sample.prompt_tokens < rules.cache_miss_prompt_tokens:
        return False
    return sample.cache_read_input_tokens <= 0


def _cost_alert(
    samples: list[UsageSample],
    *,
    current: datetime,
    day_start: datetime,
    rules: AnomalyLimits,
) -> AlertDraft | None:
    spent = sum(sample.cost_usd for sample in samples if _aware(sample.created_at) >= day_start)
    if rules.daily_cost_usd <= 0 or spent <= rules.daily_cost_usd:
        return None
    return AlertDraft(
        severity="critical",
        rule_id="global_cost_daily",
        subject_key="org",
        title="ค่าใช้จ่ายวันนี้เกินงบ",
        detail={"cost_usd": round(spent, 6), "limit_usd": rules.daily_cost_usd},
        window_start=day_start,
        window_end=current,
    )


def detect_anomalies(
    samples: list[UsageSample],
    open_keys: set[tuple[str, str]],
    *,
    now: datetime | None = None,
    limits: AnomalyLimits | None = None,
) -> list[AlertDraft]:
    """Return new alert drafts for token spikes, bursts, cost, and cache waste."""
    current = _aware(now or datetime.now(timezone.utc))
    rules = limits or AnomalyLimits()
    seen: set[tuple[str, str]] = set()
    hour_ago = current - timedelta(hours=1)
    week_ago = current - timedelta(days=7)
    burst_start = current - timedelta(minutes=rules.burst_window_minutes)
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    drafts: list[AlertDraft] = []
    users = {_subject(sample.user_id) for sample in samples}
    for user in users:
        own = [sample for sample in samples if _subject(sample.user_id) == user]
        candidates = (
            _spike_alert(
                own,
                user,
                current=current,
                hour_ago=hour_ago,
                week_ago=week_ago,
                rules=rules,
            ),
            _burst_alert(own, user, current=current, burst_start=burst_start, rules=rules),
            _cache_alert(own, user, current=current, hour_ago=hour_ago, rules=rules),
        )
        for candidate in candidates:
            accepted = _accept(candidate, open_keys, seen)
            if accepted is not None:
                drafts.append(accepted)
    cost = _accept(
        _cost_alert(samples, current=current, day_start=day_start, rules=rules),
        open_keys,
        seen,
    )
    if cost is not None:
        drafts.append(cost)
    return drafts


def detect_infra_anomalies(
    services: dict[str, str],
    waiting_ms: list[int],
    open_keys: set[tuple[str, str]],
    *,
    now: datetime | None = None,
    limits: AnomalyLimits | None = None,
) -> list[AlertDraft]:
    """Alert when a known dependency is down or admission wait is too high."""
    current = _aware(now or datetime.now(timezone.utc))
    rules = limits or AnomalyLimits()
    drafts: list[AlertDraft] = []
    down = sorted(name for name, status in services.items() if status != "up")
    health_key = ("infra_unhealthy", "deps")
    if down and health_key not in open_keys:
        drafts.append(
            AlertDraft(
                severity="critical",
                rule_id="infra_unhealthy",
                subject_key="deps",
                title="บริการโครงสร้างพื้นฐานไม่พร้อม",
                detail={"down": down},
                window_start=current,
                window_end=current,
            )
        )
    wait_p95 = percentile(waiting_ms, 95)
    wait_key = ("infra_unhealthy", "admission")
    if (
        wait_p95 is not None
        and wait_p95 > rules.admission_wait_p95_ms
        and wait_key not in open_keys
    ):
        drafts.append(
            AlertDraft(
                severity="warn",
                rule_id="infra_unhealthy",
                subject_key="admission",
                title="คิวโมเดลรอคิวนานผิดปกติ",
                detail={"wait_p95_ms": wait_p95, "limit_ms": rules.admission_wait_p95_ms},
                window_start=current,
                window_end=current,
            )
        )
    return drafts


def sample_from_mapping(row: Any) -> UsageSample | None:
    created = getattr(row, "created_at", None)
    if not isinstance(created, datetime):
        return None
    user = getattr(row, "user_id", None)
    return UsageSample(
        created_at=_aware(created),
        user_id=str(user) if user else None,
        provider=str(getattr(row, "provider", "") or ""),
        prompt_tokens=int(getattr(row, "prompt_tokens", 0) or 0),
        total_tokens=int(getattr(row, "total_tokens", 0) or 0),
        cache_read_input_tokens=int(getattr(row, "cache_read_input_tokens", 0) or 0),
        cost_usd=float(getattr(row, "cost_usd", 0) or 0),
    )
