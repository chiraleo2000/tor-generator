import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  ChatAnswerBody,
  ChatCitationBar,
  ChatSourceCards,
  citationChipText,
  isNumericCell,
  looksLikeNoRetrieve,
  parseChatBlocks,
} from "@/components/chat/chat-answer";

describe("parseChatBlocks", () => {
  it("splits headings, lists, pipe tables, and source lines", () => {
    const blocks = parseChatBlocks(
      [
        "**สรุปคำตอบ**",
        "วางหลักประกันสัญญาก่อนจ่ายงวด",
        "",
        "**หลักที่เกี่ยวข้อง**",
        "| เอกสาร | ข้อ |",
        "| --- | --- |",
        "| ระเบียบพัสดุ | ข้อ 85 |",
        "",
        "- เงื่อนไขวงเงิน",
        "- ข้อยกเว้นงานจ้าง",
        "แหล่งข้อมูล: ระเบียบพัสดุ (หน้า 12)",
      ].join("\n")
    );
    expect(blocks.map((block) => block.kind)).toEqual([
      "heading",
      "para",
      "heading",
      "table",
      "list",
      "source",
    ]);
    const table = blocks.find((block) => block.kind === "table");
    expect(table?.kind === "table" && table.rows[1][1]).toBe("ข้อ 85");
    expect(parseChatBlocks("ข้อควรระวัง\nอย่าแบ่งซื้อแบ่งจ้าง")[0]).toMatchObject({
      kind: "heading",
      text: "ข้อควรระวัง",
    });
    expect(parseChatBlocks("**สรุปคำตอบ** วางหลักประกันก่อนจ่ายงวด")[0]).toMatchObject({
      kind: "heading",
      text: "สรุปคำตอบ",
    });
  });
});

describe("isNumericCell", () => {
  it("detects quantities and percentages but not legal text", () => {
    expect(isNumericCell("1,001,306")).toBe(true);
    expect(isNumericCell("+10.9")).toBe(true);
    expect(isNumericCell("ข้อ 85")).toBe(false);
  });
});

describe("looksLikeNoRetrieve", () => {
  it("flags empty-retrieval answers and ignores cited replies", () => {
    expect(
      looksLikeNoRetrieve("ยังไม่มีข้อมูลในคลังสำหรับคำถามนี้", [])
    ).toBe(true);
    expect(
      looksLikeNoRetrieve("ยังไม่มีข้อมูลในคลัง", [{ type: "document", label: "พรบ" }])
    ).toBe(false);
    expect(looksLikeNoRetrieve("ตามระเบียบข้อ 85", [])).toBe(false);
  });
});

describe("ChatAnswerBody", () => {
  it("renders a markdown table and heading", () => {
    render(
      <ChatAnswerBody
        text={"**สรุปคำตอบ**\nรายละเอียด\n\n| ปี | ปริมาณ |\n| --- | --- |\n| 2568 | 10 |"}
      />
    );
    expect(screen.getByRole("heading", { name: "สรุปคำตอบ" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "ปี" })).toBeInTheDocument();
    expect(screen.getByText("2568")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });
});

describe("citation chips", () => {
  it("keeps type:label for e2e and shows source cards when several", () => {
    expect(citationChipText({ type: "mcp", label: "stub" })).toBe("mcp: stub");
    render(
      <ChatCitationBar
        citations={[
          { type: "mcp", label: "stub" },
          { type: "custom_rag", label: "คลัง" },
        ]}
      />
    );
    expect(screen.getAllByTestId("chat-citation")[0]).toHaveTextContent("mcp: stub");
    render(
      <ChatSourceCards
        citations={[
          { type: "document", label: "พรบ.pdf" },
          { type: "article", label: "มาตรา 64" },
        ]}
      />
    );
    expect(screen.getByTestId("chat-source-cards")).toHaveTextContent("พรบ.pdf");
  });
});
