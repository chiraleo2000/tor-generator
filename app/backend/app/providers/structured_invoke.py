"""Invoke an LLM with a JSON schema and retry once on parse failure."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)


def _as_object(payload: Any, schema: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    properties = schema.get("properties") if isinstance(schema, dict) else None
    if isinstance(payload, list) and isinstance(properties, dict) and "suggestions" in properties:
        return {"suggestions": payload}
    return None


def _parse_structured_payload(text: str) -> Any:
    array_at = text.find("[")
    object_at = text.find("{")
    if array_at >= 0 and (object_at < 0 or array_at < object_at):
        end = text.rfind("]")
        if end <= array_at:
            raise ValueError("LLM did not return JSON")
        parsed = json.loads(text[array_at : end + 1])
        if not isinstance(parsed, list):
            raise ValueError("LLM JSON was not an array")
        return parsed
    from app.rag.graph_extract import parse_json_lenient

    return parse_json_lenient(text)


async def invoke_with_schema(
    llm: LLMProvider,
    messages: list[dict],
    schema: dict[str, Any],
    schema_name: str,
    *,
    attempts: int = 2,
    **kwargs: Any,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        call_messages = list(messages)
        if attempt > 1:
            call_messages.append(
                {
                    "role": "user",
                    "content": "ตอบเป็น JSON object ตาม schema เท่านั้น ห้ามข้อความนำหรือท้าย",
                }
            )
        response = await llm.invoke(
            call_messages,
            json_schema=schema,
            json_schema_name=schema_name,
            disable_thinking=True,
            **kwargs,
        )
        try:
            parsed = _parse_structured_payload(response.content or "")
        except (ValueError, TypeError) as exc:
            last_error = exc
            logger.warning(
                "structured JSON parse failed (%s) attempt %s/%s",
                schema_name,
                attempt,
                attempts,
            )
            continue
        payload = _as_object(parsed, schema)
        if payload is not None:
            return payload
        last_error = ValueError("LLM JSON was not an object")
    raise ValueError(f"{schema_name} did not return valid JSON") from last_error
