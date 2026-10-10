import { describe, expect, it } from "vitest";
import {
  COST_WORKSHEET_DISCLAIMER,
  costWorksheetFromAnalysis,
  normalizeCostWorksheet,
  parseCostFromSectionContent,
} from "./cost-worksheet";

describe("cost-worksheet helpers", () => {
  it("normalizes five categories and never treats them as ราคากลาง", () => {
    const sheet = normalizeCostWorksheet({
      personnel: "1,000",
      equipment: 2000,
      procurement: 300,
      consultant: 700,
      training: 0,
      announcedPrice: 999999,
    });
    expect(sheet.total).toBe(4000);
    expect(sheet.is_announced_price).toBe(false);
    expect(sheet.label).toBe(COST_WORKSHEET_DISCLAIMER);
    expect(sheet.personnel).toBe(1000);
  });

  it("maps the previous four lines onto the five categories with the same total", () => {
    const sheet = normalizeCostWorksheet({
      license: "1,000",
      labor: 2000,
      maintenance: 300,
      training: 700,
    });
    expect(sheet.equipment).toBe(1000);
    expect(sheet.personnel).toBe(2000);
    expect(sheet.procurement).toBe(300);
    expect(sheet.training).toBe(700);
    expect(sheet.total).toBe(4000);
  });

  it("rolls food, snack, documents, and venue into training without double counting", () => {
    const sheet = normalizeCostWorksheet({
      personnel: 10,
      consultant: 20,
      food: 100,
      snack: 50,
      documents: 70,
      venue: 0,
      training: 999,
    });
    expect(sheet.training).toBe(220);
    expect(sheet.total).toBe(250);
  });

  it("reads nested training parts and ignores broken section JSON", () => {
    const sheet = normalizeCostWorksheet({ training_parts: { food: 40, snack: "10" } });
    expect(sheet.food).toBe(40);
    expect(sheet.snack).toBe(10);
    expect(parseCostFromSectionContent("{")).toBeNull();
  });

  it("reads analysis_json.cost_worksheet and section JSON fallback", () => {
    expect(
      costWorksheetFromAnalysis({
        cost_worksheet: { personnel: 10, equipment: 20, procurement: 0, consultant: 5 },
      }).total
    ).toBe(35);
    expect(
      parseCostFromSectionContent(
        JSON.stringify({ budgetAmount: "1", cost_worksheet: { personnel: 8 } })
      )?.personnel
    ).toBe(8);
  });
});
