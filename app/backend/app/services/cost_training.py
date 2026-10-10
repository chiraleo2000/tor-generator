"""Cost worksheet and training-scope helpers for Phase 3 draft."""

from __future__ import annotations

from typing import Any

from app.domain.consultant_budget import (
    COST_LINE_KEYS,
    TRAINING_PART_KEYS,
    suggest_budget,
)
from app.domain.section_profile import profile_for_project

COST_WORKSHEET_KEY = "cost_worksheet"
TRAINING_SCOPE_KEY = "training_scope"
TRAINING_CATEGORIES = frozenset({"hire_develop", "buy_goods"})
TRAINING_SUB_KEY = "training"

COST_LINE_LABELS = {
    "personnel": "ทรัพยากรบุคคล",
    "equipment": "อุปกรณ์",
    "procurement": "การจัดซื้อจัดจ้าง",
    "consultant": "การจ้างที่ปรึกษา",
    "training": "ค่าอบรม",
}
TRAINING_PART_LABELS = {
    "food": "อาหาร",
    "snack": "อาหารว่าง",
    "documents": "เอกสาร",
    "venue": "สถานที่",
}
_LEGACY_LINE_KEYS = {
    "personnel": "labor",
    "equipment": "license",
    "procurement": "maintenance",
}

# Official median price fields — never copy worksheet totals into these.
ANNOUNCED_PRICE_KEYS = frozenset(
    {"announcedPrice", "announced_price", "ราคากลาง", "priceBasis", "price_basis"}
)

TRAINING_FIELD_KEYS = ("cohorts", "hours", "attendees", "documents")
TRAINING_FIELD_LABELS = {
    "cohorts": "จำนวนรุ่น",
    "hours": "จำนวนชั่วโมง",
    "attendees": "จำนวนผู้เข้าอบรม",
    "documents": "เอกสารส่งมอบ",
}


def _as_amount(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else 0.0
    text = str(value).replace(",", "").strip()
    try:
        amount = float(text)
    except ValueError:
        return 0.0
    return amount if amount >= 0 else 0.0


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def empty_cost_worksheet() -> dict[str, Any]:
    sheet: dict[str, Any] = dict.fromkeys((*COST_LINE_KEYS, *TRAINING_PART_KEYS), 0.0)
    sheet.update(
        {
            "total": 0.0,
            "is_announced_price": False,
            "label": "ใบประมาณการ — ไม่ใช่ราคากลาง",
        }
    )
    return sheet


def _line_amount(src: dict[str, Any], key: str) -> float:
    legacy = _LEGACY_LINE_KEYS.get(key)
    current = _as_amount(src.get(key))
    if current > 0 or legacy is None:
        return current
    return _as_amount(src.get(legacy))


def _part_amount(src: dict[str, Any], key: str) -> float:
    if _as_amount(src.get(key)) > 0 or key in src:
        direct = src.get(key)
        if direct not in (None, ""):
            return _as_amount(direct)
    parts = src.get("training_parts")
    if isinstance(parts, dict):
        return _as_amount(parts.get(key))
    return 0.0


def _apply_calculated_lines(src: dict[str, Any]) -> dict[str, Any]:
    years = src.get("years")
    if years == "":
        years = None
    sessions = src.get("sessions")
    suggested = suggest_budget(
        team_size=int(_as_amount(src.get("team_size"))),
        months=_as_amount(src.get("months") or 1) or 1,
        years=years,
        training_days=_as_amount(src.get("training_days")),
        day_part=str(src.get("day_part") or "full"),
        attendees=int(_as_amount(src.get("attendees"))),
        venue=str(src.get("venue_kind") or src.get("venue_type") or "private"),
        audience=str(src.get("audience") or "external"),
        sessions=None if sessions in (None, "") else int(_as_amount(sessions)),
        personnel_amount=_line_amount(src, "personnel"),
        equipment_amount=_line_amount(src, "equipment"),
        equipment_quantity=_as_amount(src.get("equipment_quantity")),
        equipment_unit_price=src.get("equipment_unit_price"),
        procurement_amount=_line_amount(src, "procurement"),
        procurement_quantity=_as_amount(src.get("procurement_quantity")),
        procurement_unit_price=src.get("procurement_unit_price"),
        profession=src.get("profession") if isinstance(src.get("profession"), str) else None,
    )
    merged = dict(src)
    for key in (*COST_LINE_KEYS, *TRAINING_PART_KEYS):
        merged[key] = suggested[key]
    return merged


def normalize_cost_worksheet(raw: Any) -> dict[str, Any]:
    """Officer-editable estimate. Never treat as official median price (ราคากลาง)."""
    src = dict(raw) if isinstance(raw, dict) else {}
    if src.get("apply_calculated"):
        src = _apply_calculated_lines(src)
    out = empty_cost_worksheet()
    for key in COST_LINE_KEYS:
        if key == "training":
            continue
        out[key] = _line_amount(src, key)
    for key in TRAINING_PART_KEYS:
        out[key] = _part_amount(src, key)
    part_sum = sum(out[key] for key in TRAINING_PART_KEYS)
    out["training"] = part_sum if part_sum > 0 else _line_amount(src, "training")
    out["total"] = sum(out[key] for key in COST_LINE_KEYS)
    out["is_announced_price"] = False
    out["label"] = "ใบประมาณการ — ไม่ใช่ราคากลาง"
    for banned in ANNOUNCED_PRICE_KEYS:
        out.pop(banned, None)
    return out


def cost_worksheet_of(analysis: Any) -> dict[str, Any]:
    data = analysis if isinstance(analysis, dict) else {}
    return normalize_cost_worksheet(data.get(COST_WORKSHEET_KEY))


def merge_cost_worksheet(analysis: Any, worksheet: Any) -> dict[str, Any]:
    merged = dict(analysis or {}) if isinstance(analysis, dict) else {}
    merged[COST_WORKSHEET_KEY] = normalize_cost_worksheet(worksheet)
    return merged


def empty_training_scope() -> dict[str, str]:
    return dict.fromkeys(TRAINING_FIELD_KEYS, "")


def normalize_training_scope(raw: Any) -> dict[str, str]:
    src = raw if isinstance(raw, dict) else {}
    return {key: _as_text(src.get(key)) for key in TRAINING_FIELD_KEYS}


def training_scope_of(analysis: Any) -> dict[str, str]:
    data = analysis if isinstance(analysis, dict) else {}
    return normalize_training_scope(data.get(TRAINING_SCOPE_KEY))


def merge_training_scope(analysis: Any, scope: Any) -> dict[str, Any]:
    merged = dict(analysis or {}) if isinstance(analysis, dict) else {}
    merged[TRAINING_SCOPE_KEY] = normalize_training_scope(scope)
    return merged


def category_has_training(project_type: str | None) -> bool:
    profile = profile_for_project(project_type)
    if profile.category not in TRAINING_CATEGORIES:
        return False
    return any(
        item.storage_key == TRAINING_SUB_KEY or item.semantic_key == "scope.training"
        for item in profile.scope_subsections
    )


def training_scope_prose(scope: Any, *, project_type: str | None = None) -> str:
    """Draft Thai training text from profile scope.training fields."""
    fields = normalize_training_scope(scope)
    profile = profile_for_project(project_type)
    hint = next(
        (
            item.hint
            for item in profile.scope_subsections
            if item.storage_key == TRAINING_SUB_KEY or item.semantic_key == "scope.training"
        ),
        "หลักสูตร จำนวนผู้เข้าอบรม จำนวนรุ่น สถานที่ และการที่คู่สัญญารับผิดชอบค่าใช้จ่ายทั้งหมด",
    )
    lines = [
        "การฝึกอบรมและการถ่ายทอดความรู้",
        hint,
    ]
    if fields["cohorts"]:
        lines.append(f"{TRAINING_FIELD_LABELS['cohorts']}: {fields['cohorts']} รุ่น")
    if fields["hours"]:
        lines.append(f"{TRAINING_FIELD_LABELS['hours']}: {fields['hours']} ชั่วโมง")
    if fields["attendees"]:
        lines.append(f"{TRAINING_FIELD_LABELS['attendees']}: {fields['attendees']} คน")
    if fields["documents"]:
        lines.append(f"{TRAINING_FIELD_LABELS['documents']}: {fields['documents']}")
    lines.append(
        "คู่สัญญารับผิดชอบค่าใช้จ่ายในการอบรมทั้งหมด และต้องแจ้งกำหนดล่วงหน้าเป็นลายลักษณ์อักษร"
    )
    return "\n".join(lines)


def persist_analysis_patch(project: Any, analysis: dict[str, Any]) -> None:
    """Write analysis_json without wiping callers that only have a mock project."""
    project.analysis_json = analysis
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(project, "analysis_json")
    except Exception:
        return
