"""Canonical TOR section model — single source of truth.

Legal 13-section schema used by export, Rule Engine, orchestrator agents,
and the 8-step wizard. Discussion 01's 10-section outline is content
guidance only; product storage/export always uses these keys.

Wizard mapping (Requirement 4):
  Step 1 metadata → project row + s5 duration + s7 location
  Step 2 problem → s1
  Step 3 objectives → s2
  Step 4 scope → s4 + s4.1..s4.14
  Step 5 qualifications → s3
  Step 6 budget/payment → s5, s6, s8, s9, s10
  Step 7 review → all 13 (AI fills orphan s7/s11/s12/s13 if empty)
  Step 8 export → none
"""

from __future__ import annotations

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
    "s3": "คุณสมบัติของผู้เสนอราคา",
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
}

TOR_SECTION_LABELS_BILINGUAL: dict[str, str] = {
    "s1": "ความเป็นมา (Background)",
    "s2": "วัตถุประสงค์ (Objectives)",
    "s3": "คุณสมบัติของผู้เสนอราคา (Vendor Qualifications)",
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
}

# Scope of Work 14 subsections (Discussion 01 / mockup 06)
SCOPE_SUBSECTIONS: dict[str, str] = {
    "s4.1": "สรุปขอบเขตงาน",
    "s4.2": "ระบบงานปัจจุบัน (As-Is)",
    "s4.3": "งานหลักและกิจกรรม",
    "s4.4": "ข้อกำหนดด้านฮาร์ดแวร์",
    "s4.5": "ข้อกำหนดด้านซอฟต์แวร์และลิขสิทธิ์",
    "s4.6": "จุดเชื่อมโยงระบบ",
    "s4.7": "มาตรฐานและแบบอ้างอิง",
    "s4.8": "ผลงานส่งมอบ",
    "s4.9": "ระยะเวลาการสนับสนุนและบำรุงรักษา",
    "s4.10": "บุคลากรและทีมงาน",
    "s4.11": "รูปแบบการบำรุงรักษา",
    "s4.12": "การดำเนินงานและการบริหารจัดการ",
    "s4.13": "แผนสำรองและกู้คืนระบบ",
    "s4.14": "ข้อกำหนดด้านความมั่นคงปลอดภัย",
}

# Minimum required scope subsections for completeness (warnings, not halt)
SCOPE_REQUIRED_SUBSECTIONS: dict[str, str] = {
    "s4.1": SCOPE_SUBSECTIONS["s4.1"],
    "s4.8": SCOPE_SUBSECTIONS["s4.8"],
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
