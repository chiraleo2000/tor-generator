"""Shared Bedrock Runtime client (IAM keys or Bedrock API bearer token)."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_THROTTLE_MARKERS = ("throttlingexception", "throttling", "toomanyrequests")
_TIMEOUT_TYPE_MARKERS = (
    "readtimeouterror",
    "connecttimeouterror",
    "endpointconnectionerror",
    "connectionclosederror",
)
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BASE_DELAY = 0.4


def _error_code(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict):
            return str(error.get("Code") or "")
    return str(getattr(exc, "error_code", "") or "")


def _normalized_error_tokens(exc: BaseException) -> str:
    name = type(exc).__name__
    code = _error_code(exc)
    return f"{name} {code}".lower().replace("_", "").replace(" ", "")


def is_bedrock_throttle(exc: BaseException) -> bool:
    blob = _normalized_error_tokens(exc)
    return any(marker in blob for marker in _THROTTLE_MARKERS)


def is_bedrock_short_timeout(exc: BaseException) -> bool:
    """Retry connect blips only. A read timeout is a long generation stall, not a short retry."""
    name = type(exc).__name__.lower().replace("_", "")
    if name == "readtimeouterror":
        return False
    if name in _TIMEOUT_TYPE_MARKERS:
        return True
    if type(exc) is TimeoutError:
        return False
    text = str(exc).lower()
    if "read timeout" in text:
        return False
    return "connect timeout" in text


def is_bedrock_retryable(exc: BaseException) -> bool:
    return is_bedrock_throttle(exc) or is_bedrock_short_timeout(exc)


def call_bedrock_with_retry(
    operation: Callable[[], T],
    *,
    model_id: str,
    op: str,
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
) -> T:
    """Retry Bedrock calls on throttle / short I/O timeouts. Never logs secrets."""
    attempts = max(1, int(max_attempts))
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            last = exc
            if not is_bedrock_retryable(exc) or attempt >= attempts:
                raise
            code = _error_code(exc)
            logger.warning(
                "Bedrock %s retry %s/%s model_id=%s error_class=%s%s",
                op,
                attempt,
                attempts,
                model_id,
                type(exc).__name__,
                f" error_code={code}" if code else "",
            )
            time.sleep(base_delay * (2 ** (attempt - 1)))
    assert last is not None
    raise last


def bedrock_runtime_client(
    *,
    region: str,
    aws_access_key_id: str = "",
    aws_secret_access_key: str = "",
    bearer_token: str = "",
) -> Any:
    """Build a bedrock-runtime client without logging credential values."""
    import boto3

    token = (bearer_token or os.environ.get("AWS_BEARER_TOKEN_BEDROCK") or "").strip()
    if token:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = token
    kwargs: dict[str, Any] = {"region_name": region}
    if aws_access_key_id and aws_secret_access_key:
        kwargs["aws_access_key_id"] = aws_access_key_id
        kwargs["aws_secret_access_key"] = aws_secret_access_key
    client = boto3.client("bedrock-runtime", **kwargs)
    if not token:
        return client

    def _add_bearer(request: Any, **_kwargs: Any) -> None:
        request.headers["Authorization"] = f"Bearer {token}"

    client.meta.events.register("before-sign.bedrock-runtime.*", _add_bearer)
    logger.info("Bedrock client using API bearer token in region %s", region)
    return client
