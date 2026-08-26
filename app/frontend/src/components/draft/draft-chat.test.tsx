import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DraftChat, resetDraftChatStartsForTests } from "@/components/draft/draft-chat";
import { apiClient } from "@/lib/api-client";
import { streamSsePost } from "@/lib/chat-sse";

type SseOnEvent = (event: string, data: Record<string, unknown>) => void;

function mockStream(
  impl: (url: string, onEvent: SseOnEvent) => void | Promise<void>
): void {
  vi.mocked(streamSsePost).mockImplementation(
    async (url: string, _body: unknown, _token: string | null, onEvent: SseOnEvent) => {
      await impl(url, onEvent);
    }
  );
}

function sseCallUrl(call: readonly unknown[]): string {
  return String(call[0]);
}

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
    resetDraftChatStartsForTests();
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
    mockStream((_url, onEvent) => {
      onEvent("section_start", { section_key: "s1", title: "ความเป็นมา" });
      onEvent("token", { text: "กรม" });
      onEvent("section_done", { section_key: "s1", content: "กรมบัญชีกลางจัดซื้อระบบ", drafted_count: 1 });
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
    mockStream((_url, onEvent) => {
      onEvent("section_start", { section_key: "s1", title: "ความเป็นมา" });
      onEvent("token", { text: "กรม" });
      onEvent("section_done", {
        section_key: "s1",
        content: "กรมบัญชีกลางจัดซื้อระบบ",
        drafted_count: 1,
      });
      drafted = true;
    });
    const onSectionDone = vi.fn();
    const onAllDrafted = vi.fn();
    render(<DraftChat projectId="p1" onAllDrafted={onAllDrafted} onSectionDone={onSectionDone} />);
    expect(await screen.findByTestId("draft-chat")).toBeInTheDocument();
    await waitFor(() => expect(streamSsePost).toHaveBeenCalled());
    expect(sseCallUrl(vi.mocked(streamSsePost).mock.calls[0])).toContain("/draft-chat/start");
    expect(await screen.findByTestId("draft-accept-s1")).toBeInTheDocument();
    expect(screen.getByText(/กำลังเริ่มร่างทั้ง ๑๓ หมวด/)).toBeInTheDocument();
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
    mockStream(async () => {
      calls += 1;
      if (calls === 1) {
        throw new Error("ตัดการเชื่อมต่อ");
      }
      drafted = true;
    });
    render(<DraftChat projectId="p1" onAllDrafted={vi.fn()} />);
    await waitFor(() => expect(calls).toBeGreaterThanOrEqual(2));
    expect(await screen.findByTestId("draft-chat-count")).toHaveTextContent("13/13");
  });

  it("refreshes parent when a subsection finishes", async () => {
    const onSectionDone = vi.fn();
    mockStream((_url, onEvent) => {
      onEvent("section_start", { section_key: "s4", title: "ขอบเขตของงาน" });
      onEvent("subsection_done", { section_key: "s4", sub_key: "s4.1", content: "สรุปงาน" });
      onEvent("section_done", {
        section_key: "s4",
        content: "สรุปงาน",
        drafted_count: 1,
      });
    });
    render(<DraftChat projectId="p1" onAllDrafted={vi.fn()} onSectionDone={onSectionDone} />);
    await waitFor(() => expect(onSectionDone).toHaveBeenCalled());
  });

  it("ignores progress pings and surfaces section_error", async () => {
    mockStream((_url, onEvent) => {
      onEvent("progress", { message: "เริ่มร่างทีละหมวดจากโมเดลภาษา" });
      onEvent("section_start", { section_key: "s1", title: "ความเป็นมา" });
      onEvent("section_error", { section_key: "s1", message: "หมดเวลารอคิวโมเดลภาษา" });
    });
    render(<DraftChat projectId="p-error" onAllDrafted={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("หมดเวลารอคิวโมเดลภาษา");
  });

  it("accepts a drafted section through the message stream", async () => {
    mockStream((url, onEvent) => {
      if (url.includes("/message")) {
        onEvent("accepted", { section_key: "s1", message: "ยอมรับแล้ว" });
        return;
      }
      onEvent("section_start", { section_key: "s1", title: "ความเป็นมา" });
      onEvent("section_done", {
        section_key: "s1",
        content: "กรมบัญชีกลางจัดซื้อระบบ",
        drafted_count: 1,
      });
    });
    render(<DraftChat projectId="p-accept" onAllDrafted={vi.fn()} />);
    fireEvent.click(await screen.findByTestId("draft-accept-s1"));
    await waitFor(() =>
      expect(vi.mocked(streamSsePost).mock.calls.some((call) => sseCallUrl(call).includes("/message"))).toBe(
        true
      )
    );
    const messageCall = vi.mocked(streamSsePost).mock.calls.find((call) =>
      sseCallUrl(call).includes("/message")
    );
    expect(messageCall?.[1]).toMatchObject({ content: "ยอมรับ", section_key: "s1" });
    expect(await screen.findByText("ยอมรับแล้ว ✓")).toBeInTheDocument();
  });
});
