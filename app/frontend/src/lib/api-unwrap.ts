import type { AxiosResponse } from "axios";
import type { ApiResponse } from "@/types";

/** Unwrap FastAPI SuccessResponse { ok, data } or return raw payload. */
export function unwrapData<T>(response: AxiosResponse<unknown>): T {
  const body = response.data as ApiResponse<T> & T;
  if (body && typeof body === "object" && "ok" in body && "data" in body) {
    return ((body as ApiResponse<T>).data as T) ?? (body as T);
  }
  return body as T;
}

export function asString(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

function toOptionalNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

export function snakeToCamelProject(raw: Record<string, unknown>) {
  const qualityFromSnake = toOptionalNumber(raw.quality_score);
  const qualityFromCamel = toOptionalNumber(raw.qualityScore);
  return {
    id: asString(raw.id),
    ownerId: asString(raw.owner_id) || asString(raw.ownerId),
    name: asString(raw.name),
    ministry: asString(raw.ministry),
    budget: Number(raw.budget ?? 0),
    projectType: (asString(raw.project_type) || asString(raw.projectType) || "general") as
      | "it"
      | "construction"
      | "consulting"
      | "general",
    status: (asString(raw.status) || "draft") as
      | "draft"
      | "in_review"
      | "approved"
      | "rejected"
      | "archived",
    currentStep: Number(raw.current_step ?? raw.currentStep ?? 1),
    currentPhase: Number(raw.current_phase ?? raw.currentPhase ?? 0),
    analysisJson: (raw.analysis_json as Record<string, unknown>) || {},
    extractedFields: (raw.extracted_fields as Record<string, unknown>) || {},
    qualityScore: qualityFromSnake ?? qualityFromCamel,
    templateId: asString(raw.template_id) || asString(raw.templateId) || null,
    createdAt: asString(raw.created_at) || asString(raw.createdAt),
    updatedAt: asString(raw.updated_at) || asString(raw.updatedAt),
  };
}
