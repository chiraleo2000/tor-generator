import { describe, expect, it } from "vitest";
import { canSelectPhase, displayPhase, intakeUnlockedPhase } from "@/lib/phase-gate";

describe("phase-gate", () => {
  it("stays at phase 0 when the project has no text or files", () => {
    expect(intakeUnlockedPhase({})).toBe(0);
    expect(canSelectPhase(0, 0, 2)).toBe(false);
    expect(displayPhase(2, 0)).toBe(0);
  });

  it("unlocks phase 1 after pasted text or uploads", () => {
    expect(
      intakeUnlockedPhase({
        extractedFields: { intake_texts: [{ name: "ข้อความผู้ใช้.txt", text: "โครงการทดสอบวงเงิน" }] },
      })
    ).toBe(1);
    expect(canSelectPhase(0, 1, 1)).toBe(true);
    expect(canSelectPhase(0, 1, 2)).toBe(false);
  });

  it("unlocks phase 2 only after ready_to_compose", () => {
    expect(
      intakeUnlockedPhase({
        analysisJson: { ready_to_compose: true, intake_files: [{ name: "pack.pdf" }] },
      })
    ).toBe(2);
    expect(canSelectPhase(1, 2, 2)).toBe(true);
    expect(canSelectPhase(2, 2, 3)).toBe(true);
    expect(canSelectPhase(2, 2, 4)).toBe(false);
  });
});
