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
  uniqueCitations,
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
    const online = parseChatBlocks(
      "**แหล่งออนไลน์**\n- [กรมบัญชีกลาง](https://www.gprocurement.go.th) — 2568"
    );
    expect(online.map((block) => block.kind)).toEqual(["online"]);
    expect(online[0]).toMatchObject({
      kind: "online",
      items: [{ title: "กรมบัญชีกลาง", url: "https://www.gprocurement.go.th", date: "2568" }],
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
  it("renders paragraphs, tables, lists, and online sources without required headings", () => {
    render(
      <ChatAnswerBody
        text={[
          "วิธีเฉพาะเจาะจงใช้ได้เมื่อวงเงินไม่เกินตามที่ระเบียบกำหนด (พ.ร.บ.2560.pdf หน้า 12)",
          "",
          "| วิธี | วงเงิน |",
          "| --- | --- |",
          "| เฉพาะเจาะจง | ไม่เกิน ๕๐๐,๐๐๐ บาท |",
          "",
          "- จัดทำรายงานขอซื้อ",
          "- เสนอหัวหน้าหน่วยงาน",
          "",
          "**แหล่งออนไลน์**",
          "- [กรมบัญชีกลาง](https://www.gprocurement.go.th) — 2568",
          "- ระเบียบพัสดุ — https://www.cgd.go.th/reg",
        ].join("\n")}
      />
    );
    expect(screen.queryByRole("heading", { name: "สรุปคำตอบ" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "หลักที่เกี่ยวข้อง" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "ข้อควรระวัง" })).not.toBeInTheDocument();
    expect(
      screen.getByText(/วิธีเฉพาะเจาะจงใช้ได้เมื่อวงเงินไม่เกินตามที่ระเบียบกำหนด/)
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "วิธี" })).toBeInTheDocument();
    expect(screen.getByText("จัดทำรายงานขอซื้อ")).toBeInTheDocument();
    expect(screen.getByTestId("chat-online-sources")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "กรมบัญชีกลาง" })).toHaveAttribute(
      "href",
      "https://www.gprocurement.go.th"
    );
    expect(screen.getByRole("link", { name: "ระเบียบพัสดุ" })).toHaveAttribute(
      "href",
      "https://www.cgd.go.th/reg"
    );
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

  it("dedupes mcp+document of the same file and caps the chip bar", () => {
    expect(
      uniqueCitations([
        { type: "mcp", label: "พรบ.pdf" },
        { type: "document", label: "พรบ.pdf" },
        { type: "mcp", label: "พรบ.pdf" },
      ])
    ).toEqual([{ type: "document", label: "พรบ.pdf" }]);
    const many = Array.from({ length: 12 }, (_, index) => ({
      type: "document",
      label: `ไฟล์-${index}.pdf`,
    }));
    render(<ChatCitationBar citations={many} />);
    expect(screen.getAllByTestId("chat-citation")).toHaveLength(8);
    expect(screen.getByTestId("chat-citation-more")).toHaveTextContent("+4");
  });
});
