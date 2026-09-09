/** Section_Profile helpers — mirrors app/backend/app/domain/section_profile.py */

import {
  SECTION_PROFILES,
  type GeneratedProfile,
  type GeneratedSubsection,
  type ProfileStatus,
} from "./tor-profiles.generated";

export type ProcurementCategory =
  | "hire_develop"
  | "hire_maintain"
  | "lease_service"
  | "buy_goods"
  | "construction"
  | "hire_consult"
  | "hire_service";

export const PROCUREMENT_CATEGORIES = SECTION_PROFILES.categories.map((item) => ({
  key: item.key as ProcurementCategory,
  label: item.label,
}));

const LEGACY_MAP = SECTION_PROFILES.legacy_map as Record<string, string>;

export function mapLegacyType(raw?: string | null): string {
  const text = (raw || "").trim();
  if (!text) return "buy_goods";
  return LEGACY_MAP[text] || text;
}

export function classifyCategory(raw?: string | null): {
  status: ProfileStatus;
  category: string;
} {
  const text = (raw || "").trim();
  if (!text) return { status: "none", category: "" };
  const mapped = mapLegacyType(text);
  if (mapped in SECTION_PROFILES.profiles) {
    return { status: "ok", category: mapped };
  }
  return { status: "missing", category: mapped };
}

export function categoryForProject(raw?: string | null): ProcurementCategory {
  const { status, category } = classifyCategory(raw);
  if (status === "ok") return category as ProcurementCategory;
  return "buy_goods";
}

export function resolveProfile(
  raw?: string | null
): GeneratedProfile | { status: ProfileStatus } {
  const { status, category } = classifyCategory(raw);
  if (status !== "ok") return { status };
  return SECTION_PROFILES.profiles[category as ProcurementCategory] as unknown as GeneratedProfile;
}

export function profileForProject(raw?: string | null): GeneratedProfile {
  const key = categoryForProject(raw);
  return SECTION_PROFILES.profiles[key] as unknown as GeneratedProfile;
}

export function sectionOrderFor(raw?: string | null): string[] {
  return profileForProject(raw).main_sections.map((item) => item.key);
}

export function scopeSubsectionsFor(raw?: string | null): GeneratedSubsection[] {
  return [...profileForProject(raw).scope_subsections];
}

export function factRequiredFor(raw?: string | null): string[] {
  return [...profileForProject(raw).fact_required];
}

export function scopeSubsectionTitle(key: string, category?: string | null, fallback = ""): string {
  if (category) {
    const found = scopeSubsectionsFor(category).find(
      (item) => item.key === key || item.semantic_key === key
    );
    if (found) return found.title;
  }
  for (const profile of Object.values(SECTION_PROFILES.profiles)) {
    const found = profile.scope_subsections.find(
      (item) => item.key === key || item.semantic_key === key
    );
    if (found) return found.title;
  }
  return fallback || key;
}

export function sectionTitleFor(key: string, category?: string | null, fallback = ""): string {
  if (category) {
    const found = profileForProject(category).main_sections.find((item) => item.key === key);
    if (found) return found.title;
  }
  return fallback || key;
}

export function isProfileStatus(
  value: GeneratedProfile | { status: ProfileStatus }
): value is { status: ProfileStatus } {
  return "status" in value;
}
