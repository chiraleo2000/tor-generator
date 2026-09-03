import { describe, expect, it } from "vitest";
import { toWizardApiPayload } from "./wizard-api";

describe("toWizardApiPayload", () => {
  it("maps step 1 project fields", () => {
    expect(
      toWizardApiPayload(1, {
        project_name: "โครงการทดสอบ",
        ministry: "กระทรวง",
        budget: 1000000,
        project_type: "it",
        template_id: null,
        location: "กรุงเทพฯ",
        duration_days: 90,
      })
    ).toEqual({
      project_name: "โครงการทดสอบ",
      ministry: "กระทรวง",
      budget: 1000000,
      project_type: "it",
      template_id: null,
      location: "กรุงเทพฯ",
      duration_days: 90,
    });
  });

  it("maps step 2 description aliases", () => {
    expect(toWizardApiPayload(2, { problemDescription: "ระบบเดิมไม่พอ" })).toEqual({
      description: "ระบบเดิมไม่พอ",
    });
  });

  it("maps step 3 objectives", () => {
    expect(toWizardApiPayload(3, { objectives: ["ข้อ 1"] })).toEqual({
      objectives: ["ข้อ 1"],
    });
  });

  it("maps step 4 scope items onto s4.n keys", () => {
    const payload = toWizardApiPayload(4, {
      scope_items: [{ title: "งานหลัก", details: "รายละเอียด" }],
      deliverables: ["ส่งมอบ"],
    });
    expect(payload.scope_items).toEqual([{ title: "งานหลัก", details: "รายละเอียด" }]);
    expect(payload["s4.1"]).toBe("งานหลัก\nรายละเอียด");
  });

  it("maps step 5 qualifications", () => {
    expect(
      toWizardApiPayload(5, { qualifications: ["นิติบุคคล"], paid_up_capital: 500000 })
    ).toEqual({
      qualifications: ["นิติบุคคล"],
      paid_up_capital: 500000,
    });
  });

  it("maps step 6 budget and payment", () => {
    const payload = toWizardApiPayload(6, {
      budget_breakdown: [{ item: "ฮาร์ดแวร์", amount: 100 }],
      payment_schedule: [{ percentage: 50, deliverable: "งวดแรก" }],
      penalty_rate: 0.1,
      warranty: "1 ปี",
      duration_days: 30,
    });
    expect(payload.penalty_rate).toBe(0.1);
    expect(payload.warranty).toBe("1 ปี");
  });

  it("returns the source object for unknown steps and empty step-1 aliases", () => {
    expect(toWizardApiPayload(9, { extra: 1 })).toEqual({ extra: 1 });
    expect(toWizardApiPayload(1, {})).toMatchObject({
      location: "",
      duration_days: null,
    });
    const step4 = toWizardApiPayload(4, {
      scope_items: Array.from({ length: 20 }, (_, index) => ({
        title: `t${index}`,
        details: "d",
      })),
    });
    expect(step4["s4.20"]).toBe("t19\nd");
  });
});
