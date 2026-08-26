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
  { key: "s4.2", title: "ระบบงานปัจจุบัน" },
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
  { id: "charter", label: "เอกสารโครงการ", required: false },
  { id: "as_is", label: "เอกสารระบบเดิม", required: false },
  { id: "stakeholders", label: "รายชื่อผู้เกี่ยวข้อง", required: false },
  { id: "policy", label: "นโยบายที่เกี่ยวข้อง", required: false },
  { id: "tender_draft", label: "ร่างเอกสารประกวดราคา", required: false },
  { id: "kickoff", label: "รายงานประชุมเริ่มโครงการ", required: false },
] as const;

export const PHASE0_CHECKLIST = [
  "เอกสารอนุมัติงบประมาณ",
  "ประกาศราคากลางฉบับทางการ",
  "เอกสารโครงการ",
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
    { key: "mainObj", label: "วัตถุประสงค์หลัก (ชัดเจน วัดผลได้)", type: "textarea" },
    { key: "users", label: "กลุ่มผู้ใช้งานเป้าหมาย", type: "text" },
    { key: "kpi", label: "ตัวชี้วัดความสำเร็จ", type: "textarea" },
  ],
  s3: [
    { key: "general", label: "คุณสมบัติทั่วไป", type: "textarea" },
    { key: "paidup", label: "ทุนจดทะเบียน/มูลค่ากิจการขั้นต่ำ", type: "text", mapField: "paidupSuggest" },
    { key: "experience", label: "ผลงาน/ประสบการณ์ที่ต้องการ", type: "textarea" },
  ],
  s5: [
    { key: "timelineRange", label: "วันเริ่มต้น - วันสิ้นสุด", type: "text", mapField: "timeline" },
    { key: "milestones", label: "งวดงานหลัก", type: "textarea" },
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
      options: ["เกณฑ์ราคา", "เกณฑ์ราคาประกอบเกณฑ์คุณภาพ", "เกณฑ์คุณภาพเท่านั้น"],
    },
    { key: "evalWeight", label: "สัดส่วนคะแนน (ถ้ามีเกณฑ์คุณภาพ)", type: "text" },
  ],
  s12: [{ key: "docs", label: "รายการเอกสารที่ต้องยื่นประกอบ", type: "textarea" }],
  s13: [{ key: "other", label: "เงื่อนไขอื่น ๆ", type: "textarea" }],
};

export function parseSectionDraft(sectionKey: string, content: string): Record<string, string> {
  const fields = SECTION_FIELDS[sectionKey];
  const firstKey = fields?.[0]?.key || "body";
  const raw = (content || "").trim();
  if (!raw) return {};

  if (raw.startsWith("{")) {
    try {
      const parsed = JSON.parse(raw) as unknown;
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        const rec = parsed as Record<string, string>;
        const out: Record<string, string> = {};
        for (const field of fields || []) {
          const value = String(rec[field.key] || "").trim();
          if (value) out[field.key] = value;
        }
        const blob = String(rec.body || "").trim();
        if (blob) {
          const labeledBlob = splitByHeadings(blob, fields || [], "label");
          if (Object.keys(labeledBlob).length) {
            for (const [key, value] of Object.entries(labeledBlob)) {
              if (!out[key]) out[key] = value;
            }
          } else if (!out[firstKey]) {
            out[firstKey] = blob;
          }
        }
        if (Object.keys(out).length) return out;
      }
    } catch {
      // prose
    }
  }

  const headed = splitByHeadings(raw, fields || [], "hash");
  if (Object.keys(headed).length) return headed;

  const labeled = splitByHeadings(raw, fields || [], "label");
  if (Object.keys(labeled).length) return labeled;

  const paras = raw.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean);
  if (fields && paras.length >= 2) {
    const out: Record<string, string> = {};
    fields.forEach((field, index) => {
      if (index < paras.length) {
        out[field.key] = index === fields.length - 1 ? paras.slice(index).join("\n\n") : paras[index];
      }
    });
    return out;
  }
  return { [firstKey]: raw };
}

const DRAFT_HEADING_RE = /^#{1,3}[ \t]+([^\r\n]+)/;
const LINE_PREFIX_RE = /^(?:[#*_]+[\t ]*)?(?:[0-9๐-๙]+[.)][\t ]*)?/;

function matchFieldHeading(title: string, fields: SectionField[]): string | null {
  const trimmed = title
    .replace(LINE_PREFIX_RE, "")
    .replace(/[#*_]/g, "")
    .replace(/[:：]\s*$/, "")
    .trim();
  if (!trimmed || trimmed.length > 80) return null;
  for (const field of fields) {
    const short = field.label.split("(", 1)[0].trim();
    if (trimmed === field.key || trimmed === field.label || trimmed === short) {
      return field.key;
    }
    if (trimmed.startsWith(field.key) || trimmed.startsWith(field.label)) {
      return field.key;
    }
    if (trimmed.length >= 4 && (field.label.startsWith(trimmed) || short.startsWith(trimmed))) {
      return field.key;
    }
  }
  return null;
}

function splitByHeadings(
  raw: string,
  fields: SectionField[],
  mode: "hash" | "label"
): Record<string, string> {
  const out: Record<string, string> = {};
  let current: string | null = null;
  const buf: string[] = [];
  let sawHeading = false;
  const flush = () => {
    if (current) {
      const value = buf.join("\n").trim();
      if (value) out[current] = value;
    }
  };
  for (const line of raw.split("\n")) {
    let found: string | null = null;
    if (mode === "hash") {
      const match = DRAFT_HEADING_RE.exec(line.trim());
      found = match ? matchFieldHeading(match[1].trim(), fields) : null;
    } else if (line.trim()) {
      found = matchFieldHeading(line.trim(), fields);
    }
    if (found) {
      sawHeading = true;
      flush();
      current = found;
      buf.length = 0;
      continue;
    }
    buf.push(line);
  }
  flush();
  if (mode === "label" && !sawHeading) return {};
  return out;
}

export function isSectionFilled(section: {
  filled?: boolean;
  subs?: { filled: boolean }[];
}): boolean {
  if (section.filled) return true;
  return Boolean(section.subs?.some((sub) => sub.filled));
}

export function serializeSectionDraft(draft: Record<string, string>): string {
  const entries = Object.entries(draft)
    .filter(([key, value]) => key !== "body" && (value || "").trim())
    .map(([key, value]) => [key, value.trim()] as const);
  if (!entries.length) {
    const body = (draft.body || "").trim();
    return body;
  }
  return JSON.stringify(Object.fromEntries(entries));
}

export function previewSectionDraft(sectionKey: string, content: string): string {
  const values = parseSectionDraft(sectionKey, content);
  return Object.values(values).filter(Boolean).join(" ").slice(0, 240);
}

export function labeledSectionBlocks(
  sectionKey: string,
  content: string
): { label: string; text: string }[] {
  const fields = SECTION_FIELDS[sectionKey] || [];
  const values = parseSectionDraft(sectionKey, content);
  const blocks = fields
    .map((field) => ({ label: field.label, text: values[field.key] || "" }))
    .filter((item) => item.text.trim());
  if (blocks.length) return blocks;
  const fallback = (content || "").trim();
  return fallback ? [{ label: "", text: fallback }] : [];
}

