import type { CoverageRow } from "@/components/draft/phase1-coverage";

import { factRequiredFor } from "@/lib/tor-profiles";

/** Fallback when coverage rows omit fact_required flags (aliases include legacy s4.1). */
export const FACT_REQUIRED_KEYS = [...factRequiredFor("buy_goods"), "s4.1"];

/** Analyze finished and produced a slot coverage table. */
export function analysisMappingReady(payload: {
  analyzed?: boolean;
  coverage?: CoverageRow[];
}): boolean {
  if (payload.analyzed !== true) return false;
  return (payload.coverage?.length ?? 0) > 0;
}

function requiredFactRows(coverage: CoverageRow[]): CoverageRow[] {
  const flagged = coverage.filter((row) => row.fact_required);
  if (flagged.length) return flagged;
  const keys = new Set<string>(FACT_REQUIRED_KEYS);
  return coverage.filter((row) => keys.has(row.key));
}

/** All fact-required topics filled from mapping / Q&A. */
export function factTopicsComplete(coverage: CoverageRow[]): boolean {
  const required = requiredFactRows(coverage);
  if (!required.length) return false;
  return required.every((row) => row.filled || row.status === "filled");
}

export function factProgressFromCoverage(coverage: CoverageRow[]): {
  filled: number;
  total: number;
  percent: number;
} {
  const required = requiredFactRows(coverage);
  const total = required.length || FACT_REQUIRED_KEYS.length;
  const filled = required.filter((row) => row.filled || row.status === "filled").length;
  return {
    filled,
    total,
    percent: total ? Math.round((filled / total) * 1000) / 10 : 0,
  };
}
