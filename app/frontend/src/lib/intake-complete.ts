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

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

/** Resolve profile fact key against slot_map / coverage aliases (e.g. items ↔ s4.1). */
export function slotKeyAliases(key: string): string[] {
  const aliases = [key];
  if (key === "items") aliases.push("s4.1");
  if (key === "s4.1") aliases.push("items");
  return aliases;
}

function rowLooksFilled(row: Pick<CoverageRow, "filled" | "status"> | undefined): boolean {
  if (!row) return false;
  return Boolean(row.filled || row.status === "filled");
}

function slotMapEntryFilled(slotMap: Record<string, unknown>, key: string): boolean {
  for (const alias of slotKeyAliases(key)) {
    const raw = slotMap[alias];
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) continue;
    const slot = raw as { status?: string; content?: string };
    if (slot.status === "filled" && String(slot.content || "").trim()) {
      return true;
    }
  }
  return false;
}

function requiredFactRows(
  coverage: CoverageRow[],
  projectType?: string | null
): CoverageRow[] {
  const flagged = coverage.filter((row) => row.fact_required);
  if (flagged.length) return flagged;
  const profileKeys = factRequiredFor(projectType);
  const keys = new Set(profileKeys.length ? profileKeys : FACT_REQUIRED_KEYS);
  return coverage.filter(
    (row) => keys.has(row.key) || (row.key === "s4.1" && keys.has("items"))
  );
}

/** All fact-required topics filled from mapping / Q&A. */
export function factTopicsComplete(
  coverage: CoverageRow[],
  projectType?: string | null
): boolean {
  const flagged = coverage.filter((row) => row.fact_required);
  if (flagged.length) {
    return flagged.every((row) => rowLooksFilled(row));
  }
  const requiredKeys = factRequiredFor(projectType);
  if (!requiredKeys.length) return false;
  const byKey = new Map(coverage.map((row) => [row.key, row]));
  return requiredKeys.every((key) => {
    for (const alias of slotKeyAliases(key)) {
      if (rowLooksFilled(byKey.get(alias))) return true;
    }
    return false;
  });
}

/**
 * Mirror backend ready_criteria_met using analysisJson.slot_map so hydrate can
 * unlock Phase 3 even before coverage is fetched or ready_to_compose is stored.
 */
export function slotMapFactsComplete(
  analysis: unknown,
  projectType?: string | null
): boolean {
  const record = asRecord(analysis);
  if (record.analyzed !== true) return false;
  const slotMap = asRecord(record.slot_map);
  const requiredKeys = factRequiredFor(projectType);
  if (!requiredKeys.length) return false;
  return requiredKeys.every((key) => slotMapEntryFilled(slotMap, key));
}

export function factProgressFromCoverage(
  coverage: CoverageRow[],
  projectType?: string | null
): {
  filled: number;
  total: number;
  percent: number;
} {
  const required = requiredFactRows(coverage, projectType);
  const profileTotal = factRequiredFor(projectType).length;
  const total = required.length || profileTotal || FACT_REQUIRED_KEYS.length;
  const filled = required.filter((row) => rowLooksFilled(row)).length;
  return {
    filled,
    total,
    percent: total ? Math.round((filled / total) * 1000) / 10 : 0,
  };
}
