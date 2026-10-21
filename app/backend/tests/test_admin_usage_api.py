"""Admin usage endpoints: auth, aggregates, alerts, pricing, and infra."""

from __future__ import annotations

import fnmatch
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.llm_usage import LlmUsageEvent, UsageAlert
from app.models.user import User
from app.usage.aggregate import bucket_timeseries, filter_events, paginate, parse_range, summarize
from app.usage.cost import TokenRate
from app.usage.infra_status import admission_snapshot, ai_rate_snapshot
from app.usage.store import replace_pricing_rates, sort_alerts

NOW = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)


def _user(role: str) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user.role = role
    user.email = f"{role}@example.go.th"
    return user


def _rows(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _event(**overrides) -> LlmUsageEvent:
    payload = dict(
        created_at=datetime.now(timezone.utc),
        user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        request_id="req",
        task="draft",
        provider="claude",
        model="claude-sonnet",
        latency_ms=12,
        prompt_tokens=1000,
        completion_tokens=200,
        total_tokens=1200,
        cache_creation_input_tokens=100,
        cache_read_input_tokens=400,
        tokens_estimated=False,
        cost_usd=0.5,
        status="ok",
        error=None,
    )
    payload.update(overrides)
    return LlmUsageEvent(**payload)


class _Redis:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.values = {"rate:user:ai:1": "4"}
        self.lists = {
            "llm:admit:llm:waiters": ["a"],
            "llm:admit:shared:waiters": [],
            "llm:admit:embedding:waiters": ["e"],
        }
        self.hashes = {"llm:admit:req:a": {"status": "waiting", "waiting_ms": "150000"}}

    async def ping(self):
        return True

    async def get(self, key):
        if self.fail:
            raise RuntimeError("redis")
        return self.values.get(key)

    async def llen(self, key):
        if self.fail:
            raise RuntimeError("redis")
        return len(self.lists.get(key, []))

    async def hgetall(self, key):
        return self.hashes.get(key, {})

    async def scan_iter(self, match=None):
        if self.fail:
            raise RuntimeError("redis")
        for key in [*self.values, *self.hashes]:
            if match is None or fnmatch.fnmatch(key, match):
                yield key


@pytest.fixture
def admin_client():
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None
    app.state.mongo = None
    app.state.neo4j = None

    async def override_user():
        return _user("admin")

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _db(rows):
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_rows(rows))
    session.commit = AsyncMock()
    session.add = MagicMock()

    async def override():
        yield session

    app.dependency_overrides[get_db] = override
    return session


def test_summary_timeseries_and_events(admin_client):
    other = _event(provider="gemini", model="gemini", task="chat", total_tokens=10, cost_usd=0.1)
    _db([_event(), other])
    summary = admin_client.get("/api/v1/admin/usage/summary")
    assert summary.status_code == 200
    data = summary.json()["data"]
    assert data["requests"] == 2
    assert data["prompt_tokens"] == 2000
    assert data["completion_tokens"] == 400
    assert data["cache_read_input_tokens"] == 800
    assert data["cost_usd"] == 0.6

    series = admin_client.get(
        "/api/v1/admin/usage/timeseries",
        params={"grain": "day", "start": "not-a-date"},
    )
    assert series.status_code == 200
    assert series.json()["data"]["grain"] == "day"

    events = admin_client.get(
        "/api/v1/admin/usage/events",
        params={"provider": "claude", "limit": 1},
    )
    assert events.status_code == 200
    body = events.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["model"] == "claude-sonnet"
    assert body["items"][0]["prompt_tokens"] == 1000


def test_officer_is_forbidden(admin_client):
    async def officer():
        return _user("officer")

    app.dependency_overrides[get_current_user] = officer
    response = admin_client.get("/api/v1/admin/usage/summary")
    assert response.status_code == 403


def test_alerts_ack_and_missing(admin_client):
    open_alert = UsageAlert(
        id=uuid.uuid4(),
        rule_id="user_token_spike",
        subject_key="user-1",
        title="การใช้โทเคนสูงผิดปกติ",
        severity="critical",
        detail={"tokens_last_hour": 5},
        created_at=NOW,
    )
    closed = UsageAlert(
        id=uuid.uuid4(),
        rule_id="global_cost_daily",
        subject_key="org",
        title="ค่าใช้จ่ายวันนี้เกินงบ",
        severity="critical",
        detail={},
        created_at=NOW - timedelta(hours=1),
        acknowledged_at=NOW,
    )
    session = _db([])
    session.execute = AsyncMock(return_value=_rows([closed, open_alert]))
    listed = admin_client.get("/api/v1/admin/usage/alerts")
    assert listed.status_code == 200
    payload = listed.json()["data"]
    assert payload["open_count"] == 1
    assert payload["items"][0]["rule_id"] == "user_token_spike"

    session.get = AsyncMock(return_value=open_alert)
    acked = admin_client.post(f"/api/v1/admin/usage/alerts/{open_alert.id}/ack")
    assert acked.status_code == 200
    assert acked.json()["data"]["open"] is False

    session.get = AsyncMock(return_value=None)
    missing = admin_client.post(f"/api/v1/admin/usage/alerts/{uuid.uuid4()}/ack")
    assert missing.status_code == 404


def test_pricing_round_trip_and_negative_rejection(admin_client):
    _db([])
    listed = admin_client.get("/api/v1/admin/usage/pricing")
    assert listed.status_code == 200
    providers = {row["provider"] for row in listed.json()["data"]["rates"]}
    assert "lm_studio" in providers
    assert "*" in providers

    rejected = admin_client.put(
        "/api/v1/admin/usage/pricing",
        json={"rates": [{"provider": "claude", "model": "*", "input_per_million": -1}]},
    )
    assert rejected.status_code == 400

    saved = admin_client.put(
        "/api/v1/admin/usage/pricing",
        json={
            "rates": [
                {
                    "provider": "Claude",
                    "model": "custom",
                    "input_per_million": 1,
                    "output_per_million": 2,
                    "cache_write_per_million": 3,
                    "cache_read_per_million": 4,
                }
            ]
        },
    )
    assert saved.status_code == 200
    row = saved.json()["data"]["rates"][0]
    assert row["provider"] == "claude"
    assert row["input_per_million"] == 1


def test_infra_snapshot_with_redis_and_failure(admin_client, monkeypatch):
    monkeypatch.setattr(app.state, "redis", _Redis())
    monkeypatch.setattr(app.state, "db_engine", None)
    monkeypatch.setattr(app.state, "minio", None)
    monkeypatch.setattr(app.state, "mongo", None)
    monkeypatch.setattr(app.state, "neo4j", None)
    response = admin_client.get("/api/v1/admin/usage/infra")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["services"]["redis"] == "up"
    assert data["services"]["postgres"] == "down"
    assert data["rate_limit"]["highest_count"] == 4
    assert data["admission"]["waiting"] == 1
    assert data["admission"]["wait_p95_ms"] == 150000

    monkeypatch.setattr(app.state, "redis", _Redis(fail=True))
    failed = admin_client.get("/api/v1/admin/usage/infra")
    assert failed.status_code == 200
    assert failed.json()["data"]["rate_limit"]["redis"] == "down"
    assert failed.json()["data"]["admission"]["waiting"] is None


@pytest.mark.asyncio
async def test_aggregate_edges_and_rate_helpers():
    start, end = parse_range("2026-10-22T00:00:00Z", "2026-10-21T00:00:00Z", now=NOW)
    assert start < end
    fallback_start, _fallback_end = parse_range(None, "not-a-date", now=NOW, default_hours=2)
    assert fallback_start < NOW
    kept = _event(created_at=NOW)
    dropped = _event(
        provider="gemini",
        task="chat",
        user_id=uuid.uuid4(),
        created_at=NOW - timedelta(days=3),
    )
    selected = filter_events(
        [kept, dropped, SimpleEvent()],
        provider="claude",
        task="draft",
        user_id=str(kept.user_id),
        start=NOW - timedelta(hours=1),
        end=NOW,
    )
    assert selected == [kept]
    page, total = paginate(selected, 0, -5)
    assert total == 1
    assert page == [kept]
    summary = summarize([kept], start=NOW - timedelta(hours=2), end=NOW)
    assert summary["calls_per_hour"] == 0.5
    assert summary["by_user"][0]["key"] == str(kept.user_id)
    buckets = bucket_timeseries(
        [kept, SimpleEvent()],
        start=NOW - timedelta(days=1),
        end=NOW,
        grain="day",
    )
    assert sum(bucket["requests"] for bucket in buckets) == 1
    assert (await ai_rate_snapshot(None))["redis"] == "down"
    assert (await admission_snapshot(None))["waiting"] is None
    weird = _Redis()
    weird.values["rate:user:ai:1"] = "nope"
    snap = await ai_rate_snapshot(weird)
    assert snap["active_keys"] == 1
    assert snap["highest_count"] == 0

    class Session:
        def __init__(self):
            self.added = []

        async def execute(self, _stmt):
            return _rows([])

        def add(self, row):
            self.added.append(row)

        async def commit(self):
            return None

    stored = await replace_pricing_rates(Session(), [TokenRate("openai", "*", 1, 2, 0, 0)])
    assert stored[0].provider == "openai"
    closed = UsageAlert(
        rule_id="x",
        subject_key="y",
        title="t",
        severity="warn",
        created_at=NOW,
        acknowledged_at=NOW,
    )
    open_row = UsageAlert(
        rule_id="x",
        subject_key="z",
        title="t",
        severity="warn",
        created_at=NOW,
    )
    assert sort_alerts([closed, open_row])[0] is open_row


class SimpleEvent:
    created_at = None
    provider = "claude"
    task = "draft"
    user_id = None
    prompt_tokens = "bad"
    completion_tokens = None
    cache_creation_input_tokens = None
    cache_read_input_tokens = None
    total_tokens = "bad"
    cost_usd = "bad"
    model = ""
