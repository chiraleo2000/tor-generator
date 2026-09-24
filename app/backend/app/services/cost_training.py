"""Cost worksheet and training-scope helpers for Phase 3 draft."""

from __future__ import annotations

from typing import Any

from app.domain.section_profile import profile_for_project

COST_WORKSHEET_KEY = "cost_worksheet"
TRAINING_SCOPE_KEY = "training_scope"
TRAINING_CATEGORIES = frozenset({"hire_develop", "buy_goods"})
TRAINING_SUB_KEY = "training"

COST_LINE_KEYS = ("license", "labor", "maintenance", "training")
COST_LINE_LABELS = {
    "license": "ค่าลิขสิทธิ์",
    "labor": "ค่าแรง",
    "maintenance": "ค่าบำรุงรักษา",
    "training": "ค่าอบรม",
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
    return {
        "license": 0.0,
        "labor": 0.0,
        "maintenance": 0.0,
        "training": 0.0,
        "total": 0.0,
        "is_announced_price": False,
        "label": "ใบประมาณการ — ไม่ใช่ราคากลาง",
    }


def normalize_cost_worksheet(raw: Any) -> dict[str, Any]:
    """Officer-editable estimate. Never treat as official median price (ราคากลาง)."""
    src = raw if isinstance(raw, dict) else {}
    out = empty_cost_worksheet()
    for key in COST_LINE_KEYS:
        out[key] = _as_amount(src.get(key))
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
