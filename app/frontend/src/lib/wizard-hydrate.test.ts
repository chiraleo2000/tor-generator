import { describe, it, expect } from "vitest";
import { isMeaningfulStepData } from "./wizard-hydrate";

describe("isMeaningfulStepData", () => {
  it("rejects empty objects and non-objects", () => {
    expect(isMeaningfulStepData(1, null)).toBe(false);
    expect(isMeaningfulStepData(1, {})).toBe(false);
    expect(isMeaningfulStepData(2, { description: "  " })).toBe(false);
  });

  it("treats step 1 metadata as meaningful", () => {
    expect(
      isMeaningfulStepData(1, { project_name: "โครงการทดสอบ", budget: 1000 })
    ).toBe(true);
  });

  it("requires a non-empty objective for step 3", () => {
    expect(isMeaningfulStepData(3, { objectives: [] })).toBe(false);
    expect(isMeaningfulStepData(3, { objectives: [""] })).toBe(false);
    expect(isMeaningfulStepData(3, { objectives: ["จัดหาระบบ"] })).toBe(true);
  });

  it("requires a titled scope item or deliverable for step 4", () => {
    expect(
      isMeaningfulStepData(4, {
        scope_items: [{ title: "", details: "" }],
        deliverables: [""],
      })
    ).toBe(false);
    expect(
      isMeaningfulStepData(4, {
        scope_items: [{ title: "ติดตั้งระบบ", details: "" }],
        deliverables: [""],
      })
    ).toBe(true);
  });

  it("requires a named budget line with amount for step 6", () => {
    expect(
      isMeaningfulStepData(6, {
        budget_breakdown: [{ item: "ค่าพัฒนาระบบ", amount: 0 }],
      })
    ).toBe(false);
    expect(
      isMeaningfulStepData(6, {
        budget_breakdown: [{ item: "ค่าพัฒนาระบบ", amount: 1_000_000 }],
      })
    ).toBe(true);
  });

  it("requires exported true for step 8", () => {
    expect(isMeaningfulStepData(8, { exported: false })).toBe(false);
    expect(isMeaningfulStepData(8, { exported: true })).toBe(true);
  });

  it("requires a qualification for step 5 and any string for step 7", () => {
    expect(isMeaningfulStepData(5, { qualifications: [""] })).toBe(false);
    expect(isMeaningfulStepData(5, { qualifications: ["เป็นนิติบุคคล"] })).toBe(true);
    expect(isMeaningfulStepData(7, { s11: "  " })).toBe(false);
    expect(isMeaningfulStepData(7, { s11: "เกณฑ์ราคา" })).toBe(true);
  });

  it("treats step 4 deliverables as meaningful", () => {
    expect(
      isMeaningfulStepData(4, {
        scope_items: [{ title: "", details: "" }],
        deliverables: ["รายงานฉบับสมบูรณ์"],
      })
    ).toBe(true);
  });
});
