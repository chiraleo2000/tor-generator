"""Optional Tavily / Brave web search. Fail-open when search is unavailable."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
KNOWN_PROVIDERS = frozenset({"tavily", "brave"})
DEFAULT_TARGET_RESULTS = 8
HARD_MIN_RESULTS = 5
HARD_MAX_RESULTS = 10
JSON_MEDIA = "application/json"


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str
    snippet: str
    published: str | None = None


def clamp_result_limit(
    limit: int | None,
    *,
    min_results: int = HARD_MIN_RESULTS,
    max_results: int = HARD_MAX_RESULTS,
) -> int:
    """Default target 8, always clamp to the 5–10 window (and settings min/max)."""
    target = DEFAULT_TARGET_RESULTS if limit is None else int(limit)
    lo = max(HARD_MIN_RESULTS, int(min_results or HARD_MIN_RESULTS))
    hi = min(HARD_MAX_RESULTS, int(max_results or HARD_MAX_RESULTS))
    if lo > hi:
        lo, hi = HARD_MIN_RESULTS, HARD_MAX_RESULTS
    return max(lo, min(hi, target))


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.rstrip("/")
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def _dedupe_sources(sources: list[WebSource]) -> list[WebSource]:
    seen: set[str] = set()
    unique: list[WebSource] = []
    for source in sources:
        key = _normalize_url(source.url)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def _parse_tavily(payload: Any) -> list[WebSource]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("results")
    if not isinstance(items, list):
        return []
    sources: list[WebSource] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        sources.append(
            WebSource(
                title=str(item.get("title") or "").strip(),
                url=url,
                snippet=str(item.get("content") or item.get("snippet") or "").strip(),
                published=_opt_str(item.get("published_date") or item.get("published")),
            )
        )
    return sources


def _parse_brave(payload: Any) -> list[WebSource]:
    if not isinstance(payload, dict):
        return []
    web = payload.get("web")
    items = web.get("results") if isinstance(web, dict) else None
    if not isinstance(items, list):
        return []
    sources: list[WebSource] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        sources.append(
            WebSource(
                title=str(item.get("title") or "").strip(),
                url=url,
                snippet=str(item.get("description") or item.get("snippet") or "").strip(),
                published=_opt_str(item.get("page_age") or item.get("age")),
            )
        )
    return sources


async def _search_tavily(
    query: str, *, api_key: str, count: int, deadline_seconds: float
) -> list[WebSource]:
    headers = {
        "Accept": JSON_MEDIA,
        "Content-Type": JSON_MEDIA,
        "Authorization": f"Bearer {api_key}",
    }
    payload = {"query": query, "max_results": count}
    async with asyncio.timeout(deadline_seconds):
        async with httpx.AsyncClient() as client:
            client.timeout = httpx.Timeout(deadline_seconds)
            response = await client.post(TAVILY_SEARCH_URL, json=payload, headers=headers)
            response.raise_for_status()
            return _parse_tavily(response.json())


async def _search_brave(
    query: str, *, api_key: str, count: int, deadline_seconds: float
) -> list[WebSource]:
    headers = {
        "Accept": JSON_MEDIA,
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": count}
    async with asyncio.timeout(deadline_seconds):
        async with httpx.AsyncClient() as client:
            client.timeout = httpx.Timeout(deadline_seconds)
            response = await client.get(BRAVE_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            return _parse_brave(response.json())


async def search_web(query: str, *, limit: int | None = None) -> list[WebSource]:
    """Search the public web. Returns [] when search is off, unknown, or unkeyed."""
    settings = get_settings()
    enabled = bool(getattr(settings, "web_search_enabled", True))
    provider = str(getattr(settings, "web_search_provider", "tavily") or "").strip().lower()
    api_key = str(getattr(settings, "web_search_api_key", "") or "").strip()
    if not enabled or not api_key or provider not in KNOWN_PROVIDERS:
        return []

    count = clamp_result_limit(
        limit,
        min_results=int(getattr(settings, "web_search_min_results", HARD_MIN_RESULTS) or HARD_MIN_RESULTS),
        max_results=int(getattr(settings, "web_search_max_results", HARD_MAX_RESULTS) or HARD_MAX_RESULTS),
    )
    deadline_seconds = float(getattr(settings, "web_search_timeout_seconds", 20.0) or 20.0)
    try:
        if provider == "tavily":
            sources = await _search_tavily(
                query, api_key=api_key, count=count, deadline_seconds=deadline_seconds
            )
        else:
            sources = await _search_brave(
                query, api_key=api_key, count=count, deadline_seconds=deadline_seconds
            )
    except Exception:
        logger.warning("web search request failed provider=%s", provider)
        return []
    return _dedupe_sources(sources)[:count]
