import { describe, expect, it } from "vitest";
import {
  categoryForProject,
  classifyCategory,
  factRequiredFor,
  isProfileStatus,
  mapLegacyType,
  profileForProject,
  resolveProfile,
  scopeSubsectionsFor,
  scopeSubsectionTitle,
  sectionOrderFor,
  sectionTitleFor,
} from "@/lib/tor-profiles";

describe("tor-profiles", () => {
  it("maps empty, legacy, and unknown project types", () => {
    expect(mapLegacyType("")).toBe("buy_goods");
    expect(mapLegacyType(null)).toBe("buy_goods");
    expect(mapLegacyType("it_dev")).toBe("hire_develop");
    expect(mapLegacyType("not-a-type")).toBe("not-a-type");
  });

  it("classifies a known profile and a missing one", () => {
    expect(classifyCategory("  ")).toEqual({ status: "none", category: "" });
    expect(classifyCategory("hire_develop").status).toBe("ok");
    expect(classifyCategory("not-a-type")).toEqual({
      status: "missing",
      category: "not-a-type",
    });
  });

  it("falls back to buy_goods when the profile is missing", () => {
    expect(categoryForProject("hire_maintain")).toBe("hire_maintain");
    expect(categoryForProject("not-a-type")).toBe("buy_goods");
    expect(isProfileStatus(resolveProfile("not-a-type"))).toBe(true);
    expect(isProfileStatus(resolveProfile("buy_goods"))).toBe(false);
  });

  it("reads section order, facts, and scope titles", () => {
    expect(sectionOrderFor("hire_develop")).toContain("s1");
    expect(factRequiredFor("hire_develop").length).toBeGreaterThan(0);
    expect(scopeSubsectionsFor("hire_develop").length).toBeGreaterThan(0);
    expect(profileForProject("hire_develop").label.length).toBeGreaterThan(0);
    expect(scopeSubsectionTitle("functional", "hire_develop")).toContain("งาน");
    expect(scopeSubsectionTitle("functional", "buy_goods")).toContain("งาน");
    expect(scopeSubsectionTitle("missing-key", "hire_develop", "สำรอง")).toBe("สำรอง");
    expect(sectionTitleFor("s1", "hire_develop").length).toBeGreaterThan(0);
    expect(sectionTitleFor("missing", "hire_develop", "ไม่มี")).toBe("ไม่มี");
    expect(sectionTitleFor("missing")).toBe("missing");
  });
});
