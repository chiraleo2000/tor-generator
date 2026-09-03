import { describe, expect, it } from "vitest";
import {
  DOC_CLASSES,
  HITL_SECTIONS,
  PHASE0_CHECKLIST,
  SCOPE_SUBSECTIONS,
  TOR_SECTION_LABELS,
  TOR_SECTION_ORDER,
  isSectionFilled,
  labeledSectionBlocks,
  parseSectionDraft,
  previewSectionDraft,
  scopeSubsectionTitle,
  serializeSectionDraft,
} from "./tor-sections";

describe("canonical TOR sections", () => {
  it("keeps 13 legal sections and 14 scope sub-headings", () => {
    expect(TOR_SECTION_ORDER).toHaveLength(13);
    expect(Object.keys(TOR_SECTION_LABELS)).toHaveLength(13);
    expect(SCOPE_SUBSECTIONS).toHaveLength(14);
    expect(SCOPE_SUBSECTIONS.find((item) => item.key === "s4.2")?.title).toBe("ระบบงานปัจจุบัน");
    expect(HITL_SECTIONS).toEqual(["s3", "s6", "s8", "s10", "s13"]);
    expect(DOC_CLASSES.filter((item) => item.required).map((item) => item.id)).toEqual(
      ["announced_price", "budget_approval"]
    );
    expect(DOC_CLASSES.find((item) => item.id === "charter")?.label).toContain("เอกสารโครงการ");
    expect(PHASE0_CHECKLIST).toContain("รายงานการประชุม");
  });

  it("maps a combined body blob into the first subsection field", () => {
    const fields = parseSectionDraft("s1", JSON.stringify({ body: "โครงการจัดซื้อระบบ" }));
    expect(fields.history).toBe("โครงการจัดซื้อระบบ");
    expect(fields.body).toBeUndefined();
  });

  it("keeps structured fields as JSON", () => {
    const raw = serializeSectionDraft({ history: "ระบบเดิม", problems: "ซ่อมบ่อย" });
    expect(JSON.parse(raw)).toEqual({ history: "ระบบเดิม", problems: "ซ่อมบ่อย" });
  });

  it("splits Thai subsection labels without markdown hashes", () => {
    const fields = parseSectionDraft(
      "s1",
      [
        "ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม",
        "ระบบงานเดิมใช้เอกสารกระดาษ",
        "ปัญหาที่พบ (ระบุตัวเลข/สถิติ)",
        "ซ่อมบ่อยปีละ 12 ครั้ง",
      ].join("\n")
    );
    expect(fields.history).toBe("ระบบงานเดิมใช้เอกสารกระดาษ");
    expect(fields.problems).toBe("ซ่อมบ่อยปีละ 12 ครั้ง");
  });

  it("parses markdown subsection headings including trailing spaces", () => {
    const raw = "### history  \nระบบเดิม\n### problems\nซ่อมบ่อย";
    expect(parseSectionDraft("s1", raw)).toEqual({
      history: "ระบบเดิม",
      problems: "ซ่อมบ่อย",
    });
  });

  it("ignores stale As-Is titles from older payloads", () => {
    expect(scopeSubsectionTitle("s4.2", "ระบบงานปัจจุบัน (As-Is)")).toBe("ระบบงานปัจจุบัน");
    expect(scopeSubsectionTitle("s4.2")).not.toMatch(/As-Is/);
  });

  it("fills from paragraphs, previews, and labeled blocks", () => {
    const paras = parseSectionDraft("s7", "ย่อหน้าหนึ่ง\n\nย่อหน้าสองยาว");
    expect(paras.location).toContain("ย่อหน้าหนึ่ง");
    expect(isSectionFilled({ filled: true })).toBe(true);
    expect(isSectionFilled({ filled: false, subs: [{ filled: true }] })).toBe(true);
    expect(isSectionFilled({ filled: false, subs: [] })).toBe(false);
    expect(previewSectionDraft("s7", "สถานที่กรุงเทพ")).toContain("สถานที่กรุงเทพ");
    expect(labeledSectionBlocks("s7", "สถานที่กรุงเทพ")[0].text).toContain("สถานที่กรุงเทพ");
    expect(labeledSectionBlocks("s99", "อิสระ")).toEqual([{ label: "", text: "อิสระ" }]);
    expect(labeledSectionBlocks("s99", "")).toEqual([]);
    expect(serializeSectionDraft({ body: "  ร่าง  " })).toBe("ร่าง");
    const hashed = parseSectionDraft(
      "s1",
      "# history\nระบบเดิม\n# ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม\nซ้ำ"
    );
    expect(hashed.history).toBeTruthy();
    expect(parseSectionDraft("s1", "{not-json")).toEqual({ history: "{not-json" });
    expect(parseSectionDraft("s1", "")).toEqual({});
    expect(scopeSubsectionTitle("s4.99", "หัวข้ออื่น")).toBe("หัวข้ออื่น");
  });
});
