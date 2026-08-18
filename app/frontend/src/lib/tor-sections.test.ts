import { describe, expect, it } from "vitest";
import {
  DOC_CLASSES,
  HITL_SECTIONS,
  PHASE0_CHECKLIST,
  SCOPE_SUBSECTIONS,
  TOR_SECTION_LABELS,
  TOR_SECTION_ORDER,
  serializeSectionDraft,
} from "./tor-sections";

describe("canonical TOR sections", () => {
  it("keeps 13 legal sections and 14 scope sub-headings", () => {
    expect(TOR_SECTION_ORDER).toHaveLength(13);
    expect(Object.keys(TOR_SECTION_LABELS)).toHaveLength(13);
    expect(SCOPE_SUBSECTIONS).toHaveLength(14);
    expect(HITL_SECTIONS).toEqual(["s3", "s6", "s8", "s10", "s13"]);
    expect(DOC_CLASSES.filter((item) => item.required).map((item) => item.id)).toEqual(
      ["announced_price", "budget_approval"]
    );
    expect(DOC_CLASSES.find((item) => item.id === "charter")?.label).toContain("เอกสารโครงการ");
    expect(PHASE0_CHECKLIST).toContain("รายงานการประชุม");
  });

  it("saves a single body field as plain TOR prose", () => {
    expect(serializeSectionDraft({ body: " วงเงินหนึ่งแสนบาท " })).toBe("วงเงินหนึ่งแสนบาท");
  });

  it("keeps structured fields as JSON", () => {
    const raw = serializeSectionDraft({ history: "ระบบเดิม", problems: "ซ่อมบ่อย" });
    expect(JSON.parse(raw)).toEqual({ history: "ระบบเดิม", problems: "ซ่อมบ่อย" });
  });
});
