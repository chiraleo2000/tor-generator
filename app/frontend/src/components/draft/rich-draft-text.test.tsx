import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RichDraftText, splitDraftBlocks } from "@/components/draft/rich-draft-text";

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

  it("renders a real HTML table without raw pipes", () => {
    render(<RichDraftText text={TABLE} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("เซิร์ฟเวอร์")).toBeInTheDocument();
    expect(screen.queryByText("| รายการ | จำนวน |")).not.toBeInTheDocument();
  });
});
