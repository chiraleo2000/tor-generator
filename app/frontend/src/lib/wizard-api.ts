import type { Step1Data, Step4Data, Step5Data, Step6Data } from "@/types/wizard";
import { SCOPE_SUBSECTIONS } from "@/lib/tor-sections";

export function toWizardApiPayload(step: number, data: unknown): Record<string, unknown> {
  const source = (data ?? {}) as Record<string, unknown>;
  if (step === 1) {
    const d = source as unknown as Step1Data & {
      location?: string;
      duration_days?: number | null;
    };
    return {
      project_name: d.project_name,
      ministry: d.ministry,
      budget: d.budget,
      project_type: d.project_type,
      template_id: d.template_id,
      location: d.location ?? "",
      duration_days: d.duration_days ?? null,
    };
  }
  if (step === 2) {
    return { description: source.description ?? source.problemDescription ?? "" };
  }
  if (step === 3) {
    return { objectives: source.objectives ?? [] };
  }
  if (step === 4) {
    const d = source as unknown as Step4Data;
    const payload: Record<string, unknown> = {
      scope_items: d.scope_items ?? [],
      deliverables: d.deliverables ?? [],
    };
    (d.scope_items ?? []).forEach((item, index) => {
      const key = SCOPE_SUBSECTIONS[index]?.key ?? `s4.${index + 1}`;
      payload[key] = `${item.title}\n${item.details}`.trim();
    });
    return payload;
  }
  if (step === 5) {
    const d = source as unknown as Step5Data;
    return {
      qualifications: d.qualifications ?? [],
      paid_up_capital: d.paid_up_capital ?? null,
    };
  }
  if (step === 6) {
    const d = source as unknown as Step6Data & { warranty?: string; duration_days?: number };
    return {
      budget_breakdown: d.budget_breakdown ?? [],
      payment_schedule: d.payment_schedule ?? [],
      penalty_rate: d.penalty_rate ?? null,
      warranty: d.warranty ?? "",
      duration_days: d.duration_days ?? null,
    };
  }
  return source;
}
