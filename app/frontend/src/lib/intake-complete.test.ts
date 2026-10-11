import { describe, expect, it } from "vitest";
import {
  analysisMappingReady,
  factProgressFromCoverage,
  factTopicsComplete,
  slotMapFactsComplete,
} from "@/lib/intake-complete";
import { factRequiredFor } from "@/lib/tor-profiles";

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

  it("falls back to profile fact keys when fact_required flags are missing", () => {
    const partial = ["s1", "s2"].map((key) => ({
      key,
      label: key,
      status: "filled" as const,
      filled: true,
      fact_required: false,
    }));
    expect(factTopicsComplete(partial, "buy_goods")).toBe(false);

    const rows = factRequiredFor("buy_goods").map((key) => ({
      key,
      label: key,
      status: "filled" as const,
      filled: true,
      fact_required: false,
    }));
    expect(factTopicsComplete(rows, "buy_goods")).toBe(true);
  });

  it("unlocks from slot_map when every profile fact key is filled", () => {
    const slot_map: Record<string, { status: string; content: string }> = {};
    for (const key of factRequiredFor("buy_goods")) {
      slot_map[key] = { status: "filled", content: `ค่า ${key}` };
    }
    expect(
      slotMapFactsComplete({ analyzed: true, slot_map }, "buy_goods")
    ).toBe(true);
    expect(
      slotMapFactsComplete(
        { analyzed: true, slot_map: { s1: { status: "filled", content: "แค่ช่องเดียว" } } },
        "buy_goods"
      )
    ).toBe(false);
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
