"""Unit tests for the optional Tavily / Brave web search client."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.web_search import (
    BRAVE_SEARCH_URL,
    HARD_MAX_RESULTS,
    HARD_MIN_RESULTS,
    TAVILY_SEARCH_URL,
    WebSource,
    clamp_result_limit,
    search_web,
)


def _settings(**overrides: object) -> SimpleNamespace:
    values = {
        "web_search_enabled": True,
        "web_search_provider": "tavily",
        "web_search_api_key": "test-key",
        "web_search_min_results": 5,
        "web_search_max_results": 10,
        "web_search_timeout_seconds": 20,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _mock_async_client(*, response: MagicMock | None = None, get=None, post=None):
    client = AsyncMock()
    client.get = get or AsyncMock(return_value=response)
    client.post = post or AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def _json_response(payload: object) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    ("limit", "expected"),
    [
        (None, 8),
        (8, 8),
        (1, 5),
        (4, 5),
        (5, 5),
        (10, 10),
        (20, 10),
    ],
)
def test_clamp_result_limit_is_five_to_ten(limit: int | None, expected: int) -> None:
    assert clamp_result_limit(limit) == expected


@pytest.mark.asyncio
async def test_empty_api_key_returns_empty_without_http() -> None:
    client = _mock_async_client(response=_json_response({"results": []}))
    with (
        patch("app.services.web_search.get_settings", return_value=_settings(web_search_api_key="")),
        patch("app.services.web_search.httpx.AsyncClient", return_value=client) as http_cls,
    ):
        assert await search_web("จัดซื้อจัดจ้าง") == []
    http_cls.assert_not_called()


@pytest.mark.asyncio
async def test_disabled_or_unknown_provider_returns_empty_without_http() -> None:
    client = _mock_async_client(response=_json_response({"results": []}))
    with (
        patch(
            "app.services.web_search.get_settings",
            return_value=_settings(web_search_enabled=False),
        ),
        patch("app.services.web_search.httpx.AsyncClient", return_value=client) as http_cls,
    ):
        assert await search_web("ระเบียบพัสดุ") == []
    http_cls.assert_not_called()

    with (
        patch(
            "app.services.web_search.get_settings",
            return_value=_settings(web_search_provider="bing"),
        ),
        patch("app.services.web_search.httpx.AsyncClient", return_value=client) as http_cls,
    ):
        assert await search_web("ระเบียบพัสดุ") == []
    http_cls.assert_not_called()


@pytest.mark.asyncio
async def test_tavily_parses_results_and_dedupes_urls() -> None:
    payload = {
        "results": [
            {
                "title": "พ.ร.บ. การจัดซื้อจัดจ้าง",
                "url": "https://example.go.th/prb-2560",
                "content": "มาตรา 1",
                "published_date": "2017-02-24",
            },
            {
                "title": "สำเนาซ้ำ",
                "url": "https://example.go.th/prb-2560/",
                "content": "ซ้ำ",
            },
            {
                "title": "ระเบียบกระทรวงการคลัง",
                "url": "https://example.go.th/regulation-2560",
                "snippet": "ข้อ 21",
            },
        ]
    }
    client = _mock_async_client(response=_json_response(payload))
    with (
        patch("app.services.web_search.get_settings", return_value=_settings()),
        patch("app.services.web_search.httpx.AsyncClient", return_value=client),
    ):
        sources = await search_web("พ.ร.บ. จัดซื้อจัดจ้าง")

    assert [source.url for source in sources] == [
        "https://example.go.th/prb-2560",
        "https://example.go.th/regulation-2560",
    ]
    assert sources[0] == WebSource(
        title="พ.ร.บ. การจัดซื้อจัดจ้าง",
        url="https://example.go.th/prb-2560",
        snippet="มาตรา 1",
        published="2017-02-24",
    )
    assert sources[1].snippet == "ข้อ 21"
    posted = client.post.await_args
    assert posted.args[0] == TAVILY_SEARCH_URL
    assert posted.kwargs["json"]["max_results"] == 8
    assert posted.kwargs["json"]["query"] == "พ.ร.บ. จัดซื้อจัดจ้าง"


@pytest.mark.asyncio
async def test_brave_parses_web_results() -> None:
    payload = {
        "web": {
            "results": [
                {
                    "title": "คู่มือการจัดซื้อ",
                    "url": "https://example.go.th/manual",
                    "description": "ขั้นตอนประกาศ",
                    "page_age": "2024-01-15",
                },
                {
                    "title": "ไม่มี URL",
                    "description": "ข้าม",
                },
            ]
        }
    }
    client = _mock_async_client(response=_json_response(payload))
    with (
        patch(
            "app.services.web_search.get_settings",
            return_value=_settings(web_search_provider="brave"),
        ),
        patch("app.services.web_search.httpx.AsyncClient", return_value=client),
    ):
        sources = await search_web("คู่มือจัดซื้อ", limit=6)

    assert len(sources) == 1
    assert sources[0] == WebSource(
        title="คู่มือการจัดซื้อ",
        url="https://example.go.th/manual",
        snippet="ขั้นตอนประกาศ",
        published="2024-01-15",
    )
    requested = client.get.await_args
    assert requested.args[0] == BRAVE_SEARCH_URL
    assert requested.kwargs["params"]["q"] == "คู่มือจัดซื้อ"
    assert requested.kwargs["params"]["count"] == 6


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "expected_count"),
    [(1, 5), (20, 10), (None, 8)],
)
async def test_request_count_clamped_to_five_through_ten(
    limit: int | None, expected_count: int
) -> None:
    results = [
        {
            "title": f"แหล่ง {index}",
            "url": f"https://example.go.th/{index}",
            "content": f"snippet {index}",
        }
        for index in range(12)
    ]
    client = _mock_async_client(response=_json_response({"results": results}))
    with (
        patch("app.services.web_search.get_settings", return_value=_settings()),
        patch("app.services.web_search.httpx.AsyncClient", return_value=client),
    ):
        sources = await search_web("วงเงิน", limit=limit)

    assert client.post.await_args.kwargs["json"]["max_results"] == expected_count
    assert HARD_MIN_RESULTS <= len(sources) <= HARD_MAX_RESULTS
    assert len(sources) == expected_count
