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

  it("offers a legal-reference checkbox on send, not chips", async () => {
    render(
      <DraftConversation projectId="p1" mode="intake" apiBase="/api/v1" />
    );
    await screen.findByTestId("chat-msg-assistant");
    expect(screen.queryByTestId("intake-ref-chips")).not.toBeInTheDocument();
    const box = screen.getByTestId("intake-attach-legal") as HTMLInputElement;
    expect(box.checked).toBe(false);
    fireEvent.click(box);
    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "วงเงินสองล้านบาท" },
    });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(streamSsePost).toHaveBeenCalled());
    expect(vi.mocked(streamSsePost).mock.calls[0][1]).toMatchObject({
      content: "วงเงินสองล้านบาท",
      attach_legal_reference: true,
    });
  });

  it("shows the open-qa brief when the room has no messages yet", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        ok: true,
        data: {
          room_id: "r1",
          brief: "ขอข้อมูล ความเป็นมา (s1): ความเป็นมาคืออะไร?",
          coverage: [],
        },
      },
    } as never);
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: { messages: [] } },
    } as never);
    render(
      <DraftConversation projectId="p1" mode="intake" apiBase="/api/v1" />
    );
    expect(await screen.findByTestId("chat-msg-assistant")).toHaveTextContent(
      "ขอข้อมูล ความเป็นมา"
    );
  });

  it("opens compose mode and posts a revision", async () => {
    const onRevised = vi.fn();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: { messages: [] } },
    } as never);
    vi.mocked(apiClient.post).mockImplementation(async (url: string) => {
      if (String(url).includes("open-draft")) {
        return { data: { ok: true, data: { room_id: "r1", brief: "ร่างทั้งฉบับ" } } };
      }
      if (String(url).includes("/draft-chat")) {
        return { data: { ok: true, data: { reply: "ปรับหมวด 1 แล้ว" } } };
      }
      return { data: { ok: true, data: { room_id: "r1", brief: "ร่างทั้งฉบับ" } } };
    });
    render(
      <DraftConversation
        projectId="p1"
        mode="compose"
        apiBase="/api/v1"
        onSectionRevised={onRevised}
      />
    );
    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith("/projects/p1/intake/open-draft")
    );
    expect(await screen.findByTestId("chat-msg-assistant")).toHaveTextContent("ร่างทั้งฉบับ");
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "แก้ s1" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(onRevised).toHaveBeenCalled());
  });

  it("shows bootstrap error when open-qa fails", async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error("down"));
    render(<DraftConversation projectId="p1" mode="intake" apiBase="/api/v1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("โหลดบทสนทนาร่างไม่สำเร็จ");
  });

  it("shows send errors from a failed stream", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: { messages: [] } },
    } as never);
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: { room_id: "r1", brief: "สวัสดี" } },
    } as never);
    vi.mocked(streamSsePost).mockRejectedValue(new Error("ตัดสตรีม"));
    render(<DraftConversation projectId="p3" mode="intake" apiBase="/api/v1" />);
    await screen.findByText("สวัสดี");
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "ล้ม" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/ตัดสตรีม/));
  });

  it("streams queued tokens and coverage progress", async () => {
    const onCoverage = vi.fn();
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        ok: true,
        data: {
          room_id: "r1",
          coverage: [{ slot_key: "s1", filled: true, status: "filled" }],
          brief: "เริ่ม",
        },
      },
    } as never);
    vi.mocked(streamSsePost).mockImplementation(async (_u, _b, _t, onEvent) => {
      onEvent("queued", {});
      onEvent("started", {});
      onEvent("token", { text: "ตอบ" });
      onEvent("done", {
        content: "ตอบครบ",
        coverage: [{ slot_key: "s1", filled: true, status: "filled" }],
        progress: { filled: 1, total: 2, percent: 50 },
      });
    });
    render(
      <DraftConversation
        projectId="p1"
        mode="intake"
        apiBase="/api/v1"
        onCoverage={onCoverage}
      />
    );
    await screen.findByTestId("intake-progress");
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "เติม s1" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(onCoverage).toHaveBeenCalled());
    expect(screen.getByTestId("intake-progress-label").textContent).toMatch(/1\/2/);
  });

  it("sends compose on Enter, uses a default reply, and maps AbortError", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: { messages: [] } },
    } as never);
    vi.mocked(apiClient.post).mockImplementation(async (url: string) => {
      if (String(url).includes("open-draft")) {
        return { data: { ok: true, data: { room_id: "r1", brief: "ร่าง" } } };
      }
      if (String(url).includes("/draft-chat")) {
        return { data: { ok: true, data: {} } };
      }
      return { data: { ok: true, data: { room_id: "r1" } } };
    });
    const onRevised = vi.fn();
    render(
      <DraftConversation
        projectId="p1"
        mode="compose"
        apiBase="/api/v1"
        placeholder="พิมพ์แก้ร่าง"
        onSectionRevised={onRevised}
      />
    );
    expect(await screen.findByTestId("chat-msg-assistant")).toHaveTextContent("ร่าง");
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "แก้ s1" } });
    fireEvent.keyDown(screen.getByTestId("chat-input"), { key: "Enter", shiftKey: false });
    await waitFor(() => expect(onRevised).toHaveBeenCalled());
    expect(screen.getByText("ปรับร่างแล้วครับ")).toBeInTheDocument();
  });

  it("keeps partial assistant text on abort and derives progress from coverage", async () => {
    const abort = new DOMException("aborted", "AbortError");
    vi.mocked(streamSsePost).mockImplementation(async (_u, _b, _t, onEvent) => {
      onEvent("queued", {});
      onEvent("token", { text: "ครึ่งทาง" });
      throw abort;
    });
    render(<DraftConversation projectId="p1" mode="intake" apiBase="/api/v1" />);
    await screen.findByTestId("chat-msg-assistant");
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "ช้า" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toMatch(/การตอบใช้เวลานานเกินไป/)
    );
  });

  it("surfaces stream error events and coverage-only progress", async () => {
    vi.mocked(streamSsePost).mockImplementation(async (_u, _b, _t, onEvent) => {
      onEvent("started", {});
      onEvent("error", {});
      onEvent("done", {
        coverage: [{ slot_key: "s1", filled: true, status: "filled" }],
      });
    });
    render(<DraftConversation projectId="p1" mode="intake" apiBase="/api/v1" />);
    await screen.findByTestId("chat-msg-assistant");
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "เติม" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/แชทล้มเหลว/));
  });
});
