import { describe, expect, it } from "vitest";
import {
  COST_WORKSHEET_DISCLAIMER,
  costWorksheetFromAnalysis,
  normalizeCostWorksheet,
  parseCostFromSectionContent,
} from "./cost-worksheet";

describe("cost-worksheet helpers", () => {
  it("normalizes officer lines and never treats them as ราคากลาง", () => {
    const sheet = normalizeCostWorksheet({
      license: "1,000",
      labor: 2000,
      maintenance: 300,
      training: 700,
      announcedPrice: 999999,
    });
    expect(sheet.total).toBe(4000);
    expect(sheet.is_announced_price).toBe(false);
    expect(sheet.label).toBe(COST_WORKSHEET_DISCLAIMER);
    expect(sheet.license).toBe(1000);
  });

  it("reads analysis_json.cost_worksheet and section JSON fallback", () => {
    expect(
      costWorksheetFromAnalysis({
        cost_worksheet: { license: 10, labor: 20, maintenance: 0, training: 5 },
      }).total
    ).toBe(35);
    expect(
      parseCostFromSectionContent(
        JSON.stringify({ budgetAmount: "1", cost_worksheet: { license: 8 } })
      )?.license
    ).toBe(8);
  });
});
