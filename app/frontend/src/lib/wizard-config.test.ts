import { describe, expect, it } from "vitest";
import {
  TOTAL_STEPS,
  WIZARD_STEPS,
  calculateCompletionPercentage,
  getStepStatus,
  isStepValid,
} from "./wizard-config";

describe("wizard-config", () => {
  it("defines eight steps", () => {
    expect(TOTAL_STEPS).toBe(8);
    expect(WIZARD_STEPS).toHaveLength(8);
    expect(WIZARD_STEPS[0].requiredFields).toContain("projectName");
  });

  it("counts completed steps without errors", () => {
    const formData = { 1: { projectName: "x" }, 2: { problemDescription: "y" } };
    expect(calculateCompletionPercentage(formData, {})).toBe(25);
    expect(calculateCompletionPercentage(formData, { 2: ["ต้องกรอก"] })).toBe(13);
  });

  it("treats review and export as always valid", () => {
    expect(isStepValid(7, {}, {})).toBe(true);
    expect(isStepValid(8, {}, {})).toBe(true);
    expect(isStepValid(1, {}, {})).toBe(false);
    expect(isStepValid(1, { 1: { projectName: "x" } }, { 1: ["error"] })).toBe(false);
    expect(isStepValid(1, { 1: { projectName: "x" } }, {})).toBe(true);
  });

  it("returns indicator statuses", () => {
    const formData = { 1: { projectName: "x" } };
    expect(getStepStatus(2, 2, formData, {})).toBe("current");
    expect(getStepStatus(1, 2, formData, {})).toBe("completed");
    expect(getStepStatus(3, 2, {}, { 3: ["missing"] })).toBe("error");
    expect(getStepStatus(3, 2, {}, {})).toBe("upcoming");
  });
});
