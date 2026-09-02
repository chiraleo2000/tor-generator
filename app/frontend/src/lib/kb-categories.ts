export const KB_CATEGORIES = [
  { id: "law", label: "พ.ร.บ. / กฎหมาย" },
  { id: "regulation", label: "กฎกระทรวง" },
  { id: "guideline", label: "ระเบียบกระทรวงการคลัง" },
  { id: "circular", label: "หนังสือเวียนกรมบัญชีกลาง" },
  { id: "price_announcement", label: "ประกาศราคากลาง" },
  { id: "manual", label: "คู่มือปฏิบัติงาน" },
  { id: "example_tor", label: "ตัวอย่าง TOR" },
  { id: "template", label: "แม่แบบ" },
  { id: "other", label: "ข้อมูลอื่น ๆ" },
] as const;

export type KbCategoryId = (typeof KB_CATEGORIES)[number]["id"];

export const KB_PROCESSING_LABEL: Record<string, string> = {
  pending: "รอประมวลผล",
  processing: "กำลังอ่านโครงสร้างเอกสาร",
  completed: "พร้อมค้นหาด้วย PageIndex",
  failed: "ประมวลผลไม่สำเร็จ",
};

export function kbCategoryLabel(id: string): string {
  return KB_CATEGORIES.find((item) => item.id === id)?.label ?? id;
}

export function kbProcessingLabel(status: string | undefined): string {
  if (!status) return "";
  return KB_PROCESSING_LABEL[status] || status;
}

export function kbProcessingBadgeClass(status: string | undefined): string {
  if (status === "failed") return "bg-red-50 font-bold text-red-800";
  if (status === "completed") return "bg-green-50 font-bold text-green-800";
  if (status === "processing") return "bg-amber-50 font-bold text-amber-800";
  return "bg-gray-100 font-bold text-gray-700";
}

export function uniqueById<T extends { id: string }>(rows: T[]): T[] {
  const byId = new Map<string, T>();
  for (const row of rows) {
    byId.set(row.id, row);
  }
  return Array.from(byId.values());
}
