import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { ChatShell } from "@/components/chat/chat-shell";
import { apiClient } from "@/lib/api-client";
import { streamSsePost } from "@/lib/chat-sse";
import { useAuthStore } from "@/stores/auth-store";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/lib/chat-sse", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/chat-sse")>();
  return {
    ...actual,
    streamSsePost: vi.fn(),
  };
});

const envelope = <T,>(data: T) => ({ data: { ok: true, data } });

const ROOM = {
  id: "r1",
  kind: "kb",
  project_id: null,
  title: "ห้อง",
  updated_at: new Date().toISOString(),
  last_message: "",
  last_role: null,
};

function mockCatalog(files: Array<{ id: string; name: string }> = []) {
  vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
    if (url === "/chat/rooms") {
      return envelope({ rooms: [ROOM] });
    }
    if (url === "/chat/rooms/r1/messages") {
      return envelope({ messages: [] });
    }
    if (url === "/chat/prompts") {
      return envelope({
        prompts: [{ id: "p1", title: "หลักประกัน", body: "หลักประกันสัญญา" }],
      });
    }
    if (url === "/knowledge-base/catalog") {
      return envelope({ userFiles: files });
    }
    return envelope({});
  });
}

describe("ChatShell MCP degraded banner", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
    vi.stubGlobal(
      "crypto",
      Object.assign(globalThis.crypto ?? {}, {
        randomUUID: () => "req-test",
      })
    );
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
    useAuthStore.setState({
      token: "t",
      user: null,
      isAuthenticated: true,
      isLoading: false,
    });
    mockCatalog();
    vi.mocked(apiClient.post).mockResolvedValue(
      envelope({ ...ROOM, id: "r2" })
    );
    vi.mocked(apiClient.patch).mockResolvedValue(envelope({}));
    vi.mocked(apiClient.delete).mockResolvedValue(envelope({}));
    vi.mocked(apiClient.post).mockClear();
    vi.mocked(apiClient.patch).mockClear();
    vi.mocked(apiClient.delete).mockClear();
    vi.mocked(streamSsePost).mockImplementation(async (_url, _body, _token, onEvent) => {
      onEvent("queued", { position: 2 });
      onEvent("started", {});
      onEvent("token", { text: "คำ" });
      onEvent("done", {
        content: "คำตอบท้องถิ่น",
        mcp_degraded: true,
        citations: [{ type: "mcp", label: "mcp-retrieve-stub" }],
      });
    });
  });

  it("shows mcp unavailable copy and citation chips after send", async () => {
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    await waitFor(() => expect(screen.getByTestId("chat-send")).toBeDisabled());
    fireEvent.change(input, { target: { value: "หลักประกันสัญญา" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => {
      expect(screen.getByTestId("mcp-unavailable")).toBeInTheDocument();
    });
    expect(screen.getByTestId("mcp-unavailable").textContent).toMatch(/MCP/);
    expect(screen.getByTestId("chat-citation").textContent).toMatch(/mcp:/i);
  });

  it("sends on Enter without shift", async () => {
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    fireEvent.change(input, { target: { value: "ถามกฎหมาย" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });
    await waitFor(() => expect(streamSsePost).toHaveBeenCalled());
  });

  it("fills draft from prompt chips", async () => {
    render(<ChatShell kind="kb" />);
    const chip = await screen.findByText("หลักประกัน");
    fireEvent.click(chip);
    expect((screen.getByTestId("chat-input") as HTMLTextAreaElement).value).toBe(
      "หลักประกันสัญญา"
    );
  });

  it("changes search scope", async () => {
    render(<ChatShell kind="kb" />);
    await screen.findByTestId("chat-scope-mine");
    fireEvent.click(screen.getByTestId("chat-scope-mine"));
    fireEvent.click(screen.getByTestId("chat-scope-global"));
    fireEvent.click(screen.getByTestId("chat-scope-both"));
    expect(screen.getByTestId("chat-shell")).toBeInTheDocument();
  });

  it("copies last assistant message", async () => {
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    fireEvent.change(input, { target: { value: "ถาม" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByTestId("mcp-unavailable")).toBeInTheDocument());
    fireEvent.click(screen.getByTitle("คัดลอก"));
    expect(navigator.clipboard.writeText).toHaveBeenCalled();
  });

  it("resends the last user message", async () => {
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    fireEvent.change(input, { target: { value: "ถามซ้ำ" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByTestId("chat-citation")).toBeInTheDocument());
    fireEvent.click(screen.getByTitle("ส่งใหม่"));
    await waitFor(() => expect(vi.mocked(streamSsePost).mock.calls.length).toBeGreaterThan(1));
  });

  it("aborts an in-flight request", async () => {
    let abortSeen = false;
    vi.mocked(streamSsePost).mockImplementation(async (_u, _b, _t, onEvent, signal) => {
      signal?.addEventListener("abort", () => {
        abortSeen = true;
      });
      onEvent("token", { text: "" });
      await new Promise((resolve) => setTimeout(resolve, 40));
      onEvent("done", { content: "ช้า" });
    });
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    fireEvent.change(input, { target: { value: "ช้า" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    fireEvent.click(screen.getByTitle("หยุด"));
    await waitFor(() => expect(abortSeen).toBe(true));
  });

  it("shows stream error events", async () => {
    vi.mocked(streamSsePost).mockImplementation(async (_u, _b, _t, onEvent) => {
      onEvent("error", { message: "แชทล้มเหลวจากเซิร์ฟเวอร์" });
    });
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    fireEvent.change(input, { target: { value: "ล้ม" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByTestId("chat-error").textContent).toMatch(/ล้มเหลว/));
  });

  it("shows thrown send failures", async () => {
    vi.mocked(streamSsePost).mockRejectedValue(new Error("เครือข่ายขาด"));
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    fireEvent.change(input, { target: { value: "ล้ม" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByTestId("chat-error").textContent).toMatch(/เครือข่ายขาด/));
  });

  it("creates a room from the sidebar", async () => {
    render(<ChatShell kind="kb" />);
    await screen.findByTestId("chat-new-room");
    fireEvent.click(screen.getByTestId("chat-new-room"));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
  });

  it("renames and deletes a room", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("ชื่อใหม่");
    render(<ChatShell kind="kb" />);
    await screen.findByTestId("chat-room-item");
    fireEvent.click(screen.getByTitle("เปลี่ยนชื่อ"));
    await waitFor(() => expect(apiClient.patch).toHaveBeenCalled());
    fireEvent.click(screen.getByTitle("ลบ"));
    await waitFor(() => expect(apiClient.delete).toHaveBeenCalled());
  });

  it("attaches a file and shows ingest feedback", async () => {
    vi.mocked(apiClient.post).mockImplementation(async (url: string) => {
      if (String(url).includes("/attachments")) {
        return envelope({ name: "reg.pdf", status: "completed", chunk_count: 2 });
      }
      return envelope(ROOM);
    });
    render(<ChatShell kind="kb" />);
    const attach = await screen.findByTestId("chat-attach");
    const file = new File(["x"], "reg.pdf", { type: "application/pdf" });
    fireEvent.change(attach, { target: { files: [file] } });
    await waitFor(() =>
      expect(screen.getByTestId("chat-attach-feedback").textContent).toMatch(/คลังของฉัน/)
    );
  });

  it("shows attach errors", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { error: { message: "อัปโหลดไฟล์ไม่สำเร็จ" } } },
    });
    render(<ChatShell kind="kb" />);
    const attach = await screen.findByTestId("chat-attach");
    const file = new File(["x"], "bad.pdf", { type: "application/pdf" });
    fireEvent.change(attach, { target: { files: [file] } });
    await waitFor(() => expect(screen.getByTestId("chat-error")).toBeInTheDocument());
  });

  it("lists mine files and deletes after confirm", async () => {
    mockCatalog([{ id: "f1", name: "ของฉัน.pdf" }]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ChatShell kind="kb" />);
    await screen.findByTestId("chat-mine-f1");
    fireEvent.click(screen.getByTestId("chat-delete-mine-f1"));
    await waitFor(() => expect(apiClient.delete).toHaveBeenCalled());
  });

  it("skips mine-file delete when confirm is cancelled", async () => {
    mockCatalog([{ id: "f1", name: "ของฉัน.pdf" }]);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.mocked(apiClient.delete).mockClear();
    render(<ChatShell kind="kb" />);
    await screen.findByTestId("chat-delete-mine-f1");
    fireEvent.click(screen.getByTestId("chat-delete-mine-f1"));
    expect(apiClient.delete).not.toHaveBeenCalled();
  });

  it("hides the room list in compact mode", async () => {
    render(<ChatShell kind="kb" compact />);
    await screen.findByTestId("chat-input");
    expect(screen.queryByTestId("chat-room-list")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-attach")).not.toBeInTheDocument();
  });

  it("shows bootstrap errors", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("down"));
    render(<ChatShell kind="kb" />);
    await waitFor(() =>
      expect(screen.getByTestId("chat-error").textContent).toMatch(/โหลดห้องแชทไม่สำเร็จ/)
    );
  });

  it("creates a kb room when none exist", async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url === "/chat/rooms") {
        return envelope({ rooms: [] });
      }
      if (url === "/chat/prompts") {
        return envelope({ prompts: [] });
      }
      if (url === "/knowledge-base/catalog") {
        return envelope({ userFiles: [] });
      }
      return envelope({ messages: [] });
    });
    render(<ChatShell kind="kb" />);
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
  });

  it("shows an intake empty state and a load-messages error when switching rooms", async () => {
    const older = {
      ...ROOM,
      id: "r-old",
      title: "เก่า",
      updated_at: "2020-01-01T00:00:00.000Z",
      last_message: "",
    };
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url === "/chat/rooms") {
        return envelope({ rooms: [ROOM, older] });
      }
      if (url === "/chat/rooms/r-old/messages") {
        throw { response: { data: { error: { message: "โหลดข้อความไม่สำเร็จ" } } } };
      }
      if (url === "/chat/rooms/r1/messages") {
        return envelope({ messages: [] });
      }
      if (url === "/chat/prompts") {
        return envelope({ prompts: [] });
      }
      if (url === "/knowledge-base/catalog") {
        return envelope({ userFiles: [] });
      }
      return envelope({});
    });
    render(<ChatShell kind="intake" />);
    expect(await screen.findByText(/บอทจะสรุปผลวิเคราะห์/)).toBeInTheDocument();
    const items = await screen.findAllByTestId("chat-room-item");
    fireEvent.click(items[items.length - 1]);
    await waitFor(() =>
      expect(screen.getByTestId("chat-error").textContent).toMatch(/โหลดข้อความไม่สำเร็จ/)
    );
    fireEvent.click(screen.getByTitle("ยุบแถบ"));
  });

  it("shows a mine-file delete error and ignores empty attachments", async () => {
    mockCatalog([{ id: "f1", name: "ของฉัน.pdf" }]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(apiClient.delete).mockRejectedValue({
      response: { data: { error: { message: "ลบเอกสารไม่สำเร็จ" } } },
    });
    render(<ChatShell kind="kb" />);
    fireEvent.click(await screen.findByTestId("chat-delete-mine-f1"));
    await waitFor(() =>
      expect(screen.getByTestId("chat-error").textContent).toMatch(/ลบเอกสารไม่สำเร็จ/)
    );
    const attach = screen.getByTestId("chat-attach") as HTMLInputElement;
    fireEvent.change(attach, { target: { files: [] } });
  });

  it("creates a draft-intake room when none exist for the project", async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url === "/chat/rooms") {
        return envelope({ rooms: [] });
      }
      if (url === "/chat/prompts") {
        return envelope({ prompts: [] });
      }
      if (url === "/knowledge-base/catalog") {
        return envelope({ userFiles: [] });
      }
      return envelope({ messages: [] });
    });
    vi.mocked(apiClient.post).mockResolvedValue(
      envelope({ ...ROOM, id: "draft-room", kind: "draft_intake", project_id: "p9" })
    );
    render(<ChatShell kind="draft_intake" projectId="p9" />);
    await waitFor(() =>
      expect(vi.mocked(apiClient.post).mock.calls.some((call) => call[0] === "/chat/rooms")).toBe(
        true
      )
    );
    expect(vi.mocked(apiClient.post).mock.calls[0][1]).toMatchObject({
      kind: "draft_intake",
      project_id: "p9",
    });
  });

  it("accepts numeric token and done content, and queued position 0", async () => {
    vi.mocked(streamSsePost).mockImplementation(async (_u, _b, _t, onEvent) => {
      onEvent("queued", { position: 0 });
      onEvent("token", { text: 42 });
      onEvent("token", { text: null });
      onEvent("done", { content: 7, citations: [], mcp_degraded: false });
    });
    render(<ChatShell kind="kb" />);
    const input = await screen.findByTestId("chat-input");
    fireEvent.change(input, { target: { value: "ตัวเลข" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByTestId("chat-msg-assistant")).toHaveTextContent("7"));
  });

  it("reports when attach cannot create a room", async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url === "/chat/rooms") {
        return envelope({ rooms: [] });
      }
      if (url === "/chat/prompts") {
        return envelope({ prompts: [] });
      }
      if (url === "/knowledge-base/catalog") {
        return envelope({ userFiles: [] });
      }
      return envelope({ messages: [] });
    });
    vi.mocked(apiClient.post).mockResolvedValue(envelope({ id: undefined }));
    render(<ChatShell kind="intake" />);
    const attach = await screen.findByTestId("chat-attach");
    const file = new File(["x"], "note.pdf", { type: "application/pdf" });
    fireEvent.change(attach, { target: { files: [file] } });
    await waitFor(() =>
      expect(screen.getByTestId("chat-error").textContent).toMatch(/ยังไม่มีห้องแชทสำหรับแนบไฟล์/)
    );
  });
});
