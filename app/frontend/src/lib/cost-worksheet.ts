import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";

export const COST_LINE_KEYS = [
  "personnel",
  "equipment",
  "procurement",
  "consultant",
  "training",
] as const;

export const TRAINING_PART_KEYS = ["food", "snack", "documents", "venue"] as const;

export type CostLineKey = (typeof COST_LINE_KEYS)[number];
export type TrainingPartKey = (typeof TRAINING_PART_KEYS)[number];

export type CostWorksheet = Record<CostLineKey | TrainingPartKey, number> & {
  total: number;
  is_announced_price: false;
  label: string;
};

export type CostCalculationInput = {
  apply_calculated?: boolean;
  team_size?: number;
  months?: number;
  years?: number | null;
  training_days?: number;
  day_part?: string;
  attendees?: number;
  equipment_quantity?: number;
  equipment_unit_price?: number | null;
  procurement_quantity?: number;
  procurement_unit_price?: number | null;
};

export const COST_LINE_LABELS: Record<CostLineKey, string> = {
  personnel: "ทรัพยากรบุคคล",
  equipment: "อุปกรณ์",
  procurement: "การจัดซื้อจัดจ้าง",
  consultant: "การจ้างที่ปรึกษา",
  training: "ค่าอบรม",
};

export const TRAINING_PART_LABELS: Record<TrainingPartKey, string> = {
  food: "อาหาร",
  snack: "อาหารว่าง",
  documents: "เอกสาร",
  venue: "สถานที่",
};

export const COST_WORKSHEET_DISCLAIMER =
  "ใบประมาณการที่เจ้าหน้าที่กรอก — ไม่ใช่ราคากลาง";

const LEGACY_LINE_KEYS: Partial<Record<CostLineKey, string>> = {
  personnel: "labor",
  equipment: "license",
  procurement: "maintenance",
};

export function emptyCostWorksheet(): CostWorksheet {
  return {
    personnel: 0,
    equipment: 0,
    procurement: 0,
    consultant: 0,
    training: 0,
    food: 0,
    snack: 0,
    documents: 0,
    venue: 0,
    total: 0,
    is_announced_price: false,
    label: COST_WORKSHEET_DISCLAIMER,
  };
}

function asAmount(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
    return value;
  }
  if (typeof value !== "string") return 0;
  const text = value.replaceAll(",", "").trim();
  if (!text) return 0;
  const parsed = Number.parseFloat(text);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

function lineAmount(src: Record<string, unknown>, key: CostLineKey): number {
  const current = asAmount(src[key]);
  if (current > 0) return current;
  const legacy = LEGACY_LINE_KEYS[key];
  if (legacy) {
    const older = asAmount(src[legacy]);
    if (older > 0) return older;
  }
  return current;
}

function partAmount(src: Record<string, unknown>, key: TrainingPartKey): number {
  if (src[key] !== undefined && src[key] !== null && src[key] !== "") {
    return asAmount(src[key]);
  }
  const parts = src.training_parts;
  if (parts && typeof parts === "object") {
    return asAmount((parts as Record<string, unknown>)[key]);
  }
  return 0;
}

export function normalizeCostWorksheet(raw: unknown): CostWorksheet {
  const src = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const next = emptyCostWorksheet();
  for (const key of COST_LINE_KEYS) {
    if (key === "training") continue;
    next[key] = lineAmount(src, key);
  }
  for (const key of TRAINING_PART_KEYS) {
    next[key] = partAmount(src, key);
  }
  const partSum = TRAINING_PART_KEYS.reduce((sum, key) => sum + next[key], 0);
  next.training = partSum > 0 ? partSum : lineAmount(src, "training");
  next.total = COST_LINE_KEYS.reduce((sum, key) => sum + next[key], 0);
  next.is_announced_price = false;
  next.label = COST_WORKSHEET_DISCLAIMER;
  return next;
}

export function costWorksheetFromAnalysis(analysis?: Record<string, unknown> | null): CostWorksheet {
  return normalizeCostWorksheet(analysis?.cost_worksheet);
}

export function parseCostFromSectionContent(content: string): CostWorksheet | null {
  const raw = (content || "").trim();
  if (!raw.startsWith("{")) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const blob = parsed.cost_worksheet ?? parsed.costWorksheet;
    if (!blob || typeof blob !== "object") return null;
    return normalizeCostWorksheet(blob);
  } catch {
    return null;
  }
}

export async function fetchCostWorksheet(projectId: string): Promise<CostWorksheet> {
  const response = await apiClient.get(`/projects/${projectId}/draft-chat/cost-worksheet`);
  return normalizeCostWorksheet(unwrapData(response));
}

export async function saveCostWorksheet(
  projectId: string,
  sheet: CostWorksheet,
  extra?: CostCalculationInput
): Promise<CostWorksheet> {
  const response = await apiClient.put(`/projects/${projectId}/draft-chat/cost-worksheet`, {
    personnel: sheet.personnel,
    equipment: sheet.equipment,
    procurement: sheet.procurement,
    consultant: sheet.consultant,
    training: sheet.training,
    food: sheet.food,
    snack: sheet.snack,
    documents: sheet.documents,
    venue: sheet.venue,
    ...extra,
  });
  return normalizeCostWorksheet(unwrapData(response));
}
