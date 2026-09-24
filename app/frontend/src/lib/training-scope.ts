import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";
import { categoryForProject, scopeSubsectionsFor } from "@/lib/tor-profiles";

export const TRAINING_FIELD_KEYS = ["cohorts", "hours", "attendees", "documents"] as const;

export type TrainingFieldKey = (typeof TRAINING_FIELD_KEYS)[number];

export type TrainingScopeFields = Record<TrainingFieldKey, string>;

export const TRAINING_FIELD_LABELS: Record<TrainingFieldKey, string> = {
  cohorts: "จำนวนรุ่น",
  hours: "จำนวนชั่วโมง",
  attendees: "จำนวนผู้เข้าอบรม",
  documents: "เอกสารส่งมอบ",
};

export const TRAINING_CATEGORIES = new Set(["hire_develop", "buy_goods"]);

export const TRAINING_SUB_KEY = "training";

export function emptyTrainingScope(): TrainingScopeFields {
  return { cohorts: "", hours: "", attendees: "", documents: "" };
}

export function normalizeTrainingScope(raw: unknown): TrainingScopeFields {
  const src = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const next = emptyTrainingScope();
  for (const key of TRAINING_FIELD_KEYS) {
    const value = src[key];
    next[key] = typeof value === "string" || typeof value === "number" ? String(value).trim() : "";
  }
  return next;
}

export function categoryHasTraining(projectType?: string | null): boolean {
  const category = categoryForProject(projectType);
  if (!TRAINING_CATEGORIES.has(category)) return false;
  return scopeSubsectionsFor(category).some(
    (item) => item.key === TRAINING_SUB_KEY || item.semantic_key === "scope.training"
  );
}

export function trainingScopeProse(
  fields: TrainingScopeFields,
  hint = "หลักสูตร จำนวนผู้เข้าอบรม จำนวนรุ่น สถานที่ และการที่คู่สัญญารับผิดชอบค่าใช้จ่ายทั้งหมด"
): string {
  const lines = ["การฝึกอบรมและการถ่ายทอดความรู้", hint];
  if (fields.cohorts.trim()) lines.push(`${TRAINING_FIELD_LABELS.cohorts}: ${fields.cohorts.trim()} รุ่น`);
  if (fields.hours.trim()) lines.push(`${TRAINING_FIELD_LABELS.hours}: ${fields.hours.trim()} ชั่วโมง`);
  if (fields.attendees.trim()) {
    lines.push(`${TRAINING_FIELD_LABELS.attendees}: ${fields.attendees.trim()} คน`);
  }
  if (fields.documents.trim()) {
    lines.push(`${TRAINING_FIELD_LABELS.documents}: ${fields.documents.trim()}`);
  }
  lines.push(
    "คู่สัญญารับผิดชอบค่าใช้จ่ายในการอบรมทั้งหมด และต้องแจ้งกำหนดล่วงหน้าเป็นลายลักษณ์อักษร"
  );
  return lines.join("\n");
}

export function parseTrainingFromContent(content: string): TrainingScopeFields | null {
  const raw = (content || "").trim();
  if (!raw.startsWith("{")) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (!TRAINING_FIELD_KEYS.some((key) => {
      const value = parsed[key];
      if (typeof value === "number") return String(value).trim().length > 0;
      return typeof value === "string" && value.trim().length > 0;
    })) {
      return null;
    }
    return normalizeTrainingScope(parsed);
  } catch {
    return null;
  }
}

export async function fetchTrainingScope(projectId: string): Promise<{
  enabled: boolean;
  fields: TrainingScopeFields;
  prose: string;
}> {
  const response = await apiClient.get(`/projects/${projectId}/draft-chat/training-scope`);
  const data = unwrapData<{
    enabled?: boolean;
    fields?: TrainingScopeFields;
    prose?: string;
  }>(response);
  const fields = normalizeTrainingScope(data.fields);
  return {
    enabled: Boolean(data.enabled),
    fields,
    prose: (data.prose || "").trim() || trainingScopeProse(fields),
  };
}

export async function saveTrainingScope(
  projectId: string,
  fields: TrainingScopeFields
): Promise<{ fields: TrainingScopeFields; prose: string }> {
  const response = await apiClient.put(`/projects/${projectId}/draft-chat/training-scope`, fields);
  const data = unwrapData<{ fields?: TrainingScopeFields; prose?: string }>(response);
  const next = normalizeTrainingScope(data.fields || fields);
  return { fields: next, prose: (data.prose || "").trim() || trainingScopeProse(next) };
}
