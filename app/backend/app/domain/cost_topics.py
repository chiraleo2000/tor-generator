"""Extra analysis topics for budget, cost, personnel, and training.

These headings are observations about the TOR text. They are not a shared price
catalog and they do not change the three-part score. A baht figure is attached
only when the text asks for a rate that the rate PDF actually contains.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_SOURCE_NAME = "อัตราค่าจ้างที่ปรึกษา ประชาสัมพันธ์ อบรม .pdf"

_CORE: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("budget_estimate", "ประมาณงบประมาณ", re.compile(r"วงเงิน|งบประมาณ|บาท")),
    ("cost", "ต้นทุน", re.compile(r"ต้นทุน|ค่าใช้จ่าย")),
    ("personnel", "บุคลากร", re.compile(r"บุคลากร|ที่ปรึกษา|คณะทำงาน|ทีมงาน")),
    ("training", "ค่าอบรม", re.compile(r"อบรม|ฝึกอบรม|ถ่ายทอดความรู้")),
)
_RELATED: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("resources", "ทรัพยากร", re.compile(r"ทรัพยากร")),
    ("equipment", "อุปกรณ์", re.compile(r"อุปกรณ์")),
    ("procurement", "การจัดซื้อ", re.compile(r"จัดซื้อ|จัดจ้าง")),
)
_MEAL_ASK = re.compile(r"อาหาร|อาหารว่าง|เอกสาร")
_DEGREE_ASK = re.compile(r"ปริญญาโท|ป\.โท")
_YEAR_ASK = re.compile(r"(\d{1,2})\s*ปี")


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "consultant_training_rates.json"
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _quote(text: str, match: re.Match[str] | None) -> str:
    if match is None:
        return ""
    start = max(0, match.start() - 24)
    end = min(len(text), match.end() + 24)
    return " ".join(text[start:end].split())[:180]


def _training_rate_note(text: str) -> str:
    if _MEAL_ASK.search(text) is None:
        return ""
    training = _catalog().get("training")
    if not isinstance(training, dict):
        return ""
    domestic = training.get("domestic")
    if not isinstance(domestic, dict):
        return ""
    external = domestic.get("external")
    if not isinstance(external, dict):
        return ""
    food = external.get("food_per_day_complete")
    documents = external.get("documents_per_person_per_course")
    private_food = food.get("private") if isinstance(food, dict) else None
    private_docs = documents.get("private") if isinstance(documents, dict) else None
    if not isinstance(private_food, int) or not isinstance(private_docs, int):
        return ""
    return (
        f"ตาม {_SOURCE_NAME} การฝึกอบรมบุคคลภายนอกที่สถานที่เอกชน "
        f"อาหารเต็มวัน {private_food} บาท/วัน/คน และเอกสาร {private_docs} บาท/คน/หลักสูตร"
    )


def _personnel_rate_note(text: str) -> str:
    if _DEGREE_ASK.search(text) is None:
        return ""
    years_match = _YEAR_ASK.search(text)
    years = int(years_match.group(1)) if years_match else 2
    rows = _catalog().get("rows")
    if not isinstance(rows, list):
        return ""
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("degree") == "master"
        and row.get("experience_years") == years
        and isinstance(row.get("private_independent"), int)
    ]
    if not matches:
        return ""
    chosen = min(matches, key=lambda row: int(row["private_independent"]))
    group = str(chosen.get("group") or "").strip()
    amount = int(chosen["private_independent"])
    group_bit = f" กลุ่ม{group}" if group else ""
    return (
        f"ตาม {_SOURCE_NAME}{group_bit} ปริญญาโท อายุงาน {years} ปี "
        f"อัตราที่ปรึกษาไม่ได้ทำงานประจำในบริษัท {amount} บาทต่อเดือน"
    )


def _topic(
    topic_id: str,
    title: str,
    text: str,
    pattern: re.Pattern[str],
    *,
    rate_note: str = "",
) -> dict[str, str]:
    match = pattern.search(text)
    if match is None:
        return {
            "id": topic_id,
            "title": title,
            "status": "ไม่พบในข้อความ",
            "note": f"ข้อความยังไม่พูดถึง{title} จึงควรวิเคราะห์หัวข้อนี้เพิ่ม",
            "evidence": "",
            "rate_note": "",
        }
    note = f"ข้อความพูดถึง{title}"
    if rate_note:
        note = f"{note} {rate_note}"
    return {
        "id": topic_id,
        "title": title,
        "status": "พบในข้อความ",
        "note": note,
        "evidence": _quote(text, match),
        "rate_note": rate_note,
    }


def cost_analysis_topics(document_text: str) -> dict[str, Any]:
    """Analysis headings for budget, cost, personnel, training, and related items."""
    text = document_text or ""
    topics: list[dict[str, str]] = []
    for topic_id, title, pattern in _CORE:
        rate_note = ""
        if topic_id == "training":
            rate_note = _training_rate_note(text)
        elif topic_id == "personnel":
            rate_note = _personnel_rate_note(text)
        topics.append(_topic(topic_id, title, text, pattern, rate_note=rate_note))
    for topic_id, title, pattern in _RELATED:
        if pattern.search(text) is None:
            continue
        topics.append(_topic(topic_id, title, text, pattern))
    return {"topics": topics}
