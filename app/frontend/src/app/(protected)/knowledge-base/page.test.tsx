import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import KnowledgeBasePage from "./page";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
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
  userFiles: [{ id: "b", name: "ของฉัน.pdf", chunk_count: 2 }],
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
  });

  it("posts officer uploads to /knowledge-base/mine", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true } } as never);
    render(<KnowledgeBasePage />);
    await screen.findByTestId("knowledge-base-page");
    fireEvent.click(screen.getByTestId("upload-trigger"));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
    expect(vi.mocked(apiClient.post).mock.calls[0][0]).toBe("/knowledge-base/mine");
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
