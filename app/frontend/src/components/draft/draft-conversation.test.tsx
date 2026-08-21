import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DraftConversation } from "@/components/draft/draft-conversation";
import { apiClient } from "@/lib/api-client";
import { streamSsePost } from "@/lib/chat-sse";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock("@/lib/chat-sse", () => ({
  streamSsePost: vi.fn(),
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (select: (state: { token: string }) => string) => select({ token: "t" }),
}));

describe("DraftConversation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: { room_id: "r1", coverage: [] } },
    } as never);
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          messages: [
            {
              id: "m1",
              role: "assistant",
              content: "สวัสดีครับ ผมอ่านเอกสารจาก Phase 1 แล้ว",
              citations: [],
            },
          ],
        },
      },
    } as never);
    vi.mocked(streamSsePost).mockResolvedValue(undefined);
  });

  it("opens Phase 2 with the Phase 1 brief in a dedicated chat", async () => {
    render(
      <DraftConversation projectId="p1" mode="intake" apiBase="/api/v1" />
    );
    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith("/projects/p1/intake/open-qa")
    );
    expect(await screen.findByTestId("chat-msg-assistant")).toHaveTextContent(
      "ผมอ่านเอกสารจาก Phase 1"
    );
    expect(screen.queryByTestId("chat-shell")).not.toBeInTheDocument();
  });

  it("sends a spoken answer through intake chat", async () => {
    render(
      <DraftConversation projectId="p1" mode="intake" apiBase="/api/v1" />
    );
    await screen.findByTestId("chat-msg-assistant");
    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "วงเงินสองล้านบาท" },
    });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(streamSsePost).toHaveBeenCalled());
    expect(String(vi.mocked(streamSsePost).mock.calls[0][0])).toContain(
      "/projects/p1/intake/chat"
    );
  });
});
