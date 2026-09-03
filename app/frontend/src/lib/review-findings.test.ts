import { describe, expect, it } from "vitest";
import {
  findingCheckTone,
  splitReviewFindings,
  toFindingSeverity,
  toReviewFinding,
} from "./review-findings";

describe("toFindingSeverity", () => {
  it("keeps known severities and defaults the rest to warning", () => {
    expect(toFindingSeverity("error")).toBe("error");
    expect(toFindingSeverity("suggestion")).toBe("suggestion");
    expect(toFindingSeverity("other")).toBe("warning");
    expect(toFindingSeverity({ nested: true })).toBe("warning");
  });
});

describe("findingCheckTone", () => {
  it("maps error findings to fail and warnings to warn", () => {
    expect(findingCheckTone("error")).toBe("fail");
    expect(findingCheckTone("warning")).toBe("warn");
    expect(findingCheckTone("suggestion")).toBe("pass");
  });
});

describe("toReviewFinding", () => {
  it("maps API aliases without stringifying objects", () => {
    const finding = toReviewFinding({
      severity: "error",
      rule_violated: "PAY-001",
      affected_section: "s9",
      message: "งวดจ่ายไม่ครบ 100%",
      recommended_correction: "ปรับเปอร์เซ็นต์ให้รวม 100",
    });
    expect(finding).toEqual({
      severity: "error",
      rule: "PAY-001",
      section: "s9",
      message: "งวดจ่ายไม่ครบ 100%",
      recommendation: "ปรับเปอร์เซ็นต์ให้รวม 100",
      findingKind: "legal_violation",
      legalBasis: "",
      excerpt: "",
      riskType: "",
    });
  });

  it("classifies RISK_ and CONSISTENCY_ rules as risk when kind is omitted", () => {
    const risk = toReviewFinding({
      severity: "warning",
      rule_violated: "RISK_VAGUE_LANGUAGE",
      affected_section: "s4",
      message: "คลุมเครือ",
    });
    expect(risk.findingKind).toBe("risk_abnormality");
  });

  it("does not stringify nested objects into [object Object]", () => {
    const finding = toReviewFinding({
      severity: "warning",
      rule: { id: "x" },
      section: { key: "s1" },
      message: { text: "nope" },
      recommendation: { hint: "nope" },
    });
    expect(finding.rule).toBe("");
    expect(finding.section).toBe("");
    expect(finding.message).toBe("");
    expect(finding.recommendation).toBe("");
  });
});

describe("splitReviewFindings", () => {
  it("puts unspecified kinds in the legal bucket", () => {
    const split = splitReviewFindings([
      {
        severity: "error",
        rule: "LEGAL_X",
        section: "s6",
        message: "ผิดกฎ",
        recommendation: "",
      },
      {
        severity: "warning",
        rule: "RISK_VAGUE_LANGUAGE",
        section: "s4",
        message: "คลุมเครือ",
        recommendation: "",
        findingKind: "risk_abnormality",
      },
    ]);
    expect(split.legal).toHaveLength(1);
    expect(split.risk).toHaveLength(1);
  });

  it("honours an explicit finding_kind", () => {
    const finding = toReviewFinding({
      finding_kind: "legal_violation",
      rule: "RISK_VAGUE_LANGUAGE",
      message: "ผิดกฎ",
    });
    expect(finding.findingKind).toBe("legal_violation");
  });
});
