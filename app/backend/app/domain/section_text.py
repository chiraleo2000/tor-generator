"""Flatten TOR section content for Rule Engine, LLM context, and export."""

from __future__ import annotations

from app.domain.section_fields import SECTION_FIELDS, parse_section_fields


def _blocks_from_known_fields(fields: dict, rows: list[tuple[str, str]]) -> list[str]:
    blocks: list[str] = []
    used: set[str] = set()
    for key, _label in rows:
        value = str(fields.get(key) or "").strip()
        if not value:
            continue
        blocks.append(value)
        used.add(key)
    for key, value in fields.items():
        if key in used or key == "body":
            continue
        text = str(value).strip()
        if text:
            blocks.append(text)
    return blocks


def _blocks_from_loose_fields(fields: dict) -> list[str]:
    parts = [
        str(value).strip()
        for key, value in fields.items()
        if key != "body" and str(value).strip()
    ]
    if parts:
        return parts
    body = str(fields.get("body") or "").strip()
    return [body] if body else []


def section_plain_text(content: str | None, section_key: str | None = None) -> str:
    raw = (content or "").strip()
    if not raw:
        return ""
    if not raw.startswith("{") and "### " not in raw:
        return raw
    fields = parse_section_fields(section_key or "", raw)
    if not fields:
        return raw
    rows = SECTION_FIELDS.get(section_key or "", [])
    blocks = (
        _blocks_from_known_fields(fields, rows)
        if rows
        else _blocks_from_loose_fields(fields)
    )
    return "\n\n".join(blocks) if blocks else raw
