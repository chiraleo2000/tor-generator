import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import StandaloneReviewPage from "./page";
import { apiClient } from "@/lib/api-client";
import {
  compareExtractJobs,
  extractCompareFiles,
  extractReviewFile,
} from "@/lib/review-compare";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("@/lib/review-compare", () => ({
  extractReviewFile: vi.fn(),
  extractCompareFiles: vi.fn(),
  compareExtractJobs: vi.fn(),
}));

vi.mock("@/components/brand/upload-area", () => ({
  UploadArea: ({ onFiles }: { onFiles: (files: FileList) => void }) => (
    <button
      type="button"
      data-testid="review-upload"
      onClick={() => {
        const file = new File(["tor"], "tor.txt", { type: "text/plain" });
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

describe("StandaloneReviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows an alert when review fails", async () => {
    vi.mocked(extractReviewFile).mockRejectedValue({
      response: { data: { error: { message: "ไฟล์ว่างเปล่า" } } },
    });
    render(<StandaloneReviewPage />);
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    fireEvent.click(screen.getByRole("button", { name: "เริ่มตรวจสอบ TOR" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("ไฟล์ว่างเปล่า");
  });

  it("shows a warning score when Rule Engine is below 70", async () => {
    vi.mocked(extractReviewFile).mockResolvedValue({
      id: "job-1",
      extracted_text: "ร่าง",
    });
    vi.mocked(extractCompareFiles).mockResolvedValue([]);
    vi.mocked(compareExtractJobs).mockResolvedValue({ comparisons: [] });
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        ok: true,
        data: { quality_score: 40, findings: [] },
      },
    } as never);
    render(<StandaloneReviewPage />);
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    fireEvent.click(screen.getByRole("button", { name: "เริ่มตรวจสอบ TOR" }));
    expect(await screen.findByText("คะแนนความพร้อม 40/100")).toBeInTheDocument();
    expect(screen.getByText("ตรวจเสร็จ — ยังไม่ผ่านเกณฑ์ 70 (40/100)")).toBeInTheDocument();
  });
});
