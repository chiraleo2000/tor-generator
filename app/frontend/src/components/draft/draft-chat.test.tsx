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
          sections: [],
          drafted_count: 0,
          total: 13,
          all_drafted: false,
        },
      },
    } as never);
    vi.mocked(streamSsePost).mockImplementation(async (_url, body, _token, onEvent) => {
      const key = (body as { section_key?: string }).section_key || "s1";
      onEvent("section_start", { section_key: key, title: "ความเป็นมา" });
      onEvent("token", { text: "กรม" });
      onEvent("section_done", { content: "กรมบัญชีกลางจัดซื้อระบบ", drafted_count: 1 });
    });
  });

  it("auto-starts drafting and shows a completed section with actions", async () => {
    let drafted = false;
    vi.mocked(apiClient.get).mockImplementation(async () => ({
      data: {
        ok: true,
        data: {
          sections: [],
          drafted_count: drafted ? 13 : 0,
          total: 13,
          all_drafted: drafted,
        },
      },
    } as never));
    vi.mocked(streamSsePost).mockImplementation(async (_url, body, _token, onEvent) => {
      const key = (body as { section_key?: string }).section_key || "s1";
      onEvent("section_start", { section_key: key, title: "ความเป็นมา" });
      onEvent("token", { text: "กรม" });
      onEvent("section_done", { content: "กรมบัญชีกลางจัดซื้อระบบ", drafted_count: 1 });
      drafted = true;
    });
    const onSectionDone = vi.fn();
    const onAllDrafted = vi.fn();
    render(<DraftChat projectId="p1" onAllDrafted={onAllDrafted} onSectionDone={onSectionDone} />);
    expect(await screen.findByTestId("draft-chat")).toBeInTheDocument();
    await waitFor(() => expect(streamSsePost).toHaveBeenCalled());
    expect(vi.mocked(streamSsePost).mock.calls[0][0]).toContain("/draft-chat/message");
    expect(await screen.findByTestId("draft-accept-s1")).toBeInTheDocument();
    expect(screen.getByText(/กำลังเริ่มร่าง TOR ทั้ง 13 หมวด/)).toBeInTheDocument();
    await waitFor(() => expect(onAllDrafted).toHaveBeenCalled());
    expect(onSectionDone).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("draft-edit-s1"));
    expect(screen.getByTestId("draft-chat-input")).toHaveValue("แก้ไข หมวด 1: ");
  });

  it("does not restart drafting when all 13 sections already exist", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          sections: [],
          drafted_count: 13,
          total: 13,
          all_drafted: true,
        },
      },
    } as never);
    const onAllDrafted = vi.fn();
    render(<DraftChat projectId="p1" onAllDrafted={onAllDrafted} />);
    await waitFor(() => expect(onAllDrafted).toHaveBeenCalled());
    expect(streamSsePost).not.toHaveBeenCalled();
  });

  it("retries a section once when the first stream fails", async () => {
    let drafted = false;
    let calls = 0;
    vi.mocked(apiClient.get).mockImplementation(async () => ({
      data: {
        ok: true,
        data: {
          sections: [],
          drafted_count: drafted ? 13 : 0,
          total: 13,
          all_drafted: drafted,
        },
      },
    } as never));
    vi.mocked(streamSsePost).mockImplementation(async () => {
      calls += 1;
      if (calls === 1) {
        throw new Error("ตัดการเชื่อมต่อ");
      }
      drafted = true;
    });
    render(<DraftChat projectId="p1" />);
    await waitFor(() => expect(calls).toBeGreaterThanOrEqual(2));
    expect(await screen.findByTestId("draft-chat-count")).toHaveTextContent("13/13");
  });
});
