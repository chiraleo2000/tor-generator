"""Assemble TOR rows into a review/export document without duplicate s4 keys."""

from __future__ import annotations

from typing import Any

from app.domain.section_text import section_plain_text


def document_section_key(section_key: str, sub_key: str | None) -> str:
    """Canonical document key: s4 parent, s4.1 for subsections (never s4.s4.1)."""
    parent = str(section_key or "").strip()
    sub = str(sub_key or "").strip()
    if not sub:
        return parent
    if sub.startswith("s") and "." in sub:
        return sub
    if sub[0:1].isdigit() and "." in sub:
        return f"s{sub}"
    if parent and (sub.startswith(f"{parent}.") or sub.startswith(parent)):
        if sub.startswith("s"):
            return sub
        if sub[0:1].isdigit():
            return f"s{sub}"
        return sub
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
