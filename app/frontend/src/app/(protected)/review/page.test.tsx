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

  it("shows an alert when extract fails", async () => {
    vi.mocked(extractReviewFile).mockRejectedValue({
      response: { data: { error: { message: "ไฟล์ว่างเปล่า" } } },
    });
    render(<StandaloneReviewPage />);
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    fireEvent.click(screen.getByTestId("review-extract"));
    expect(await screen.findByRole("alert")).toHaveTextContent("ไฟล์ว่างเปล่า");
  });

  it("extracts first, then runs after confirm", async () => {
    vi.mocked(extractReviewFile).mockResolvedValue({
      id: "job-1",
      extracted_text: "ร่าง TOR ทดสอบ",
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
    fireEvent.click(screen.getByTestId("review-extract"));
    expect(await screen.findByTestId("review-extract-preview")).toHaveTextContent(
      "ร่าง TOR ทดสอบ"
    );
    expect(apiClient.post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("review-confirm-run"));
    expect(await screen.findByText("คะแนนความพร้อม 40/100")).toBeInTheDocument();
    expect(screen.getByTestId("review-result")).toBeInTheDocument();
    expect(screen.getByText("ตรวจเสร็จ — ยังไม่ผ่านเกณฑ์ 70 (40/100)")).toBeInTheDocument();
  });

  it("goes back from preview without running the rule engine", async () => {
    vi.mocked(extractReviewFile).mockResolvedValue({
      id: "job-1",
      extracted_text: "ร่าง TOR ทดสอบ",
    });
    render(<StandaloneReviewPage />);
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    fireEvent.click(screen.getByTestId("review-extract"));
    expect(await screen.findByTestId("review-extract-preview")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("review-back"));
    expect(screen.queryByTestId("review-extract-preview")).not.toBeInTheDocument();
    expect(screen.getByTestId("review-extract")).toBeInTheDocument();
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it("shows a 20k-character extract preview with an ellipsis when longer", async () => {
    const longText = `${"ก".repeat(20050)}ท้าย`;
    vi.mocked(extractReviewFile).mockResolvedValue({
      id: "job-long",
      extracted_text: longText,
    });
    render(<StandaloneReviewPage />);
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    fireEvent.click(screen.getByTestId("review-extract"));
    const preview = await screen.findByTestId("review-extract-preview");
    expect(preview.textContent).toContain("…");
    expect(preview.textContent?.includes("ท้าย")).toBe(false);
  });

  it("does not extract until the user starts extract", () => {
    render(<StandaloneReviewPage />);
    expect(screen.getByTestId("review-extract")).toBeDisabled();
    expect(extractReviewFile).not.toHaveBeenCalled();
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    expect(extractReviewFile).not.toHaveBeenCalled();
    expect(screen.getByTestId("review-extract")).toBeEnabled();
  });
});
