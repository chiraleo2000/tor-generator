import { describe, expect, it } from "vitest";
import { canSelectPhase, displayPhase, hasIntakeMaterial, intakeUnlockedPhase } from "@/lib/phase-gate";

describe("phase-gate", () => {
  it("stays at phase 0 when the project has no text or files", () => {
    expect(intakeUnlockedPhase({})).toBe(0);
    expect(canSelectPhase(0, 0, 2)).toBe(false);
    expect(displayPhase(2, 0)).toBe(0);
  });

  it("does not unlock analysis until the user starts it", () => {
    expect(
      hasIntakeMaterial({
        extractedFields: { intake_texts: [{ name: "ข้อความผู้ใช้.txt", text: "โครงการทดสอบวงเงิน" }] },
      })
    ).toBe(true);
    expect(
      intakeUnlockedPhase({
        extractedFields: { intake_texts: [{ name: "ข้อความผู้ใช้.txt", text: "โครงการทดสอบวงเงิน" }] },
      })
    ).toBe(0);
    expect(canSelectPhase(0, 0, 1)).toBe(false);
  });

  it("unlocks Q&A (phase 2) after analysis, not compose", () => {
    expect(
      intakeUnlockedPhase({
        analysisJson: { analyzed: true, slot_map: { s1: { status: "gap", content: "" } } },
      })
    ).toBe(2);
    expect(canSelectPhase(1, 2, 2)).toBe(true);
    expect(canSelectPhase(2, 2, 3)).toBe(false);
    expect(canSelectPhase(2, 2, 4)).toBe(false);
  });

  it("unlocks draft (phase 3) only after ready_to_compose", () => {
    expect(
      intakeUnlockedPhase({
        analysisJson: { ready_to_compose: true, analyzed: true, intake_files: [{ name: "pack.pdf" }] },
      })
    ).toBe(3);
    expect(canSelectPhase(2, 3, 3)).toBe(true);
    expect(canSelectPhase(3, 3, 4)).toBe(false);
  });

  it("unlocks phase 4 only after explicit confirm", () => {
    expect(
      intakeUnlockedPhase({
        analysisJson: { ready_to_compose: true, phase4_confirmed: true },
      })
    ).toBe(4);
    expect(canSelectPhase(3, 4, 4)).toBe(true);
  });

  it("clamps a saved phase display back when intake is empty", () => {
    expect(displayPhase(1, 0)).toBe(0);
    expect(displayPhase(0, 0)).toBe(0);
    expect(canSelectPhase(0, 0, -1)).toBe(false);
  });

  it("treats slot_map keys as analyzed and filled slots as material", () => {
    expect(
      intakeUnlockedPhase({
        analysisJson: { slot_map: { s1: { status: "gap" } } },
      })
    ).toBe(2);
    expect(
      hasIntakeMaterial({
        analysisJson: { slot_map: { s1: { status: "filled", content: "มีข้อมูล" } } },
      })
    ).toBe(true);
    expect(
      hasIntakeMaterial({
        analysisJson: { intake_files: [] },
        extractedFields: { intake_texts: ["not-an-object", { text: "  " }] },
      })
    ).toBe(false);
    expect(canSelectPhase(2, 4, 2)).toBe(true);
    expect(displayPhase(3, 4)).toBe(3);
  });
});
