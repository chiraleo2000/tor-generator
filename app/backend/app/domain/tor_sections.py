"""Canonical TOR storage keys — catalog of mother sections s1–s13 plus extras.

Per-project topic lists come from ``section_profile``. This module keeps the
storage catalog, wizard step map, and sample payloads.
"""

from __future__ import annotations

from app.domain.section_profile import (
    LEGACY_SCOPE_TITLES,
    all_scope_storage_keys,
    profile_for_project,
)

# Ordered legal TOR sections (พ.ร.บ. 2560 / government TOR structure)
TOR_SECTION_ORDER: list[str] = [
    "s1",
    "s2",
    "s3",
    "s4",
    "s5",
    "s6",
    "s7",
    "s8",
    "s9",
    "s10",
    "s11",
    "s12",
    "s13",
]

TOR_SECTION_LABELS: dict[str, str] = {
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

EXTRA_SECTION_ORDER: list[str] = ["s15", "s16", "s17"]

TOR_SECTION_LABELS_BILINGUAL: dict[str, str] = {
    "s1": "ความเป็นมา (Background)",
    "s2": "วัตถุประสงค์ (Objectives)",
    "s3": "คุณสมบัติของผู้ยื่นข้อเสนอ (Vendor Qualifications)",
    "s4": "ขอบเขตของงาน (Scope of Work)",
    "s5": "ระยะเวลาดำเนินการ (Timeline)",
    "s6": "วงเงินงบประมาณ (Budget)",
    "s7": "สถานที่ดำเนินการ (Location)",
    "s8": "งวดงานและการจ่ายเงิน (Payment Schedule)",
    "s9": "การรับประกัน (Warranty)",
    "s10": "อัตราค่าปรับ (Penalties)",
    "s11": "หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ (Evaluation Criteria)",
    "s12": "เอกสารและหลักฐานที่ผู้เสนอราคาต้องนำมายื่น (Supporting Documents)",
    "s13": "เงื่อนไขอื่น ๆ (Other Conditions)",
    "s15": "ลิขสิทธิ์และกรรมสิทธิ์ในผลงาน (Intellectual Property)",
    "s16": "การรักษาความลับของข้อมูลและการคุ้มครองข้อมูลส่วนบุคคล (Confidentiality)",
    "s17": "หน่วยงานผู้รับผิดชอบและสถานที่ติดต่อ (Responsible Unit)",
}

SCOPE_SUBSECTIONS: dict[str, str] = {**LEGACY_SCOPE_TITLES, **all_scope_storage_keys()}

# Default warnings when no project type is available (buy_goods profile).
SCOPE_REQUIRED_SUBSECTIONS: dict[str, str] = {
    item.storage_key: item.title
    for item in profile_for_project("buy_goods").scope_subsections
    if item.required
}

MINIMUM_CONTENT_LENGTH: int = 20

CRITICAL_SECTIONS_MIN_LENGTH: dict[str, int] = {
    "s1": 50,
    "s2": 30,
    "s3": 30,
    "s4": 100,
    "s6": 20,
    "s8": 30,
    "s10": 30,
}

WIZARD_STEP_COUNT = 8
VALID_STEPS = set(range(1, WIZARD_STEP_COUNT + 1))

# Wizard step → TOR section keys persisted by that step
STEP_SECTION_MAP: dict[int, list[str]] = {
    1: ["s5", "s7"],
    2: ["s1"],
    3: ["s2"],
    4: ["s4"],
    5: ["s3"],
    6: ["s5", "s6", "s8", "s9", "s10"],
    7: list(TOR_SECTION_ORDER),
    8: [],
}

# Sections with no dedicated wizard form — AI-drafted when entering Step 7
ORPHAN_SECTIONS: list[str] = ["s7", "s11", "s12", "s13"]

# HITL breakpoints (Req 12.7): legal, budget, payment, penalty, other conditions
MANDATORY_HUMAN_REVIEW_SECTIONS: set[str] = {
    "s3",
    "s6",
    "s8",
    "s10",
    "s13",
}


def sample_complete_sections() -> dict[str, str]:
    """Return a legally keyed 13-section document with adequate Thai content."""
    return {
        "s1": (
            "ความเป็นมาของโครงการพัฒนาระบบสารสนเทศเพื่อการจัดการทรัพยากรบุคคล "
            "ของกระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม ตาม พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560"
        ),
        "s2": "วัตถุประสงค์เพื่อพัฒนาระบบสารสนเทศที่มีประสิทธิภาพ วัดผลได้ และแล้วเสร็จตามกำหนด",
        "s3": (
            "ผู้เสนอราคาต้องมีประสบการณ์ด้านเทคโนโลยีสารสนเทศไม่น้อยกว่า 5 ปี "
            "มีผลงานที่ผ่านมา และมีทุนจดทะเบียนชำระแล้วตามที่กฎหมายกำหนด"
        ),
        "s4": (
            "ขอบเขตของงานประกอบด้วยการพัฒนาระบบสารสนเทศเพื่อการจัดการทรัพยากรบุคคล "
            "รวมถึงการออกแบบ พัฒนา ทดสอบ และติดตั้งระบบ ผลงานส่งมอบ 3 งวด"
        ),
        "s5": "ระยะเวลาดำเนินการ 180 วัน นับจากวันลงนามในสัญญา",
        "s6": "งบประมาณ 5,000,000 บาท (ห้าล้านบาทถ้วน) รวมภาษีมูลค่าเพิ่ม",
        "s7": "สถานที่ดำเนินการ ณ สำนักงานกระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม กรุงเทพมหานคร",
        "s8": "การจ่ายเงินแบ่งเป็น งวดที่ 1 ร้อยละ 30 งวดที่ 2 ร้อยละ 40 งวดที่ 3 ร้อยละ 30",
        "s9": "ผู้รับจ้างต้องรับประกันผลงานไม่น้อยกว่า 1 ปี นับจากวันตรวจรับงวดสุดท้าย",
        "s10": "ค่าปรับวันละร้อยละ 0.10 ของมูลค่าสัญญา แต่ไม่ต่ำกว่า 100 บาทต่อวัน",
        "s11": "เกณฑ์การพิจารณาคัดเลือกใช้เกณฑ์ราคาประกอบคุณภาพ ตาม พ.ร.บ. 2560 มาตรา 65",
        "s12": "เอกสารหลักฐานประกอบการเสนอราคาตามที่กำหนด รวมถึงหลักประกันการเสนอราคา",
        "s13": "เงื่อนไขอื่น ๆ ให้เป็นไปตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ พ.ศ. 2560",
    }
