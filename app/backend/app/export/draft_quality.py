"""Repeatable TOR draft quality metrics (style, leaks, emptiness, depth)."""

from __future__ import annotations

import re
from typing import Any

from app.services.thai_draft import (
    BANNED_ENGLISH_TOKENS,
    INTAKE_WRAPPER_RE,
    SEPARATOR_ROW_RE,
    detect_unauthorized_english,
)

SCAFFOLD_LEAKS = (
    "ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม",
    "ปัญหาที่พบ (ระบุตัวเลข/สถิติ)",
    "### history",
    "### problems",
    "### policy",
    "### workKind",
)

MARKDOWN_HEADING_RE = re.compile(r"(?m)^(?:#{1,6}\s+|\*\*[^*\n]+\*\*)")
BOLD_IN_HEADING_RE = re.compile(r"(?m)^\s*[\d๐-๙.]+\s+[^\n]*\*\*")

TYPE_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "hire_develop": (
        "ผู้ขาย",
        "จัดซื้อครุภัณฑ์/ฮาร์ดแวร์",
        "งานจัดซื้อครุภัณฑ์",
    ),
}


def scaffold_leaks(text: str) -> list[str]:
    return [item for item in SCAFFOLD_LEAKS if item in (text or "")]


def filename_leaks(text: str) -> list[str]:
    blob = text or ""
    found = [str(item) for item in INTAKE_WRAPPER_RE.findall(blob)]
    if "===== ไฟล์" in blob:
        found.append("file_banner")
    return found


def markdown_separator_leaks(text: str) -> list[str]:
    """Flag `| --- |` rows that are not part of a markdown table (no header above)."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    for index, line in enumerate(lines):
        if not SEPARATOR_ROW_RE.match(line):
            continue
        prev = lines[index - 1].strip() if index else ""
        if not prev.startswith("|"):
            return ["orphan_markdown_separator"]
    return []


def type_forbidden_hits(text: str, category: str | None = None) -> list[str]:
    blob = text or ""
    banned = TYPE_FORBIDDEN.get(category or "", ())
    return [token for token in banned if token in blob]


def markdown_heading_leaks(text: str) -> list[str]:
    found: list[str] = []
    blob = text or ""
    if BOLD_IN_HEADING_RE.search(blob):
        found.append("bold_in_numbered_heading")
    if "**" in blob.split("\n", 1)[0] if blob else False:
        found.append("bold_in_first_line")
    if MARKDOWN_HEADING_RE.search(blob):
        found.append("markdown_heading")
    return found


def empty_sections(draft_chars: dict[str, Any]) -> list[str]:
    empty: list[str] = []
    for key, value in (draft_chars or {}).items():
        try:
            length = int(value)
        except (TypeError, ValueError):
            length = len(str(value or ""))
        if length <= 0:
            empty.append(str(key))
    return empty


def score_draft_text(
    text: str,
    *,
    draft_chars: dict[str, Any] | None = None,
    gold_headings: list[str] | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    blob = text or ""
    english = detect_unauthorized_english(blob)
    banned_hits = [
        token
        for token in BANNED_ENGLISH_TOKENS
        if re.search(rf"(?i)(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", blob)
    ]
    missing_gold = [
        heading for heading in gold_headings or [] if heading and heading not in blob
    ]
    chars = draft_chars or {}
    return {
        "chars": len(blob),
        "unauthorized_english": english,
        "unauthorized_english_count": len(english),
        "banned_english": banned_hits,
        "scaffold": scaffold_leaks(blob),
        "filename_leak": filename_leaks(blob),
        "markdown_leak": markdown_heading_leaks(blob),
        "markdown_separator": markdown_separator_leaks(blob),
        "type_forbidden": type_forbidden_hits(blob, category),
        "section_empty": empty_sections(chars),
        "has_arabic_heading": "1. ความเป็นมา" in blob,
        "has_thai_heading": "๑. ความเป็นมา" in blob or "ความเป็นมา" in blob,
        "has_payment_table": "งวดที่" in blob and "ร้อยละ" in blob,
        "missing_gold_headings": missing_gold,
    }


def score_fixture_report(report: dict[str, Any]) -> dict[str, Any]:
    """Score a SKK-style JSON report (old_tor4 / new_export / draft_chars)."""
    export = report.get("new_export") or {}
    sample = str(export.get("sample") or "")
    joined = "\n".join(
        str(report.get(key) or "")
        for key in ("s1_sample", "s8_sample", "s5_sample", "s11_sample")
    )
    body = sample or joined
    metrics = score_draft_text(
        body,
        draft_chars=report.get("draft_chars") or {},
    )
    metrics["draft_english"] = list(report.get("draft_english") or [])
    metrics["export_chars"] = export.get("chars")
    metrics["export_english"] = list(export.get("english") or [])
    metrics["old_chars"] = (report.get("old_tor4") or {}).get("chars")
    return metrics
