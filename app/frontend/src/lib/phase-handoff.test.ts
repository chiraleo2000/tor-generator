import { describe, expect, it } from "vitest";
import {
  canLeavePhase0,
  canLeavePhase2,
  canLeavePhase3,
  canSubmitPhase4,
  coverageStatusLabel,
  phaseLabelTh,
} from "@/lib/phase-handoff";

describe("phase-handoff", () => {
  it("labels phases in Thai", () => {
    expect(phaseLabelTh(0)).toBe("ขั้นที่ ๐ เตรียมข้อมูล");
    expect(phaseLabelTh(3)).toBe("ขั้นที่ ๓ ร่างเนื้อหา");
    expect(phaseLabelTh(9)).toBe("ขั้นตอน");
  });

  it("gates leaving each phase", () => {
    expect(canLeavePhase0(false, 3)).toBe(false);
    expect(canLeavePhase0(true, 0)).toBe(false);
    expect(canLeavePhase0(true, 2)).toBe(true);
    expect(canLeavePhase2(true)).toBe(true);
    expect(canLeavePhase3(true)).toBe(true);
    expect(canSubmitPhase4(12, 13)).toBe(false);
    expect(canSubmitPhase4(13, 13)).toBe(true);
  });

  it("maps coverage status to Thai", () => {
    expect(coverageStatusLabel("filled")).toBe("ครบ");
    expect(coverageStatusLabel("gap")).toBe("ยังขาด");
    expect(coverageStatusLabel("reference_only")).toBe("อ้างอิง");
    expect(coverageStatusLabel("unknown")).toBe("unknown");
    expect(canSubmitPhase4(1, 0)).toBe(false);
  });
});
