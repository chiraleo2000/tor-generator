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
});
