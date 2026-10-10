"""Consultant and training budget figures taken only from the rate catalog.

The local model must not invent these numbers. ``suggest_budget`` reads
``consultant_training_rates.json``, which was parsed from the Bureau of the
Budget rate PDF. A cell that could not be checked against the printed markup
was left out of that file.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("consultant_training_rates.json")

COST_LINE_KEYS = ("personnel", "equipment", "procurement", "consultant", "training")
TRAINING_PART_KEYS = ("food", "snack", "documents", "venue")
PRIVATE_COLUMNS = (
    "private_independent",
    "private_firm_no_evidence",
    "private_firm_evidence_1",
    "private_firm_evidence_2",
    "private_firm_evidence_3",
)

DEGREE_ALIASES = {
    "master": "master",
    "doctorate": "doctorate",
    "bachelor": "bachelor",
    "ป.โท": "master",
    "ป.เอก": "doctorate",
    "ป.ตรี": "bachelor",
    "ปริญญาโท": "master",
    "ปริญญาเอก": "doctorate",
    "ปริญญาตรี": "bachelor",
    "โท": "master",
    "เอก": "doctorate",
    "ตรี": "bachelor",
}
DEGREE_LABELS = {
    "master": "ปริญญาโท",
    "doctorate": "ปริญญาเอก",
    "bachelor": "ปริญญาตรี",
}

_MEAL_RE = re.compile(r"อาหาร(?!ว่าง)\s*(\d+)\s*มื้อ|(\d+)\s*มื้ออาหาร(?!ว่าง)")
_SNACK_RE = re.compile(r"อาหารว่าง\s*(\d+)\s*มื้อ|(\d+)\s*มื้ออาหารว่าง")
_HALF_DAY_RE = re.compile(r"ครึ่งวัน")
_FULL_DAY_RE = re.compile(r"เต็มวัน|ทั้งเช้าและบ่าย")
_CONSULTANT_RE = re.compile(r"จ้างที่ปรึกษา|ค่าที่ปรึกษา|ค่าจ้างที่ปรึกษา")
_TRAINING_RE = re.compile(r"ค่าอบรม|ฝึกอบรม|การอบรม")
_DOCUMENT_RE = re.compile(r"ค่าเอกสาร|เอกสารประกอบ|เอกสารการอบรม|เอกสารสำหรับผู้เข้า|เอกสารทุกครั้ง")
_GOV_RATE_RE = re.compile(
    r"(ข้าราชการ|บุคลากรของรัฐ|บุคลากรภาครัฐ|บุคลากรในหน่วยงานของรัฐ|สถาบันของรัฐ)"
    r".{0,80}(อัตรา|ค่าจ้าง|ค่าตอบแทน|เป็นค่าเริ่มต้น)"
    r"|(อัตรา|ค่าจ้างที่ปรึกษา|ค่าตอบแทนที่ปรึกษา).{0,80}"
    r"(ข้าราชการ|บุคลากรของรัฐ|บุคลากรภาครัฐ|สถาบันของรัฐ)",
    re.DOTALL,
)
_AGENCY_VENUE_RE = re.compile(
    r"(อบรม|ฝึกอบรม|สัมมนา).{0,80}(สถานที่ของหน่วยงาน|สถานที่ราชการ|ห้องประชุมของหน่วยงาน)"
    r"|(สถานที่ของหน่วยงาน|สถานที่ราชการ|ห้องประชุมของหน่วยงาน).{0,80}(อบรม|ฝึกอบรม|สัมมนา)",
    re.DOTALL,
)
_FIVE_CATEGORIES = (
    "ทรัพยากรบุคคล",
    "อุปกรณ์",
    "การจัดซื้อจัดจ้าง",
    "การจ้างที่ปรึกษา",
    "ค่าอบรม",
)

_REPLACE_CONSULTANT = (
    "ให้เพิ่มหมวดการจ้างที่ปรึกษาในใบประมาณการ โดยจัดทีมสลับวุฒิปริญญาโทแล้วปริญญาเอก "
    "ใช้อัตราภาคเอกชน ไม่ใช้ข้าราชการ บุคลากรในหน่วยงานของรัฐ หรือสถาบันของรัฐ "
    "หากไม่ได้กำหนดอายุงานให้ใช้ 2 ปี และเลือกแถวที่เข้าเงื่อนไขแล้วมีราคาต่ำสุด"
)
_REPLACE_TRAINING = (
    "ให้เพิ่มหมวดค่าอบรมโดยแยกค่าอาหาร ค่าอาหารว่าง ค่าเอกสาร และค่าสถานที่ "
    "สถานที่อบรมให้เป็นโรงแรมหรือสถานที่เอกชนเป็นค่าเริ่มต้น "
    "ครึ่งวันเช้าหรือครึ่งวันบ่ายคิดอาหาร 1 มื้อและอาหารว่าง 1 มื้อ "
    "เต็มวันทั้งเช้าและบ่ายคิดอาหาร 2 มื้อและอาหารว่าง 2 มื้อ "
    "และมีเอกสารทุกครั้งตามจำนวนผู้เข้าอบรม"
)
_REPLACE_PRIVATE = (
    "ให้ใช้อัตราค่าจ้างที่ปรึกษาภาคเอกชนเป็นค่าเริ่มต้น ไม่ใช้ข้าราชการ "
    "บุคลากรในหน่วยงานของรัฐ หรือสถาบันของรัฐ "
    "จัดทีมสลับวุฒิปริญญาโทแล้วปริญญาเอก "
    "หากไม่ได้กำหนดอายุงานให้ใช้ 2 ปี โดยเลือกแถวที่เข้าเงื่อนไขแล้วมีราคาต่ำสุด"
)
_REPLACE_VENUE = (
    "ให้กำหนดสถานที่อบรมเป็นโรงแรมหรือสถานที่เอกชนเป็นค่าเริ่มต้น "
    "ไม่ใช้สถานที่ของหน่วยงานเป็นค่าเริ่มต้น "
    "การใช้สถานที่เอกชนไม่ให้ตั้งค่าเช่าสถานที่หรือห้องประชุมเพิ่ม "
    "และให้ใช้อัตราค่าอาหารกับค่าอาหารว่างในคอลัมน์สถานที่เอกชน"
)
_REPLACE_MEALS = (
    "ครึ่งวันเช้าหรือครึ่งวันบ่ายให้คิดอาหาร 1 มื้อและอาหารว่าง 1 มื้อ "
    "เต็มวันทั้งเช้าและบ่ายให้คิดอาหาร 2 มื้อและอาหารว่าง 2 มื้อ"
)
_REPLACE_DOCUMENTS = "ให้กำหนดค่าเอกสารทุกครั้งตามจำนวนผู้เข้าอบรม"
_REPLACE_EVALUATION = (
    "หัวข้อประเมินงบประมาณในเกณฑ์คัดเลือกข้อเสนอต้องตรวจว่าวงเงินครอบห้าหมวด "
    "ได้แก่ ทรัพยากรบุคคล อุปกรณ์ การจัดซื้อจัดจ้าง การจ้างที่ปรึกษา และค่าอบรม "
    "และเป็นไปตามกฎวุฒิที่สลับปริญญาโทกับปริญญาเอก อัตราภาคเอกชน "
    "อายุงานที่กำหนดหรือ 2 ปีหากไม่ได้กำหนด สถานที่โรงแรมหรือเอกชน "
    "และจำนวนมื้ออาหารให้ตรงกับครึ่งวันหรือเต็มวัน"
)


@lru_cache(maxsize=1)
def load_rate_catalog() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _baht(value: float) -> int:
    return int(math.floor(float(value) + 0.5))


def _amount(value: Any) -> float:
    if value is None or value == "" or isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else 0.0
    try:
        parsed = float(str(value).replace(",", "").strip())
    except ValueError:
        return 0.0
    return parsed if parsed >= 0 else 0.0


def _optional_price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return _amount(value)


def _experience_years(years: Any) -> float:
    """Unspecified experience uses 2 years. Non-positive values do too."""
    if years is None or years == "":
        return 2.0
    try:
        number = float(years)
    except (TypeError, ValueError):
        return 2.0
    if number <= 0:
        return 2.0
    return number


def _degree_code(value: Any, index: int) -> str:
    text = str(value or "").strip()
    if text in DEGREE_ALIASES:
        return DEGREE_ALIASES[text]
    return "master" if index % 2 == 0 else "doctorate"


def _normalize_degree_name(value: Any) -> str | None:
    text = str(value or "").strip()
    return DEGREE_ALIASES.get(text)


def _venue_key(venue: Any) -> str:
    text = str(venue or "")
    if any(word in text for word in ("ราชการ", "หน่วยงาน", "government", "agency")):
        return "government"
    return "private"


def _audience_key(audience: Any) -> str:
    text = str(audience or "external").strip()
    aliases = {
        "external": "external",
        "บุคคลภายนอก": "external",
        "civil_type_a": "civil_type_a",
        "ประเภท ก": "civil_type_a",
        "civil_type_b": "civil_type_b",
        "ประเภท ข": "civil_type_b",
    }
    return aliases.get(text, "external")


def _day_counts(day_part: Any) -> tuple[int, int]:
    """Return (meals, snacks) for one training day."""
    text = str(day_part or "full").strip().lower()
    if any(word in text for word in ("full", "เต็ม", "ทั้งเช้า")):
        return 2, 2
    if any(word in text for word in ("half", "ครึ่ง", "morning", "afternoon", "เช้า", "บ่าย")):
        return 1, 1
    return 2, 2


def _row_matches_years(row: dict[str, Any], years: float) -> bool:
    if years > 30:
        return row.get("experience_label") == ">30"
    experience = row.get("experience_years")
    if not isinstance(experience, int):
        return False
    return experience >= math.ceil(years - 1e-9)


def _quote(row: dict[str, Any], sector: str) -> tuple[str, int] | None:
    if sector == "state":
        value = row.get("state_institution")
        if isinstance(value, int):
            return "state_institution", value
        return None
    best: tuple[str, int] | None = None
    for column in PRIVATE_COLUMNS:
        value = row.get(column)
        if isinstance(value, int) and (best is None or value < best[1]):
            best = (column, value)
    return best


def _select_row(
    rows: list[dict[str, Any]],
    *,
    degree: str,
    years: float,
    sector: str,
    profession: str | None,
) -> tuple[dict[str, Any], str, int] | None:
    matches: list[tuple[int, int, dict[str, Any], str]] = []
    for row in rows:
        if row.get("degree") != degree:
            continue
        if profession and profession not in str(row.get("group") or ""):
            continue
        if not _row_matches_years(row, years):
            continue
        quoted = _quote(row, sector)
        if quoted is None:
            continue
        column, price = quoted
        experience = row.get("experience_years")
        sort_year = experience if isinstance(experience, int) else 99
        matches.append((price, sort_year, row, column))
    if not matches:
        return None
    matches.sort(key=lambda item: (item[0], item[1]))
    price, _, row, column = matches[0]
    return row, column, price


def _people(
    team_size: int,
    consultants: list[dict[str, Any]] | None,
    years: float,
) -> list[dict[str, Any]]:
    if consultants:
        people: list[dict[str, Any]] = []
        for index, item in enumerate(consultants):
            people.append(
                {
                    "degree": _degree_code(item.get("degree"), index),
                    "years": _experience_years(item.get("years", years)),
                    "months": _amount(item.get("months") or 1) or 1,
                    "count": max(int(_amount(item.get("count") or 1)), 1),
                    "profession": item.get("profession") or item.get("group"),
                }
            )
        return people
    return [
        {
            "degree": _degree_code(None, index),
            "years": years,
            "months": 1,
            "count": 1,
            "profession": None,
        }
        for index in range(max(team_size, 0))
    ]


def _priced_line(amount: Any, quantity: Any, unit_price: Any) -> tuple[int, str | None]:
    price = _optional_price(unit_price)
    qty = _amount(quantity)
    if price is None:
        note = None
        if qty > 0 and _amount(amount) == 0:
            note = "ไม่มีราคาในเอกสารอัตรา จึงไม่ใส่ราคาตลาด ใช้จำนวนที่เจ้าหน้าที่กรอกเมื่อมีราคาต่อหน่วย"
        return _baht(_amount(amount)), note
    return _baht(qty * price), None


def _training_block(audience: str) -> dict[str, Any]:
    domestic = load_rate_catalog()["training"]["domestic"]
    block = domestic.get(audience) or domestic["external"]
    return block


_BUDGET_DEFAULTS: dict[str, Any] = {
    "team_size": 0,
    "months": 1,
    "years": None,
    "sector": "private",
    "profession": None,
    "consultants": None,
    "training_days": 0,
    "day_part": "full",
    "attendees": 0,
    "audience": "external",
    "venue": "private",
    "sessions": None,
    "personnel_amount": 0,
    "equipment_amount": 0,
    "equipment_quantity": 0,
    "equipment_unit_price": None,
    "procurement_amount": 0,
    "procurement_quantity": 0,
    "procurement_unit_price": None,
}

_BUDGET_ASSUMPTIONS = (
    "จัดทีมสลับวุฒิปริญญาโทแล้วปริญญาเอก",
    "ค่าเริ่มต้นเป็นอัตราภาคเอกชนราคาต่ำสุด และไม่ใช้สถาบันของรัฐหรือบุคลากรภาครัฐ",
    "หากไม่ได้กำหนดอายุงาน ใช้ 2 ปี และเลือกแถวที่เข้าเงื่อนไขแล้วราคาต่ำสุด",
    "สถานที่อบรมค่าเริ่มต้นเป็นโรงแรมหรือสถานที่เอกชน",
    "เอกสารอัตราไม่ให้ตั้งค่าเช่าสถานที่หรือห้องประชุมเมื่อใช้สถานที่เอกชน จึงไม่ใส่ราคาเช่าสถานที่",
    "ครึ่งวันเช้าหรือครึ่งวันบ่ายคืออาหาร 1 มื้อกับอาหารว่าง 1 มื้อ",
    "เต็มวันทั้งเช้าและบ่ายคืออาหาร 2 มื้อกับอาหารว่าง 2 มื้อ",
    "ค่าอาหารใช้เพดานรายวันจากเอกสารอัตรา ค่าอาหารว่างคูณตามจำนวนมื้อ",
    "เอกสารคิดทุกครั้งตามจำนวนผู้เข้าอบรม",
)


def _budget_request(fields: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(fields) - set(_BUDGET_DEFAULTS))
    if unknown:
        names = ", ".join(unknown)
        raise TypeError(f"suggest_budget() got an unexpected keyword argument '{names}'")
    request = dict(_BUDGET_DEFAULTS)
    request.update(fields)
    return request


def _sector_name(sector: str) -> str:
    if sector in {"state", "government", "สถาบันของรัฐ"}:
        return "state"
    return "private"


def _person_profession(person: dict[str, Any], fallback: str | None) -> str | None:
    named = person.get("profession")
    if named:
        return str(named)
    return fallback


def _quote_person(
    rows: list[dict[str, Any]],
    index: int,
    person: dict[str, Any],
    month_count: float,
    use_sector: str,
    profession: str | None,
) -> dict[str, Any] | None:
    degree = _normalize_degree_name(person["degree"]) or _degree_code(None, index)
    person_years = _experience_years(person["years"])
    selected = _select_row(
        rows,
        degree=degree,
        years=person_years,
        sector=use_sector,
        profession=_person_profession(person, profession),
    )
    if selected is None:
        return None
    row, column, monthly = selected
    person_months = _amount(person["months"]) or month_count
    count = int(person["count"])
    amount = _baht(monthly * person_months * count)
    experience = row.get("experience_years")
    recorded_years = experience if isinstance(experience, int) else person_years
    return {
        "index": index + 1,
        "degree": degree,
        "degree_label": DEGREE_LABELS[degree],
        "years": recorded_years,
        "experience_label": row.get("experience_label"),
        "sector": use_sector,
        "column": column,
        "group": row.get("group"),
        "monthly_rate": monthly,
        "state_rate": row.get("state_institution"),
        "months": person_months,
        "count": count,
        "amount": amount,
        "file_page": row.get("file_page"),
    }


def _consultant_lines(
    rows: list[dict[str, Any]],
    people: list[dict[str, Any]],
    month_count: float,
    use_sector: str,
    profession: str | None,
) -> tuple[list[dict[str, Any]], int]:
    lines: list[dict[str, Any]] = []
    total = 0
    for index, person in enumerate(people):
        quoted = _quote_person(rows, index, person, month_count, use_sector, profession)
        if quoted is None:
            continue
        total += int(quoted["amount"])
        lines.append(quoted)
    return lines, total


def _scaled_baht(unit: float, left: float, right: float) -> int:
    if not left or not right:
        return 0
    return _baht(unit * left * right)


def _training_quote(request: dict[str, Any]) -> dict[str, Any]:
    venue_name = _venue_key(request["venue"])
    audience_name = _audience_key(request["audience"])
    meals, snacks = _day_counts(request["day_part"])
    days = _amount(request["training_days"])
    headcount = max(int(_amount(request["attendees"])), 0)
    sessions = request["sessions"]
    times = days if sessions is None else _amount(sessions)
    block = _training_block(audience_name)
    food_key = "food_per_day_complete" if meals >= 2 else "food_per_day_incomplete"
    food_unit = int(block[food_key][venue_name])
    snack_unit = int(block["snack_per_meal"][venue_name])
    document_unit = int(block["documents_per_person_per_course"][venue_name])
    food = _scaled_baht(food_unit, headcount, days)
    snack = _scaled_baht(float(snack_unit) * float(snacks), headcount, days)
    documents = _scaled_baht(document_unit, headcount, times)
    venue_amount = 0
    return {
        "food": food,
        "snack": snack,
        "documents": documents,
        "venue": venue_amount,
        "total": food + snack + documents + venue_amount,
        "meal_count": meals,
        "snack_count": snacks,
        "venue_key": venue_name,
        "audience": audience_name,
        "food_basis": food_key,
    }


def _budget_assumptions(equipment_note: str | None, procurement_note: str | None) -> list[str]:
    notes = list(_BUDGET_ASSUMPTIONS)
    if equipment_note:
        notes.append("อุปกรณ์: " + equipment_note)
    if procurement_note:
        notes.append("การจัดซื้อจัดจ้าง: " + procurement_note)
    return notes


def suggest_budget(**fields: Any) -> dict[str, Any]:
    """Calculate a five-category worksheet from the rate catalog.

    Defaults: alternate master's then doctorate, private-sector column with the
    lowest rate (not a state institution), 2 years when experience is omitted,
    and a hotel or private venue. Half a day is 1 meal and 1 snack. A full day
    is 2 meals and 2 snacks. Documents are charged on every occurrence per attendee.
    """
    return _suggest_budget(_budget_request(fields))


def _suggest_budget(request: dict[str, Any]) -> dict[str, Any]:
    catalog = load_rate_catalog()
    target_years = _experience_years(request["years"])
    use_sector = _sector_name(str(request["sector"]))
    month_count = _amount(request["months"]) or 1
    people = _people(int(_amount(request["team_size"])), request["consultants"], target_years)
    lines, consultant_total = _consultant_lines(
        catalog["rows"],
        people,
        month_count,
        use_sector,
        request["profession"] if isinstance(request["profession"], str) else None,
    )
    training = _training_quote(request)
    equipment, equipment_note = _priced_line(
        request["equipment_amount"],
        request["equipment_quantity"],
        request["equipment_unit_price"],
    )
    procurement, procurement_note = _priced_line(
        request["procurement_amount"],
        request["procurement_quantity"],
        request["procurement_unit_price"],
    )
    personnel = _baht(_amount(request["personnel_amount"]))
    total = personnel + equipment + procurement + consultant_total + int(training["total"])
    return {
        "personnel": personnel,
        "equipment": equipment,
        "procurement": procurement,
        "consultant": consultant_total,
        "training": training["total"],
        "food": training["food"],
        "snack": training["snack"],
        "documents": training["documents"],
        "venue": training["venue"],
        "total": total,
        "consultants": lines,
        "meal_count": training["meal_count"],
        "snack_count": training["snack_count"],
        "venue_key": training["venue_key"],
        "audience": training["audience"],
        "sector": use_sector,
        "years": target_years,
        "food_basis": training["food_basis"],
        "assumptions": _budget_assumptions(equipment_note, procurement_note),
        "locked": True,
    }


def _finding(
    rule_id: str,
    severity: str,
    message: str,
    suggestion: str,
    evidence: str,
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "suggestion": suggestion,
        "evidence": evidence,
    }


def _evidence(text: str, match: re.Match[str] | None, fallback: str) -> str:
    if match is None:
        return fallback
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 40)
    return text[start:end].strip() or fallback


def _ints(pattern: re.Pattern[str], text: str) -> list[int]:
    numbers: list[int] = []
    for groups in pattern.findall(text):
        if isinstance(groups, str):
            numbers.append(int(groups))
            continue
        for group in groups:
            if group:
                numbers.append(int(group))
    return numbers


def _numbers_outside(numbers: list[int], allowed: set[int]) -> bool:
    return any(number not in allowed for number in numbers)


def _sentence_meal_mismatch(sentence: str) -> bool:
    half = _HALF_DAY_RE.search(sentence) is not None
    full = _FULL_DAY_RE.search(sentence) is not None
    meals = _ints(_MEAL_RE, sentence)
    snacks = _ints(_SNACK_RE, sentence)
    if half and full:
        return _numbers_outside(meals, {1, 2}) or _numbers_outside(snacks, {1, 2})
    if half:
        return _numbers_outside(meals, {1}) or _numbers_outside(snacks, {1})
    if full:
        return _numbers_outside(meals, {2}) or _numbers_outside(snacks, {2})
    return False


def _meal_mismatch_evidence(text: str) -> str:
    sentences = re.split(r"[\n\r]+", text)
    for sentence in sentences:
        if _sentence_meal_mismatch(sentence):
            return sentence.strip()[:180]
    return ""


def budget_rule_findings(document_text: str) -> list[dict]:
    """Shared budget findings for draft review and TOR analysis.

    Each item has rule_id, severity, message, suggestion, and evidence.
    ``suggestion`` is replacement text an officer can paste into the TOR.
    """
    text = document_text or ""
    if len(text.strip()) < 20:
        return []
    findings: list[dict[str, str]] = []
    if _CONSULTANT_RE.search(text) is None:
        findings.append(
            _finding(
                "missing_consultant_category",
                "suggestion",
                "เอกสารยังไม่มีหมวดการจ้างที่ปรึกษา",
                _REPLACE_CONSULTANT,
                "(ไม่พบหมวดการจ้างที่ปรึกษาในเอกสาร)",
            )
        )
    if _TRAINING_RE.search(text) is None:
        findings.append(
            _finding(
                "missing_training_category",
                "suggestion",
                "เอกสารยังไม่มีหมวดค่าอบรม",
                _REPLACE_TRAINING,
                "(ไม่พบหมวดค่าอบรมในเอกสาร)",
            )
        )
    government = _GOV_RATE_RE.search(text)
    if government is not None:
        findings.append(
            _finding(
                "government_staff_default",
                "warning",
                "เอกสารใช้อัตราบุคลากรภาครัฐหรือสถาบันของรัฐเป็นค่าเริ่มต้น",
                _REPLACE_PRIVATE,
                _evidence(text, government, ""),
            )
        )
    venue = _AGENCY_VENUE_RE.search(text)
    if venue is not None:
        findings.append(
            _finding(
                "agency_venue",
                "warning",
                "เอกสารใช้สถานที่ของหน่วยงานเป็นสถานที่อบรม",
                _REPLACE_VENUE,
                _evidence(text, venue, ""),
            )
        )
    meal_evidence = _meal_mismatch_evidence(text)
    if meal_evidence:
        findings.append(
            _finding(
                "training_meal_mismatch",
                "warning",
                "จำนวนมื้ออาหารไม่ตรงกับครึ่งวันหรือเต็มวัน",
                _REPLACE_MEALS,
                meal_evidence,
            )
        )
    if _TRAINING_RE.search(text) is not None and _DOCUMENT_RE.search(text) is None:
        findings.append(
            _finding(
                "missing_training_documents",
                "suggestion",
                "มีการอบรมแต่ยังไม่กำหนดเอกสารตามจำนวนผู้เข้าอบรม",
                _REPLACE_DOCUMENTS,
                "(ไม่พบค่าเอกสารตามจำนวนผู้เข้าอบรม)",
            )
        )
    if re.search(r"เกณฑ์", text) and not all(name in text for name in _FIVE_CATEGORIES):
        findings.append(
            _finding(
                "evaluation_budget_coverage",
                "suggestion",
                "หัวข้อประเมินงบประมาณยังไม่ตรวจว่าวงเงินครอบห้าหมวดและเป็นไปตามกฎอัตรา",
                _REPLACE_EVALUATION,
                "(เกณฑ์การพิจารณาไม่ระบุห้าหมวดงบประมาณ)",
            )
        )
    return findings
