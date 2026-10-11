import { describe, expect, it } from "vitest";
import { elapsedStatusText } from "./elapsed-status";

describe("elapsedStatusText", () => {
  it("keeps the in-progress sentence until a second has passed", () => {
    expect(elapsedStatusText("กำลังวิเคราะห์", 0)).toBe("กำลังวิเคราะห์");
  });

  it("changes the same sentence by appending elapsed seconds", () => {
    expect(elapsedStatusText("กำลังตรวจด้วยกฎระเบียบ...", 4)).toBe(
      "กำลังตรวจด้วยกฎระเบียบ... ผ่านมา 4 วินาที"
    );
    expect(elapsedStatusText("กำลังประมวลผล…", 2)).toBe(
      "กำลังประมวลผล... ผ่านมา 2 วินาที"
    );
  });
});
