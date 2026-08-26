"""Flatten TOR section content for Rule Engine, LLM context, and export."""

from __future__ import annotations

from app.domain.section_fields import SECTION_FIELDS, parse_section_fields


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
    if rows:
        blocks: list[str] = []
        used: set[str] = set()
        for key, label in rows:
            value = str(fields.get(key) or "").strip()
            if not value:
                continue
            blocks.append(f"{label}\n{value}")
            used.add(key)
        for key, value in fields.items():
            if key in used or key == "body":
                continue
            text = str(value).strip()
            if text:
                blocks.append(text)
        return "\n\n".join(blocks) if blocks else raw
    parts = [
        str(value).strip()
        for key, value in fields.items()
        if key != "body" and str(value).strip()
    ]
    if not parts and str(fields.get("body") or "").strip():
        parts = [str(fields["body"]).strip()]
    return "\n\n".join(parts) if parts else raw
