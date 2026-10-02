import { describe, expect, it } from "vitest";
import { analysisMappingReady, factProgressFromCoverage, factTopicsComplete } from "@/lib/intake-complete";

describe("intake-complete", () => {
  it("requires analyzed plus coverage rows before leaving Phase 0", () => {
    expect(analysisMappingReady({ analyzed: true, coverage: [] })).toBe(false);
    expect(
      analysisMappingReady({
        analyzed: true,
        coverage: [
          { key: "s1", label: "s1", status: "gap", filled: false, fact_required: true },
        ],
      })
    ).toBe(true);
    expect(
      analysisMappingReady({
        analyzed: false,
        coverage: [
          { key: "s1", label: "s1", status: "filled", filled: true, fact_required: true },
        ],
      })
    ).toBe(false);
  });

  it("requires every fact-required topic filled", () => {
    expect(
      factTopicsComplete([
        { key: "s1", label: "s1", status: "filled", filled: true, fact_required: true },
        { key: "s2", label: "s2", status: "gap", filled: false, fact_required: true },
      ])
    ).toBe(false);
    expect(
      factTopicsComplete([
        { key: "s1", label: "s1", status: "filled", filled: true, fact_required: true },
        { key: "s10", label: "s10", status: "gap", filled: false, fact_required: false },
      ])
    ).toBe(true);
  });

  it("falls back to known fact keys when fact_required flags are missing", () => {
    const rows = ["s1", "s2", "s5", "s6", "s7", "s4.1"].map((key) => ({
      key,
      label: key,
      status: "filled",
      filled: true,
      fact_required: false,
    }));
    expect(factTopicsComplete(rows)).toBe(true);
  });

  it("reports zero progress when no coverage rows exist", () => {
    expect(factProgressFromCoverage([])).toEqual({
      filled: 0,
      total: expect.any(Number),
      percent: 0,
    });
    const progress = factProgressFromCoverage([
      { key: "s1", label: "s1", status: "filled", filled: true, fact_required: true },
      { key: "s2", label: "s2", status: "gap", filled: false, fact_required: true },
    ]);
    expect(progress.filled).toBe(1);
    expect(progress.total).toBe(2);
    expect(progress.percent).toBe(50);
  });
});
