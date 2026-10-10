import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  coerceLicenseMarkdown,
  RichDraftText,
  splitDraftBlocks,
} from "@/components/draft/rich-draft-text";

const TABLE = `| รายการ | จำนวน |
| --- | --- |
| เซิร์ฟเวอร์ | 2 |`;

describe("RichDraftText", () => {
  it("parses a markdown pipe table into table blocks", () => {
    const blocks = splitDraftBlocks(`ขอบเขตงาน\n${TABLE}\nหมายเหตุ`);
    expect(blocks.map((block) => block.kind)).toEqual(["para", "table", "para"]);
    const table = blocks[1];
    expect(table.kind).toBe("table");
    if (table.kind === "table") {
      expect(table.rows[0]).toEqual(["รายการ", "จำนวน"]);
      expect(table.rows[1]).toEqual(["เซิร์ฟเวอร์", "2"]);
    }
  });

  it("turns a pasted ICT license table into pipe markdown", () => {
    expect(coerceLicenseMarkdown("")).toBe("");
    expect(coerceLicenseMarkdown("ไม่มีตาราง")).toBe("ไม่มีตาราง");
    const ready = "| ลำดับ | รายการ |\n| --- | --- |\n| 1 | ของ |";
    expect(coerceLicenseMarkdown(ready)).toBe(ready);
    const pasted = [
      "ลำดับ\tรายการ\tจำนวนสิทธิ์\tราคาต่อหน่วย (บาท)\tราคารวม (บาท)\tใช้เกณฑ์กลาง ICT\tเหตุผล\tเพิ่ม",
      "\t\t\t\t\tใช้\tไม่ใช้",
      "1\tแท็บเล็ต\t40\t22000\t880000\tใช้\t\tเหตุผลพิเศษ",
      "1\tแท็บเล็ต\t40\t22000\t880000\tใช้\t\tเหตุผลพิเศษ",
      "รวม\t\t\t\t880000",
      "2\tซอฟต์แวร์\t1\t100\t100\tไม่ใช้",
      "ไม่ใช่แถว",
    ].join("\n");
    const markdown = coerceLicenseMarkdown(pasted);
    expect(markdown).toContain("| ลำดับ | รายการ |");
    expect(markdown).toContain("แท็บเล็ต");
    expect(markdown.split("แท็บเล็ต").length - 1).toBe(1);
    expect(markdown).toContain("ไม่ใช้");
  });

  it("renders a real HTML table without raw pipes", () => {
    render(<RichDraftText text={TABLE} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("เซิร์ฟเวอร์")).toBeInTheDocument();
    expect(screen.queryByText("| รายการ | จำนวน |")).not.toBeInTheDocument();
  });
});
