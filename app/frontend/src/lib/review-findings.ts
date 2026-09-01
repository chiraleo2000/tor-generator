import { asString } from "@/lib/api-unwrap";

export type FindingSeverity = "error" | "warning" | "suggestion";
export type FindingKind = "legal_violation" | "risk_abnormality";
export type RiskType = "vague" | "price" | "cost" | "content";

export interface ReviewFinding {
  severity: FindingSeverity;
  rule: string;
  section: string;
  message: string;
  recommendation: string;
  findingKind?: FindingKind;
  legalBasis?: string;
  excerpt?: string;
  riskType?: string;
}

const RISK_RULE_MARKERS = /CONSISTENCY_|FORMAT_INFORMAL|RISK_/;

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

export function toFindingKind(raw: Record<string, unknown>): FindingKind {
  const explicit = asString(raw.finding_kind) || asString(raw.findingKind);
  if (explicit === "legal_violation" || explicit === "risk_abnormality") {
    return explicit;
  }
  const rule = asString(raw.rule) || asString(raw.rule_violated);
  if (RISK_RULE_MARKERS.test(rule)) {
    return "risk_abnormality";
  }
  return "legal_violation";
}

export function toReviewFinding(raw: Record<string, unknown>): ReviewFinding {
  return {
    severity: toFindingSeverity(raw.severity),
    rule: asString(raw.rule) || asString(raw.rule_violated),
    section: asString(raw.section) || asString(raw.affected_section),
    message: asString(raw.message),
    recommendation:
      asString(raw.recommendation) || asString(raw.recommended_correction),
    findingKind: toFindingKind(raw),
    legalBasis: asString(raw.legal_basis) || asString(raw.legalBasis),
    excerpt: asString(raw.excerpt),
    riskType: asString(raw.risk_type) || asString(raw.riskType),
  };
}

export function splitReviewFindings(findings: ReviewFinding[]): {
  legal: ReviewFinding[];
  risk: ReviewFinding[];
} {
  return {
    legal: findings.filter((item) => item.findingKind !== "risk_abnormality"),
    risk: findings.filter((item) => item.findingKind === "risk_abnormality"),
  };
}

export function findingDetail(finding: ReviewFinding): string {
  return [finding.section, finding.legalBasis, finding.recommendation]
    .filter(Boolean)
    .join(" — ");
}
