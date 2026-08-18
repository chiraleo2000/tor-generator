import { asString } from "@/lib/api-unwrap";

export type FindingSeverity = "error" | "warning" | "suggestion";

export interface ReviewFinding {
  severity: FindingSeverity;
  rule: string;
  section: string;
  message: string;
  recommendation: string;
}

export function toFindingSeverity(value: unknown): FindingSeverity {
  if (value === "error" || value === "warning" || value === "suggestion") {
    return value;
  }
  return "warning";
}

export function findingCheckTone(severity: string): "pass" | "warn" | "fail" {
  if (severity === "error") return "fail";
  if (severity === "warning") return "warn";
  return "pass";
}

export function toReviewFinding(raw: Record<string, unknown>): ReviewFinding {
  return {
    severity: toFindingSeverity(raw.severity),
    rule: asString(raw.rule) || asString(raw.rule_violated),
    section: asString(raw.section) || asString(raw.affected_section),
    message: asString(raw.message),
    recommendation:
      asString(raw.recommendation) || asString(raw.recommended_correction),
  };
}
