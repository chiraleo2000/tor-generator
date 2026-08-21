import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DraftChat } from "@/components/draft/draft-chat";
import { apiClient } from "@/lib/api-client";
import { streamSsePost } from "@/lib/chat-sse";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("@/lib/chat-sse", () => ({
  streamSsePost: vi.fn(),
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (select: (state: { token: string }) => string) => select({ token: "t" }),
}));

describe("DraftChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          sections: [
            {
              section_key: "s1",
              title: "ความเป็นมา",
              has_content: true,
              content_preview: "ร่างหมวด 1",
              human_confirmed: false,
            },
          ],
          drafted_count: 1,
          total: 13,
          all_drafted: false,
        },
      },
    } as never);
    vi.mocked(streamSsePost).mockImplementation(async (_url, _body, _token, onEvent) => {
      onEvent("section_start", { section_key: "s1", title: "ความเป็นมา" });
      onEvent("token", { text: "กรม" });
      onEvent("section_done", { content: "กรมบัญชีกลางจัดซื้อระบบ", drafted_count: 1 });
      onEvent("all_done", { drafted_count: 1 });
    });
  });

  it("auto-starts drafting and shows a completed section with actions", async () => {
    const onSectionDone = vi.fn();
    render(<DraftChat projectId="p1" onAllDrafted={vi.fn()} onSectionDone={onSectionDone} />);
    expect(await screen.findByTestId("draft-chat")).toBeInTheDocument();
    await waitFor(() => expect(streamSsePost).toHaveBeenCalled());
    expect(await screen.findByTestId("draft-accept-s1")).toBeInTheDocument();
    expect(screen.getByText(/ตรวจร่างแต่ละหมวด/)).toBeInTheDocument();
    expect(onSectionDone).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("draft-edit-s1"));
    expect(screen.getByTestId("draft-chat-input")).toHaveValue("แก้ไข หมวด 1: ");
  });
});
