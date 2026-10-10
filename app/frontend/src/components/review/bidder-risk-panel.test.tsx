import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BidderRiskPanel, bidderRiskMarkdown } from "@/components/review/bidder-risk-panel";

describe("bidderRiskMarkdown", () => {
  it("builds a table when the server did not send ready markdown", () => {
    const report = {
      recommendation: "",
      penalty: {
        base_label: "วงเงิน",
        amount_note: "ไม่มีอัตรา",
        hourly_note: "คิดรายชั่วโมง",
        phase_penalty_note: "ต่องวด",
        overlap_note: "งวดซ้อน",
        baht_per_day: null,
      },
      categories: [
        { key: "empty", label: "ว่าง", rows: [] },
        {
          key: "clarity",
          label: "ชัดเจน",
          rows: [
            {
              issue: "ก|ข\nค",
              requirement: "ข้อ",
              impact: "สูง",
              level: "สูง",
              mitigation: "ตรวจ",
            },
          ],
        },
      ],
    };
    const markdown = bidderRiskMarkdown(report);
    expect(markdown).toContain("| ไม่พบประเด็นจากข้อความที่มี |");
    expect(markdown).toContain(String.raw`ก\|ข ค`);
    expect(markdown).toContain("คิดรายชั่วโมง");

    render(<BidderRiskPanel report={report} />);
    expect(screen.getByTestId("bidder-risk-recommendation")).toHaveTextContent(
      "ข้อมูลไม่พอสำหรับประเมินความเสี่ยงก่อนยื่น"
    );
    expect(screen.getByTestId("bidder-risk-penalty")).toHaveTextContent("ไม่มีอัตรา");
    expect(screen.getByTestId("bidder-risk-table-empty")).toHaveTextContent(
      "ไม่พบประเด็นจากข้อความที่มี"
    );
    expect(screen.getByTestId("bidder-risk-table-clarity")).toHaveTextContent("ก|ข");
  });

  it("keeps a ready markdown report and formats baht amounts", () => {
    const report = {
      markdown: "# พร้อมแล้ว",
      recommendation: "ยื่นได้",
      gates: ["หลักประกัน"],
      penalty: {
        baht_per_day: 1000,
        amount_30_days: 30000,
        amount_60_days: Number.NaN,
      },
      categories: [],
    };
    expect(bidderRiskMarkdown(report)).toBe("# พร้อมแล้ว");
    render(<BidderRiskPanel report={report} />);
    expect(screen.getByTestId("bidder-risk-penalty-amounts")).toHaveTextContent("1,000");
    expect(screen.getByTestId("bidder-risk-gates")).toHaveTextContent("หลักประกัน");
  });
});
