import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ReviewChat } from "@/components/draft/review-chat";

describe("ReviewChat", () => {
  it("auto-runs review and requests a re-check from chat", async () => {
    const onReview = vi.fn().mockResolvedValue(undefined);
    render(
      <ReviewChat
        score={80}
        findings={[{ severity: "warning", rule: "budget", section: "s6", message: "ตรวจวงเงิน", recommendation: "ปรับวงเงินให้ตรงงบ" }]}
        busy={false}
        onReview={onReview}
      />
    );
    expect(await screen.findByTestId("review-chat")).toHaveTextContent("คะแนนคุณภาพ 80/100");
    expect(onReview).not.toHaveBeenCalled();
    fireEvent.change(screen.getByTestId("review-chat-input"), {
      target: { value: "ตรวจอีกครั้ง" },
    });
    fireEvent.click(screen.getByTestId("review-chat-send"));
    await waitFor(() => expect(onReview).toHaveBeenCalledWith(true));
  });

  it("asks the reviewer model for a freeform opinion", async () => {
    const onAsk = vi.fn().mockResolvedValue("ควรเพิ่มอัตราค่าปรับให้สอดคล้องงวดงาน");
    render(
      <ReviewChat
        score={70}
        findings={[]}
        busy={false}
        onReview={vi.fn().mockResolvedValue(undefined)}
        onAsk={onAsk}
      />
    );
    fireEvent.change(screen.getByTestId("review-chat-input"), {
      target: { value: "ร่างนี้ขาดอะไร" },
    });
    fireEvent.click(screen.getByTestId("review-chat-send"));
    await waitFor(() => expect(onAsk).toHaveBeenCalledWith("ร่างนี้ขาดอะไร"));
    expect(await screen.findByText(/อัตราค่าปรับ/)).toBeInTheDocument();
  });

  it("shows Rule Engine waiting copy before a score exists", async () => {
    const onReview = vi.fn().mockResolvedValue(undefined);
    render(
      <ReviewChat
        score={null}
        findings={[]}
        busy
        onReview={onReview}
      />
    );
    expect(await screen.findByTestId("review-chat")).toHaveTextContent(
      "กำลังตรวจด้วยกฎระเบียบ พ.ร.บ. และเอกสารขั้นที่ ๐ ของโครงการนี้"
    );
  });
});
