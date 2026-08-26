import { describe, expect, it } from "vitest";
import { analysisMappingReady, factTopicsComplete } from "@/lib/intake-complete";

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
});
