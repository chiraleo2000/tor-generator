import { describe, expect, it } from "vitest";
import {
  categoryHasTraining,
  normalizeTrainingScope,
  parseTrainingFromContent,
  trainingScopeProse,
} from "./training-scope";

describe("training-scope helpers", () => {
  it("is enabled for hire_develop and buy_goods from section profiles", () => {
    expect(categoryHasTraining("hire_develop")).toBe(true);
    expect(categoryHasTraining("buy_goods")).toBe(true);
    expect(categoryHasTraining("it")).toBe(true);
    expect(categoryHasTraining("construction")).toBe(false);
  });

  it("drafts cohorts hours attendees and deliverable documents", () => {
    const fields = normalizeTrainingScope({
      cohorts: "2",
      hours: "12",
      attendees: "30",
      documents: "คู่มือผู้ใช้, รายงานอบรม",
    });
    const prose = trainingScopeProse(fields);
    expect(prose).toContain("2 รุ่น");
    expect(prose).toContain("12 ชั่วโมง");
    expect(prose).toContain("30 คน");
    expect(prose).toContain("คู่มือผู้ใช้");
    expect(parseTrainingFromContent(JSON.stringify(fields))?.cohorts).toBe("2");
  });
});
