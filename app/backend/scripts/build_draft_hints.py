"""Build category_hints.json from taxonomy + optional OCR of example TOR PDFs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.domain.section_profile import (  # noqa: E402
    PROCUREMENT_CATEGORY_ORDER,
    SEMANTIC_TO_STORAGE,
    profile_for_project,
    scope_storage_key,
)
from app.domain.tor_taxonomy import (  # noqa: E402
    CANONICAL_PHRASES,
    SCOPE_BY_TYPE,
    SCOPE_HINTS,
    SECTION_HINTS,
)

CORPUS_MAP = {
    "hire_develop": ["พัฒนาระบบเว็บไซต์", "เชื่อมโยง e-Service"],
    "hire_maintain": ["จ้างบำรุงรักษาระบบบริหารงบประมาณ", "จ้างบำรุงรักษาและแก้ไขอุปกรณ์"],
    "lease_service": ["เช่าใช้บริการระบบสื่อสารข้อมูล", "เช่าบริการสื่อสารแบบ MPLS"],
    "buy_goods": ["จัดซื้อเครื่องคอมพิวเตอร์", "จัดซื้อระบบเครือข่าย", "ครุภัณฑ์โต๊ะ"],
    "construction": ["ปรับปรุงห้องประชุม", "ปรับปรุงระบบปรับอากาศ"],
    "hire_consult": ["สำรวจระดับความพร้อม", "วิเคราะห์และตรวจสอบเพื่อป้องกันความเสี่ยง"],
    "hire_service": ["สแกนและจัดเก็บเอกสาร"],
}


def _formulaic_for(category: str) -> dict[str, str]:
    profile = profile_for_project(category)
    out: dict[str, str] = dict(CANONICAL_PHRASES)
    for item in profile.main_sections:
        hint = SECTION_HINTS.get(item.semantic_key) or item.hint
        if hint:
            out[item.storage_key] = hint
            out[item.semantic_key] = hint
    for semantic in SCOPE_BY_TYPE.get(category, []):
        hint = SCOPE_HINTS.get(semantic, "")
        if hint:
            out[scope_storage_key(semantic)] = hint
            out[semantic] = hint
    for storage, semantic in SEMANTIC_TO_STORAGE.items():
        if storage in out:
            continue
        hint = SECTION_HINTS.get(semantic, "")
        if hint:
            out[storage] = hint
    return out


def build_payload() -> dict:
    profiles = {}
    for category in PROCUREMENT_CATEGORY_ORDER:
        profile = profile_for_project(category)
        profiles[category] = {
            "structure": profile.main_storage_keys(),
            "scope_order": profile.scope_storage_keys(),
            "formulaic": _formulaic_for(category),
            "corpus_name_hints": CORPUS_MAP.get(category, []),
            "used_example_corpus": True,
        }
    return profiles


def main() -> None:
    dest = BACKEND / "app" / "domain" / "category_hints.json"
    dest.write_text(json.dumps(build_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dest)


if __name__ == "__main__":
    main()
