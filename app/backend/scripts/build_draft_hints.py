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
    "hire_develop": [
        "พัฒนาระบบเว็บไซต์อินเตอร์เน็ตอินทราเน็ตกรมบัญชีกลาง",
        "514_BMA MARKET",
    ],
    "hire_maintain": [
        "จ้างบำรุงรักษาระบบบริหารงบประมาณ",
        "จ้างบำรุงรักษาและแก้ไขอุปกรณ์สนับสนุนห้องศูนย์คอมพิวเตอร์",
        "จ้างบำรุงรักษาระบบความรับผิดทางละเมิดและแพ่ง",
        "506_RD EPAYMENT",
        "513_DISASTER DATA",
    ],
    "lease_service": [
        "เช่าใช้บริการระบบสื่อสารข้อมูลอินเทอร์เน็ต",
        "เช่าบริการสื่อสารแบบ MPLS",
        "เข่ารถนั่งส่วนกลาง รถยนต์ไฟฟ้า",
    ],
    "buy_goods": [
        "จัดซื้อเครื่องคอมพิวเตอร์และอุปกรณ์ต่อพ่วง",
        "ครุภัณฑ์โต๊ะ เก้าอี้",
    ],
    "construction": [
        "ปรับปรุงห้องประชุม",
        "ปรับปรุงระบบปรับอากาศ",
    ],
    "hire_consult": [
        "จ้างวิเคราะห์และตรวจสอบเพื่อป้องกันความเสี่ยงจากภัยคุกคามทางไซเบอร์",
        "การจ้างเฝ้าระวัง ตรวจสอบ วิเคราะห์ภัยคุกคามด้านความปลอดภัย",
    ],
    "hire_service": [
        "สแกนและจัดเก็บเอกสารบำเหน็จบำนาญ",
    ],
}

_NAME_KEYWORDS = (
    ("hire_consult", ("เฝ้าระวัง", "ไซเบอร์", "ที่ปรึกษา", "สำรวจ", "วิเคราะห์ภัย")),
    ("hire_service", ("สแกน", "จัดเก็บเอกสาร")),
    ("lease_service", ("เช่า", "เข่า", "MPLS", "Internet", "BEV", "รถยนต์ไฟฟ้า")),
    ("hire_maintain", ("บำรุงรักษา", "MA", "EPAYMENT", "DATA_BIDDING")),
    ("construction", ("ปรับปรุงห้อง", "ก่อสร้าง", "ปรับอากาศ")),
    ("buy_goods", ("จัดซื้อเครื่อง", "ครุภัณฑ์", "ฮาร์ดแวร์")),
    ("hire_develop", ("พัฒนาระบบ", "เว็บไซต์", "MARKET")),
)


def _classify_example_name(name: str) -> str | None:
    lowered = name.lower()
    for category, keywords in _NAME_KEYWORDS:
        if any(token.lower() in lowered for token in keywords):
            return category
    return None


def _merge_unique(base: list[str], extra: list[str]) -> list[str]:
    merged = list(base)
    for item in extra:
        if item not in merged:
            merged.append(item)
    return merged


def _scan_example_names() -> dict[str, list[str]]:
    root = BACKEND.parents[1] / "documents" / "ตัวอย่าง TOR"
    found: dict[str, list[str]] = {key: [] for key in CORPUS_MAP}
    if not root.is_dir():
        return {key: list(names) for key, names in CORPUS_MAP.items()}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".docx"}:
            continue
        assigned = _classify_example_name(path.stem)
        if assigned is None:
            continue
        if path.stem not in found[assigned]:
            found[assigned].append(path.stem)
    return {
        key: _merge_unique(names, found.get(key, []))
        for key, names in CORPUS_MAP.items()
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
    corpus = _scan_example_names()
    profiles = {}
    for category in PROCUREMENT_CATEGORY_ORDER:
        profile = profile_for_project(category)
        profiles[category] = {
            "structure": profile.main_storage_keys(),
            "scope_order": profile.scope_storage_keys(),
            "formulaic": _formulaic_for(category),
            "corpus_name_hints": corpus.get(category, []),
            "used_example_corpus": True,
        }
    return profiles


def main() -> None:
    dest = BACKEND / "app" / "domain" / "category_hints.json"
    dest.write_text(json.dumps(build_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dest)


if __name__ == "__main__":
    main()
