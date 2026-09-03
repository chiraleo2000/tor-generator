import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import KnowledgeBasePage from "./page";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/components/brand/upload-area", () => ({
  UploadArea: ({ onFiles }: { onFiles: (files: FileList) => void }) => (
    <button
      type="button"
      data-testid="upload-trigger"
      onClick={() => {
        const file = new File(["%PDF"], "mine.pdf", { type: "application/pdf" });
        const files = {
          0: file,
          length: 1,
          item: (index: number) => (index === 0 ? file : null),
        } as unknown as FileList;
        onFiles(files);
      }}
    >
      upload
    </button>
  ),
}));

const catalog = {
  groups: [
    {
      key: "mandatory_raw",
      label: "ข้อมูลดิบกฎหมาย/ระเบียบ (บังคับ)",
      mandatory: true,
      files: 1,
      chunks: 10,
      items: [{ id: "a", name: "พรบ.pdf", chunk_count: 10 }],
    },
    {
      key: "user",
      label: "เอกสารของฉัน",
      mandatory: false,
      files: 1,
      chunks: 2,
      items: [{ id: "b", name: "ของฉัน.pdf", chunk_count: 2 }],
    },
  ],
  userFiles: [
    {
      id: "b",
      name: "ของฉัน.pdf",
      chunk_count: 2,
      category: "other",
      processing_status: "completed",
    },
  ],
  totals: { files: 2, chunks: 12 },
  raw: {},
  chunked: [{ key: "law", name: "law", files: 1, chunks: 10 }],
};

describe("KnowledgeBasePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: "1",
        name: "Officer",
        email: "officer@example.go.th",
        organization: "กรม",
        role: "officer",
        createdAt: "",
        updatedAt: "",
      },
      token: "t",
      isAuthenticated: true,
      isLoading: false,
    });
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: catalog },
    } as never);
  });

  it("shows grouped mandatory corpus and private files", async () => {
    render(<KnowledgeBasePage />);
    expect(await screen.findByTestId("knowledge-base-page")).toBeInTheDocument();
    expect(screen.getByText("อัปโหลดเอกสารของฉัน")).toBeInTheDocument();
    expect(screen.getByText("ข้อมูลดิบกฎหมาย/ระเบียบ (บังคับ)")).toBeInTheDocument();
    expect(screen.getByText("เอกสารที่ผู้ใช้อัปโหลด (เฉพาะบัญชีนี้)")).toBeInTheDocument();
    expect(screen.getByText("ของฉัน.pdf")).toBeInTheDocument();
    expect(screen.getAllByText("ของฉัน.pdf")).toHaveLength(1);
    expect(screen.getByText("ส่วนตัว")).toBeInTheDocument();
    expect(screen.getAllByText("ข้อมูลอื่น ๆ").length).toBeGreaterThan(0);
    expect(screen.getByTestId("kb-mine-status-b")).toHaveTextContent("ใช้กับ RAG ได้");
    expect(screen.getByTestId("kb-mine-count")).toHaveTextContent("1 ไฟล์");
    expect(screen.getByTestId("download-mine-b")).toBeInTheDocument();
    expect(screen.queryByText("ประกาศราคากลาง / ระเบียบ")).not.toBeInTheDocument();
    expect(screen.getAllByText("พ.ร.บ. / กฎหมาย").length).toBeGreaterThan(0);
    expect(screen.getByText("หนังสือเวียนกรมบัญชีกลาง")).toBeInTheDocument();
  });

  it("shows a failed status badge and download control", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          ...catalog,
          userFiles: [
            {
              id: "fail-1",
              name: "เสีย.pdf",
              chunk_count: 0,
              category: "other",
              processing_status: "failed",
              error_message: "อ่านไฟล์ไม่สำเร็จ",
            },
          ],
          groups: catalog.groups.filter((group) => group.mandatory),
        },
      },
    } as never);
    render(<KnowledgeBasePage />);
    const badge = await screen.findByTestId("kb-mine-status-fail-1");
    expect(badge).toHaveTextContent("ประมวลผลไม่สำเร็จ");
    expect(badge).toHaveAttribute("title", "อ่านไฟล์ไม่สำเร็จ");
    expect(screen.getByTestId("download-mine-fail-1")).toBeInTheDocument();
  });

  it("posts officer uploads to /knowledge-base/mine", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true } } as never);
    render(<KnowledgeBasePage />);
    await screen.findByTestId("knowledge-base-page");
    fireEvent.click(screen.getByTestId("upload-trigger"));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
    expect(vi.mocked(apiClient.post).mock.calls[0][0]).toBe("/knowledge-base/mine");
  });

  it("deletes private files via /knowledge-base/mine/{id}", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: { ok: true } } as never);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<KnowledgeBasePage />);
    await screen.findByTestId("knowledge-base-page");
    fireEvent.click(screen.getByTestId("delete-user-file-b"));
    await waitFor(() => expect(apiClient.delete).toHaveBeenCalled());
    expect(vi.mocked(apiClient.delete).mock.calls[0][0]).toBe("/knowledge-base/mine/b");
    confirmSpy.mockRestore();
  });

  it("does not extract or duplicate private files across groups", async () => {
    render(<KnowledgeBasePage />);
    await screen.findByTestId("knowledge-base-page");
    expect(screen.getAllByTestId("delete-user-file-b")).toHaveLength(1);
    expect(screen.queryByTestId("delete-mine-b")).not.toBeInTheDocument();
  });

  it("posts admin uploads to the shared /knowledge-base/upload path", async () => {
    useAuthStore.setState({
      user: {
        id: "2",
        name: "Admin",
        email: "admin@example.go.th",
        organization: "กรม",
        role: "admin",
        createdAt: "",
        updatedAt: "",
      },
    });
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true } } as never);
    render(<KnowledgeBasePage />);
    expect(await screen.findByText("อัปโหลดเอกสารเข้าคลังความรู้ส่วนกลาง")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("upload-trigger"));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
    expect(vi.mocked(apiClient.post).mock.calls[0][0]).toBe("/knowledge-base/upload");
  });

  it("shows an alert when the catalog fails to load", async () => {
    vi.mocked(apiClient.get).mockRejectedValue({
      response: { data: { error: { message: "โหลดคลังความรู้ไม่สำเร็จ" } } },
    });
    render(<KnowledgeBasePage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("โหลดคลังความรู้ไม่สำเร็จ");
  });

  it("shows an alert when officer upload fails", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { error: { message: "ไฟล์ไม่รองรับ" } } },
    });
    render(<KnowledgeBasePage />);
    await screen.findByTestId("knowledge-base-page");
    fireEvent.click(screen.getByTestId("upload-trigger"));
    expect(await screen.findByRole("alert")).toHaveTextContent("ไฟล์ไม่รองรับ");
  });

  it("expands a mandatory group and changes the upload category chip", async () => {
    render(<KnowledgeBasePage />);
    fireEvent.click(await screen.findByText("ข้อมูลดิบกฎหมาย/ระเบียบ (บังคับ)"));
    expect(screen.getByText("พรบ.pdf")).toBeInTheDocument();
    expect(screen.getByText(/10 chunks · ลบไม่ได้/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "กฎกระทรวง" }));
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true } } as never);
    fireEvent.click(screen.getByTestId("upload-trigger"));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
    const body = vi.mocked(apiClient.post).mock.calls[0][1] as FormData;
    expect(body.get("category")).toBe("regulation");
  });

  it("shows a download error for a private file", async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (String(url).includes("/file")) {
        throw { response: { data: { error: { message: "ดาวน์โหลดไม่สำเร็จ" } } } };
      }
      return { data: { ok: true, data: catalog } } as never;
    });
    render(<KnowledgeBasePage />);
    fireEvent.click(await screen.findByTestId("download-mine-b"));
    expect(await screen.findByRole("alert")).toHaveTextContent("ดาวน์โหลดไม่สำเร็จ");
  });

  it("keeps the file when delete is cancelled", async () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    render(<KnowledgeBasePage />);
    fireEvent.click(await screen.findByTestId("delete-user-file-b"));
    expect(apiClient.delete).not.toHaveBeenCalled();
  });

  it("shows a delete error and falls back to raw catalog groups", async () => {
    vi.mocked(apiClient.delete).mockRejectedValue({
      response: { data: { error: { message: "ลบเอกสารไม่สำเร็จ" } } },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<KnowledgeBasePage />);
    fireEvent.click(await screen.findByTestId("delete-user-file-b"));
    expect(await screen.findByRole("alert")).toHaveTextContent("ลบเอกสารไม่สำเร็จ");
  });

  it("expands a raw category when grouped catalog is empty", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          groups: [],
          userFiles: [],
          totals: { files: 1, chunks: 3 },
          raw: {
            law: [{ id: "raw-1", name: "พรบ-raw.pdf", chunk_count: 3 }],
          },
          chunked: [],
        },
      },
    } as never);
    render(<KnowledgeBasePage />);
    fireEvent.click(
      await screen.findByText((text, el) =>
        Boolean(el?.classList.contains("font-semibold") && text === "พ.ร.บ. / กฎหมาย")
      )
    );
    expect(await screen.findByText("พรบ-raw.pdf")).toBeInTheDocument();
    expect(screen.getAllByText(/3 chunks/).length).toBeGreaterThan(0);
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    fireEvent(window, new Event("focus"));
    fireEvent(document, new Event("visibilitychange"));
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    fireEvent(document, new Event("visibilitychange"));
  });

  it("downloads a private file through a blob link", async () => {
    const click = vi.fn();
    const createObjectURL = vi.fn(() => "blob:kb-file");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const realCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = realCreate(tag);
      if (tag === "a") {
        el.click = click;
      }
      return el;
    });
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (String(url).includes("/file")) {
        return { data: new Blob(["pdf"]) } as never;
      }
      return { data: { ok: true, data: catalog } } as never;
    });
    render(<KnowledgeBasePage />);
    fireEvent.click(await screen.findByTestId("download-mine-b"));
    await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:kb-file");
  });
});
