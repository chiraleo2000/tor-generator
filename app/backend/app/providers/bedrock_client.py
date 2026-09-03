"""Shared Bedrock Runtime client (IAM keys or Bedrock API bearer token)."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


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
