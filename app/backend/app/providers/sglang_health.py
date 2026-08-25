"""Cached health probe for the SGLang OpenAI-compatible server."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 20.0
_cache_at: float = 0.0
_cache_ok: bool = False


def health_url_from_openai_base(base_url: str) -> str:
    cleaned = (base_url or "").rstrip("/")
    if cleaned.endswith("/v1"):
        cleaned = cleaned[:-3]
    return f"{cleaned.rstrip('/')}/health"


def clear_sglang_health_cache() -> None:
    global _cache_at, _cache_ok
    _cache_at = 0.0
    _cache_ok = False


def probe_sglang_health_sync(base_url: str) -> bool:
    """Return True when SGLang /health responds. Cache both outcomes briefly."""
    global _cache_at, _cache_ok
    now = time.monotonic()
    if _cache_at and now - _cache_at < _CACHE_TTL_SEC:
        return _cache_ok
    url = health_url_from_openai_base(base_url)
    try:
        import httpx

        response = httpx.get(url, timeout=1.0)
        ok = response.status_code < 500
    except Exception:
        logger.debug("SGLang health probe failed for %s", url)
        ok = False
    _cache_at = now
    _cache_ok = ok
    return ok
