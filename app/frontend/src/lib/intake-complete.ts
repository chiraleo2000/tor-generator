import type { CoverageRow } from "@/components/draft/phase1-coverage";

/** Analyze finished and produced a slot coverage table. */
export function analysisMappingReady(payload: {
  analyzed?: boolean;
  coverage?: CoverageRow[];
}): boolean {
  if (payload.analyzed !== true) return false;
  return (payload.coverage?.length ?? 0) > 0;
}

/** All fact-required topics filled from mapping / Q&A. */
export function factTopicsComplete(coverage: CoverageRow[]): boolean {
  const required = coverage.filter((row) => row.fact_required);
  if (!required.length) return false;
  return required.every((row) => row.filled || row.status === "filled");
}
