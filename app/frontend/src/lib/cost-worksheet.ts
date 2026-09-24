import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";

export const COST_LINE_KEYS = ["license", "labor", "maintenance", "training"] as const;

export type CostLineKey = (typeof COST_LINE_KEYS)[number];

export type CostWorksheet = Record<CostLineKey, number> & {
  total: number;
  is_announced_price: false;
  label: string;
};

export const COST_LINE_LABELS: Record<CostLineKey, string> = {
  license: "ค่าลิขสิทธิ์",
  labor: "ค่าแรง",
  maintenance: "ค่าบำรุงรักษา",
  training: "ค่าอบรม",
};

export const COST_WORKSHEET_DISCLAIMER =
  "ใบประมาณการที่เจ้าหน้าที่กรอก — ไม่ใช่ราคากลาง";

export function emptyCostWorksheet(): CostWorksheet {
  return {
    license: 0,
    labor: 0,
    maintenance: 0,
    training: 0,
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
  const text = value
    .replaceAll(",", "")
    .trim();
  if (!text) return 0;
  const parsed = Number.parseFloat(text);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

export function normalizeCostWorksheet(raw: unknown): CostWorksheet {
  const src = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const next = emptyCostWorksheet();
  for (const key of COST_LINE_KEYS) {
    next[key] = asAmount(src[key]);
  }
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
  sheet: CostWorksheet
): Promise<CostWorksheet> {
  const response = await apiClient.put(`/projects/${projectId}/draft-chat/cost-worksheet`, {
    license: sheet.license,
    labor: sheet.labor,
    maintenance: sheet.maintenance,
    training: sheet.training,
  });
  return normalizeCostWorksheet(unwrapData(response));
}
