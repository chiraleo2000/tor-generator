"""Assemble TOR rows into a review/export document without duplicate s4 keys."""

from __future__ import annotations

from typing import Any

from app.domain.section_text import section_plain_text
from app.domain.tor_sections import TOR_SECTION_LABELS


def _dotted_sub_key(sub: str) -> str | None:
    if sub.startswith("s") and "." in sub:
        return sub
    if sub[0:1].isdigit() and "." in sub:
        return f"s{sub}"
    return None


def _key_under_parent(parent: str, sub: str) -> str | None:
    if not parent or not (sub.startswith(f"{parent}.") or sub.startswith(parent)):
        return None
    if sub.startswith("s") or not sub[0:1].isdigit():
        return sub
    return f"s{sub}"


def document_section_key(section_key: str, sub_key: str | None) -> str:
    """Canonical document key: s4 parent, s4.1 for subsections (never s4.s4.1)."""
    parent = str(section_key or "").strip()
    sub = str(sub_key or "").strip()
    if not sub:
        return parent
    dotted = _dotted_sub_key(sub)
    if dotted is not None:
        return dotted
    under_parent = _key_under_parent(parent, sub)
    if under_parent is not None:
        return under_parent
    if sub[0:1].isdigit():
        return f"{parent}.{sub}" if parent else f"s{sub}"
    return f"{parent}.{sub}" if parent else sub


def assemble_review_document(sections: list[Any]) -> tuple[dict[str, str], dict[str, str]]:
    """Build (tor_document, parent_sections_map) for the Rule Engine and LLM review.

    Subsection rows use keys like s4.1. Parent map is never overwritten by a sub-row.
    """
    tor_document: dict[str, str] = {}
    sections_map: dict[str, str] = {}
    for section in sections:
        content = section_plain_text(
            getattr(section, "content", None) or "",
            str(getattr(section, "section_key", "") or "") or None,
        )
        if not str(content).strip():
            continue
        parent = str(getattr(section, "section_key", "") or "")
        sub = getattr(section, "sub_key", None)
        key = document_section_key(parent, sub)
        tor_document[key] = content
        if not sub:
            sections_map[parent] = content
    return tor_document, sections_map


def _scope_subsection_body(item: dict[str, Any]) -> str:
    chunks: list[str] = []
    for sub in item.get("subs") or []:
        sub_key = str(sub.get("key") or "")
        text = section_plain_text(sub.get("content") or "", sub_key)
        if not text:
            continue
        sub_title = str(sub.get("title") or "")
        chunks.append(f"{sub_key} {sub_title}\n{text}".strip())
    return "\n\n".join(chunks)


def _section_item_body(item: dict[str, Any], key: str) -> str:
    if key == "s4":
        return _scope_subsection_body(item)
    return section_plain_text(item.get("content") or item.get("content_preview") or "", key)


def plain_tor_from_section_items(items: list[dict[str, Any]]) -> str:
    """Join GET /sections payloads into heading + prose, including s4.1–s4.14.

    Parent s4 is often a short JSON field blob; real scope lives in ``subs``.
    """
    parts: list[str] = []
    for item in items:
        key = str(item.get("key") or "")
        title = str(item.get("title") or TOR_SECTION_LABELS.get(key) or key)
        body = _section_item_body(item, key)
        if body:
            parts.append(f"{key}. {title}\n{body}")
    return "\n\n".join(parts)
