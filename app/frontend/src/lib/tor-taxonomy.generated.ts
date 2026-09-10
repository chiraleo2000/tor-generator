/* AUTO-GENERATED — do not edit.
 * Source: app/backend/app/domain/tor_taxonomy.py
 * Regenerate: python app/backend/scripts/gen_taxonomy_ts.py
 */

export const SCHEMA_VERSION = 2;

export const PROCUREMENT_TYPES: Record<string, string> = {
  "hire_develop": "จ้างพัฒนาระบบ",
  "hire_maintain": "จ้างบำรุงรักษา (MA)",
  "lease_service": "เช่าบริการ/สื่อสาร/ยานพาหนะ",
  "buy_goods": "จัดซื้อครุภัณฑ์/ฮาร์ดแวร์",
  "construction": "งานปรับปรุง/ก่อสร้าง",
  "hire_consult": "จ้างที่ปรึกษา/สำรวจ/วิเคราะห์/เฝ้าระวังไซเบอร์",
  "hire_service": "จ้างเหมาบริการงานเอกสาร"
};

export const DEFAULT_PROCUREMENT_TYPE = "buy_goods";

export const CONTRACTOR_TERM: Record<string, string> = {
  "buy_goods": "ผู้ขาย",
  "hire_develop": "ผู้รับจ้าง",
  "hire_maintain": "ผู้รับจ้าง",
  "lease_service": "ผู้ให้เช่า",
  "hire_service": "ผู้รับจ้าง",
  "hire_consult": "ผู้รับจ้าง",
  "construction": "ผู้รับจ้าง"
};

export const SECTION_LABELS: Record<string, string> = {
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
  "responsible_unit": "หน่วยงานผู้รับผิดชอบและสถานที่ติดต่อ"
};

export const SECTION_LABELS_EN: Record<string, string> = {
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
  "responsible_unit": "Responsible Unit"
};

export const CORE_SECTION_ORDER: string[] = [
  "background",
  "objective",
  "qualification",
  "scope",
  "schedule",
  "evaluation",
  "budget",
  "payment",
  "penalty",
  "warranty"
];

export const CLOSING_SECTION = "responsible_unit";

export const EXTRA_SECTIONS_BY_TYPE: Record<string, string[]> = {
  "buy_goods": [],
  "hire_develop": [
    "ip_ownership",
    "confidentiality"
  ],
  "hire_maintain": [
    "confidentiality"
  ],
  "lease_service": [],
  "hire_service": [
    "ip_ownership",
    "confidentiality"
  ],
  "hire_consult": [
    "ip_ownership",
    "confidentiality",
    "other_conditions"
  ],
  "construction": []
};

export const SECTION_LABEL_OVERRIDES: Record<string, Record<string, string>> = {
  "buy_goods": {
    "schedule": "กำหนดเวลาส่งมอบพัสดุ"
  },
  "hire_maintain": {
    "schedule": "ระยะเวลาการให้บริการและการส่งมอบงาน",
    "payment": "ค่าจ้างและการจ่ายเงิน",
    "warranty": "การรับประกันผลงานการบำรุงรักษา"
  },
  "lease_service": {
    "scope": "ขอบเขตของงานและบริการที่เช่าใช้",
    "schedule": "กำหนดระยะเวลาเช่าและการส่งมอบงานรายงวด",
    "warranty": "การรับประกันการให้บริการและความชำรุดบกพร่อง"
  },
  "hire_consult": {
    "scope": "ขอบเขตการดำเนินงาน",
    "budget": "วงเงินในการจัดหา",
    "penalty": "เงื่อนไขการปรับ",
    "warranty": "การรับประกันผลงาน"
  },
  "hire_service": {
    "scope": "รายละเอียดของงาน",
    "warranty": "การรับประกันผลงาน"
  },
  "construction": {
    "scope": "ขอบเขตของงานและรายละเอียดการก่อสร้าง",
    "schedule": "ระยะเวลาดำเนินการก่อสร้างและการส่งมอบงาน",
    "warranty": "การรับประกันผลงานก่อสร้าง"
  }
};

export const SCOPE_SUBSECTION_LABELS: Record<string, string> = {
  "scope.items": "รายการพัสดุที่จัดซื้อและจำนวน",
  "scope.general_conditions": "เงื่อนไขทั่วไปของพัสดุ",
  "scope.specification": "คุณลักษณะเฉพาะของพัสดุ",
  "scope.installation": "เงื่อนไขการติดตั้งและสถานที่ติดตั้ง",
  "scope.delivery_acceptance": "เงื่อนไขการส่งมอบและการตรวจรับ",
  "scope.training": "การฝึกอบรมและการถ่ายทอดความรู้",
  "scope.documents": "เอกสารและคู่มือที่ต้องส่งมอบ",
  "scope.after_sales": "การบริการสนับสนุนและบำรุงรักษาระหว่างรับประกัน",
  "scope.system_overview": "ภาพรวมและสถาปัตยกรรมของระบบที่ต้องการ",
  "scope.functional": "ขอบเขตระบบงานและหน้าที่การทำงานที่ต้องพัฒนา",
  "scope.integration": "การเชื่อมโยงระบบและการโอนย้ายข้อมูล",
  "scope.licenses": "ครุภัณฑ์และลิขสิทธิ์ซอฟต์แวร์ที่ต้องจัดหา",
  "scope.standards_security": "มาตรฐานและข้อกำหนดด้านความมั่นคงปลอดภัยสารสนเทศ",
  "scope.testing": "การทดสอบระบบและเกณฑ์การยอมรับ",
  "scope.deliverable_docs": "เอกสารระบบและซอร์สโค้ดที่ต้องส่งมอบ",
  "scope.project_team": "บุคลากรประจำโครงการ",
  "scope.sla_warranty": "การบำรุงรักษาและระดับการให้บริการระหว่างรับประกัน",
  "scope.asset_list": "รายการระบบและอุปกรณ์ที่ต้องบำรุงรักษา",
  "scope.cm": "การบำรุงรักษาเชิงแก้ไข",
  "scope.pm": "การบำรุงรักษาเชิงป้องกันและรอบการเข้าดำเนินการ",
  "scope.sla": "ระดับการให้บริการ เวลาตอบสนอง และเวลาแก้ไขให้แล้วเสร็จ",
  "scope.helpdesk": "ศูนย์รับแจ้งเหตุขัดข้องและการบริหารจัดการปัญหา",
  "scope.spare_parts": "อะไหล่ วัสดุสิ้นเปลือง และอุปกรณ์ทดแทนระหว่างซ่อม",
  "scope.onsite_staff": "บุคลากรและการปฏิบัติงานร่วมกับเจ้าหน้าที่ของหน่วยงาน",
  "scope.reporting": "การรายงานผลการปฏิบัติงาน",
  "scope.backup": "การสำรองข้อมูลและการกู้คืนระบบ",
  "scope.service_spec": "รายละเอียดบริการที่เช่าใช้",
  "scope.provided_equipment": "อุปกรณ์และสื่อสัญญาณที่ผู้ให้เช่าต้องจัดหา",
  "scope.availability": "ความพร้อมใช้งาน เส้นทางสำรอง และการสลับเส้นทาง",
  "scope.noc": "ศูนย์รับแจ้งเหตุตลอด ๒๔ ชั่วโมงและการแจ้งเตือน",
  "scope.usage_report": "ระบบรายงานและการตรวจสอบปริมาณการใช้งาน",
  "scope.lease_maintenance": "การบำรุงรักษาระบบตลอดอายุสัญญาเช่า",
  "scope.lessee_rights": "สิทธิของผู้เช่าระหว่างอายุสัญญา",
  "scope.workload": "ปริมาณงานและหน่วยนับ",
  "scope.workflow": "กระบวนการปฏิบัติงาน",
  "scope.quality_standard": "มาตรฐานคุณภาพของผลงาน",
  "scope.resources": "บุคลากร เครื่องมือ และสถานที่ปฏิบัติงาน",
  "scope.custody": "การขนย้ายและการดูแลรักษาทรัพย์สินของผู้ว่าจ้าง",
  "scope.progress_report": "การรายงานความคืบหน้า",
  "scope.output_delivery": "การส่งมอบผลงานและรูปแบบสื่อบันทึกข้อมูล",
  "scope.methodology": "กรอบแนวคิดและระเบียบวิธีดำเนินงาน",
  "scope.population": "กลุ่มเป้าหมาย ขนาดตัวอย่าง และอัตราตอบกลับขั้นต่ำ",
  "scope.instrument": "เครื่องมือเก็บข้อมูลและการทดสอบความแม่นยำ",
  "scope.fieldwork": "การเก็บรวบรวมและตรวจสอบความถูกต้องของข้อมูล",
  "scope.analysis": "การวิเคราะห์ข้อมูลและการนำเสนอผล",
  "scope.expert_review": "การประชุมและการรับฟังความเห็นผู้เชี่ยวชาญ",
  "scope.reports": "รายงานตามลำดับขั้นและรูปแบบการส่งมอบ",
  "scope.expert_team": "คณะผู้เชี่ยวชาญและปริมาณงานเป็นคน-เดือน",
  "scope.works": "รายการงานก่อสร้างหรือปรับปรุง",
  "scope.drawings": "แบบรูปรายการและมาตรฐานวัสดุ",
  "scope.demolition": "งานรื้อถอนและการจัดการพื้นที่",
  "scope.site_access": "เงื่อนไขการเข้าปฏิบัติงานและความปลอดภัยในการทำงาน",
  "scope.supervision": "การควบคุมงานและการตรวจสอบคุณภาพ",
  "scope.handover": "การส่งมอบพื้นที่และแบบตามที่สร้างจริง"
};

export const SCOPE_BY_TYPE: Record<string, string[]> = {
  "buy_goods": [
    "scope.items",
    "scope.general_conditions",
    "scope.specification",
    "scope.installation",
    "scope.delivery_acceptance",
    "scope.training",
    "scope.documents",
    "scope.after_sales"
  ],
  "hire_develop": [
    "scope.system_overview",
    "scope.functional",
    "scope.integration",
    "scope.licenses",
    "scope.standards_security",
    "scope.testing",
    "scope.deliverable_docs",
    "scope.training",
    "scope.project_team",
    "scope.sla_warranty"
  ],
  "hire_maintain": [
    "scope.asset_list",
    "scope.cm",
    "scope.pm",
    "scope.sla",
    "scope.helpdesk",
    "scope.spare_parts",
    "scope.onsite_staff",
    "scope.reporting",
    "scope.backup"
  ],
  "lease_service": [
    "scope.service_spec",
    "scope.provided_equipment",
    "scope.availability",
    "scope.noc",
    "scope.usage_report",
    "scope.lease_maintenance",
    "scope.lessee_rights"
  ],
  "hire_service": [
    "scope.workload",
    "scope.workflow",
    "scope.quality_standard",
    "scope.resources",
    "scope.custody",
    "scope.progress_report",
    "scope.output_delivery"
  ],
  "hire_consult": [
    "scope.methodology",
    "scope.population",
    "scope.instrument",
    "scope.fieldwork",
    "scope.analysis",
    "scope.expert_review",
    "scope.reports",
    "scope.expert_team"
  ],
  "construction": [
    "scope.works",
    "scope.drawings",
    "scope.demolition",
    "scope.site_access",
    "scope.supervision",
    "scope.handover",
    "scope.delivery_acceptance"
  ]
};

export const SCOPE_REQUIRED_BY_TYPE: Record<string, string[]> = {
  "buy_goods": [
    "scope.items",
    "scope.specification",
    "scope.delivery_acceptance"
  ],
  "hire_develop": [
    "scope.functional",
    "scope.deliverable_docs",
    "scope.testing"
  ],
  "hire_maintain": [
    "scope.asset_list",
    "scope.cm",
    "scope.pm",
    "scope.sla"
  ],
  "lease_service": [
    "scope.service_spec",
    "scope.availability",
    "scope.noc"
  ],
  "hire_service": [
    "scope.workload",
    "scope.workflow",
    "scope.quality_standard"
  ],
  "hire_consult": [
    "scope.methodology",
    "scope.population",
    "scope.reports"
  ],
  "construction": [
    "scope.works",
    "scope.drawings",
    "scope.handover"
  ]
};

export const QUALIFICATION_SUBSECTION_LABELS: Record<string, string> = {
  "qual.legal": "คุณสมบัติทั่วไปตามกฎหมายและการลงทะเบียนในระบบ e-GP",
  "qual.jv": "กรณีกิจการร่วมค้า",
  "qual.networth": "มูลค่าสุทธิของกิจการ ทุนจดทะเบียน หรือวงเงินสินเชื่อ",
  "qual.experience": "ผลงานประเภทเดียวกันกับงานที่จัดซื้อจัดจ้าง",
  "qual.personnel": "บุคลากรหลักในโครงการ",
  "qual.dealer": "หนังสือแต่งตั้งตัวแทนจำหน่ายจากเจ้าของผลิตภัณฑ์",
  "qual.license": "ใบอนุญาตประกอบกิจการตามกฎหมายเฉพาะ",
  "qual.documents": "เอกสารและหลักฐานที่ผู้ยื่นข้อเสนอต้องนำมายื่น"
};

export const QUALIFICATION_BY_TYPE: Record<string, string[]> = {
  "buy_goods": [
    "qual.legal",
    "qual.jv",
    "qual.networth",
    "qual.experience",
    "qual.dealer",
    "qual.documents"
  ],
  "hire_develop": [
    "qual.legal",
    "qual.jv",
    "qual.networth",
    "qual.experience",
    "qual.personnel",
    "qual.documents"
  ],
  "hire_maintain": [
    "qual.legal",
    "qual.jv",
    "qual.networth",
    "qual.experience",
    "qual.personnel",
    "qual.documents"
  ],
  "lease_service": [
    "qual.legal",
    "qual.jv",
    "qual.networth",
    "qual.license",
    "qual.documents"
  ],
  "hire_service": [
    "qual.legal",
    "qual.jv",
    "qual.networth",
    "qual.experience",
    "qual.documents"
  ],
  "hire_consult": [
    "qual.legal",
    "qual.experience",
    "qual.personnel",
    "qual.documents"
  ],
  "construction": [
    "qual.legal",
    "qual.jv",
    "qual.networth",
    "qual.experience",
    "qual.license",
    "qual.documents"
  ]
};

export interface TaxonomyField {
  key: string;
  label: string;
  type: "text" | "textarea" | "number" | "select";
  options?: string[];
  mapField?: string;
}

export const SECTION_FIELDS: Record<string, TaxonomyField[]> = {
  "background": [
    {
      "key": "mandate",
      "label": "ภารกิจและอำนาจหน้าที่ของหน่วยงาน (อ้างกฎหมายจัดตั้ง)",
      "type": "textarea"
    },
    {
      "key": "currentState",
      "label": "สภาพปัจจุบัน พร้อมตัวเลขปริมาณงานหรืออายุการใช้งาน",
      "type": "textarea"
    },
    {
      "key": "problems",
      "label": "ปัญหาและผลกระทบที่วัดได้",
      "type": "textarea"
    },
    {
      "key": "policy",
      "label": "นโยบาย แผน หรือกฎหมายที่รองรับ",
      "type": "textarea"
    },
    {
      "key": "necessity",
      "label": "เหตุผลความจำเป็นที่ต้องดำเนินการ",
      "type": "textarea"
    }
  ],
  "objective": [
    {
      "key": "mainObjectives",
      "label": "วัตถุประสงค์รายข้อ (ขึ้นต้นด้วย “เพื่อ”)",
      "type": "textarea"
    },
    {
      "key": "users",
      "label": "กลุ่มผู้ใช้งานหรือผู้รับบริการเป้าหมาย",
      "type": "textarea"
    },
    {
      "key": "kpi",
      "label": "ตัวชี้วัดความสำเร็จ",
      "type": "textarea"
    }
  ],
  "qualification": [
    {
      "key": "experienceValue",
      "label": "มูลค่าผลงานขั้นต่ำต่อสัญญา (บาท) และจำนวนปีย้อนหลัง",
      "type": "textarea"
    },
    {
      "key": "networth",
      "label": "ทุนจดทะเบียนชำระแล้ว มูลค่าสุทธิ หรือวงเงินสินเชื่อขั้นต่ำ",
      "type": "textarea"
    },
    {
      "key": "personnel",
      "label": "ตำแหน่ง คุณวุฒิ ประสบการณ์ และจำนวนบุคลากรหลัก",
      "type": "textarea"
    },
    {
      "key": "specialLicense",
      "label": "ใบอนุญาตหรือการขึ้นทะเบียนเฉพาะทาง",
      "type": "textarea"
    },
    {
      "key": "bidDocuments",
      "label": "เอกสารและหลักฐานที่ต้องยื่นพร้อมข้อเสนอ",
      "type": "textarea"
    }
  ],
  "scope": [
    {
      "key": "summary",
      "label": "สรุปสาระสำคัญของงานที่จะจัดซื้อจัดจ้าง",
      "type": "textarea"
    },
    {
      "key": "quantities",
      "label": "ปริมาณงานหรือบัญชีรายการพร้อมจำนวน",
      "type": "textarea"
    },
    {
      "key": "location",
      "label": "สถานที่ติดตั้ง ส่งมอบ หรือปฏิบัติงาน",
      "type": "textarea",
      "mapField": "location"
    },
    {
      "key": "annexRefs",
      "label": "เอกสารแนบที่อ้างถึงในหมวดนี้",
      "type": "textarea"
    }
  ],
  "schedule": [
    {
      "key": "totalDuration",
      "label": "ระยะเวลาดำเนินการรวม (วัน) นับถัดจากวันลงนามในสัญญา",
      "type": "number",
      "mapField": "duration_days"
    },
    {
      "key": "milestones",
      "label": "งวดส่งมอบ พร้อมจำนวนวันและผลงานของแต่ละงวด",
      "type": "textarea"
    },
    {
      "key": "noticeDays",
      "label": "จำนวนวันที่ต้องแจ้งกำหนดส่งมอบล่วงหน้า",
      "type": "number"
    },
    {
      "key": "deliveryPlace",
      "label": "สถานที่ส่งมอบงาน",
      "type": "text"
    }
  ],
  "evaluation": [
    {
      "key": "method",
      "label": "เกณฑ์ที่ใช้ (เกณฑ์ราคา หรือเกณฑ์ราคาประกอบเกณฑ์อื่น)",
      "type": "select",
      "options": [
        "เกณฑ์ราคา",
        "เกณฑ์ราคาประกอบเกณฑ์อื่น (Price Performance)",
        "เกณฑ์คุณภาพ"
      ],
      "mapField": "evaluation_method"
    },
    {
      "key": "weights",
      "label": "สัดส่วนน้ำหนักคะแนนด้านราคาและด้านคุณภาพ",
      "type": "textarea"
    },
    {
      "key": "passingScore",
      "label": "คะแนนผ่านขั้นต่ำและวิธีการนำเสนอ",
      "type": "textarea"
    },
    {
      "key": "preferences",
      "label": "แต้มต่อ SMEs หรือพัสดุที่ผลิตในประเทศไทย (ถ้ามี)",
      "type": "textarea"
    }
  ],
  "budget": [
    {
      "key": "budgetAmount",
      "label": "วงเงินงบประมาณ (บาท)",
      "type": "number",
      "mapField": "budget"
    },
    {
      "key": "budgetSource",
      "label": "ที่มาของงบประมาณและปีงบประมาณ",
      "type": "textarea"
    },
    {
      "key": "vatIncluded",
      "label": "รวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงหรือไม่",
      "type": "select",
      "options": [
        "รวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงแล้ว",
        "ไม่รวมภาษีมูลค่าเพิ่ม"
      ]
    },
    {
      "key": "referencePrice",
      "label": "ราคากลางและวิธีคำนวณ",
      "type": "text"
    },
    {
      "key": "procurementMethod",
      "label": "วิธีจัดซื้อจัดจ้าง",
      "type": "select",
      "options": [
        "ประกวดราคาอิเล็กทรอนิกส์ (e-bidding)",
        "วิธีคัดเลือก",
        "วิธีเฉพาะเจาะจง",
        "วิธีประกาศเชิญชวนทั่วไป",
        "วิธีตกลงราคา (ที่ปรึกษา)"
      ]
    }
  ],
  "payment": [
    {
      "key": "installments",
      "label": "จำนวนงวดการจ่ายเงิน",
      "type": "number"
    },
    {
      "key": "paymentTerms",
      "label": "ร้อยละและเงื่อนไขการเบิกจ่ายแต่ละงวด",
      "type": "textarea"
    },
    {
      "key": "retention",
      "label": "หลักประกันสัญญาหรือเงินประกันผลงาน",
      "type": "textarea"
    },
    {
      "key": "withholding",
      "label": "เงื่อนไขการงดหรือยึดหน่วงค่าจ้าง (ถ้ามี)",
      "type": "textarea"
    }
  ],
  "penalty": [
    {
      "key": "lateRate",
      "label": "อัตราค่าปรับส่งมอบล่าช้า (ร้อยละต่อวัน)",
      "type": "text",
      "mapField": "penalty_rate"
    },
    {
      "key": "slaPenalty",
      "label": "ค่าปรับกรณีไม่เข้าดำเนินการหรือระบบขัดข้อง",
      "type": "textarea"
    },
    {
      "key": "cap",
      "label": "เพดานค่าปรับและสิทธิบอกเลิกสัญญา",
      "type": "textarea"
    },
    {
      "key": "settlement",
      "label": "กำหนดเวลาชำระค่าปรับและการหักจากหลักประกัน",
      "type": "textarea"
    }
  ],
  "warranty": [
    {
      "key": "period",
      "label": "ระยะเวลารับประกัน นับถัดจากวันตรวจรับ",
      "type": "text",
      "mapField": "warranty"
    },
    {
      "key": "coverage",
      "label": "ขอบเขตการรับประกันและรูปแบบบริการ (เช่น On-site Service)",
      "type": "textarea"
    },
    {
      "key": "responseTime",
      "label": "เวลาเข้าดำเนินการและเวลาแก้ไขให้แล้วเสร็จ",
      "type": "textarea"
    },
    {
      "key": "supportChannel",
      "label": "ช่องทางแจ้งเหตุและเจ้าหน้าที่ประสานงาน",
      "type": "textarea"
    }
  ],
  "ip_ownership": [
    {
      "key": "ownership",
      "label": "กรรมสิทธิ์ในผลงาน เอกสาร และข้อมูล",
      "type": "textarea"
    },
    {
      "key": "sourceCode",
      "label": "การส่งมอบซอร์สโค้ดและสิทธิในการพัฒนาต่อ",
      "type": "textarea"
    },
    {
      "key": "thirdParty",
      "label": "ความรับผิดกรณีละเมิดลิขสิทธิ์หรือสิทธิบัตรของบุคคลภายนอก",
      "type": "textarea"
    }
  ],
  "confidentiality": [
    {
      "key": "nda",
      "label": "ข้อตกลงไม่เปิดเผยข้อมูลที่เป็นความลับ",
      "type": "textarea"
    },
    {
      "key": "pdpa",
      "label": "การคุ้มครองข้อมูลส่วนบุคคลตามกฎหมาย",
      "type": "textarea"
    },
    {
      "key": "accessControl",
      "label": "การควบคุมการเข้าพื้นที่และการนำข้อมูลออก",
      "type": "textarea"
    },
    {
      "key": "termination",
      "label": "วิธีปฏิบัติเมื่อสัญญาสิ้นสุด (คืนหรือทำลายข้อมูล)",
      "type": "textarea"
    }
  ],
  "other_conditions": [
    {
      "key": "reservations",
      "label": "ข้อสงวนสิทธิ์ของหน่วยงาน",
      "type": "textarea"
    },
    {
      "key": "subcontract",
      "label": "เงื่อนไขการจ้างช่วง",
      "type": "textarea"
    },
    {
      "key": "contractSecurity",
      "label": "หลักประกันสัญญา",
      "type": "textarea"
    },
    {
      "key": "misc",
      "label": "เงื่อนไขอื่นตามระเบียบกระทรวงการคลัง",
      "type": "textarea"
    }
  ],
  "responsible_unit": [
    {
      "key": "unit",
      "label": "ชื่อหน่วยงานผู้รับผิดชอบ",
      "type": "text",
      "mapField": "ministry"
    },
    {
      "key": "address",
      "label": "ที่อยู่สำหรับติดต่อ",
      "type": "textarea"
    },
    {
      "key": "contact",
      "label": "โทรศัพท์ โทรสาร ไปรษณีย์อิเล็กทรอนิกส์ และเว็บไซต์",
      "type": "textarea"
    },
    {
      "key": "budgetNote",
      "label": "หมายเหตุเงื่อนไขพระราชบัญญัติงบประมาณรายจ่ายประจำปี",
      "type": "textarea"
    }
  ]
};

export const HITL_SECTIONS: string[] = [
  "budget",
  "evaluation",
  "ip_ownership",
  "payment",
  "penalty",
  "qualification"
];

export const CRITICAL_SECTIONS_MIN_LENGTH: Record<string, number> = {
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
  "responsible_unit": 60
};

export const MINIMUM_CONTENT_LENGTH = 20;

export const WIZARD_STEP_COUNT = 8;

export const STEP_SECTION_MAP: Record<number, string[]> = {
  "1": [],
  "2": [
    "background"
  ],
  "3": [
    "objective"
  ],
  "4": [
    "scope"
  ],
  "5": [
    "qualification"
  ],
  "6": [
    "schedule",
    "evaluation",
    "budget",
    "payment",
    "penalty",
    "warranty"
  ],
  "7": [],
  "8": []
};

export const STEP_LABELS: Record<number, string> = {
  "1": "ข้อมูลโครงการและประเภทการจัดซื้อจัดจ้าง",
  "2": "ความเป็นมา",
  "3": "วัตถุประสงค์",
  "4": "ขอบเขตของงาน",
  "5": "คุณสมบัติของผู้ยื่นข้อเสนอ",
  "6": "ระยะเวลา วงเงิน งวดงาน และเงื่อนไขสัญญา",
  "7": "ตรวจสอบร่างและข้อเสนอแนะ",
  "8": "ส่งออกเอกสาร"
};

export const SECTION_HINTS: Record<string, string> = {
  "background": "เขียนเป็นย่อหน้าต่อเนื่อง ๒–๔ ย่อหน้า ตามลำดับ (๑) ภารกิจและอำนาจหน้าที่ของหน่วยงานพร้อมตัวเลขโครงสร้างจริง (๒) สภาพปัจจุบันของระบบหรือพัสดุเดิม ระบุปีที่จัดหาและอายุการใช้งาน (๓) ปัญหาและผลกระทบที่วัดได้ (๔) ปิดท้ายด้วย “ดังนั้น … จึงมีความจำเป็นต้อง …” ห้ามระบุจำนวนเงินงบประมาณและห้ามลงรายละเอียดทางเทคนิคในหมวดนี้",
  "objective": "เขียนเป็นข้อย่อยเรียงลำดับ ๓–๘ ข้อ ทุกข้อขึ้นต้นด้วย “เพื่อ” แต่ละข้อต้องผูกกับรายการหรืองานจริงในขอบเขตของงาน วัดผลได้ ห้ามใช้ข้อความกว้างอย่าง “เพื่อพัฒนาองค์กร”",
  "qualification": "เริ่มด้วยคุณสมบัติทั่วไปตามกฎหมายชุดมาตรฐาน ๙ ข้อ (ความสามารถตามกฎหมาย ไม่เป็นบุคคลล้มละลาย ไม่อยู่ระหว่างเลิกกิจการ ไม่อยู่ระหว่างถูกระงับการยื่นข้อเสนอ ไม่เป็นผู้ทิ้งงาน ไม่มีลักษณะต้องห้าม เป็นผู้มีอาชีพขายหรือรับจ้างงานดังกล่าว ไม่เป็นผู้มีผลประโยชน์ร่วมกัน ไม่ได้รับเอกสิทธิ์หรือความคุ้มกัน) ตามด้วยการลงทะเบียนในระบบ e-GP กิจการร่วมค้า มูลค่าสุทธิของกิจการ แล้วจึงเป็นคุณสมบัติเฉพาะโครงการ และปิดท้ายด้วยบัญชีเอกสารที่ต้องยื่น",
  "scope": "เขียนแยกเป็นหัวข้อย่อยตามที่กำหนดให้เท่านั้น ระบุจำนวน หน่วยนับ และเกณฑ์ที่ตรวจรับได้ทุกข้อ ใช้ตารางมาร์กดาวน์เมื่อมีหลายรายการ ห้ามระบุยี่ห้อหรือรุ่นเฉพาะโดยไม่มีคำว่า “หรือเทียบเท่า” และห้ามใช้คำที่ตรวจสอบไม่ได้ เช่น “คุณภาพดี” “ทันสมัย”",
  "schedule": "ระบุระยะเวลารวมเป็นจำนวนวัน ตามด้วย “นับถัดจากวันลงนามในสัญญา” แล้วแจกแจงงวดส่งมอบเป็นตาราง (งวดที่ / ผลงานที่ต้องส่งมอบ / ภายในกี่วัน) จำนวนวันของแต่ละงวดต้องเรียงเพิ่มขึ้นและงวดสุดท้ายเท่ากับระยะเวลารวม พร้อมเงื่อนไขการแจ้งกำหนดส่งมอบล่วงหน้าเป็นลายลักษณ์อักษร",
  "evaluation": "ระบุเกณฑ์ที่ใช้ให้ชัด หากใช้เกณฑ์ราคาให้เขียนสั้นว่าพิจารณาจากราคารวม หากใช้เกณฑ์ราคาประกอบเกณฑ์อื่น ต้องมีตารางน้ำหนักคะแนนที่รวมได้ ๑๐๐ พร้อมคะแนนผ่านขั้นต่ำ และหมายเหตุว่าไม่ส่งเอกสารจะไม่ได้คะแนนในข้อนั้น รวมแต้มต่อผู้ประกอบการ SMEs และพัสดุที่ผลิตในประเทศไทยเมื่อเข้าเงื่อนไข",
  "budget": "ระบุแหล่งเงินและปีงบประมาณ จำนวนเงินเป็นตัวเลขตามด้วยตัวอักษรในวงเล็บ และระบุว่ารวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงไว้ด้วยแล้วหรือไม่ แยกวงเงินงบประมาณที่ได้รับจัดสรรออกจากราคากลางเมื่อมีทั้งสองค่า",
  "payment": "แจกแจงเป็นตารางงวดจ่ายเงิน ร้อยละรวมต้องเท่ากับ ๑๐๐ พอดี แต่ละงวดผูกกับผลงานส่งมอบที่ตรวจรับได้ ใช้รูปประโยค “งวดที่ X ชำระเงินในอัตราร้อยละ Y ของจำนวนเงินในสัญญา เมื่อผู้รับจ้างส่งมอบงานงวดที่ X และคณะกรรมการตรวจรับพัสดุได้ตรวจรับเรียบร้อยแล้ว”",
  "penalty": "แยกค่าปรับส่งมอบล่าช้าเป็นร้อยละต่อวันของมูลค่าตามสัญญา (ปกติร้อยละ ๐.๑๐ หรือ ๐.๒๐) เขียนตัวเลขพร้อมคำอ่านในวงเล็บ เช่น ร้อยละ ๐.๑๐ (ศูนย์จุดหนึ่งศูนย์) ถ้าเป็นงานบำรุงรักษาหรือเช่า ให้เพิ่มค่าปรับรายชั่วโมงกรณีไม่เข้าดำเนินการ และค่าปรับกรณีระบบขัดข้องเกินเวลาที่ยอมให้ พร้อมกำหนดเวลาชำระค่าปรับ และสิทธิหักจากหลักประกันสัญญา",
  "warranty": "ระบุระยะเวลารับประกันเป็นปี นับถัดจากวันที่ตรวจรับเรียบร้อยแล้ว ระบุรูปแบบบริการ เวลาเข้าดำเนินการ เวลาแก้ไขให้แล้วเสร็จ และย้ำว่าไม่มีค่าใช้จ่ายใด ๆ ตลอดระยะเวลารับประกัน",
  "ip_ownership": "ระบุว่าลิขสิทธิ์ กรรมสิทธิ์ เอกสาร ข้อมูล และผลงานตกเป็นของหน่วยงาน ทันทีที่ส่งมอบ ระบุการส่งมอบซอร์สโค้ดฉบับสมบูรณ์ล่าสุดและสิทธิพัฒนาต่อ และความรับผิดของคู่สัญญากรณีถูกกล่าวหาว่าละเมิดสิทธิของบุคคลภายนอก",
  "confidentiality": "กำหนดให้ลงนามในข้อตกลงไม่เปิดเผยข้อมูลที่เป็นความลับพร้อมสัญญาจ้าง ระบุการปฏิบัติตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล การควบคุมการเข้าพื้นที่ และวิธีปฏิบัติเมื่อสัญญาสิ้นสุดคือส่งคืนหรือทำลายข้อมูลพร้อมแจ้งยืนยันเป็นลายลักษณ์อักษร",
  "other_conditions": "ระบุหลักประกันสัญญาร้อยละ ๕ ของวงเงินตามสัญญา ข้อห้ามจ้างช่วง ข้อสงวนสิทธิ์ที่จะไม่รับราคาต่ำสุดหรือยกเลิกการจัดซื้อจัดจ้าง และเงื่อนไขอื่นตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ",
  "responsible_unit": "ระบุชื่อหน่วยงาน ที่อยู่ หมายเลขโทรศัพท์ โทรสาร ไปรษณีย์อิเล็กทรอนิกส์ และเว็บไซต์สำหรับเสนอแนะวิจารณ์ร่างขอบเขตของงาน ปิดท้ายด้วยหมายเหตุเงื่อนไขพระราชบัญญัติงบประมาณรายจ่ายประจำปีเมื่อยังไม่ได้รับจัดสรร"
};

export const SUBSECTION_HINTS: Record<string, string> = {
  "scope.items": "บัญชีรายการพร้อมจำนวนและหน่วยนับ เรียงเป็นตาราง (ลำดับ / รายการ / จำนวน / หน่วย)",
  "scope.general_conditions": "ของใหม่ ไม่ใช่ของใช้แล้ว ล้าสมัย หรือปรับปรุงใหม่ ยังอยู่ในสายการผลิต ใช้กับระบบไฟฟ้าในประเทศไทยได้ และมีมาตรฐานรับรอง",
  "scope.specification": "อ้างคุณลักษณะเฉพาะรายรายการในเอกสารแนบ และกำหนดให้ยื่นตารางเปรียบเทียบคุณลักษณะพร้อมแคตตาล็อกที่ทำแถบสีอ้างอิงหน้า",
  "scope.installation": "สถานที่ติดตั้ง จำนวนจุด งานตั้งค่าที่ต้องทำ การเดินสายสัญญาณ การติดสติกเกอร์ทรัพย์สิน และสิทธิของหน่วยงานในการเปลี่ยนแปลงสถานที่ติดตั้ง",
  "scope.delivery_acceptance": "เงื่อนไขการแจ้งส่งมอบล่วงหน้าเป็นลายลักษณ์อักษร วิธีตรวจรับ และเอกสารที่ต้องแนบตอนส่งมอบ",
  "scope.training": "หลักสูตร จำนวนผู้เข้าอบรม จำนวนรุ่น สถานที่ และการที่คู่สัญญารับผิดชอบค่าใช้จ่ายทั้งหมด พร้อมแจ้งกำหนดล่วงหน้า",
  "scope.documents": "คู่มือติดตั้ง คู่มือใช้งาน คู่มือผู้ดูแลระบบ จำนวนชุด รูปแบบเอกสารและสื่อบันทึกข้อมูล",
  "scope.after_sales": "บริการสนับสนุนระหว่างรับประกัน รอบการบำรุงรักษาเชิงป้องกัน เวลาเข้าแก้ไข และค่าปรับกรณีไม่ปฏิบัติตาม",
  "scope.system_overview": "สถาปัตยกรรมระบบเป้าหมาย จำนวนผู้ใช้ ปริมาณข้อมูล และสภาพแวดล้อมที่ต้องรองรับ",
  "scope.functional": "แจกแจงโมดูลและหน้าที่การทำงานเป็นข้อย่อย ทุกข้อต้องตรวจรับได้",
  "scope.integration": "ระบบปลายทางที่ต้องเชื่อมโยง รูปแบบการเชื่อมโยงผ่านส่วนต่อประสานโปรแกรม และขอบเขตการโอนย้ายข้อมูลเดิม",
  "scope.licenses": "รายการลิขสิทธิ์ซอฟต์แวร์ จำนวนสิทธิ์ ระยะเวลา และเงื่อนไขการอัปเกรดระหว่างรับประกัน",
  "scope.standards_security": "มาตรฐานที่ต้องผ่าน เช่น มาตรฐานเว็บไซต์ภาครัฐ OWASP Top 10 ISO/IEC 27001 และการประเมินช่องโหว่ก่อนขึ้นใช้งานจริง รวมถึงการคุ้มครองข้อมูลส่วนบุคคล",
  "scope.testing": "แผนการทดสอบ ประเภทการทดสอบ (หน้าที่การทำงาน การเชื่อมโยง ประสิทธิภาพ ความมั่นคงปลอดภัย และการยอมรับโดยผู้ใช้) และเกณฑ์การยอมรับ",
  "scope.deliverable_docs": "เอกสารระบบที่ต้องส่งมอบ (เอกสารระบบ กรณีใช้งาน แผนภาพความสัมพันธ์ข้อมูล พจนานุกรมข้อมูล) และซอร์สโค้ดฉบับสมบูรณ์ล่าสุดก่อนสิ้นสุดการรับประกัน",
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
  "scope.expert_team": "ตำแหน่ง คุณวุฒิ ประสบการณ์ จำนวนคน และปริมาณงานเป็นคน-เดือน",
  "scope.works": "รายการงานก่อสร้างหรือปรับปรุงพร้อมปริมาณงานตามแบบ",
  "scope.drawings": "แบบรูปรายการ มาตรฐานวัสดุ และมาตรฐานฝีมือช่างที่อ้างอิง",
  "scope.demolition": "ขอบเขตการรื้อถอน การขนย้ายวัสดุ และการจัดการเศษวัสดุ",
  "scope.site_access": "เวลาเข้าปฏิบัติงาน การขออนุญาต มาตรการความปลอดภัย และการไม่รบกวนการปฏิบัติราชการ",
  "scope.supervision": "ผู้ควบคุมงาน การรายงานความก้าวหน้า และการตรวจสอบคุณภาพงานแต่ละขั้น",
  "scope.handover": "การส่งมอบพื้นที่ การทำความสะอาด และการส่งมอบแบบตามที่สร้างจริง",
  "qual.legal": "คัดลอกชุดคุณสมบัติมาตรฐานตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐ ครบทุกข้อ แล้วต่อด้วยการลงทะเบียนในระบบจัดซื้อจัดจ้างภาครัฐด้วยอิเล็กทรอนิกส์",
  "qual.jv": "เงื่อนไขสัดส่วนการเข้าร่วมค้า ผลงานของผู้เข้าร่วมค้าหลัก และการมอบอำนาจในการยื่นข้อเสนอ",
  "qual.networth": "ระบุทางเลือกให้ครบ ทั้งงบแสดงฐานะการเงิน ทุนจดทะเบียนชำระแล้วตามบันไดวงเงิน วงเงินสินเชื่อจากสถาบันการเงิน และข้อยกเว้นตามที่กฎหมายกำหนด",
  "qual.experience": "ระบุประเภทผลงานให้ตรงกับงานที่จัดซื้อจัดจ้าง มูลค่าขั้นต่ำต่อสัญญา จำนวนผลงาน จำนวนปีย้อนหลัง และต้องเป็นคู่สัญญาโดยตรงกับหน่วยงานของรัฐ",
  "qual.personnel": "ตารางบุคลากรหลัก (ตำแหน่ง / คุณวุฒิ / ประสบการณ์ขั้นต่ำ / จำนวนคน) พร้อมกำหนดให้ยื่นแบบฟอร์มประวัติและเอกสารรับรอง",
  "qual.dealer": "หนังสือแต่งตั้งตัวแทนจำหน่ายจากเจ้าของผลิตภัณฑ์ ระบุรายการที่ต้องมีหนังสือแต่งตั้ง และต้องระบุชื่อโครงการ",
  "qual.license": "ใบอนุญาตประกอบกิจการตามกฎหมายเฉพาะ พร้อมขีดความสามารถขั้นต่ำที่ต้องแสดงหลักฐาน",
  "qual.documents": "บัญชีเอกสารที่ต้องยื่น ระบุรูปแบบ (ต้นฉบับหรือสำเนารับรอง) จำนวนชุด อายุเอกสาร และผลของการยื่นไม่ครบ"
};

export const LEGACY_SECTION_MAP: Record<string, [string, string | null] | null> = {
  "s1": [
    "background",
    null
  ],
  "s2": [
    "objective",
    null
  ],
  "s3": [
    "qualification",
    null
  ],
  "s4": [
    "scope",
    null
  ],
  "s5": [
    "schedule",
    null
  ],
  "s6": [
    "budget",
    null
  ],
  "s7": [
    "scope",
    "scope.installation"
  ],
  "s8": [
    "payment",
    null
  ],
  "s9": [
    "warranty",
    null
  ],
  "s10": [
    "penalty",
    null
  ],
  "s11": [
    "evaluation",
    null
  ],
  "s12": [
    "qualification",
    "qual.documents"
  ],
  "s13": [
    "other_conditions",
    null
  ]
};

export const DOCUMENT_TITLE = "ขอบเขตของงาน (Terms of Reference : TOR)";

export const DRAFT_DOCUMENT_TITLE = "ร่างขอบเขตของงาน (Terms of Reference : TOR)";
