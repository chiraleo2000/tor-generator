"""Flatten TOR section content for Rule Engine and LLM context."""

from __future__ import annotations

import json


def section_plain_text(content: str | None) -> str:
    raw = (content or "").strip()
    if not raw.startswith("{"):
        return raw
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(parsed, dict):
        return raw
    parts = [str(value).strip() for value in parsed.values() if str(value).strip()]
    return "\n\n".join(parts)
