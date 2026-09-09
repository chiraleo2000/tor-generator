"""Canonical TOR taxonomy (v2) — type-aware single source of truth.

Derived from 12 real Thai government TOR documents in
``documents/ตัวอย่าง TOR`` (กรมบัญชีกลาง, สพร., กรมกิจการผู้สูงอายุ).

What changed from the old flat ``s1``–``s13`` model
---------------------------------------------------
* Section order now matches real TORs: ความเป็นมา → วัตถุประสงค์ →
  คุณสมบัติผู้ยื่นข้อเสนอ → ขอบเขตของงาน → ระยะเวลา/ส่งมอบ →
  หลักเกณฑ์พิจารณา → วงเงิน → งวดงานและการจ่ายเงิน → ค่าปรับ →
  รับประกัน → (หมวดเสริมตามประเภทงาน) → หน่วยงานผู้รับผิดชอบ.
* ``สถานที่ดำเนินการ`` is no longer a top-level section — real TORs put
  it inside ขอบเขตของงาน (เงื่อนไขการติดตั้ง/สถานที่ปฏิบัติงาน).
* ``เอกสารและหลักฐานที่ต้องยื่น`` is no longer a top-level section — real
  TORs put it inside ข้อ ๓ as "ส่วนที่ ๒ เอกสารที่ต้องยื่น".
* ``เงื่อนไขอื่น ๆ`` is split into the specific sections real TORs use
  (ลิขสิทธิ์/กรรมสิทธิ์, การรักษาความลับ, ข้อสงวนสิทธิ์).
* Scope subsections are now chosen by procurement type. The old fixed
  14 subsections (including ``4.2 ระบบงานปัจจุบัน``, which appears in no
  real TOR) are gone.

Keys are semantic strings, not positional, so display numbering can
differ per procurement type without breaking stored data.
"""

from __future__ import annotations

SCHEMA_VERSION = 2

# ---------------------------------------------------------------------------
# Procurement types
# ---------------------------------------------------------------------------

PROCUREMENT_TYPES: dict[str, str] = {
    "hire_develop": "จ้างพัฒนาระบบ",
    "hire_maintain": "จ้างบำรุงรักษา (MA)",
    "lease_service": "เช่าบริการ/สื่อสาร",
    "buy_goods": "จัดซื้อครุภัณฑ์/ฮาร์ดแวร์",
    "construction": "งานปรับปรุง/ก่อสร้าง",
    "hire_consult": "จ้างที่ปรึกษา/สำรวจ/วิเคราะห์",
    "hire_service": "จ้างเหมาบริการงานเอกสาร",
}

DEFAULT_PROCUREMENT_TYPE = "buy_goods"

# Wording of the counterparty, per type. Real TORs are consistent about this
# and mixing them ("ผู้ขาย" in a จ้าง document) is a common drafting defect.
CONTRACTOR_TERM: dict[str, str] = {
    "buy_goods": "ผู้ขาย",
    "hire_develop": "ผู้รับจ้าง",
    "hire_maintain": "ผู้รับจ้าง",
    "lease_service": "ผู้ให้เช่า",
    "hire_service": "ผู้รับจ้าง",
    "hire_consult": "ผู้รับจ้าง",
    "construction": "ผู้รับจ้าง",
}

OWNER_TERM: dict[str, str] = {
    "buy_goods": "ผู้ซื้อ",
    "lease_service": "ผู้เช่า",
}

# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

SECTION_LABELS: dict[str, str] = {
    "background": "ความเป็นมา",
    "objective": "วัตถุประสงค์",
    "qualification": "คุณสมบัติของผู้ยื่นข้อเสนอ",
    "scope": "ขอบเขตของงาน",
    "schedule": "ระยะเวลาดำเนินการและกำหนดส่งมอบ",
    "evaluation": "หลักเกณฑ์ในการพิจารณาคัดเลือกข้อเสนอ",
    "budget": "วงเงินงบประมาณที่ได้รับจัดสรร",
    "payment": "งวดงานและการจ่ายเงิน",
    "penalty": "อัตราค่าปรับ",
    "warranty": "การกำหนดระยะเวลารับประกันความชำรุดบกพร่อง",
    "ip_ownership": "ลิขสิทธิ์และกรรมสิทธิ์ในผลงาน",
    "confidentiality": "การรักษาความลับของข้อมูลและการคุ้มครองข้อมูลส่วนบุคคล",
    "other_conditions": "เงื่อนไขอื่น ๆ และข้อสงวนสิทธิ์",
    "responsible_unit": "หน่วยงานผู้รับผิดชอบและสถานที่ติดต่อ",
}

SECTION_LABELS_EN: dict[str, str] = {
    "background": "Background",
    "objective": "Objectives",
    "qualification": "Bidder Qualifications",
    "scope": "Scope of Work",
    "schedule": "Timeline and Delivery",
    "evaluation": "Evaluation Criteria",
    "budget": "Budget",
    "payment": "Payment Schedule",
    "penalty": "Liquidated Damages",
    "warranty": "Warranty",
    "ip_ownership": "Intellectual Property",
    "confidentiality": "Confidentiality and PDPA",
    "other_conditions": "Other Conditions",
    "responsible_unit": "Responsible Unit",
}

# Sections present in every TOR regardless of procurement type, in order.
CORE_SECTION_ORDER: list[str] = [
    "background",
    "objective",
    "qualification",
    "scope",
    "schedule",
    "evaluation",
    "budget",
    "payment",
    "penalty",
    "warranty",
]

# Always last.
CLOSING_SECTION = "responsible_unit"

# Extra sections inserted between ``warranty`` and ``responsible_unit``.
EXTRA_SECTIONS_BY_TYPE: dict[str, list[str]] = {
    "buy_goods": [],
    "hire_develop": ["ip_ownership", "confidentiality"],
    "hire_maintain": ["confidentiality"],
    "lease_service": [],
    "hire_service": ["ip_ownership", "confidentiality"],
    "hire_consult": ["ip_ownership", "confidentiality", "other_conditions"],
    "construction": [],
}

# Per-type heading wording. Real TORs rename the same slot depending on
# whether the work is a purchase, a lease, a maintenance contract, etc.
SECTION_LABEL_OVERRIDES: dict[str, dict[str, str]] = {
    "buy_goods": {
        "schedule": "กำหนดเวลาส่งมอบพัสดุ",
    },
    "hire_maintain": {
        "schedule": "ระยะเวลาการให้บริการและการส่งมอบงาน",
        "payment": "ค่าจ้างและการจ่ายเงิน",
        "warranty": "การรับประกันผลงานการบำรุงรักษา",
    },
    "lease_service": {
        "scope": "ขอบเขตของงานและบริการที่เช่าใช้",
        "schedule": "กำหนดระยะเวลาเช่าและการส่งมอบงานรายงวด",
        "warranty": "การรับประกันการให้บริการและความชำรุดบกพร่อง",
    },
    "hire_consult": {
        "scope": "ขอบเขตการดำเนินงาน",
        "budget": "วงเงินในการจัดหา",
        "penalty": "เงื่อนไขการปรับ",
        "warranty": "การรับประกันผลงาน",
    },
    "hire_service": {
        "scope": "รายละเอียดของงาน",
        "warranty": "การรับประกันผลงาน",
    },
    "construction": {
        "scope": "ขอบเขตของงานและรายละเอียดการก่อสร้าง",
        "schedule": "ระยะเวลาดำเนินการก่อสร้างและการส่งมอบงาน",
        "warranty": "การรับประกันผลงานก่อสร้าง",
    },
}


def section_order(procurement_type: str) -> list[str]:
    """Ordered section keys for one procurement type."""
    key = procurement_type if procurement_type in PROCUREMENT_TYPES else DEFAULT_PROCUREMENT_TYPE
    return [*CORE_SECTION_ORDER, *EXTRA_SECTIONS_BY_TYPE.get(key, []), CLOSING_SECTION]


def section_label(section_key: str, procurement_type: str = DEFAULT_PROCUREMENT_TYPE) -> str:
    """Thai heading for a section, honouring per-type wording."""
    overrides = SECTION_LABEL_OVERRIDES.get(procurement_type, {})
    return overrides.get(section_key) or SECTION_LABELS.get(section_key, section_key)


def section_number(section_key: str, procurement_type: str = DEFAULT_PROCUREMENT_TYPE) -> int:
    """1-based display number of a section within its procurement type."""
    order = section_order(procurement_type)
    return order.index(section_key) + 1 if section_key in order else 0


# ---------------------------------------------------------------------------
# ข้อ ๓ คุณสมบัติของผู้ยื่นข้อเสนอ — subsections
# ---------------------------------------------------------------------------
# Real TORs open with the same nine statutory clauses, then add
# project-specific clauses. b517e2e3 splits the section into
# "ส่วนที่ ๑ คุณสมบัติ" and "ส่วนที่ ๒ เอกสารที่ต้องยื่น"; we keep that split
# as the last subsection instead of a separate top-level section.

QUALIFICATION_SUBSECTIONS: dict[str, str] = {
    "qual.legal": "คุณสมบัติทั่วไปตามกฎหมายและการลงทะเบียนในระบบ e-GP",
    "qual.jv": "กรณีกิจการร่วมค้า",
    "qual.networth": "มูลค่าสุทธิของกิจการ ทุนจดทะเบียน หรือวงเงินสินเชื่อ",
    "qual.experience": "ผลงานประเภทเดียวกันกับงานที่จัดซื้อจัดจ้าง",
    "qual.personnel": "บุคลากรหลักในโครงการ",
    "qual.dealer": "หนังสือแต่งตั้งตัวแทนจำหน่ายจากเจ้าของผลิตภัณฑ์",
    "qual.license": "ใบอนุญาตประกอบกิจการตามกฎหมายเฉพาะ",
    "qual.documents": "เอกสารและหลักฐานที่ผู้ยื่นข้อเสนอต้องนำมายื่น",
}

# Subsections used by each procurement type, in order.
QUALIFICATION_BY_TYPE: dict[str, list[str]] = {
    "buy_goods": [
        "qual.legal", "qual.jv", "qual.networth", "qual.experience",
        "qual.dealer", "qual.documents",
    ],
    "hire_develop": [
        "qual.legal", "qual.jv", "qual.networth", "qual.experience",
        "qual.personnel", "qual.documents",
    ],
    "hire_maintain": [
        "qual.legal", "qual.jv", "qual.networth", "qual.experience",
        "qual.personnel", "qual.documents",
    ],
    "lease_service": [
        "qual.legal", "qual.jv", "qual.networth", "qual.license",
        "qual.documents",
    ],
    "hire_service": [
        "qual.legal", "qual.jv", "qual.networth", "qual.experience",
        "qual.documents",
    ],
    "hire_consult": [
        "qual.legal", "qual.experience", "qual.personnel", "qual.documents",
    ],
    "construction": [
        "qual.legal", "qual.jv", "qual.networth", "qual.experience",
        "qual.license", "qual.documents",
    ],
}

# ---------------------------------------------------------------------------
# ข้อ ๔ ขอบเขตของงาน — subsections per procurement type
# ---------------------------------------------------------------------------

SCOPE_SUBSECTIONS: dict[str, str] = {
    # งานซื้อ
    "scope.items": "รายการพัสดุที่จัดซื้อและจำนวน",
    "scope.general_conditions": "เงื่อนไขทั่วไปของพัสดุ",
    "scope.specification": "คุณลักษณะเฉพาะของพัสดุ",
    "scope.installation": "เงื่อนไขการติดตั้งและสถานที่ติดตั้ง",
    "scope.delivery_acceptance": "เงื่อนไขการส่งมอบและการตรวจรับ",
    "scope.training": "การฝึกอบรมและการถ่ายทอดความรู้",
    "scope.documents": "เอกสารและคู่มือที่ต้องส่งมอบ",
    "scope.after_sales": "การบริการสนับสนุนและบำรุงรักษาระหว่างรับประกัน",
    # งานจ้างพัฒนาระบบ
    "scope.system_overview": "ภาพรวมและสถาปัตยกรรมของระบบที่ต้องการ",
    "scope.functional": "ขอบเขตระบบงานและหน้าที่การทำงานที่ต้องพัฒนา",
    "scope.integration": "การเชื่อมโยงระบบและการโอนย้ายข้อมูล",
    "scope.licenses": "ครุภัณฑ์และลิขสิทธิ์ซอฟต์แวร์ที่ต้องจัดหา",
    "scope.standards_security": "มาตรฐานและข้อกำหนดด้านความมั่นคงปลอดภัยสารสนเทศ",
    "scope.testing": "การทดสอบระบบและเกณฑ์การยอมรับ",
    "scope.deliverable_docs": "เอกสารระบบและซอร์สโค้ดที่ต้องส่งมอบ",
    "scope.project_team": "บุคลากรประจำโครงการ",
    "scope.sla_warranty": "การบำรุงรักษาและระดับการให้บริการระหว่างรับประกัน",
    # งานจ้างบำรุงรักษา
    "scope.asset_list": "รายการระบบและอุปกรณ์ที่ต้องบำรุงรักษา",
    "scope.cm": "การบำรุงรักษาเชิงแก้ไข (Corrective Maintenance)",
    "scope.pm": "การบำรุงรักษาเชิงป้องกัน (Preventive Maintenance) และรอบการเข้าดำเนินการ",
    "scope.sla": "ระดับการให้บริการ เวลาตอบสนอง และเวลาแก้ไขให้แล้วเสร็จ",
    "scope.helpdesk": "ศูนย์รับแจ้งเหตุขัดข้องและการบริหารจัดการปัญหา",
    "scope.spare_parts": "อะไหล่ วัสดุสิ้นเปลือง และอุปกรณ์ทดแทนระหว่างซ่อม",
    "scope.onsite_staff": "บุคลากรและการปฏิบัติงานร่วมกับเจ้าหน้าที่ของหน่วยงาน",
    "scope.reporting": "การรายงานผลการปฏิบัติงาน",
    "scope.backup": "การสำรองข้อมูลและการกู้คืนระบบ",
    # งานเช่า
    "scope.service_spec": "รายละเอียดบริการที่เช่าใช้",
    "scope.provided_equipment": "อุปกรณ์และสื่อสัญญาณที่ผู้ให้เช่าต้องจัดหา",
    "scope.availability": "ความพร้อมใช้งาน เส้นทางสำรอง และการสลับเส้นทาง",
    "scope.noc": "ศูนย์รับแจ้งเหตุตลอด ๒๔ ชั่วโมงและการแจ้งเตือน",
    "scope.usage_report": "ระบบรายงานและการตรวจสอบปริมาณการใช้งาน",
    "scope.lease_maintenance": "การบำรุงรักษาระบบตลอดอายุสัญญาเช่า",
    "scope.lessee_rights": "สิทธิของผู้เช่าระหว่างอายุสัญญา",
    # งานจ้างบริการ
    "scope.workload": "ปริมาณงานและหน่วยนับ",
    "scope.workflow": "กระบวนการปฏิบัติงาน",
    "scope.quality_standard": "มาตรฐานคุณภาพของผลงาน",
    "scope.resources": "บุคลากร เครื่องมือ และสถานที่ปฏิบัติงาน",
    "scope.custody": "การขนย้ายและการดูแลรักษาทรัพย์สินของผู้ว่าจ้าง",
    "scope.progress_report": "การรายงานความคืบหน้า",
    "scope.output_delivery": "การส่งมอบผลงานและรูปแบบสื่อบันทึกข้อมูล",
    # งานจ้างที่ปรึกษา/สำรวจ
    "scope.methodology": "กรอบแนวคิดและระเบียบวิธีดำเนินงาน",
    "scope.population": "กลุ่มเป้าหมาย ขนาดตัวอย่าง และอัตราตอบกลับขั้นต่ำ",
    "scope.instrument": "เครื่องมือเก็บข้อมูลและการทดสอบความแม่นยำ",
    "scope.fieldwork": "การเก็บรวบรวมและตรวจสอบความถูกต้องของข้อมูล",
    "scope.analysis": "การวิเคราะห์ข้อมูลและการนำเสนอผล",
    "scope.expert_review": "การประชุมและการรับฟังความเห็นผู้เชี่ยวชาญ",
    "scope.reports": "รายงานตามลำดับขั้นและรูปแบบการส่งมอบ",
    "scope.expert_team": "คณะผู้เชี่ยวชาญและปริมาณงาน (man-month)",
    # งานก่อสร้าง/ปรับปรุง
    "scope.works": "รายการงานก่อสร้างหรือปรับปรุง",
    "scope.drawings": "แบบรูปรายการและมาตรฐานวัสดุ",
    "scope.demolition": "งานรื้อถอนและการจัดการพื้นที่",
    "scope.site_access": "เงื่อนไขการเข้าปฏิบัติงานและความปลอดภัยในการทำงาน",
    "scope.supervision": "การควบคุมงานและการตรวจสอบคุณภาพ",
    "scope.handover": "การส่งมอบพื้นที่และแบบ As-built",
}

SCOPE_BY_TYPE: dict[str, list[str]] = {
    "buy_goods": [
        "scope.items", "scope.general_conditions", "scope.specification",
        "scope.installation", "scope.delivery_acceptance", "scope.training",
        "scope.documents", "scope.after_sales",
    ],
    "hire_develop": [
        "scope.system_overview", "scope.functional", "scope.integration",
        "scope.licenses", "scope.standards_security", "scope.testing",
        "scope.deliverable_docs", "scope.training", "scope.project_team",
        "scope.sla_warranty",
    ],
    "hire_maintain": [
        "scope.asset_list", "scope.cm", "scope.pm", "scope.sla",
        "scope.helpdesk", "scope.spare_parts", "scope.onsite_staff",
        "scope.reporting", "scope.backup",
    ],
    "lease_service": [
        "scope.service_spec", "scope.provided_equipment", "scope.availability",
        "scope.noc", "scope.usage_report", "scope.lease_maintenance",
        "scope.lessee_rights",
    ],
    "hire_service": [
        "scope.workload", "scope.workflow", "scope.quality_standard",
        "scope.resources", "scope.custody", "scope.progress_report",
        "scope.output_delivery",
    ],
    "hire_consult": [
        "scope.methodology", "scope.population", "scope.instrument",
        "scope.fieldwork", "scope.analysis", "scope.expert_review",
        "scope.reports", "scope.expert_team",
    ],
    "construction": [
        "scope.works", "scope.drawings", "scope.demolition",
        "scope.site_access", "scope.supervision", "scope.handover",
        "scope.delivery_acceptance",
    ],
}

# Subsections that must not be left empty for the draft to count as complete.
SCOPE_REQUIRED_BY_TYPE: dict[str, list[str]] = {
    "buy_goods": ["scope.items", "scope.specification", "scope.delivery_acceptance"],
    "hire_develop": ["scope.functional", "scope.deliverable_docs", "scope.testing"],
    "hire_maintain": ["scope.asset_list", "scope.cm", "scope.pm", "scope.sla"],
    "lease_service": ["scope.service_spec", "scope.availability", "scope.noc"],
    "hire_service": ["scope.workload", "scope.workflow", "scope.quality_standard"],
    "hire_consult": ["scope.methodology", "scope.population", "scope.reports"],
    "construction": ["scope.works", "scope.drawings", "scope.handover"],
}


def scope_subsections(procurement_type: str) -> list[str]:
    key = procurement_type if procurement_type in PROCUREMENT_TYPES else DEFAULT_PROCUREMENT_TYPE
    return list(SCOPE_BY_TYPE.get(key, SCOPE_BY_TYPE[DEFAULT_PROCUREMENT_TYPE]))


def qualification_subsections(procurement_type: str) -> list[str]:
    key = procurement_type if procurement_type in PROCUREMENT_TYPES else DEFAULT_PROCUREMENT_TYPE
    return list(QUALIFICATION_BY_TYPE.get(key, QUALIFICATION_BY_TYPE[DEFAULT_PROCUREMENT_TYPE]))


def subsection_label(sub_key: str) -> str:
    return SCOPE_SUBSECTIONS.get(sub_key) or QUALIFICATION_SUBSECTIONS.get(sub_key, sub_key)


def subsections_for(section_key: str, procurement_type: str) -> list[str]:
    if section_key == "scope":
        return scope_subsections(procurement_type)
    if section_key == "qualification":
        return qualification_subsections(procurement_type)
    return []


# ---------------------------------------------------------------------------
# Structured input fields shown in the wizard and fed to the drafting agents
# ---------------------------------------------------------------------------

SECTION_FIELDS: dict[str, list[tuple[str, str]]] = {
    "background": [
        ("mandate", "ภารกิจและอำนาจหน้าที่ของหน่วยงาน (อ้างกฎหมายจัดตั้ง)"),
        ("currentState", "สภาพปัจจุบัน พร้อมตัวเลขปริมาณงานหรืออายุการใช้งาน"),
        ("problems", "ปัญหาและผลกระทบที่วัดได้"),
        ("policy", "นโยบาย แผน หรือกฎหมายที่รองรับ"),
        ("necessity", "เหตุผลความจำเป็นที่ต้องดำเนินการ"),
    ],
    "objective": [
        ("mainObjectives", "วัตถุประสงค์รายข้อ (ขึ้นต้นด้วย “เพื่อ”)"),
        ("users", "กลุ่มผู้ใช้งานหรือผู้รับบริการเป้าหมาย"),
        ("kpi", "ตัวชี้วัดความสำเร็จ"),
    ],
    "qualification": [
        ("experienceValue", "มูลค่าผลงานขั้นต่ำต่อสัญญา (บาท) และจำนวนปีย้อนหลัง"),
        ("networth", "ทุนจดทะเบียนชำระแล้ว มูลค่าสุทธิ หรือวงเงินสินเชื่อขั้นต่ำ"),
        ("personnel", "ตำแหน่ง คุณวุฒิ ประสบการณ์ และจำนวนบุคลากรหลัก"),
        ("specialLicense", "ใบอนุญาตหรือการขึ้นทะเบียนเฉพาะทาง"),
        ("bidDocuments", "เอกสารและหลักฐานที่ต้องยื่นพร้อมข้อเสนอ"),
    ],
    "scope": [
        ("summary", "สรุปสาระสำคัญของงานที่จะจัดซื้อจัดจ้าง"),
        ("quantities", "ปริมาณงานหรือบัญชีรายการพร้อมจำนวน"),
        ("location", "สถานที่ติดตั้ง ส่งมอบ หรือปฏิบัติงาน"),
        ("annexRefs", "เอกสารแนบที่อ้างถึงในหมวดนี้"),
    ],
    "schedule": [
        ("totalDuration", "ระยะเวลาดำเนินการรวม (วัน) นับถัดจากวันลงนามในสัญญา"),
        ("milestones", "งวดส่งมอบ พร้อมจำนวนวันและผลงานของแต่ละงวด"),
        ("noticeDays", "จำนวนวันที่ต้องแจ้งกำหนดส่งมอบล่วงหน้า"),
        ("deliveryPlace", "สถานที่ส่งมอบงาน"),
    ],
    "evaluation": [
        ("method", "เกณฑ์ที่ใช้ (เกณฑ์ราคา หรือเกณฑ์ราคาประกอบเกณฑ์อื่น)"),
        ("weights", "สัดส่วนน้ำหนักคะแนนด้านราคาและด้านคุณภาพ"),
        ("passingScore", "คะแนนผ่านขั้นต่ำและวิธีการนำเสนอ"),
        ("preferences", "แต้มต่อ SMEs หรือพัสดุที่ผลิตในประเทศไทย (ถ้ามี)"),
    ],
    "budget": [
        ("budgetAmount", "วงเงินงบประมาณ (บาท)"),
        ("budgetSource", "ที่มาของงบประมาณและปีงบประมาณ"),
        ("vatIncluded", "รวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงหรือไม่"),
        ("referencePrice", "ราคากลางและวิธีคำนวณ"),
        ("procurementMethod", "วิธีจัดซื้อจัดจ้าง"),
    ],
    "payment": [
        ("installments", "จำนวนงวดการจ่ายเงิน"),
        ("paymentTerms", "ร้อยละและเงื่อนไขการเบิกจ่ายแต่ละงวด"),
        ("retention", "หลักประกันสัญญาหรือเงินประกันผลงาน"),
        ("withholding", "เงื่อนไขการงดหรือยึดหน่วงค่าจ้าง (ถ้ามี)"),
    ],
    "penalty": [
        ("lateRate", "อัตราค่าปรับส่งมอบล่าช้า (ร้อยละต่อวัน)"),
        ("slaPenalty", "ค่าปรับกรณีไม่เข้าดำเนินการหรือระบบขัดข้อง"),
        ("cap", "เพดานค่าปรับและสิทธิบอกเลิกสัญญา"),
        ("settlement", "กำหนดเวลาชำระค่าปรับและการหักจากหลักประกัน"),
    ],
    "warranty": [
        ("period", "ระยะเวลารับประกัน นับถัดจากวันตรวจรับ"),
        ("coverage", "ขอบเขตการรับประกันและรูปแบบบริการ (เช่น On-site Service)"),
        ("responseTime", "เวลาเข้าดำเนินการและเวลาแก้ไขให้แล้วเสร็จ"),
        ("supportChannel", "ช่องทางแจ้งเหตุและเจ้าหน้าที่ประสานงาน"),
    ],
    "ip_ownership": [
        ("ownership", "กรรมสิทธิ์ในผลงาน เอกสาร และข้อมูล"),
        ("sourceCode", "การส่งมอบซอร์สโค้ดและสิทธิในการพัฒนาต่อ"),
        ("thirdParty", "ความรับผิดกรณีละเมิดลิขสิทธิ์หรือสิทธิบัตรของบุคคลภายนอก"),
    ],
    "confidentiality": [
        ("nda", "ข้อตกลงไม่เปิดเผยข้อมูลที่เป็นความลับ"),
        ("pdpa", "การคุ้มครองข้อมูลส่วนบุคคลตามกฎหมาย"),
        ("accessControl", "การควบคุมการเข้าพื้นที่และการนำข้อมูลออก"),
        ("termination", "วิธีปฏิบัติเมื่อสัญญาสิ้นสุด (คืนหรือทำลายข้อมูล)"),
    ],
    "other_conditions": [
        ("reservations", "ข้อสงวนสิทธิ์ของหน่วยงาน"),
        ("subcontract", "เงื่อนไขการจ้างช่วง"),
        ("contractSecurity", "หลักประกันสัญญา"),
        ("misc", "เงื่อนไขอื่นตามระเบียบกระทรวงการคลัง"),
    ],
    "responsible_unit": [
        ("unit", "ชื่อหน่วยงานผู้รับผิดชอบ"),
        ("address", "ที่อยู่สำหรับติดต่อ"),
        ("contact", "โทรศัพท์ โทรสาร ไปรษณีย์อิเล็กทรอนิกส์ และเว็บไซต์"),
        ("budgetNote", "หมายเหตุเงื่อนไขพระราชบัญญัติงบประมาณรายจ่ายประจำปี"),
    ],
}


def field_keys(section_key: str) -> list[str]:
    return [item[0] for item in SECTION_FIELDS.get(section_key, [])]


# ---------------------------------------------------------------------------
# Completeness thresholds and human-review gates
# ---------------------------------------------------------------------------

MINIMUM_CONTENT_LENGTH = 20

CRITICAL_SECTIONS_MIN_LENGTH: dict[str, int] = {
    "background": 400,
    "objective": 150,
    "qualification": 400,
    "scope": 600,
    "schedule": 120,
    "evaluation": 80,
    "budget": 60,
    "payment": 150,
    "penalty": 120,
    "warranty": 100,
    "responsible_unit": 60,
}

# Sections a human must sign off before export (legal / financial exposure).
MANDATORY_HUMAN_REVIEW_SECTIONS: set[str] = {
    "qualification",
    "budget",
    "payment",
    "penalty",
    "evaluation",
    "ip_ownership",
}

# ---------------------------------------------------------------------------
# Wizard mapping
# ---------------------------------------------------------------------------

WIZARD_STEP_COUNT = 8
VALID_STEPS = set(range(1, WIZARD_STEP_COUNT + 1))

STEP_SECTION_MAP: dict[int, list[str]] = {
    1: [],
    2: ["background"],
    3: ["objective"],
    4: ["scope"],
    5: ["qualification"],
    6: ["schedule", "evaluation", "budget", "payment", "penalty", "warranty"],
    7: [],
    8: [],
}

STEP_LABELS: dict[int, str] = {
    1: "ข้อมูลโครงการและประเภทการจัดซื้อจัดจ้าง",
    2: "ความเป็นมา",
    3: "วัตถุประสงค์",
    4: "ขอบเขตของงาน",
    5: "คุณสมบัติของผู้ยื่นข้อเสนอ",
    6: "ระยะเวลา วงเงิน งวดงาน และเงื่อนไขสัญญา",
    7: "ตรวจสอบร่างและข้อเสนอแนะ",
    8: "ส่งออกเอกสาร",
}


def orphan_sections(procurement_type: str) -> list[str]:
    """Sections with no dedicated wizard form; drafted by AI before review."""
    covered = {key for keys in STEP_SECTION_MAP.values() for key in keys}
    return [key for key in section_order(procurement_type) if key not in covered]


# ---------------------------------------------------------------------------
# Canonical wording lifted from the example TOR corpus
# ---------------------------------------------------------------------------
# These are the fixed phrases real Thai TORs use. Drafts that deviate read as
# non-official, so the agents are told to reuse them verbatim.

CANONICAL_PHRASES: dict[str, str] = {
    "duration_start": "นับถัดจากวันลงนามในสัญญา",
    "acceptance": "และคณะกรรมการตรวจรับพัสดุได้ตรวจรับเรียบร้อยแล้ว",
    "not_less_than": "ไม่น้อยกว่า / ไม่ต่ำกว่า (ใช้แทนการระบุค่าตายตัว)",
    "at_least_list": "อย่างน้อยดังนี้",
    "or_better": "หรือดีกว่า",
    "no_extra_cost": "โดยไม่คิดค่าใช้จ่ายใด ๆ เพิ่มเติมทั้งสิ้น",
    "committee_discretion": "ตามที่คณะกรรมการตรวจรับพัสดุกำหนด",
    "reserve_right": "ทั้งนี้ หน่วยงานขอสงวนสิทธิ์",
    "money_format": "ระบุจำนวนเงินเป็นตัวเลข แล้วตามด้วยตัวอักษรในวงเล็บ",
    "vat_included": "ซึ่งเป็นวงเงินที่รวมภาษีมูลค่าเพิ่มไว้ด้วยแล้ว",
    "budget_act_note": (
        "การจัดซื้อจัดจ้างครั้งนี้จะมีการลงนามในสัญญาหรือข้อตกลงเป็นหนังสือได้ต่อเมื่อ"
        "พระราชบัญญัติงบประมาณรายจ่ายประจำปีงบประมาณมีผลใช้บังคับ "
        "และได้รับจัดสรรงบประมาณรายจ่ายจากสำนักงบประมาณแล้ว"
    ),
}

# ---------------------------------------------------------------------------
# Drafting hints — what a section must contain to match the example corpus
# ---------------------------------------------------------------------------

SECTION_HINTS: dict[str, str] = {
    "background": (
        "เขียนเป็นย่อหน้าต่อเนื่อง ๒–๔ ย่อหน้า ตามลำดับ "
        "(๑) ภารกิจและอำนาจหน้าที่ของหน่วยงานพร้อมตัวเลขโครงสร้างจริง "
        "(๒) สภาพปัจจุบันของระบบหรือพัสดุเดิม ระบุปีที่จัดหาและอายุการใช้งาน "
        "(๓) ปัญหาและผลกระทบที่วัดได้ "
        "(๔) ปิดท้ายด้วย “ดังนั้น … จึงมีความจำเป็นต้อง …” "
        "ห้ามระบุจำนวนเงินงบประมาณและห้ามลงรายละเอียดทางเทคนิคในหมวดนี้"
    ),
    "objective": (
        "เขียนเป็นข้อย่อยเรียงลำดับ ๓–๘ ข้อ ทุกข้อขึ้นต้นด้วย “เพื่อ” "
        "แต่ละข้อต้องผูกกับรายการหรืองานจริงในขอบเขตของงาน วัดผลได้ "
        "ห้ามใช้ข้อความกว้างอย่าง “เพื่อพัฒนาองค์กร”"
    ),
    "qualification": (
        "เริ่มด้วยคุณสมบัติทั่วไปตามกฎหมายชุดมาตรฐาน ๙ ข้อ "
        "(ความสามารถตามกฎหมาย ไม่เป็นบุคคลล้มละลาย ไม่อยู่ระหว่างเลิกกิจการ "
        "ไม่อยู่ระหว่างถูกระงับการยื่นข้อเสนอ ไม่เป็นผู้ทิ้งงาน ไม่มีลักษณะต้องห้าม "
        "เป็นผู้มีอาชีพขายหรือรับจ้างงานดังกล่าว ไม่เป็นผู้มีผลประโยชน์ร่วมกัน "
        "ไม่ได้รับเอกสิทธิ์หรือความคุ้มกัน) ตามด้วยการลงทะเบียนในระบบ e-GP "
        "กิจการร่วมค้า มูลค่าสุทธิของกิจการ แล้วจึงเป็นคุณสมบัติเฉพาะโครงการ "
        "และปิดท้ายด้วยบัญชีเอกสารที่ต้องยื่น"
    ),
    "scope": (
        "เขียนแยกเป็นหัวข้อย่อยตามที่กำหนดให้เท่านั้น "
        "ระบุจำนวน หน่วยนับ และเกณฑ์ที่ตรวจรับได้ทุกข้อ "
        "ใช้ตารางมาร์กดาวน์เมื่อมีหลายรายการ "
        "ห้ามระบุยี่ห้อหรือรุ่นเฉพาะโดยไม่มีคำว่า “หรือเทียบเท่า” "
        "และห้ามใช้คำที่ตรวจสอบไม่ได้ เช่น “คุณภาพดี” “ทันสมัย”"
    ),
    "schedule": (
        "ระบุระยะเวลารวมเป็นจำนวนวัน ตามด้วย “นับถัดจากวันลงนามในสัญญา” "
        "แล้วแจกแจงงวดส่งมอบเป็นตาราง (งวดที่ / ผลงานที่ต้องส่งมอบ / ภายในกี่วัน) "
        "จำนวนวันของแต่ละงวดต้องเรียงเพิ่มขึ้นและงวดสุดท้ายเท่ากับระยะเวลารวม "
        "พร้อมเงื่อนไขการแจ้งกำหนดส่งมอบล่วงหน้าเป็นลายลักษณ์อักษร"
    ),
    "evaluation": (
        "ระบุเกณฑ์ที่ใช้ให้ชัด หากใช้เกณฑ์ราคาให้เขียนสั้นว่าพิจารณาจากราคารวม "
        "หากใช้เกณฑ์ราคาประกอบเกณฑ์อื่น ต้องมีตารางน้ำหนักคะแนนที่รวมได้ ๑๐๐ "
        "พร้อมคะแนนผ่านขั้นต่ำ และหมายเหตุว่าไม่ส่งเอกสารจะไม่ได้คะแนนในข้อนั้น "
        "รวมแต้มต่อผู้ประกอบการ SMEs และพัสดุที่ผลิตในประเทศไทยเมื่อเข้าเงื่อนไข"
    ),
    "budget": (
        "ระบุแหล่งเงินและปีงบประมาณ จำนวนเงินเป็นตัวเลขตามด้วยตัวอักษรในวงเล็บ "
        "และระบุว่ารวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงไว้ด้วยแล้วหรือไม่ "
        "แยกวงเงินงบประมาณที่ได้รับจัดสรรออกจากราคากลางเมื่อมีทั้งสองค่า"
    ),
    "payment": (
        "แจกแจงเป็นตารางงวดจ่ายเงิน ร้อยละรวมต้องเท่ากับ ๑๐๐ พอดี "
        "แต่ละงวดผูกกับผลงานส่งมอบที่ตรวจรับได้ "
        "ใช้รูปประโยค “งวดที่ X ชำระเงินในอัตราร้อยละ Y ของจำนวนเงินในสัญญา "
        "เมื่อผู้รับจ้างส่งมอบงานงวดที่ X และคณะกรรมการตรวจรับพัสดุได้ตรวจรับเรียบร้อยแล้ว”"
    ),
    "penalty": (
        "แยกค่าปรับส่งมอบล่าช้าเป็นร้อยละต่อวันของมูลค่าตามสัญญา (ปกติร้อยละ ๐.๑๐ "
        "หรือ ๐.๒๐) เขียนตัวเลขพร้อมคำอ่านในวงเล็บ เช่น ร้อยละ ๐.๑๐ (ศูนย์จุดหนึ่งศูนย์) "
        "ถ้าเป็นงานบำรุงรักษาหรือเช่า ให้เพิ่มค่าปรับรายชั่วโมงกรณีไม่เข้าดำเนินการ "
        "และค่าปรับกรณีระบบขัดข้องเกินเวลาที่ยอมให้ พร้อมกำหนดเวลาชำระค่าปรับ "
        "และสิทธิหักจากหลักประกันสัญญา"
    ),
    "warranty": (
        "ระบุระยะเวลารับประกันเป็นปี นับถัดจากวันที่ตรวจรับเรียบร้อยแล้ว "
        "ระบุรูปแบบบริการ เวลาเข้าดำเนินการ เวลาแก้ไขให้แล้วเสร็จ "
        "และย้ำว่าไม่มีค่าใช้จ่ายใด ๆ ตลอดระยะเวลารับประกัน"
    ),
    "ip_ownership": (
        "ระบุว่าลิขสิทธิ์ กรรมสิทธิ์ เอกสาร ข้อมูล และผลงานตกเป็นของหน่วยงาน "
        "ทันทีที่ส่งมอบ ระบุการส่งมอบซอร์สโค้ดฉบับสมบูรณ์ล่าสุดและสิทธิพัฒนาต่อ "
        "และความรับผิดของคู่สัญญากรณีถูกกล่าวหาว่าละเมิดสิทธิของบุคคลภายนอก"
    ),
    "confidentiality": (
        "กำหนดให้ลงนามในข้อตกลงไม่เปิดเผยข้อมูลที่เป็นความลับพร้อมสัญญาจ้าง "
        "ระบุการปฏิบัติตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล การควบคุมการเข้าพื้นที่ "
        "และวิธีปฏิบัติเมื่อสัญญาสิ้นสุดคือส่งคืนหรือทำลายข้อมูลพร้อมแจ้งยืนยันเป็นลายลักษณ์อักษร"
    ),
    "other_conditions": (
        "ระบุหลักประกันสัญญาร้อยละ ๕ ของวงเงินตามสัญญา ข้อห้ามจ้างช่วง "
        "ข้อสงวนสิทธิ์ที่จะไม่รับราคาต่ำสุดหรือยกเลิกการจัดซื้อจัดจ้าง "
        "และเงื่อนไขอื่นตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ"
    ),
    "responsible_unit": (
        "ระบุชื่อหน่วยงาน ที่อยู่ หมายเลขโทรศัพท์ โทรสาร ไปรษณีย์อิเล็กทรอนิกส์ "
        "และเว็บไซต์สำหรับเสนอแนะวิจารณ์ร่างขอบเขตของงาน "
        "ปิดท้ายด้วยหมายเหตุเงื่อนไขพระราชบัญญัติงบประมาณรายจ่ายประจำปีเมื่อยังไม่ได้รับจัดสรร"
    ),
}

SCOPE_HINTS: dict[str, str] = {
    "scope.items": "บัญชีรายการพร้อมจำนวนและหน่วยนับ เรียงเป็นตาราง (ลำดับ / รายการ / จำนวน / หน่วย)",
    "scope.general_conditions": "ของใหม่ ไม่ใช่ของใช้แล้ว (Used) ล้าสมัย (Obsolete) หรือปรับปรุงใหม่ (Reconditioned) ยังอยู่ในสายการผลิต ใช้กับระบบไฟฟ้าในประเทศไทยได้ และมีมาตรฐานรับรอง",
    "scope.specification": "อ้างคุณลักษณะเฉพาะรายรายการในเอกสารแนบ และกำหนดให้ยื่นตารางเปรียบเทียบคุณลักษณะพร้อมแคตตาล็อกที่ทำแถบสีอ้างอิงหน้า",
    "scope.installation": "สถานที่ติดตั้ง จำนวนจุด งานตั้งค่าที่ต้องทำ การเดินสายสัญญาณ การติดสติกเกอร์ทรัพย์สิน และสิทธิของหน่วยงานในการเปลี่ยนแปลงสถานที่ติดตั้ง",
    "scope.delivery_acceptance": "เงื่อนไขการแจ้งส่งมอบล่วงหน้าเป็นลายลักษณ์อักษร วิธีตรวจรับ และเอกสารที่ต้องแนบตอนส่งมอบ",
    "scope.training": "หลักสูตร จำนวนผู้เข้าอบรม จำนวนรุ่น สถานที่ และการที่คู่สัญญารับผิดชอบค่าใช้จ่ายทั้งหมด พร้อมแจ้งกำหนดล่วงหน้า",
    "scope.documents": "คู่มือติดตั้ง คู่มือใช้งาน คู่มือผู้ดูแลระบบ จำนวนชุด รูปแบบเอกสารและสื่อบันทึกข้อมูล",
    "scope.after_sales": "บริการสนับสนุนระหว่างรับประกัน รอบการบำรุงรักษาเชิงป้องกัน เวลาเข้าแก้ไข และค่าปรับกรณีไม่ปฏิบัติตาม",
    "scope.system_overview": "สถาปัตยกรรมระบบเป้าหมาย จำนวนผู้ใช้ ปริมาณข้อมูล และสภาพแวดล้อมที่ต้องรองรับ",
    "scope.functional": "แจกแจงโมดูลและหน้าที่การทำงานเป็นข้อย่อย ทุกข้อต้องตรวจรับได้",
    "scope.integration": "ระบบปลายทางที่ต้องเชื่อมโยง รูปแบบการเชื่อมโยง (เช่น RESTful API) และขอบเขตการโอนย้ายข้อมูลเดิม",
    "scope.licenses": "รายการลิขสิทธิ์ซอฟต์แวร์ จำนวนสิทธิ์ ระยะเวลา และเงื่อนไขการอัปเกรดระหว่างรับประกัน",
    "scope.standards_security": "มาตรฐานที่ต้องผ่าน เช่น มาตรฐานเว็บไซต์ภาครัฐ OWASP Top 10 ISO/IEC 27001 และการประเมินช่องโหว่ก่อนขึ้นใช้งานจริง รวมถึงการคุ้มครองข้อมูลส่วนบุคคล",
    "scope.testing": "แผนการทดสอบ ประเภทการทดสอบ (Functional, Integration, Performance, Security, UAT) และเกณฑ์การยอมรับ",
    "scope.deliverable_docs": "เอกสารระบบที่ต้องส่งมอบ (System Document, Use Case, ER-Diagram, Data Dictionary) และซอร์สโค้ดฉบับสมบูรณ์ล่าสุดก่อนสิ้นสุดการรับประกัน",
    "scope.project_team": "ตำแหน่ง จำนวนคน คุณวุฒิ และประสบการณ์ขั้นต่ำ พร้อมแบบฟอร์มประวัติบุคลากร",
    "scope.sla_warranty": "เวลาเข้าดำเนินการ เวลาแก้ไขให้แล้วเสร็จ เวลาที่ยอมให้ระบบขัดข้องต่อเดือน และเจ้าหน้าที่ประจำ ณ หน่วยงาน",
    "scope.asset_list": "ตารางอุปกรณ์หรือระบบงานที่รับผิดชอบ ระบุยี่ห้อ รุ่น จำนวน และรายการที่ไม่รวมอยู่ในการบำรุงรักษา",
    "scope.cm": "นิยามการบำรุงรักษาแบบไม่มีกำหนดเวลาแน่นอน ขั้นตอนเมื่อได้รับแจ้ง และการจัดหาอุปกรณ์ทดแทนระหว่างซ่อม",
    "scope.pm": "รอบการเข้าบำรุงรักษา (ทุก ๑ / ๓ / ๖ / ๑๒ เดือน) รายการตรวจสอบ การออกใบรับบริการ และเงื่อนไขรายการที่ต้องตัดระบบ",
    "scope.sla": "เวลาเข้าถึงหน้างาน เวลาแก้ไขให้แล้วเสร็จ เวลาที่ยอมให้ขัดข้องต่อเดือน และค่าตัวถ่วงของอุปกรณ์แต่ละรายการ",
    "scope.helpdesk": "ศูนย์รับแจ้งเหตุตลอด ๒๔ ชั่วโมง ช่องทางรับแจ้ง ข้อมูลที่ต้องบันทึก และการส่งต่อปัญหา",
    "scope.spare_parts": "การบำรุงรักษาแบบรวมอะไหล่ รายการวัสดุสิ้นเปลืองที่รวมและไม่รวม และคุณภาพอะไหล่ทดแทน",
    "scope.onsite_staff": "เจ้าหน้าที่ประจำ จำนวน คุณวุฒิ เวลาปฏิบัติงาน และการทำงานร่วมกับเจ้าหน้าที่ของหน่วยงาน",
    "scope.reporting": "รายงานผลการปฏิบัติงานรายเดือนหรือราย ๓ เดือน แยกตามระบบ พร้อมสถิติปัญหาและวิธีแก้ไข",
    "scope.backup": "รอบการสำรองข้อมูล สื่อบันทึก การส่งมอบสื่อสำรอง และขั้นตอนการกู้คืนที่ต้องได้รับความเห็นชอบก่อน",
    "scope.service_spec": "ความเร็วหรือปริมาณบริการแยกรายจุด เงื่อนไขไม่จำกัดปริมาณข้อมูลและช่วงเวลา",
    "scope.provided_equipment": "อุปกรณ์และสื่อสัญญาณที่ผู้ให้เช่าจัดหาโดยไม่คิดค่าบริการเพิ่ม และรายการที่หน่วยงานจัดหาเอง",
    "scope.availability": "เส้นทางสำรองต่างชุมสาย การสลับเส้นทางอัตโนมัติ และแหล่งจ่ายไฟสำรองของอุปกรณ์",
    "scope.noc": "ศูนย์รับแจ้งเหตุตลอด ๒๔ ชั่วโมงไม่เว้นวันหยุด เวลาตอบรับ และการแจ้งเตือนเชิงรุก",
    "scope.usage_report": "ระบบรายงานปริมาณการใช้งานแบบออนไลน์ที่หน่วยงานเข้าดูได้ตลอดอายุสัญญา และรายงานสรุปรายเดือน",
    "scope.lease_maintenance": "หน้าที่บำรุงรักษาอุปกรณ์และวงจรให้ใช้งานได้ดีตลอดอายุสัญญาโดยไม่คิดค่าใช้จ่ายเพิ่ม",
    "scope.lessee_rights": "สิทธิขอปรับเพิ่มความเร็วชั่วคราว การย้ายจุดติดตั้งภายในสถานที่เดียวกัน และการเปลี่ยนอุปกรณ์เมื่อพบช่องโหว่",
    "scope.workload": "ปริมาณงานทั้งหมดพร้อมหน่วยนับที่ตรวจนับได้ และวิธีคำนวณปริมาณ",
    "scope.workflow": "ขั้นตอนการปฏิบัติงานเรียงตามลำดับ ตั้งแต่รับงานจนส่งมอบ",
    "scope.quality_standard": "เกณฑ์คุณภาพที่วัดได้ เช่น ความละเอียดของไฟล์ รูปแบบการตั้งชื่อ และอัตราความผิดพลาดที่ยอมรับได้",
    "scope.resources": "บุคลากร เครื่องมือ และสถานที่ปฏิบัติงานที่คู่สัญญาต้องจัดหาเอง",
    "scope.custody": "การขนย้าย การรักษาความปลอดภัย และความรับผิดต่อทรัพย์สินหรือเอกสารของหน่วยงาน",
    "scope.progress_report": "ความถี่และรูปแบบของรายงานความคืบหน้า",
    "scope.output_delivery": "รูปแบบผลงาน จำนวนชุด สื่อบันทึกข้อมูล และสถานที่ส่งมอบ",
    "scope.methodology": "กรอบแนวคิด ระเบียบวิธี และแผนการดำเนินงานที่ต้องได้รับความเห็นชอบก่อนเริ่มงาน",
    "scope.population": "กลุ่มเป้าหมายตามหลักสถิติ จำนวนขั้นต่ำ และอัตราตอบกลับขั้นต่ำที่ใช้เป็นเงื่อนไขตรวจรับ",
    "scope.instrument": "เครื่องมือเก็บข้อมูล เกณฑ์การให้คะแนนรายข้อ และกลไกทดสอบความแม่นยำ",
    "scope.fieldwork": "วิธีเก็บข้อมูล การติดตาม และการตรวจสอบความถูกต้องของข้อมูลที่ได้รับ",
    "scope.analysis": "วิธีวิเคราะห์ เครื่องมือทางสถิติที่ใช้ และรูปแบบการนำเสนอผล เช่น แดชบอร์ด",
    "scope.expert_review": "จำนวนครั้งของการประชุม จำนวนผู้เชี่ยวชาญขั้นต่ำ และการที่คู่สัญญารับผิดชอบค่าตอบแทน",
    "scope.reports": "รายงานขั้นต้น ขั้นกลาง ร่างฉบับสมบูรณ์ และฉบับสมบูรณ์ พร้อมจำนวนชุดและรูปแบบไฟล์",
    "scope.expert_team": "ตำแหน่ง คุณวุฒิ ประสบการณ์ จำนวนคน และปริมาณงานเป็น man-month",
    "scope.works": "รายการงานก่อสร้างหรือปรับปรุงพร้อมปริมาณงานตามแบบ",
    "scope.drawings": "แบบรูปรายการ มาตรฐานวัสดุ และมาตรฐานฝีมือช่างที่อ้างอิง",
    "scope.demolition": "ขอบเขตการรื้อถอน การขนย้ายวัสดุ และการจัดการเศษวัสดุ",
    "scope.site_access": "เวลาเข้าปฏิบัติงาน การขออนุญาต มาตรการความปลอดภัย และการไม่รบกวนการปฏิบัติราชการ",
    "scope.supervision": "ผู้ควบคุมงาน การรายงานความก้าวหน้า และการตรวจสอบคุณภาพงานแต่ละขั้น",
    "scope.handover": "การส่งมอบพื้นที่ การทำความสะอาด และการส่งมอบแบบ As-built",
}

QUALIFICATION_HINTS: dict[str, str] = {
    "qual.legal": "คัดลอกชุดคุณสมบัติมาตรฐานตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐ ครบทุกข้อ แล้วต่อด้วยการลงทะเบียนในระบบจัดซื้อจัดจ้างภาครัฐด้วยอิเล็กทรอนิกส์",
    "qual.jv": "เงื่อนไขสัดส่วนการเข้าร่วมค้า ผลงานของผู้เข้าร่วมค้าหลัก และการมอบอำนาจในการยื่นข้อเสนอ",
    "qual.networth": "ระบุทางเลือกให้ครบ ทั้งงบแสดงฐานะการเงิน ทุนจดทะเบียนชำระแล้วตามบันไดวงเงิน วงเงินสินเชื่อจากสถาบันการเงิน และข้อยกเว้นตามที่กฎหมายกำหนด",
    "qual.experience": "ระบุประเภทผลงานให้ตรงกับงานที่จัดซื้อจัดจ้าง มูลค่าขั้นต่ำต่อสัญญา จำนวนผลงาน จำนวนปีย้อนหลัง และต้องเป็นคู่สัญญาโดยตรงกับหน่วยงานของรัฐ",
    "qual.personnel": "ตารางบุคลากรหลัก (ตำแหน่ง / คุณวุฒิ / ประสบการณ์ขั้นต่ำ / จำนวนคน) พร้อมกำหนดให้ยื่นแบบฟอร์มประวัติและเอกสารรับรอง",
    "qual.dealer": "หนังสือแต่งตั้งตัวแทนจำหน่ายจากเจ้าของผลิตภัณฑ์ ระบุรายการที่ต้องมีหนังสือแต่งตั้ง และต้องระบุชื่อโครงการ",
    "qual.license": "ใบอนุญาตประกอบกิจการตามกฎหมายเฉพาะ พร้อมขีดความสามารถขั้นต่ำที่ต้องแสดงหลักฐาน",
    "qual.documents": "บัญชีเอกสารที่ต้องยื่น ระบุรูปแบบ (ต้นฉบับหรือสำเนารับรอง) จำนวนชุด อายุเอกสาร และผลของการยื่นไม่ครบ",
}


def hint_for(key: str) -> str:
    if key in SCOPE_HINTS:
        return SCOPE_HINTS[key]
    if key in QUALIFICATION_HINTS:
        return QUALIFICATION_HINTS[key]
    return SECTION_HINTS.get(key, "")
