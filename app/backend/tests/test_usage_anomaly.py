"""Anomaly rules, sweep, and process-level infra probe."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.usage.anomaly import (
    AnomalyLimits,
    UsageSample,
    detect_anomalies,
    detect_infra_anomalies,
    limits_from_settings,
    median,
    percentile,
    sample_from_mapping,
)
from app.usage.infra_status import probe_process_services
from app.usage.sweep import run_usage_sweep_once, usage_sweep_loop

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
LIMITS = AnomalyLimits(
    spike_multiplier=5,
    spike_floor_tokens=1000,
    burst_requests=3,
    burst_window_minutes=15,
    daily_cost_usd=10,
    cache_miss_prompt_tokens=100,
    admission_wait_p95_ms=1000,
)


def _sample(**overrides) -> UsageSample:
    payload = dict(
        created_at=NOW,
        user_id="user-1",
        provider="claude",
        prompt_tokens=10,
        total_tokens=10,
        cache_read_input_tokens=0,
        cost_usd=0.0,
    )
    payload.update(overrides)
    return UsageSample(**payload)


def test_median_percentile_and_limits_defaults():
    assert median([]) == 0
    assert median([1, 3, 9]) == 3
    assert median([1, 2, 3, 4]) == 2.5
    assert percentile([], 95) is None
    assert percentile([10, 20, 30], 95) == 30
    limits = limits_from_settings(SimpleNamespace())
    assert limits.burst_requests == 40
    assert sample_from_mapping(SimpleNamespace(created_at="nope")) is None
    mapped = sample_from_mapping(
        SimpleNamespace(
            created_at=NOW.replace(tzinfo=None),
            user_id=None,
            provider="gemini",
            prompt_tokens=4,
            total_tokens=5,
            cache_read_input_tokens=1,
            cost_usd=0.2,
        )
    )
    assert mapped is not None
    assert mapped.user_id is None
    assert mapped.provider == "gemini"


def test_spike_burst_cost_and_cache_rules():
    history = [
        _sample(created_at=NOW - timedelta(hours=index + 2), total_tokens=100, prompt_tokens=100)
        for index in range(4)
    ]
    spike = detect_anomalies(
        [*history, _sample(total_tokens=10_000, prompt_tokens=10_000)],
        set(),
        now=NOW,
        limits=LIMITS,
    )
    assert any(item.rule_id == "user_token_spike" for item in spike)

    quiet = detect_anomalies(
        [_sample(total_tokens=10, prompt_tokens=10)],
        set(),
        now=NOW,
        limits=LIMITS,
    )
    assert quiet == []

    burst = detect_anomalies(
        [_sample(created_at=NOW - timedelta(minutes=1), total_tokens=1) for _ in range(4)],
        set(),
        now=NOW,
        limits=LIMITS,
    )
    assert [item.rule_id for item in burst] == ["user_request_burst"]
    again = detect_anomalies(
        [_sample(created_at=NOW - timedelta(minutes=1), total_tokens=1) for _ in range(4)],
        {("user_request_burst", "user-1")},
        now=NOW,
        limits=LIMITS,
    )
    assert again == []

    cost = detect_anomalies(
        [_sample(cost_usd=11), _sample(created_at=NOW - timedelta(days=2), cost_usd=100)],
        set(),
        now=NOW,
        limits=LIMITS,
    )
    daily = [item for item in cost if item.rule_id == "global_cost_daily"]
    assert daily
    assert daily[0].detail["cost_usd"] == 11

    cache = detect_anomalies(
        [
            _sample(
                created_at=NOW - timedelta(hours=3),
                cache_read_input_tokens=20,
                prompt_tokens=20,
            ),
            _sample(prompt_tokens=500, cache_read_input_tokens=0, provider="bedrock"),
        ],
        set(),
        now=NOW,
        limits=LIMITS,
    )
    assert any(item.rule_id == "cache_miss_waste" for item in cache)
    no_prior = detect_anomalies(
        [_sample(prompt_tokens=500, provider="lm_studio")],
        set(),
        now=NOW,
        limits=LIMITS,
    )
    assert no_prior == []


def test_infra_rules_skip_open_alerts():
    down = detect_infra_anomalies(
        {"postgres": "down", "redis": "up"},
        [50, 5000],
        set(),
        now=NOW,
        limits=LIMITS,
    )
    assert {item.subject_key for item in down} == {"deps", "admission"}
    quiet = detect_infra_anomalies({"postgres": "up"}, [], {("infra_unhealthy", "deps")}, now=NOW)
    assert quiet == []


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _Session:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        self.committed = True

    async def execute(self, _stmt):
        return _Rows([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


class _Factory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


@pytest.mark.asyncio
async def test_sweep_skips_without_database(monkeypatch):
    monkeypatch.setattr("app.infra.session_factory", None)
    assert await run_usage_sweep_once() == 0


@pytest.mark.asyncio
async def test_sweep_persists_infra_alerts(monkeypatch):
    session = _Session()
    monkeypatch.setattr("app.infra.session_factory", _Factory(session))
    monkeypatch.setattr("app.infra.redis_client", None)

    async def services():
        return {"postgres": "down", "redis": "down"}

    async def waits(_redis):
        return [5000]

    monkeypatch.setattr("app.usage.sweep.probe_process_services", services)
    monkeypatch.setattr("app.usage.sweep.collect_waiting_ms", waits)
    monkeypatch.setattr("app.usage.sweep.limits_from_settings", lambda: LIMITS)
    created = await run_usage_sweep_once()
    assert created == 2
    assert session.committed is True
    assert {row.subject_key for row in session.added} == {"deps", "admission"}


@pytest.mark.asyncio
async def test_sweep_loop_survives_a_failure_then_stops():
    calls = {"n": 0}
    stop = asyncio.Event()

    async def once():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        stop.set()
        return 0

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("app.usage.sweep.run_usage_sweep_once", once)
    monkeypatch.setattr("app.usage.sweep._interval_seconds", lambda: 0.01)
    try:
        await usage_sweep_loop(stop)
    finally:
        monkeypatch.undo()
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_process_probe_marks_each_dependency(monkeypatch):
    monkeypatch.setattr("app.infra.session_factory", None)
    monkeypatch.setattr("app.infra.redis_client", None)
    monkeypatch.setattr("app.infra.minio_client", None)
    monkeypatch.setattr("app.infra.mongo_client", None)
    monkeypatch.setattr("app.infra.neo4j_driver", None)
    down = await probe_process_services()
    assert set(down.values()) == {"down"}

    class Redis:
        async def ping(self):
            return True

    class Mongo:
        def __init__(self, fail: bool) -> None:
            self.fail = fail
            self.admin = self

        def command(self, _name):
            if self.fail:
                raise RuntimeError("mongo")
            return {"ok": 1}

    class Neo4j:
        def __init__(self, fail: bool) -> None:
            self.fail = fail

        async def verify_connectivity(self):
            if self.fail:
                raise RuntimeError("neo")

    class BoomRedis:
        async def ping(self):
            raise RuntimeError("redis")

    monkeypatch.setattr("app.infra.session_factory", object())
    monkeypatch.setattr("app.infra.redis_client", Redis())
    monkeypatch.setattr("app.infra.minio_client", object())
    monkeypatch.setattr("app.infra.mongo_client", Mongo(False))
    monkeypatch.setattr("app.infra.neo4j_driver", Neo4j(False))
    up = await probe_process_services()
    assert set(up.values()) == {"up"}

    monkeypatch.setattr("app.infra.redis_client", BoomRedis())
    monkeypatch.setattr("app.infra.mongo_client", Mongo(True))
    monkeypatch.setattr("app.infra.neo4j_driver", Neo4j(True))
    mixed = await probe_process_services()
    assert mixed["redis"] == "down"
    assert mixed["mongo"] == "down"
    assert mixed["neo4j"] == "down"
    assert mixed["postgres"] == "up"
