import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ReviewChat } from "@/components/draft/review-chat";

describe("ReviewChat", () => {
  it("auto-runs review and accepts a HITL section from chat", async () => {
    const onReview = vi.fn().mockResolvedValue(undefined);
    const onAcceptHitl = vi.fn().mockResolvedValue(undefined);
    render(
      <ReviewChat
        score={80}
        findings={[{ severity: "warning", rule: "budget", section: "s6", message: "ตรวจวงเงิน" }]}
        busy={false}
        onReview={onReview}
        onAcceptHitl={onAcceptHitl}
      />
    );
    expect(await screen.findByTestId("review-chat")).toHaveTextContent("คะแนนคุณภาพ 80/100");
    await waitFor(() => expect(onReview).toHaveBeenCalled());
    fireEvent.change(screen.getByTestId("review-chat-input"), {
      target: { value: "ยืนยันหมวด 6" },
    });
    fireEvent.click(screen.getByTestId("review-chat-send"));
    await waitFor(() => expect(onAcceptHitl).toHaveBeenCalledWith("s6"));
  });

  it("shows Rule Engine waiting copy before a score exists", async () => {
    const onReview = vi.fn().mockResolvedValue(undefined);
    render(
      <ReviewChat
        score={null}
        findings={[]}
        busy
        onReview={onReview}
        onAcceptHitl={vi.fn()}
      />
    );
    expect(await screen.findByTestId("review-chat")).toHaveTextContent(
      "กำลังรัน Rule Engine เพื่อทบทวนร่าง TOR"
    );
  });
});
