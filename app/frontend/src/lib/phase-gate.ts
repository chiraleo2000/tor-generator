import type { Project } from "@/types";

type SlotLike = { status?: string; content?: string };

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function hasBeenAnalyzed(analysis: Record<string, unknown>): boolean {
  if (analysis.analyzed === true) {
    return true;
  }
  const slotMap = asRecord(analysis.slot_map);
  return Object.keys(slotMap).length > 0;
}

/** Highest selectable phase: 0 before analyze, 2 after analyze, 3 compose, 4 confirmed. */
export function intakeUnlockedPhase(
  project: Pick<Project, "analysisJson" | "extractedFields">
): number {
  const analysis = asRecord(project.analysisJson);
  if (analysis.phase4_confirmed === true) {
    return 4;
  }
  if (analysis.ready_to_compose === true) {
    return 3;
  }
  if (hasBeenAnalyzed(analysis)) {
    return 2;
  }
  return 0;
}

export function canSelectPhase(current: number, unlocked: number, target: number): boolean {
  if (target < 0 || target > 4) return false;
  if (target <= current) return true;
  return target <= unlocked;
}

export function displayPhase(saved: number, unlocked: number): number {
  if (saved <= unlocked) return saved;
  return unlocked;
}

export function hasIntakeMaterial(project: Pick<Project, "analysisJson" | "extractedFields">): boolean {
  const texts = project.extractedFields?.intake_texts;
  if (Array.isArray(texts)) {
    const hasText = texts.some((item) => {
      if (!item || typeof item !== "object") return false;
      return Boolean(String((item as { text?: string }).text || "").trim());
    });
    if (hasText) return true;
  }
  const analysis = asRecord(project.analysisJson);
  const files = analysis.intake_files;
  if (Array.isArray(files) && files.length > 0) {
    return true;
  }
  const slotMap = asRecord(analysis.slot_map);
  for (const slot of Object.values(slotMap)) {
    const row = slot as SlotLike;
    if (row?.status === "filled" && String(row.content || "").trim()) {
      return true;
    }
  }
  return false;
}
