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
    "lease_service": "เช่าบริการ/สื่อสาร/ยานพาหนะ",
    "buy_goods": "จัดซื้อครุภัณฑ์/ฮาร์ดแวร์",
    "construction": "งานปรับปรุง/ก่อสร้าง",
    "hire_consult": "จ้างที่ปรึกษา/สำรวจ/วิเคราะห์/เฝ้าระวังไซเบอร์",
    "hire_service": "จ้างเหมาบริการงานเอกสาร",
}

DEFAULT_PROCUREMENT_TYPE = "buy_goods"

# Wording of the counterparty, per type. Real TORs are consistent about this
# and mixing them ("ผู้ขาย" in a จ้าง document) is a common drafting defect.
CONTRACTOR_HIRE = "ผู้รับจ้าง"
CONTRACTOR_TERM: dict[str, str] = {
    "buy_goods": "ผู้ขาย",
    "hire_develop": CONTRACTOR_HIRE,
    "hire_maintain": CONTRACTOR_HIRE,
    "lease_service": "ผู้ให้เช่า",
    "hire_service": CONTRACTOR_HIRE,
    "hire_consult": CONTRACTOR_HIRE,
    "construction": CONTRACTOR_HIRE,
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
# Semantic keys defined once (reused in profiles, hints, and legacy maps)
# ---------------------------------------------------------------------------
class Qual:
    LEGAL = "qual.legal"
    JV = "qual.jv"
    NETWORTH = "qual.networth"
    EXPERIENCE = "qual.experience"
    PERSONNEL = "qual.personnel"
    DEALER = "qual.dealer"
    LICENSE = "qual.license"
    DOCUMENTS = "qual.documents"


class Scope:
    ITEMS = "scope.items"
    GENERAL_CONDITIONS = "scope.general_conditions"
    SPECIFICATION = "scope.specification"
    INSTALLATION = "scope.installation"
    DELIVERY_ACCEPTANCE = "scope.delivery_acceptance"
    TRAINING = "scope.training"
    DOCUMENTS = "scope.documents"
    AFTER_SALES = "scope.after_sales"
    SYSTEM_OVERVIEW = "scope.system_overview"
    FUNCTIONAL = "scope.functional"
    INTEGRATION = "scope.integration"
    LICENSES = "scope.licenses"
    STANDARDS_SECURITY = "scope.standards_security"
    TESTING = "scope.testing"
    DELIVERABLE_DOCS = "scope.deliverable_docs"
    PROJECT_TEAM = "scope.project_team"
    SLA_WARRANTY = "scope.sla_warranty"
    ASSET_LIST = "scope.asset_list"
    CM = "scope.cm"
    PM = "scope.pm"
    SLA = "scope.sla"
    HELPDESK = "scope.helpdesk"
    SPARE_PARTS = "scope.spare_parts"
    ONSITE_STAFF = "scope.onsite_staff"
    REPORTING = "scope.reporting"
    BACKUP = "scope.backup"
    SERVICE_SPEC = "scope.service_spec"
    PROVIDED_EQUIPMENT = "scope.provided_equipment"
    AVAILABILITY = "scope.availability"
    NOC = "scope.noc"
    USAGE_REPORT = "scope.usage_report"
    LEASE_MAINTENANCE = "scope.lease_maintenance"
    LESSEE_RIGHTS = "scope.lessee_rights"
    WORKLOAD = "scope.workload"
    WORKFLOW = "scope.workflow"
    QUALITY_STANDARD = "scope.quality_standard"
    RESOURCES = "scope.resources"
    CUSTODY = "scope.custody"
    PROGRESS_REPORT = "scope.progress_report"
    OUTPUT_DELIVERY = "scope.output_delivery"
    METHODOLOGY = "scope.methodology"
    POPULATION = "scope.population"
    INSTRUMENT = "scope.instrument"
    FIELDWORK = "scope.fieldwork"
    ANALYSIS = "scope.analysis"
    EXPERT_REVIEW = "scope.expert_review"
    REPORTS = "scope.reports"
    EXPERT_TEAM = "scope.expert_team"
    WORKS = "scope.works"
    DRAWINGS = "scope.drawings"
    DEMOLITION = "scope.demolition"
    SITE_ACCESS = "scope.site_access"
    SUPERVISION = "scope.supervision"
    HANDOVER = "scope.handover"

# ข้อ ๓ คุณสมบัติของผู้ยื่นข้อเสนอ — subsections
# ---------------------------------------------------------------------------
# Real TORs open with the same nine statutory clauses, then add
# project-specific clauses. b517e2e3 splits the section into
# "ส่วนที่ ๑ คุณสมบัติ" and "ส่วนที่ ๒ เอกสารที่ต้องยื่น"; we keep that split
# as the last subsection instead of a separate top-level section.

QUALIFICATION_SUBSECTIONS: dict[str, str] = {
    Qual.LEGAL: "คุณสมบัติทั่วไปตามกฎหมายและการลงทะเบียนในระบบ e-GP",
    Qual.JV: "กรณีกิจการร่วมค้า",
    Qual.NETWORTH: "มูลค่าสุทธิของกิจการ ทุนจดทะเบียน หรือวงเงินสินเชื่อ",
    Qual.EXPERIENCE: "ผลงานประเภทเดียวกันกับงานที่จัดซื้อจัดจ้าง",
    Qual.PERSONNEL: "บุคลากรหลักในโครงการ",
    Qual.DEALER: "หนังสือแต่งตั้งตัวแทนจำหน่ายจากเจ้าของผลิตภัณฑ์",
    Qual.LICENSE: "ใบอนุญาตประกอบกิจการตามกฎหมายเฉพาะ",
    Qual.DOCUMENTS: "เอกสารและหลักฐานที่ผู้ยื่นข้อเสนอต้องนำมายื่น",
}

# Subsections used by each procurement type, in order.
QUALIFICATION_BY_TYPE: dict[str, list[str]] = {
    "buy_goods": [
        Qual.LEGAL, Qual.JV, Qual.NETWORTH, Qual.EXPERIENCE,
        Qual.DEALER, Qual.DOCUMENTS,
    ],
    "hire_develop": [
        Qual.LEGAL, Qual.JV, Qual.NETWORTH, Qual.EXPERIENCE,
        Qual.PERSONNEL, Qual.DOCUMENTS,
    ],
    "hire_maintain": [
        Qual.LEGAL, Qual.JV, Qual.NETWORTH, Qual.EXPERIENCE,
        Qual.PERSONNEL, Qual.DOCUMENTS,
    ],
    "lease_service": [
        Qual.LEGAL, Qual.JV, Qual.NETWORTH, Qual.LICENSE,
        Qual.DOCUMENTS,
    ],
    "hire_service": [
        Qual.LEGAL, Qual.JV, Qual.NETWORTH, Qual.EXPERIENCE,
        Qual.DOCUMENTS,
    ],
    "hire_consult": [
        Qual.LEGAL, Qual.EXPERIENCE, Qual.PERSONNEL, Qual.DOCUMENTS,
    ],
    "construction": [
        Qual.LEGAL, Qual.JV, Qual.NETWORTH, Qual.EXPERIENCE,
        Qual.LICENSE, Qual.DOCUMENTS,
    ],
}

# ---------------------------------------------------------------------------
# ข้อ ๔ ขอบเขตของงาน — subsections per procurement type
# ---------------------------------------------------------------------------

SCOPE_SUBSECTIONS: dict[str, str] = {
    # งานซื้อ
    Scope.ITEMS: "รายการพัสดุที่จัดซื้อและจำนวน",
    Scope.GENERAL_CONDITIONS: "เงื่อนไขทั่วไปของพัสดุ",
    Scope.SPECIFICATION: "คุณลักษณะเฉพาะของพัสดุ",
    Scope.INSTALLATION: "เงื่อนไขการติดตั้งและสถานที่ติดตั้ง",
    Scope.DELIVERY_ACCEPTANCE: "เงื่อนไขการส่งมอบและการตรวจรับ",
    Scope.TRAINING: "การฝึกอบรมและการถ่ายทอดความรู้",
    Scope.DOCUMENTS: "เอกสารและคู่มือที่ต้องส่งมอบ",
    Scope.AFTER_SALES: "การบริการสนับสนุนและบำรุงรักษาระหว่างรับประกัน",
    # งานจ้างพัฒนาระบบ
    Scope.SYSTEM_OVERVIEW: "ภาพรวมและสถาปัตยกรรมของระบบที่ต้องการ",
    Scope.FUNCTIONAL: "ขอบเขตระบบงานและหน้าที่การทำงานที่ต้องพัฒนา",
    Scope.INTEGRATION: "การเชื่อมโยงระบบและการโอนย้ายข้อมูล",
    Scope.LICENSES: "ครุภัณฑ์และลิขสิทธิ์ซอฟต์แวร์ที่ต้องจัดหา",
    Scope.STANDARDS_SECURITY: "มาตรฐานและข้อกำหนดด้านความมั่นคงปลอดภัยสารสนเทศ",
    Scope.TESTING: "การทดสอบระบบและเกณฑ์การยอมรับ",
    Scope.DELIVERABLE_DOCS: "เอกสารระบบและซอร์สโค้ดที่ต้องส่งมอบ",
    Scope.PROJECT_TEAM: "บุคลากรประจำโครงการ",
    Scope.SLA_WARRANTY: "การบำรุงรักษาและระดับการให้บริการระหว่างรับประกัน",
    # งานจ้างบำรุงรักษา
    Scope.ASSET_LIST: "รายการระบบและอุปกรณ์ที่ต้องบำรุงรักษา",
    Scope.CM: "การบำรุงรักษาเชิงแก้ไข",
    Scope.PM: "การบำรุงรักษาเชิงป้องกันและรอบการเข้าดำเนินการ",
    Scope.SLA: "ระดับการให้บริการ เวลาตอบสนอง และเวลาแก้ไขให้แล้วเสร็จ",
    Scope.HELPDESK: "ศูนย์รับแจ้งเหตุขัดข้องและการบริหารจัดการปัญหา",
    Scope.SPARE_PARTS: "อะไหล่ วัสดุสิ้นเปลือง และอุปกรณ์ทดแทนระหว่างซ่อม",
    Scope.ONSITE_STAFF: "บุคลากรและการปฏิบัติงานร่วมกับเจ้าหน้าที่ของหน่วยงาน",
    Scope.REPORTING: "การรายงานผลการปฏิบัติงาน",
    Scope.BACKUP: "การสำรองข้อมูลและการกู้คืนระบบ",
    # งานเช่า
    Scope.SERVICE_SPEC: "รายละเอียดบริการที่เช่าใช้",
    Scope.PROVIDED_EQUIPMENT: "อุปกรณ์และสื่อสัญญาณที่ผู้ให้เช่าต้องจัดหา",
    Scope.AVAILABILITY: "ความพร้อมใช้งาน เส้นทางสำรอง และการสลับเส้นทาง",
    Scope.NOC: "ศูนย์รับแจ้งเหตุตลอด ๒๔ ชั่วโมงและการแจ้งเตือน",
    Scope.USAGE_REPORT: "ระบบรายงานและการตรวจสอบปริมาณการใช้งาน",
    Scope.LEASE_MAINTENANCE: "การบำรุงรักษาระบบตลอดอายุสัญญาเช่า",
    Scope.LESSEE_RIGHTS: "สิทธิของผู้เช่าระหว่างอายุสัญญา",
    # งานจ้างบริการ
    Scope.WORKLOAD: "ปริมาณงานและหน่วยนับ",
    Scope.WORKFLOW: "กระบวนการปฏิบัติงาน",
    Scope.QUALITY_STANDARD: "มาตรฐานคุณภาพของผลงาน",
    Scope.RESOURCES: "บุคลากร เครื่องมือ และสถานที่ปฏิบัติงาน",
    Scope.CUSTODY: "การขนย้ายและการดูแลรักษาทรัพย์สินของผู้ว่าจ้าง",
    Scope.PROGRESS_REPORT: "การรายงานความคืบหน้า",
    Scope.OUTPUT_DELIVERY: "การส่งมอบผลงานและรูปแบบสื่อบันทึกข้อมูล",
    # งานจ้างที่ปรึกษา/สำรวจ
    Scope.METHODOLOGY: "กรอบแนวคิดและระเบียบวิธีดำเนินงาน",
    Scope.POPULATION: "กลุ่มเป้าหมาย ขนาดตัวอย่าง และอัตราตอบกลับขั้นต่ำ",
    Scope.INSTRUMENT: "เครื่องมือเก็บข้อมูลและการทดสอบความแม่นยำ",
    Scope.FIELDWORK: "การเก็บรวบรวมและตรวจสอบความถูกต้องของข้อมูล",
    Scope.ANALYSIS: "การวิเคราะห์ข้อมูลและการนำเสนอผล",
    Scope.EXPERT_REVIEW: "การประชุมและการรับฟังความเห็นผู้เชี่ยวชาญ",
    Scope.REPORTS: "รายงานตามลำดับขั้นและรูปแบบการส่งมอบ",
    Scope.EXPERT_TEAM: "คณะผู้เชี่ยวชาญและปริมาณงานเป็นคน-เดือน",
    # งานก่อสร้าง/ปรับปรุง
    Scope.WORKS: "รายการงานก่อสร้างหรือปรับปรุง",
    Scope.DRAWINGS: "แบบรูปรายการและมาตรฐานวัสดุ",
    Scope.DEMOLITION: "งานรื้อถอนและการจัดการพื้นที่",
    Scope.SITE_ACCESS: "เงื่อนไขการเข้าปฏิบัติงานและความปลอดภัยในการทำงาน",
    Scope.SUPERVISION: "การควบคุมงานและการตรวจสอบคุณภาพ",
    Scope.HANDOVER: "การส่งมอบพื้นที่และแบบตามที่สร้างจริง",
}

SCOPE_BY_TYPE: dict[str, list[str]] = {
    "buy_goods": [
        Scope.ITEMS, Scope.GENERAL_CONDITIONS, Scope.SPECIFICATION,
        Scope.INSTALLATION, Scope.DELIVERY_ACCEPTANCE, Scope.TRAINING,
        Scope.DOCUMENTS, Scope.AFTER_SALES,
    ],
    "hire_develop": [
        Scope.SYSTEM_OVERVIEW, Scope.FUNCTIONAL, Scope.INTEGRATION,
        Scope.LICENSES, Scope.STANDARDS_SECURITY, Scope.TESTING,
        Scope.DELIVERABLE_DOCS, Scope.TRAINING, Scope.PROJECT_TEAM,
        Scope.SLA_WARRANTY,
    ],
    "hire_maintain": [
        Scope.ASSET_LIST, Scope.CM, Scope.PM, Scope.SLA,
        Scope.HELPDESK, Scope.SPARE_PARTS, Scope.ONSITE_STAFF,
        Scope.REPORTING, Scope.BACKUP,
    ],
    "lease_service": [
        Scope.SERVICE_SPEC, Scope.PROVIDED_EQUIPMENT, Scope.AVAILABILITY,
        Scope.NOC, Scope.USAGE_REPORT, Scope.LEASE_MAINTENANCE,
        Scope.LESSEE_RIGHTS,
    ],
    "hire_service": [
        Scope.WORKLOAD, Scope.WORKFLOW, Scope.QUALITY_STANDARD,
        Scope.RESOURCES, Scope.CUSTODY, Scope.PROGRESS_REPORT,
        Scope.OUTPUT_DELIVERY,
    ],
    "hire_consult": [
        Scope.METHODOLOGY, Scope.POPULATION, Scope.INSTRUMENT,
        Scope.FIELDWORK, Scope.ANALYSIS, Scope.EXPERT_REVIEW,
        Scope.REPORTS, Scope.EXPERT_TEAM,
    ],
    "construction": [
        Scope.WORKS, Scope.DRAWINGS, Scope.DEMOLITION,
        Scope.SITE_ACCESS, Scope.SUPERVISION, Scope.HANDOVER,
        Scope.DELIVERY_ACCEPTANCE,
    ],
}

# Subsections that must not be left empty for the draft to count as complete.
SCOPE_REQUIRED_BY_TYPE: dict[str, list[str]] = {
    "buy_goods": [Scope.ITEMS, Scope.SPECIFICATION, Scope.DELIVERY_ACCEPTANCE],
    "hire_develop": [Scope.FUNCTIONAL, Scope.DELIVERABLE_DOCS, Scope.TESTING],
    "hire_maintain": [Scope.ASSET_LIST, Scope.CM, Scope.PM, Scope.SLA],
    "lease_service": [Scope.SERVICE_SPEC, Scope.AVAILABILITY, Scope.NOC],
    "hire_service": [Scope.WORKLOAD, Scope.WORKFLOW, Scope.QUALITY_STANDARD],
    "hire_consult": [Scope.METHODOLOGY, Scope.POPULATION, Scope.REPORTS],
    "construction": [Scope.WORKS, Scope.DRAWINGS, Scope.HANDOVER],
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
    Scope.ITEMS: "บัญชีรายการพร้อมจำนวนและหน่วยนับ เรียงเป็นตาราง (ลำดับ / รายการ / จำนวน / หน่วย)",
    Scope.GENERAL_CONDITIONS: "ของใหม่ ไม่ใช่ของใช้แล้ว ล้าสมัย หรือปรับปรุงใหม่ ยังอยู่ในสายการผลิต ใช้กับระบบไฟฟ้าในประเทศไทยได้ และมีมาตรฐานรับรอง",
    Scope.SPECIFICATION: "อ้างคุณลักษณะเฉพาะรายรายการในเอกสารแนบ และกำหนดให้ยื่นตารางเปรียบเทียบคุณลักษณะพร้อมแคตตาล็อกที่ทำแถบสีอ้างอิงหน้า",
    Scope.INSTALLATION: "สถานที่ติดตั้ง จำนวนจุด งานตั้งค่าที่ต้องทำ การเดินสายสัญญาณ การติดสติกเกอร์ทรัพย์สิน และสิทธิของหน่วยงานในการเปลี่ยนแปลงสถานที่ติดตั้ง",
    Scope.DELIVERY_ACCEPTANCE: "เงื่อนไขการแจ้งส่งมอบล่วงหน้าเป็นลายลักษณ์อักษร วิธีตรวจรับ และเอกสารที่ต้องแนบตอนส่งมอบ",
    Scope.TRAINING: "หลักสูตร จำนวนผู้เข้าอบรม จำนวนรุ่น สถานที่ และการที่คู่สัญญารับผิดชอบค่าใช้จ่ายทั้งหมด พร้อมแจ้งกำหนดล่วงหน้า",
    Scope.DOCUMENTS: "คู่มือติดตั้ง คู่มือใช้งาน คู่มือผู้ดูแลระบบ จำนวนชุด รูปแบบเอกสารและสื่อบันทึกข้อมูล",
    Scope.AFTER_SALES: "บริการสนับสนุนระหว่างรับประกัน รอบการบำรุงรักษาเชิงป้องกัน เวลาเข้าแก้ไข และค่าปรับกรณีไม่ปฏิบัติตาม",
    Scope.SYSTEM_OVERVIEW: "สถาปัตยกรรมระบบเป้าหมาย จำนวนผู้ใช้ ปริมาณข้อมูล และสภาพแวดล้อมที่ต้องรองรับ",
    Scope.FUNCTIONAL: "แจกแจงโมดูลและหน้าที่การทำงานเป็นข้อย่อย ทุกข้อต้องตรวจรับได้",
    Scope.INTEGRATION: "ระบบปลายทางที่ต้องเชื่อมโยง รูปแบบการเชื่อมโยงผ่านส่วนต่อประสานโปรแกรม และขอบเขตการโอนย้ายข้อมูลเดิม",
    Scope.LICENSES: "รายการลิขสิทธิ์ซอฟต์แวร์ จำนวนสิทธิ์ ระยะเวลา และเงื่อนไขการอัปเกรดระหว่างรับประกัน",
    Scope.STANDARDS_SECURITY: "มาตรฐานที่ต้องผ่าน เช่น มาตรฐานเว็บไซต์ภาครัฐ OWASP Top 10 ISO/IEC 27001 และการประเมินช่องโหว่ก่อนขึ้นใช้งานจริง รวมถึงการคุ้มครองข้อมูลส่วนบุคคล",
    Scope.TESTING: "แผนการทดสอบ ประเภทการทดสอบ (หน้าที่การทำงาน การเชื่อมโยง ประสิทธิภาพ ความมั่นคงปลอดภัย และการยอมรับโดยผู้ใช้) และเกณฑ์การยอมรับ",
    Scope.DELIVERABLE_DOCS: "เอกสารระบบที่ต้องส่งมอบ (เอกสารระบบ กรณีใช้งาน แผนภาพความสัมพันธ์ข้อมูล พจนานุกรมข้อมูล) และซอร์สโค้ดฉบับสมบูรณ์ล่าสุดก่อนสิ้นสุดการรับประกัน",
    Scope.PROJECT_TEAM: "ตำแหน่ง จำนวนคน คุณวุฒิ และประสบการณ์ขั้นต่ำ พร้อมแบบฟอร์มประวัติบุคลากร",
    Scope.SLA_WARRANTY: "เวลาเข้าดำเนินการ เวลาแก้ไขให้แล้วเสร็จ เวลาที่ยอมให้ระบบขัดข้องต่อเดือน และเจ้าหน้าที่ประจำ ณ หน่วยงาน",
    Scope.ASSET_LIST: "ตารางอุปกรณ์หรือระบบงานที่รับผิดชอบ ระบุยี่ห้อ รุ่น จำนวน และรายการที่ไม่รวมอยู่ในการบำรุงรักษา",
    Scope.CM: "นิยามการบำรุงรักษาแบบไม่มีกำหนดเวลาแน่นอน ขั้นตอนเมื่อได้รับแจ้ง และการจัดหาอุปกรณ์ทดแทนระหว่างซ่อม",
    Scope.PM: "รอบการเข้าบำรุงรักษา (ทุก ๑ / ๓ / ๖ / ๑๒ เดือน) รายการตรวจสอบ การออกใบรับบริการ และเงื่อนไขรายการที่ต้องตัดระบบ",
    Scope.SLA: "เวลาเข้าถึงหน้างาน เวลาแก้ไขให้แล้วเสร็จ เวลาที่ยอมให้ขัดข้องต่อเดือน และค่าตัวถ่วงของอุปกรณ์แต่ละรายการ",
    Scope.HELPDESK: "ศูนย์รับแจ้งเหตุตลอด ๒๔ ชั่วโมง ช่องทางรับแจ้ง ข้อมูลที่ต้องบันทึก และการส่งต่อปัญหา",
    Scope.SPARE_PARTS: "การบำรุงรักษาแบบรวมอะไหล่ รายการวัสดุสิ้นเปลืองที่รวมและไม่รวม และคุณภาพอะไหล่ทดแทน",
    Scope.ONSITE_STAFF: "เจ้าหน้าที่ประจำ จำนวน คุณวุฒิ เวลาปฏิบัติงาน และการทำงานร่วมกับเจ้าหน้าที่ของหน่วยงาน",
    Scope.REPORTING: "รายงานผลการปฏิบัติงานรายเดือนหรือราย ๓ เดือน แยกตามระบบ พร้อมสถิติปัญหาและวิธีแก้ไข",
    Scope.BACKUP: "รอบการสำรองข้อมูล สื่อบันทึก การส่งมอบสื่อสำรอง และขั้นตอนการกู้คืนที่ต้องได้รับความเห็นชอบก่อน",
    Scope.SERVICE_SPEC: "ความเร็วหรือปริมาณบริการแยกรายจุด เงื่อนไขไม่จำกัดปริมาณข้อมูลและช่วงเวลา",
    Scope.PROVIDED_EQUIPMENT: "อุปกรณ์และสื่อสัญญาณที่ผู้ให้เช่าจัดหาโดยไม่คิดค่าบริการเพิ่ม และรายการที่หน่วยงานจัดหาเอง",
    Scope.AVAILABILITY: "เส้นทางสำรองต่างชุมสาย การสลับเส้นทางอัตโนมัติ และแหล่งจ่ายไฟสำรองของอุปกรณ์",
    Scope.NOC: "ศูนย์รับแจ้งเหตุตลอด ๒๔ ชั่วโมงไม่เว้นวันหยุด เวลาตอบรับ และการแจ้งเตือนเชิงรุก",
    Scope.USAGE_REPORT: "ระบบรายงานปริมาณการใช้งานแบบออนไลน์ที่หน่วยงานเข้าดูได้ตลอดอายุสัญญา และรายงานสรุปรายเดือน",
    Scope.LEASE_MAINTENANCE: "หน้าที่บำรุงรักษาอุปกรณ์และวงจรให้ใช้งานได้ดีตลอดอายุสัญญาโดยไม่คิดค่าใช้จ่ายเพิ่ม",
    Scope.LESSEE_RIGHTS: "สิทธิขอปรับเพิ่มความเร็วชั่วคราว การย้ายจุดติดตั้งภายในสถานที่เดียวกัน และการเปลี่ยนอุปกรณ์เมื่อพบช่องโหว่",
    Scope.WORKLOAD: "ปริมาณงานทั้งหมดพร้อมหน่วยนับที่ตรวจนับได้ และวิธีคำนวณปริมาณ",
    Scope.WORKFLOW: "ขั้นตอนการปฏิบัติงานเรียงตามลำดับ ตั้งแต่รับงานจนส่งมอบ",
    Scope.QUALITY_STANDARD: "เกณฑ์คุณภาพที่วัดได้ เช่น ความละเอียดของไฟล์ รูปแบบการตั้งชื่อ และอัตราความผิดพลาดที่ยอมรับได้",
    Scope.RESOURCES: "บุคลากร เครื่องมือ และสถานที่ปฏิบัติงานที่คู่สัญญาต้องจัดหาเอง",
    Scope.CUSTODY: "การขนย้าย การรักษาความปลอดภัย และความรับผิดต่อทรัพย์สินหรือเอกสารของหน่วยงาน",
    Scope.PROGRESS_REPORT: "ความถี่และรูปแบบของรายงานความคืบหน้า",
    Scope.OUTPUT_DELIVERY: "รูปแบบผลงาน จำนวนชุด สื่อบันทึกข้อมูล และสถานที่ส่งมอบ",
    Scope.METHODOLOGY: "กรอบแนวคิด ระเบียบวิธี และแผนการดำเนินงานที่ต้องได้รับความเห็นชอบก่อนเริ่มงาน",
    Scope.POPULATION: "กลุ่มเป้าหมายตามหลักสถิติ จำนวนขั้นต่ำ และอัตราตอบกลับขั้นต่ำที่ใช้เป็นเงื่อนไขตรวจรับ",
    Scope.INSTRUMENT: "เครื่องมือเก็บข้อมูล เกณฑ์การให้คะแนนรายข้อ และกลไกทดสอบความแม่นยำ",
    Scope.FIELDWORK: "วิธีเก็บข้อมูล การติดตาม และการตรวจสอบความถูกต้องของข้อมูลที่ได้รับ",
    Scope.ANALYSIS: "วิธีวิเคราะห์ เครื่องมือทางสถิติที่ใช้ และรูปแบบการนำเสนอผล เช่น แดชบอร์ด",
    Scope.EXPERT_REVIEW: "จำนวนครั้งของการประชุม จำนวนผู้เชี่ยวชาญขั้นต่ำ และการที่คู่สัญญารับผิดชอบค่าตอบแทน",
    Scope.REPORTS: "รายงานขั้นต้น ขั้นกลาง ร่างฉบับสมบูรณ์ และฉบับสมบูรณ์ พร้อมจำนวนชุดและรูปแบบไฟล์",
    Scope.EXPERT_TEAM: "ตำแหน่ง คุณวุฒิ ประสบการณ์ จำนวนคน และปริมาณงานเป็นคน-เดือน",
    Scope.WORKS: "รายการงานก่อสร้างหรือปรับปรุงพร้อมปริมาณงานตามแบบ",
    Scope.DRAWINGS: "แบบรูปรายการ มาตรฐานวัสดุ และมาตรฐานฝีมือช่างที่อ้างอิง",
    Scope.DEMOLITION: "ขอบเขตการรื้อถอน การขนย้ายวัสดุ และการจัดการเศษวัสดุ",
    Scope.SITE_ACCESS: "เวลาเข้าปฏิบัติงาน การขออนุญาต มาตรการความปลอดภัย และการไม่รบกวนการปฏิบัติราชการ",
    Scope.SUPERVISION: "ผู้ควบคุมงาน การรายงานความก้าวหน้า และการตรวจสอบคุณภาพงานแต่ละขั้น",
    Scope.HANDOVER: "การส่งมอบพื้นที่ การทำความสะอาด และการส่งมอบแบบตามที่สร้างจริง",
}

QUALIFICATION_HINTS: dict[str, str] = {
    Qual.LEGAL: "คัดลอกชุดคุณสมบัติมาตรฐานตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐ ครบทุกข้อ แล้วต่อด้วยการลงทะเบียนในระบบจัดซื้อจัดจ้างภาครัฐด้วยอิเล็กทรอนิกส์",
    Qual.JV: "เงื่อนไขสัดส่วนการเข้าร่วมค้า ผลงานของผู้เข้าร่วมค้าหลัก และการมอบอำนาจในการยื่นข้อเสนอ",
    Qual.NETWORTH: "ระบุทางเลือกให้ครบ ทั้งงบแสดงฐานะการเงิน ทุนจดทะเบียนชำระแล้วตามบันไดวงเงิน วงเงินสินเชื่อจากสถาบันการเงิน และข้อยกเว้นตามที่กฎหมายกำหนด",
    Qual.EXPERIENCE: "ระบุประเภทผลงานให้ตรงกับงานที่จัดซื้อจัดจ้าง มูลค่าขั้นต่ำต่อสัญญา จำนวนผลงาน จำนวนปีย้อนหลัง และต้องเป็นคู่สัญญาโดยตรงกับหน่วยงานของรัฐ",
    Qual.PERSONNEL: "ตารางบุคลากรหลัก (ตำแหน่ง / คุณวุฒิ / ประสบการณ์ขั้นต่ำ / จำนวนคน) พร้อมกำหนดให้ยื่นแบบฟอร์มประวัติและเอกสารรับรอง",
    Qual.DEALER: "หนังสือแต่งตั้งตัวแทนจำหน่ายจากเจ้าของผลิตภัณฑ์ ระบุรายการที่ต้องมีหนังสือแต่งตั้ง และต้องระบุชื่อโครงการ",
    Qual.LICENSE: "ใบอนุญาตประกอบกิจการตามกฎหมายเฉพาะ พร้อมขีดความสามารถขั้นต่ำที่ต้องแสดงหลักฐาน",
    Qual.DOCUMENTS: "บัญชีเอกสารที่ต้องยื่น ระบุรูปแบบ (ต้นฉบับหรือสำเนารับรอง) จำนวนชุด อายุเอกสาร และผลของการยื่นไม่ครบ",
}


def hint_for(key: str) -> str:
    if key in SCOPE_HINTS:
        return SCOPE_HINTS[key]
    if key in QUALIFICATION_HINTS:
        return QUALIFICATION_HINTS[key]
    return SECTION_HINTS.get(key, "")


# ---------------------------------------------------------------------------
# Legacy s1–s13 compatibility (v1 → v2 migration)
# ---------------------------------------------------------------------------
# ``None`` means the legacy row has no home in v2 and is archived by the
# migration script instead of being written back.

LEGACY_SECTION_MAP: dict[str, tuple[str, str | None] | None] = {
    "s1": ("background", None),
    "s2": ("objective", None),
    "s3": ("qualification", None),
    "s4": ("scope", None),
    "s5": ("schedule", None),
    "s6": ("budget", None),
    "s7": ("scope", Scope.INSTALLATION),
    "s8": ("payment", None),
    "s9": ("warranty", None),
    "s10": ("penalty", None),
    "s11": ("evaluation", None),
    "s12": ("qualification", Qual.DOCUMENTS),
    "s13": ("other_conditions", None),
}

# Legacy scope subsections. ``s4.2 ระบบงานปัจจุบัน`` is deliberately dropped:
# it appears in none of the 12 example TORs.
LEGACY_SCOPE_MAP: dict[str, str | None] = {
    "s4.1": None,
    "s4.2": None,
    "s4.3": Scope.FUNCTIONAL,
    "s4.4": Scope.SPECIFICATION,
    "s4.5": Scope.LICENSES,
    "s4.6": Scope.INTEGRATION,
    "s4.7": Scope.STANDARDS_SECURITY,
    "s4.8": Scope.DELIVERABLE_DOCS,
    "s4.9": Scope.SLA,
    "s4.10": Scope.PROJECT_TEAM,
    "s4.11": Scope.PM,
    "s4.12": Scope.WORKFLOW,
    "s4.13": Scope.BACKUP,
    "s4.14": Scope.STANDARDS_SECURITY,
}

# Old ``project_type`` values on the projects table.
LEGACY_PROJECT_TYPE_MAP: dict[str, str] = {
    "it": "hire_develop",
    "construction": "construction",
    "consulting": "hire_consult",
    "general": "buy_goods",
}


def resolve_legacy(
    section_key: str, sub_key: str | None, procurement_type: str
) -> tuple[str, str | None] | None:
    """Map a v1 (section_key, sub_key) row onto the v2 taxonomy.

    Returns ``None`` when the content has no home in v2. A subsection that
    does not exist for this procurement type collapses onto its parent.
    """
    raw_sub = (sub_key or "").strip()
    if raw_sub:
        target = LEGACY_SCOPE_MAP.get(raw_sub, "__unknown__")
        if target == "__unknown__":
            return ("scope", None)
        if target is None:
            return None
        return ("scope", target if target in scope_subsections(procurement_type) else None)
    mapped = LEGACY_SECTION_MAP.get(section_key)
    if mapped is None:
        return None
    parent, sub = mapped
    if sub and sub not in subsections_for(parent, procurement_type):
        return (parent, None)
    if parent not in section_order(procurement_type):
        return ("other_conditions", None)
    return (parent, sub)


# ---------------------------------------------------------------------------
# Thai numerals for headings
# ---------------------------------------------------------------------------

_THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙"


def to_thai_numeral(value: int | str) -> str:
    return "".join(_THAI_DIGITS[int(ch)] if ch.isdigit() else ch for ch in str(value))


class TaxonomyEditError(ValueError):
    """Raised when a taxonomy change would skip CORE sections or numbering."""


def validate_taxonomy_edit(
    procurement_types: dict[str, str] | None = None,
    core: list[str] | None = None,
    extra_by_type: dict[str, list[str]] | None = None,
    closing: str | None = None,
) -> None:
    """Reject edits that drop CORE sections or produce non-contiguous numbers."""
    types = procurement_types or PROCUREMENT_TYPES
    core_list = list(core or CORE_SECTION_ORDER)
    extras = extra_by_type or EXTRA_SECTIONS_BY_TYPE
    close = closing if closing is not None else CLOSING_SECTION
    missing_core = [key for key in CORE_SECTION_ORDER if key not in core_list]
    if missing_core:
        raise TaxonomyEditError(f"CORE_SECTION_ORDER missing {missing_core}")
    for ptype in types:
        order = [*core_list, *extras.get(ptype, []), close]
        if len(order) != len(set(order)):
            raise TaxonomyEditError(f"{ptype} has duplicate section keys")
        for index, key in enumerate(order, start=1):
            if order.index(key) + 1 != index:
                raise TaxonomyEditError(f"{ptype} {key} numbering is not contiguous")


def heading_number(
    section_key: str,
    procurement_type: str = DEFAULT_PROCUREMENT_TYPE,
    sub_key: str | None = None,
    use_thai_numerals: bool = True,
) -> str:
    """Display number for a heading, e.g. ``๔`` or ``๔.๓``."""
    parent = section_number(section_key, procurement_type)
    if not parent:
        return ""
    if sub_key:
        subs = subsections_for(section_key, procurement_type)
        index = subs.index(sub_key) + 1 if sub_key in subs else 0
        if index:
            raw = f"{parent}.{index}"
            return to_thai_numeral(raw) if use_thai_numerals else raw
    raw = str(parent)
    return to_thai_numeral(raw) if use_thai_numerals else raw


def heading_text(
    section_key: str,
    procurement_type: str = DEFAULT_PROCUREMENT_TYPE,
    sub_key: str | None = None,
    use_thai_numerals: bool = True,
) -> str:
    """Full heading line, e.g. ``๔.๓ การบำรุงรักษาเชิงป้องกัน ...``."""
    number = heading_number(section_key, procurement_type, sub_key, use_thai_numerals)
    label = subsection_label(sub_key) if sub_key else section_label(section_key, procurement_type)
    return f"{number}. {label}" if not sub_key else f"{number} {label}"


DOCUMENT_TITLE = "ขอบเขตของงาน (Terms of Reference : TOR)"
DRAFT_DOCUMENT_TITLE = "ร่างขอบเขตของงาน (Terms of Reference : TOR)"


# ---------------------------------------------------------------------------
# Form input hints (consumed by the generated frontend mirror)
# ---------------------------------------------------------------------------
# field_key → (input type, options, legacy wizard field it maps to)

FIELD_INPUT: dict[str, tuple[str, list[str], str | None]] = {
    "budgetAmount": ("number", [], "budget"),
    "referencePrice": ("text", [], None),
    "installments": ("number", [], None),
    "totalDuration": ("number", [], "duration_days"),
    "noticeDays": ("number", [], None),
    "location": ("textarea", [], "location"),
    "deliveryPlace": ("text", [], None),
    "vatIncluded": (
        "select",
        ["รวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงแล้ว", "ไม่รวมภาษีมูลค่าเพิ่ม"],
        None,
    ),
    "procurementMethod": (
        "select",
        [
            "ประกวดราคาอิเล็กทรอนิกส์ (e-bidding)",
            "วิธีคัดเลือก",
            "วิธีเฉพาะเจาะจง",
            "วิธีประกาศเชิญชวนทั่วไป",
            "วิธีตกลงราคา (ที่ปรึกษา)",
        ],
        None,
    ),
    "method": (
        "select",
        [
            "เกณฑ์ราคา",
            "เกณฑ์ราคาประกอบเกณฑ์อื่น (Price Performance)",
            "เกณฑ์คุณภาพ",
        ],
        "evaluation_method",
    ),
    "lateRate": ("text", [], "penalty_rate"),
    "period": ("text", [], "warranty"),
    "unit": ("text", [], "ministry"),
    "address": ("textarea", [], None),
    "contact": ("textarea", [], None),
}

DEFAULT_FIELD_INPUT = "textarea"


def field_input(field_key: str) -> tuple[str, list[str], str | None]:
    return FIELD_INPUT.get(field_key, (DEFAULT_FIELD_INPUT, [], None))


validate_taxonomy_edit()
