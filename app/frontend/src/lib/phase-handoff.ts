/** Continuous Phase 0→4 handoff contract (UI labels + exit checks). */

export const PHASE_LABELS_TH = [
  "ขั้นที่ ๐ เตรียมข้อมูล",
  "ขั้นที่ ๑ ผลวิเคราะห์",
  "ขั้นที่ ๒ สอบถามเพิ่ม",
  "ขั้นที่ ๓ ร่างเนื้อหา",
  "ขั้นที่ ๔ ทบทวนและส่งออก",
] as const;

export function phaseLabelTh(phase: number): string {
  if (phase < 0 || phase > 4) return "ขั้นตอน";
  return PHASE_LABELS_TH[phase];
}

export function canLeavePhase0(analyzed: boolean, coverageCount: number): boolean {
  return analyzed && coverageCount > 0;
}

export function canLeavePhase2(factReady: boolean): boolean {
  return factReady;
}

export function canLeavePhase3(allDrafted: boolean): boolean {
  return allDrafted;
}

export function canSubmitPhase4(filledCount: number, total: number): boolean {
  return total > 0 && filledCount >= total;
}

export function coverageStatusLabel(status: string): string {
  if (status === "filled") return "ครบ";
  if (status === "reference_only") return "อ้างอิง";
  if (status === "gap") return "ยังขาด";
  return status;
}
