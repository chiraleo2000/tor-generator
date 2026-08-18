/** Canonical TOR section model — mirrors backend/app/domain/tor_sections.py. */

export const TOR_SECTION_ORDER = [
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
] as const;

export type TorSectionKey = (typeof TOR_SECTION_ORDER)[number];

export const TOR_SECTION_LABELS: Record<TorSectionKey, string> = {
  s1: "ความเป็นมา",
  s2: "วัตถุประสงค์",
  s3: "คุณสมบัติของผู้เสนอราคา",
  s4: "ขอบเขตของงาน",
  s5: "ระยะเวลาดำเนินการ",
  s6: "วงเงินงบประมาณ",
  s7: "สถานที่ดำเนินการ",
  s8: "งวดงานและการจ่ายเงิน",
  s9: "การรับประกัน",
  s10: "อัตราค่าปรับ",
  s11: "หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ",
  s12: "เอกสารและหลักฐานที่ผู้เสนอราคาต้องนำมายื่น",
  s13: "เงื่อนไขอื่น ๆ",
};

export const SCOPE_SUBSECTIONS: { key: string; title: string }[] = [
  { key: "s4.1", title: "สรุปขอบเขตงาน" },
  { key: "s4.2", title: "ระบบงานปัจจุบัน (As-Is)" },
  { key: "s4.3", title: "งานหลักและกิจกรรม" },
  { key: "s4.4", title: "ข้อกำหนดด้านฮาร์ดแวร์" },
  { key: "s4.5", title: "ข้อกำหนดด้านซอฟต์แวร์และลิขสิทธิ์" },
  { key: "s4.6", title: "จุดเชื่อมโยงระบบ" },
  { key: "s4.7", title: "มาตรฐานและแบบอ้างอิง" },
  { key: "s4.8", title: "ผลงานส่งมอบ" },
  { key: "s4.9", title: "ระยะเวลาการสนับสนุนและบำรุงรักษา" },
  { key: "s4.10", title: "บุคลากรและทีมงาน" },
  { key: "s4.11", title: "รูปแบบการบำรุงรักษา" },
  { key: "s4.12", title: "การดำเนินงานและการบริหารจัดการ" },
  { key: "s4.13", title: "แผนสำรองและกู้คืนระบบ" },
  { key: "s4.14", title: "ข้อกำหนดด้านความมั่นคงปลอดภัย" },
];

export const STEP_SECTION_MAP: Record<number, string[]> = {
  1: ["s5", "s7"],
  2: ["s1"],
  3: ["s2"],
  4: ["s4"],
  5: ["s3"],
  6: ["s5", "s6", "s8", "s9", "s10"],
  7: [...TOR_SECTION_ORDER],
  8: [],
};

export const ORPHAN_SECTIONS = ["s7", "s11", "s12", "s13"] as const;

export const HITL_SECTIONS: string[] = ["s3", "s6", "s8", "s10", "s13"];

export const DOC_CLASSES = [
  { id: "announced_price", label: "ประกาศราคากลาง", required: true },
  { id: "budget_approval", label: "หนังสืออนุมัติงบประมาณ", required: true },
  { id: "fiscal_year", label: "เอกสารปีงบประมาณ", required: false },
  { id: "charter", label: "เอกสารโครงการ (Charter / Brief)", required: false },
  { id: "as_is", label: "เอกสารระบบเดิม (As-Is)", required: false },
  { id: "stakeholders", label: "รายชื่อผู้เกี่ยวข้อง", required: false },
  { id: "policy", label: "นโยบายที่เกี่ยวข้อง", required: false },
  { id: "tender_draft", label: "ร่างเอกสารประกวดราคา", required: false },
  { id: "kickoff", label: "รายงานประชุม Kickoff", required: false },
] as const;

export const PHASE0_CHECKLIST = [
  "เอกสารอนุมัติงบประมาณ",
  "ประกาศราคากลางฉบับทางการ",
  "เอกสารโครงการ (Charter / Brief)",
  "รายงานการประชุม",
  "รายชื่อผู้เกี่ยวข้อง",
] as const;

export interface SectionField {
  key: string;
  label: string;
  type: "text" | "textarea" | "number" | "select";
  placeholder?: string;
  mapField?: string;
  options?: string[];
}

export const SECTION_FIELDS: Record<string, SectionField[]> = {
  s1: [
    { key: "history", label: "ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม", type: "textarea" },
    { key: "problems", label: "ปัญหาที่พบ (ระบุตัวเลข/สถิติ)", type: "textarea", mapField: "problem" },
    { key: "policy", label: "นโยบาย/กฎหมายที่เกี่ยวข้อง", type: "text" },
  ],
  s2: [
    { key: "mainObj", label: "วัตถุประสงค์หลัก (SMART)", type: "textarea" },
    { key: "users", label: "กลุ่มผู้ใช้งานเป้าหมาย", type: "text" },
    { key: "kpi", label: "ตัวชี้วัดความสำเร็จ (KPI)", type: "textarea" },
  ],
  s3: [
    { key: "general", label: "คุณสมบัติทั่วไป", type: "textarea" },
    { key: "paidup", label: "ทุนจดทะเบียน/มูลค่ากิจการขั้นต่ำ", type: "text", mapField: "paidupSuggest" },
    { key: "experience", label: "ผลงาน/ประสบการณ์ที่ต้องการ", type: "textarea" },
  ],
  s5: [
    { key: "timelineRange", label: "วันเริ่มต้น - วันสิ้นสุด", type: "text", mapField: "timeline" },
    { key: "milestones", label: "งวดงาน/Milestone หลัก", type: "textarea" },
  ],
  s6: [
    { key: "budgetAmount", label: "วงเงินงบประมาณ (บาท)", type: "number", mapField: "budget" },
    { key: "budgetSource", label: "ที่มาของงบประมาณ", type: "text" },
  ],
  s7: [{ key: "location", label: "สถานที่ดำเนินการ", type: "textarea" }],
  s8: [
    { key: "installments", label: "จำนวนงวดการจ่ายเงิน", type: "number" },
    { key: "paymentTerms", label: "เงื่อนไขการเบิกจ่ายแต่ละงวด", type: "textarea", mapField: "paymentPercentsText" },
  ],
  s9: [{ key: "warranty", label: "ระยะเวลารับประกัน", type: "textarea" }],
  s10: [{ key: "penalty", label: "ค่าปรับกรณีระบบขัดข้อง/ล่าช้า", type: "textarea" }],
  s11: [
    {
      key: "evalMethod",
      label: "วิธีการประเมิน",
      type: "select",
      mapField: "evaluationMethod",
      options: ["เกณฑ์ราคา (Price)", "เกณฑ์ราคาประกอบเกณฑ์คุณภาพ", "เกณฑ์คุณภาพเท่านั้น"],
    },
    { key: "evalWeight", label: "สัดส่วนคะแนน (ถ้ามีเกณฑ์คุณภาพ)", type: "text" },
  ],
  s12: [{ key: "docs", label: "รายการเอกสารที่ต้องยื่นประกอบ", type: "textarea" }],
  s13: [{ key: "other", label: "เงื่อนไขอื่น ๆ", type: "textarea" }],
};

