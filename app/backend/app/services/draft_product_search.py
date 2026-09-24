"""Draft-chat product/vendor search using the shared web_search client."""

from __future__ import annotations

import re
from typing import Any

PRODUCT_SEARCH_RE = re.compile(
    r"(สเปก|spec(?:ification)?s?|คุณลักษณะเฉพาะ|"
    r"ผู้ขาย|ผู้จำหน่าย|vendor|ยี่ห้อ|ผลิตภัณฑ์|แคตตาล[อ็]ก|catalog|"
    r"ค้นหาสินค้า|หาสเปก|เปรียบเทียบรุ่น)",
    re.IGNORECASE,
)
INSERT_CONFIRM_RE = re.compile(
    r"(ยืนยันแทรก|แทรกแหล่ง|ยืนยัน.*แหล่งค้นหา|insert.?search)",
    re.IGNORECASE,
)

SEARCH_DISCLAIMER = (
    "แหล่งอ้างอิงเท่านั้น ไม่ใช่สเปกที่ผูกยี่ห้อ "
    "เจ้าหน้าที่ต้องยืนยันก่อนแทรกลง TOR และเขียนเชิงหน้าที่การงาน"
)

INSERT_HEADER = (
    "ข้อมูลอ้างอิงจากแหล่งออนไลน์ "
    "(ไม่ใช่สเปกที่ผูกยี่ห้อ — ใช้ประกอบการเขียนคุณลักษณะเชิงหน้าที่การงานเท่านั้น)"
)


def is_product_search_query(message: str) -> bool:
    return bool(PRODUCT_SEARCH_RE.search(message or ""))


def is_insert_search_confirm(message: str) -> bool:
    return bool(INSERT_CONFIRM_RE.search(message or ""))


def _hit_field(item: Any, *names: str) -> str:
    if isinstance(item, dict):
        for name in names:
            value = item.get(name)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""
    for name in names:
        value = getattr(item, name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_search_hits(raw: Any) -> list[dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in rows:
        title = _hit_field(item, "title", "name")
        url = _hit_field(item, "url", "link", "href")
        snippet = _hit_field(item, "snippet", "content", "description")
        if not (title or url or snippet):
            continue
        key = url or title
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": title, "url": url, "snippet": snippet})
    return out


async def run_product_search(query: str) -> list[dict[str, str]]:
    """Call the shared search_web client. Results are reference-only."""
    from app.services.web_search import search_web

    raw = await search_web(query)
    return normalize_search_hits(raw)


def format_search_reference(hits: Any, *, query: str = "") -> str:
    rows = normalize_search_hits(hits)
    lines = [INSERT_HEADER]
    if query.strip():
        lines.append(f"คำค้น: {query.strip()}")
    if not rows:
        lines.append("ไม่พบแหล่งอ้างอิงที่เลือก")
        return "\n".join(lines)
    for index, hit in enumerate(rows, start=1):
        title = hit["title"] or "แหล่งอ้างอิง"
        url = hit["url"]
        snippet = hit["snippet"]
        lines.append(f"{index}. {title}")
        if url:
            lines.append(f"   {url}")
        if snippet:
            lines.append(f"   {snippet}")
    lines.append(
        "ห้ามคัดลอกชื่อผลิตภัณฑ์หรือยี่ห้อข้างต้นเป็นคุณลักษณะเฉพาะที่ผูกยี่ห้อ"
    )
    return "\n".join(lines)
