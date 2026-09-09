"""Few-shot completeness hints from the example TOR corpus and taxonomy.

Loads ``category_hints.json`` when present. Falls back to in-code SECTION_HINTS
from ``tor_taxonomy`` and the generic SECTION_DRAFT_HINTS below.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.section_profile import (
    STORAGE_TO_SEMANTIC,
    profile_for_project,
    storage_to_semantic_scope,
)

logger = logging.getLogger("tor_app.draft_hints")

SECTION_DRAFT_HINTS: dict[str, str] = {
    "s1": (
        "ต้องมีประวัติระบบ/ภารกิจเดิม สถิติหรือปริมาณงานจริง ปัญหาที่วัดได้ "
        "นโยบายหรือกฎหมายที่เกี่ยวข้อง และประเภทงาน (จ้างพัฒนา จ้างบำรุงรักษา หรือจ้างที่ปรึกษา)"
    ),
    "s2": (
        "วัตถุประสงค์ต้องวัดผลได้ ระบุกลุ่มผู้ใช้ และตัวชี้วัด/SLA ไม่ใช่ข้อความกว้าง ๆ"
    ),
    "s3": (
        "ครอบคลุมสถานะตามกฎหมาย (ไม่ล้มละลาย ไม่เป็นผู้ทิ้งงาน ขึ้นทะเบียน e-GP) "
        "ทุนจดทะเบียนหรือมูลค่าสุทธิ/สินเชื่อประมาณหนึ่งในสี่ของวงเงิน "
        "อายุกิจการ ผลงานย้อนหลังเป็นวงเงิน หนังสือแต่งตั้งผู้ผลิตถ้ามีอุปกรณ์เฉพาะ "
        "และโครงสร้างทีมหรือ man-month เมื่อเป็นงานพัฒนา"
    ),
    "s4": (
        "เขียนเฉพาะหัวข้อย่อยตามประเภทงาน ระบุจำนวน หน่วยนับ และเกณฑ์ตรวจรับ "
        "ใช้ตารางเมื่อมีหลายรายการ และห้ามระบุยี่ห้อโดยไม่มีคำว่า หรือเทียบเท่า"
    ),
    "s5": "ระบุระยะเวลาเป็นจำนวนวัน นับถัดจากวันลงนามในสัญญา และงวดส่งมอบให้ตรงงวดเงิน",
    "s6": (
        "ต้องแยกวงเงินงบประมาณที่ได้รับจัดสรร กับราคากลาง และวิธีได้มา "
        "พร้อมวิธีจัดซื้อจัดจ้าง (ประกาศเชิญชวน/e-bidding คัดเลือก เฉพาะเจาะจง)"
    ),
    "s7": "สถานที่ติดตั้งหรือปฏิบัติงาน และหน่วยงานผู้รับผิดชอบติดต่อได้",
    "s8": (
        "งวดจ่ายต้องรวมร้อยละ 100 แต่ละงวดมีผลงานส่งมอบ "
        "และคณะกรรมการตรวจรับพัสดุได้ตรวจรับเรียบร้อยแล้ว"
    ),
    "s9": "ระยะเวลารับประกัน ช่องทางสนับสนุน และเงื่อนไขแก้ไขข้อบกพร่องโดยไม่คิดค่าใช้จ่าย",
    "s10": (
        "แยกค่าปรับส่งมอบล่าช้าเป็นร้อยละต่อวัน ตามระเบียบ "
        "กับค่าปรับระบบขัดข้อง/SLA เป็นชั่วโมงถ้าเป็นงานบำรุงรักษา"
    ),
    "s11": (
        "ระบุเกณฑ์ราคา หรือราคาประกอบคุณภาพ พร้อมสัดส่วนน้ำหนัก "
        "คะแนนผ่านขั้นต่ำ และการนำเสนอถ้าใช้เกณฑ์คุณภาพ"
    ),
    "s12": (
        "รายการเอกสารยื่นซอง รวมตารางเปรียบเทียบข้อกำหนด "
        "หนังสือรับรองผลงาน และหนังสือแต่งตั้งผู้ผลิตเมื่อกำหนดยี่ห้ออุปกรณ์"
    ),
    "s13": (
        "ข้อสงวนสิทธิ์ หลักประกันสัญญา และเงื่อนไขตามระเบียบกระทรวงการคลัง"
    ),
    "s15": "ลิขสิทธิ์ กรรมสิทธิ์ เอกสาร และซอร์สโค้ดตกเป็นของหน่วยงานเมื่อส่งมอบ",
    "s16": "การรักษาความลับและปฏิบัติตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล",
    "s17": "ชื่อหน่วยงาน ที่อยู่ โทรศัพท์ และช่องทางวิจารณ์ร่าง TOR",
}

SCOPE_DRAFT_HINTS: dict[str, str] = {}

_HINTS_WARNED = False


@lru_cache(maxsize=1)
def _load_category_hints() -> dict[str, Any]:
    global _HINTS_WARNED
    path = Path(__file__).with_name("category_hints.json")
    if not path.is_file():
        if not _HINTS_WARNED:
            logger.warning("category_hints.json not found; using built-in Draft_Hints")
            _HINTS_WARNED = True
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read category_hints.json: %s", exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def hint_for(section_key: str, category: str | None = None) -> str:
    if category:
        profile = profile_for_project(category)
        blob = _load_category_hints().get(profile.category) or {}
        formulaic = blob.get("formulaic") if isinstance(blob, dict) else None
        if isinstance(formulaic, dict):
            semantic = STORAGE_TO_SEMANTIC.get(section_key) or storage_to_semantic_scope(
                section_key
            )
            found = str(formulaic.get(section_key) or formulaic.get(semantic) or "").strip()
            if found:
                return found
        for item in profile.main_sections:
            if item.storage_key == section_key and item.hint:
                return item.hint
        for item in profile.scope_subsections:
            if item.storage_key == section_key and item.hint:
                return item.hint
    if section_key in SCOPE_DRAFT_HINTS:
        return SCOPE_DRAFT_HINTS[section_key]
    from app.domain.tor_taxonomy import hint_for as tax_hint

    semantic = STORAGE_TO_SEMANTIC.get(section_key) or storage_to_semantic_scope(section_key)
    found = tax_hint(semantic)
    if found:
        return found
    return SECTION_DRAFT_HINTS.get(section_key, "")


def category_hints_available(category: str | None) -> bool:
    if not category:
        return False
    blob = _load_category_hints().get(profile_for_project(category).category)
    return bool(blob)
