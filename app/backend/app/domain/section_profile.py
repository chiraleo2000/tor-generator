"""Section_Profile — type-aware TOR structure (single source of truth).

Wraps ``tor_taxonomy`` (semantic keys) and maps to storage keys used by
``tor_sections`` rows (s1–s13, s15–s17, scope sub_keys without the ``scope.`` prefix).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from app.domain import tor_taxonomy as tax

SCHEMA_VERSION = 2

PROCUREMENT_CATEGORY_ORDER: list[str] = [
    "hire_develop",
    "hire_maintain",
    "lease_service",
    "buy_goods",
    "construction",
    "hire_consult",
    "hire_service",
]

PROCUREMENT_CATEGORY_LABELS: dict[str, str] = {
    "hire_develop": "จ้างพัฒนาระบบ",
    "hire_maintain": "จ้างบำรุงรักษา (MA)",
    "lease_service": "เช่าบริการ/สื่อสาร",
    "buy_goods": "จัดซื้อครุภัณฑ์/ฮาร์ดแวร์",
    "construction": "งานปรับปรุง/ก่อสร้าง",
    "hire_consult": "จ้างที่ปรึกษา/สำรวจ/วิเคราะห์",
    "hire_service": "จ้างเหมาบริการงานเอกสาร",
}

LEGACY_TYPE_MAP: dict[str, str] = {
    "it": "hire_develop",
    "it_dev": "hire_develop",
    "it_ma": "hire_maintain",
    "goods": "buy_goods",
    "construction": "construction",
    "consulting": "hire_consult",
    "general": "buy_goods",
    "hire_develop": "hire_develop",
    "hire_maintain": "hire_maintain",
    "lease_service": "lease_service",
    "buy_goods": "buy_goods",
    "hire_consult": "hire_consult",
    "hire_service": "hire_service",
}

SEMANTIC_TO_STORAGE: dict[str, str] = {
    "background": "s1",
    "objective": "s2",
    "qualification": "s3",
    "scope": "s4",
    "schedule": "s5",
    "budget": "s6",
    "location": "s7",
    "payment": "s8",
    "warranty": "s9",
    "penalty": "s10",
    "evaluation": "s11",
    "documents": "s12",
    "other_conditions": "s13",
    "ip_ownership": "s15",
    "confidentiality": "s16",
    "responsible_unit": "s17",
}

STORAGE_TO_SEMANTIC: dict[str, str] = {value: key for key, value in SEMANTIC_TO_STORAGE.items()}

LEGAL_REQUIRED_SEMANTIC: frozenset[str] = frozenset(
    {
        "background",
        "objective",
        "qualification",
        "scope",
        "schedule",
        "budget",
        "location",
        "payment",
        "evaluation",
        "other_conditions",
    }
)

# Headings that must never appear as a required As-Is scope chip.
CURRENT_SYSTEM_TITLES: frozenset[str] = frozenset(
    {"ระบบงานปัจจุบัน", "ระบบงานปัจจุบัน (As-Is)", "As-Is"}
)

CATEGORIES_WITHOUT_CURRENT_SYSTEM: frozenset[str] = frozenset(
    {"buy_goods", "construction", "hire_service"}
)

LEGACY_SCOPE_TITLES: dict[str, str] = {
    "s4.1": "สรุปขอบเขตงาน",
    "s4.2": "ระบบงานปัจจุบัน",
    "s4.3": "งานหลักและกิจกรรม",
    "s4.4": "ข้อกำหนดด้านฮาร์ดแวร์",
    "s4.5": "ข้อกำหนดด้านซอฟต์แวร์และลิขสิทธิ์",
    "s4.6": "จุดเชื่อมโยงระบบ",
    "s4.7": "มาตรฐานและแบบอ้างอิง",
    "s4.8": "ผลงานส่งมอบ",
    "s4.9": "ระยะเวลาการสนับสนุน บำรุงรักษา และ SLA",
    "s4.10": "บุคลากร ทีมงาน และปริมาณงาน (man-day)",
    "s4.11": "รูปแบบการบำรุงรักษา (PM/CM)",
    "s4.12": "การดำเนินงานและการบริหารจัดการ",
    "s4.13": "แผนสำรอง กู้คืนระบบ และการสำรองข้อมูล",
    "s4.14": "ข้อกำหนดด้านความมั่นคงปลอดภัย PDPA",
}


class ProfileStatus(str, Enum):
    OK = "ok"
    NONE = "none"
    MISSING = "missing"


@dataclass(frozen=True)
class Subsection:
    key: str
    title: str
    required: bool
    storage_key: str
    semantic_key: str
    hint: str = ""


@dataclass(frozen=True)
class MainSection:
    key: str
    title: str
    required: bool
    storage_key: str
    semantic_key: str
    hitl: bool = False
    hint: str = ""


@dataclass(frozen=True)
class SectionProfile:
    category: str
    label: str
    main_sections: tuple[MainSection, ...]
    scope_subsections: tuple[Subsection, ...]

    def main_storage_keys(self) -> list[str]:
        return [item.storage_key for item in self.main_sections]

    def scope_storage_keys(self) -> list[str]:
        return [item.storage_key for item in self.scope_subsections]

    def required_scope_keys(self) -> list[str]:
        return [item.storage_key for item in self.scope_subsections if item.required]

    def fact_required_keys(self) -> list[str]:
        keys = ["s1", "s2", "s5", "s6", "s7"]
        required_scope = self.required_scope_keys()
        if required_scope:
            keys.append(required_scope[0])
        return keys

    def slot_order(self) -> list[str]:
        return [*self.main_storage_keys(), *self.scope_storage_keys()]

    def slot_labels(self) -> dict[str, str]:
        labels = {item.storage_key: item.title for item in self.main_sections}
        labels.update({item.storage_key: item.title for item in self.scope_subsections})
        return labels

    def to_export_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "main_sections": [
                {
                    "key": item.storage_key,
                    "semantic_key": item.semantic_key,
                    "title": item.title,
                    "required": item.required,
                    "hitl": item.hitl,
                    "hint": item.hint,
                }
                for item in self.main_sections
            ],
            "scope_subsections": [
                {
                    "key": item.storage_key,
                    "semantic_key": item.semantic_key,
                    "title": item.title,
                    "required": item.required,
                    "hint": item.hint,
                }
                for item in self.scope_subsections
            ],
            "fact_required": self.fact_required_keys(),
        }


def map_legacy_type(legacy: str | None) -> str:
    raw = str(legacy or "").strip()
    if not raw:
        return tax.DEFAULT_PROCUREMENT_TYPE
    return LEGACY_TYPE_MAP.get(raw, raw)


def is_known_category(category: str) -> bool:
    return category in PROCUREMENT_CATEGORY_LABELS


def classify_category(raw: str | None) -> tuple[ProfileStatus, str]:
    text = str(raw or "").strip()
    if not text:
        return ProfileStatus.NONE, ""
    mapped = map_legacy_type(text)
    if is_known_category(mapped):
        return ProfileStatus.OK, mapped
    return ProfileStatus.MISSING, mapped


def category_for_project(raw: str | None) -> str:
    """Normalized 7-key for stored projects (empty → buy_goods)."""
    status, mapped = classify_category(raw)
    if status is ProfileStatus.OK:
        return mapped
    return tax.DEFAULT_PROCUREMENT_TYPE


def category_is_locked(*, current_step: int, current_phase: int) -> bool:
    return int(current_step or 1) >= 3 or int(current_phase or 0) >= 3


def scope_storage_key(semantic: str) -> str:
    short = semantic.removeprefix("scope.")
    if len(short) > 20:
        return short[:20]
    return short


def storage_to_semantic_scope(storage_key: str) -> str:
    if storage_key.startswith("scope."):
        return storage_key
    if storage_key.startswith("s4."):
        return storage_key
    return f"scope.{storage_key}"


def semantic_section_order(category: str) -> list[str]:
    key = category if is_known_category(category) else tax.DEFAULT_PROCUREMENT_TYPE
    order: list[str] = []
    for item in tax.section_order(key):
        order.append(item)
        if item == "schedule":
            order.append("location")
    if "other_conditions" not in order:
        closing = tax.CLOSING_SECTION
        if closing in order:
            order.insert(order.index(closing), "other_conditions")
        else:
            order.append("other_conditions")
    return order


def _hitl_for(semantic: str) -> bool:
    return semantic in tax.MANDATORY_HUMAN_REVIEW_SECTIONS


def _build_profile(category: str) -> SectionProfile:
    mains: list[MainSection] = []
    for semantic in semantic_section_order(category):
        storage = SEMANTIC_TO_STORAGE[semantic]
        required = semantic in LEGAL_REQUIRED_SEMANTIC
        mains.append(
            MainSection(
                key=storage,
                title=tax.section_label(semantic, category)
                if semantic != "location"
                else "สถานที่ดำเนินการ",
                required=required,
                storage_key=storage,
                semantic_key=semantic,
                hitl=_hitl_for(semantic),
                hint=tax.hint_for(semantic),
            )
        )
    required_scope = set(tax.SCOPE_REQUIRED_BY_TYPE.get(category, ()))
    subs: list[Subsection] = []
    for semantic in tax.scope_subsections(category):
        title = tax.SCOPE_SUBSECTIONS[semantic]
        if category in CATEGORIES_WITHOUT_CURRENT_SYSTEM and title in CURRENT_SYSTEM_TITLES:
            continue
        storage = scope_storage_key(semantic)
        subs.append(
            Subsection(
                key=storage,
                title=title,
                required=semantic in required_scope,
                storage_key=storage,
                semantic_key=semantic,
                hint=tax.hint_for(semantic),
            )
        )
    return SectionProfile(
        category=category,
        label=PROCUREMENT_CATEGORY_LABELS[category],
        main_sections=tuple(mains),
        scope_subsections=tuple(subs),
    )


_PROFILE_CACHE: dict[str, SectionProfile] = {
    key: _build_profile(key) for key in PROCUREMENT_CATEGORY_ORDER
}


def resolve_profile(category: str | None) -> SectionProfile | ProfileStatus:
    status, mapped = classify_category(category)
    if status is not ProfileStatus.OK:
        return status
    return _PROFILE_CACHE[mapped]


def require_profile(category: str | None) -> SectionProfile:
    resolved = resolve_profile(category)
    if isinstance(resolved, SectionProfile):
        return resolved
    raise MissingSectionProfile(str(category or ""), resolved)


class MissingSectionProfile(Exception):
    def __init__(self, category: str, status: ProfileStatus) -> None:
        self.category = category
        self.status = status
        if status is ProfileStatus.NONE:
            message = "ให้เลือกหมวดใหญ่ประเภทการจัดซื้อจัดจ้างก่อน"
        else:
            message = f"ไม่พบ Section_Profile สำหรับ Procurement_Category {category}"
        super().__init__(message)


def profile_for_project(project_type: str | None) -> SectionProfile:
    return _PROFILE_CACHE[category_for_project(project_type)]


def section_order(category: str | None) -> list[str]:
    return profile_for_project(category).main_storage_keys()


def scope_subsections(category: str | None) -> list[Subsection]:
    return list(profile_for_project(category).scope_subsections)


def scope_required(category: str | None) -> list[str]:
    return profile_for_project(category).required_scope_keys()


def display_number(index: int) -> int:
    return index + 1


def subsection_title(storage_key: str, category: str | None = None, fallback: str = "") -> str:
    if category:
        for item in profile_for_project(category).scope_subsections:
            if item.storage_key == storage_key or item.semantic_key == storage_key:
                return item.title
    title = tax.SCOPE_SUBSECTIONS.get(storage_to_semantic_scope(storage_key), "")
    if title:
        return title
    return LEGACY_SCOPE_TITLES.get(storage_key, fallback or storage_key)


def is_scope_storage_key(key: str) -> bool:
    if key in LEGACY_SCOPE_TITLES:
        return True
    if key.startswith("s4.") or key.startswith("scope."):
        return True
    semantic = storage_to_semantic_scope(key)
    return semantic in tax.SCOPE_SUBSECTIONS


def all_scope_storage_keys() -> dict[str, str]:
    out: dict[str, str] = {}
    for semantic, title in tax.SCOPE_SUBSECTIONS.items():
        out[scope_storage_key(semantic)] = title
    return out


def all_main_storage_labels() -> dict[str, str]:
    labels = {
        "s1": "ความเป็นมา",
        "s2": "วัตถุประสงค์",
        "s3": "คุณสมบัติของผู้ยื่นข้อเสนอ",
        "s4": "ขอบเขตของงาน",
        "s5": "ระยะเวลาดำเนินการ",
        "s6": "วงเงินงบประมาณ",
        "s7": "สถานที่ดำเนินการ",
        "s8": "งวดงานและการจ่ายเงิน",
        "s9": "การรับประกัน",
        "s10": "อัตราค่าปรับ",
        "s11": "หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ",
        "s12": "เอกสารและหลักฐานที่ผู้เสนอราคาต้องนำมายื่น",
        "s13": "เงื่อนไขอื่น ๆ",
        "s15": "ลิขสิทธิ์และกรรมสิทธิ์ในผลงาน",
        "s16": "การรักษาความลับของข้อมูลและการคุ้มครองข้อมูลส่วนบุคคล",
        "s17": "หน่วยงานผู้รับผิดชอบและสถานที่ติดต่อ",
    }
    return labels


def procurement_categories() -> list[dict[str, str]]:
    return [
        {"key": key, "label": PROCUREMENT_CATEGORY_LABELS[key]}
        for key in PROCUREMENT_CATEGORY_ORDER
    ]


def profile_export() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "categories": procurement_categories(),
        "legacy_map": dict(LEGACY_TYPE_MAP),
        "profiles": {
            key: _PROFILE_CACHE[key].to_export_dict() for key in PROCUREMENT_CATEGORY_ORDER
        },
    }


def extra_legacy_scope_items(
    stored_subs: dict[str, str],
    category: str | None,
) -> list[dict[str, str]]:
    """Content on disk that is not in the active profile (Req 6.3)."""
    allowed = set(profile_for_project(category).scope_storage_keys())
    extras: list[dict[str, str]] = []
    for key, text in stored_subs.items():
        if not str(text or "").strip():
            continue
        if key in allowed:
            continue
        extras.append(
            {
                "key": key,
                "title": subsection_title(key, category, key),
                "content": text,
            }
        )
    return extras


def export_main_plan(project_type: str | None) -> list[tuple[str, str]]:
    profile = profile_for_project(project_type)
    return [(item.storage_key, item.title) for item in profile.main_sections]


def ordered_scope_export(
    project_type: str | None, sub_sections: dict[str, str]
) -> list[tuple[str, str, str]]:
    """(storage_key, title, content) in profile order, then leftover extras."""
    profile = profile_for_project(project_type)
    ordered: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for item in profile.scope_subsections:
        text = str(sub_sections.get(item.storage_key) or "")
        if not text.strip():
            continue
        ordered.append((item.storage_key, item.title, text))
        seen.add(item.storage_key)
    for extra in extra_legacy_scope_items(sub_sections, project_type):
        if extra["key"] in seen:
            continue
        ordered.append((extra["key"], extra["title"], extra["content"]))
        seen.add(extra["key"])
    return ordered


def parse_section_ref(key: str, category: str | None = None) -> tuple[str, str | None] | None:
    """Map a client section id to (mother_storage_key, sub_key or None)."""
    text = str(key or "").strip()
    if not text:
        return None
    labels = all_main_storage_labels()
    if text in labels:
        return text, None
    if text.startswith(("s4.", "4.")):
        sub = text if text.startswith("s4.") else f"s4.{text[2:]}"
        return "s4", sub
    if is_scope_storage_key(text):
        return "s4", scope_storage_key(text) if text.startswith("scope.") else text
    if category:
        allowed_subs = set(profile_for_project(category).scope_storage_keys())
        if text in allowed_subs:
            return "s4", text
    return None
