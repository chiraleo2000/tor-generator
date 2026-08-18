import type { Project } from "@/types";

type SlotLike = { status?: string; content?: string };

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

/** Highest intake phase allowed: 0 empty, 1 has text/files, 2 confirmed ready. */
export function intakeUnlockedPhase(project: Pick<Project, "analysisJson" | "extractedFields">): number {
  const analysis = asRecord(project.analysisJson);
  if (analysis.ready_to_compose === true) {
    return 2;
  }
  const texts = project.extractedFields?.intake_texts;
  if (Array.isArray(texts)) {
    const hasText = texts.some((item) => {
      if (!item || typeof item !== "object") return false;
      return Boolean(String((item as { text?: string }).text || "").trim());
    });
    if (hasText) return 1;
  }
  const files = analysis.intake_files;
  if (Array.isArray(files) && files.length > 0) {
    return 1;
  }
  const slotMap = asRecord(analysis.slot_map);
  for (const slot of Object.values(slotMap)) {
    const row = slot as SlotLike;
    if (row?.status === "filled" && String(row.content || "").trim()) {
      return 1;
    }
  }
  return 0;
}

export function canSelectPhase(current: number, unlocked: number, target: number): boolean {
  if (target < 0 || target > 4) return false;
  if (target <= current) return true;
  if (target <= unlocked) return true;
  return unlocked >= 2 && target === current + 1;
}

export function displayPhase(saved: number, unlocked: number): number {
  if (saved <= unlocked) return saved;
  if (saved >= 2 && unlocked < 2) return unlocked;
  if (saved === 1 && unlocked < 1) return 0;
  return saved;
}
