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
    get: vi.fn(),
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
    sessionStorage.clear();
    window.history.replaceState(null, "", "/review");
    vi.mocked(apiClient.get).mockRejectedValue(new Error("no stored job"));
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
    expect(await screen.findByTestId("review-score")).toHaveTextContent(
      "คะแนนความพร้อม 40/100"
    );
    expect(screen.getByTestId("review-legal-findings")).toHaveTextContent(
      "ไม่พบรายการในกลุ่มนี้"
    );
    expect(screen.getByTestId("review-risk-findings")).toBeInTheDocument();
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

  it("restores a completed job from sessionStorage after refresh", async () => {
    sessionStorage.setItem("tor-standalone-review-job", "job-restore");
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: { id: "job-restore", quality_score: 88, findings: [], status: "completed" },
      },
    } as never);
    render(<StandaloneReviewPage />);
    expect(await screen.findByTestId("review-score")).toHaveTextContent(
      "คะแนนความพร้อม 88/100"
    );
    expect(apiClient.get).toHaveBeenCalledWith("/review/job-restore");
  });

  it("restores an extract-only job, then fails confirm with a comparison row", async () => {
    sessionStorage.setItem("tor-standalone-review-job", "job-extract");
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: { id: "job-extract", extracted_text: "ร่างสกัด", status: "extracted" },
      },
    } as never);
    vi.mocked(extractCompareFiles).mockRejectedValue({
      response: { data: { error: { message: "ตรวจสอบไม่สำเร็จ" } } },
    });
    render(<StandaloneReviewPage />);
    expect(await screen.findByTestId("review-extract-preview")).toHaveTextContent("ร่างสกัด");
    fireEvent.click(screen.getByTestId("review-confirm-run"));
    expect(await screen.findByRole("alert")).toHaveTextContent("ตรวจสอบไม่สำเร็จ");
  });

  it("shows a passing score, assessment, and optional compare project controls", async () => {
    vi.stubGlobal("crypto", { randomUUID: () => "cmp-1" });
    vi.mocked(extractReviewFile).mockResolvedValue({
      id: "job-pass",
      extracted_text: "",
    });
    vi.mocked(extractCompareFiles).mockResolvedValue([
      { id: "c1", filename: "คู่.docx", extracted_text: "คู่เทียบ" },
    ]);
    vi.mocked(compareExtractJobs).mockResolvedValue({
      comparisons: [{ left: "หลัก", right: "คู่", jaccard: 0.8 }],
    });
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        ok: true,
        data: {
          quality_score: 88,
          overall_assessment: "ผ่านเกณฑ์เบื้องต้น",
          findings: [],
        },
      },
    } as never);
    render(<StandaloneReviewPage />);
    fireEvent.click(screen.getByRole("button", { name: "+ เพิ่มโครงการเปรียบเทียบ" }));
    fireEvent.change(screen.getByPlaceholderText("ชื่อโครงการเปรียบเทียบ"), {
      target: { value: "โครงการคู่" },
    });
    fireEvent.click(screen.getAllByTestId("review-upload")[1]);
    expect(screen.getByText("tor.txt")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "ลบ #1" }));
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    fireEvent.click(screen.getByTestId("review-extract"));
    expect(await screen.findByTestId("review-extract-preview")).toHaveTextContent(
      "(ไม่มีข้อความ)"
    );
    fireEvent.click(screen.getByTestId("review-confirm-run"));
    expect(await screen.findByTestId("review-score")).toHaveTextContent(
      "คะแนนความพร้อม 88/100"
    );
    expect(screen.getByTestId("review-assessment")).toHaveTextContent("ผ่านเกณฑ์เบื้องต้น");
    expect(screen.getByText("เทียบเคียง หลัก กับ คู่")).toBeInTheDocument();
    expect(screen.getByText("ตรวจเสร็จ — ผ่านเกณฑ์เบื้องต้น (88/100)")).toBeInTheDocument();
  });

  it("restores findings from a completed job and ignores a late response after unmount", async () => {
    sessionStorage.setItem("tor-standalone-review-job", "job-findings");
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: {
          id: "job-findings",
          quality_score: 55,
          extracted_text: "ร่างพร้อมผล",
          findings: [null, { message: "วงเงินไม่ตรง", severity: "warning", rule: "budget", section: "s6" }],
          status: "completed",
        },
      },
    } as never);
    render(<StandaloneReviewPage />);
    expect(await screen.findByTestId("review-score")).toHaveTextContent("คะแนนความพร้อม 55/100");
    expect(screen.getByTestId("review-legal-findings")).toHaveTextContent("วงเงินไม่ตรง");

    let resolveGet: ((value: unknown) => void) | undefined;
    vi.mocked(apiClient.get).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveGet = resolve;
        })
    );
    sessionStorage.setItem("tor-standalone-review-job", "job-late");
    const { unmount } = render(<StandaloneReviewPage />);
    unmount();
    resolveGet?.({
      data: { ok: true, data: { id: "job-late", extracted_text: "ช้า", status: "extracted" } },
    });
  });

  it("shows a low Jaccard comparison as a warning", async () => {
    vi.mocked(extractReviewFile).mockResolvedValue({
      id: "job-jac",
      extracted_text: "ร่าง",
    });
    vi.mocked(extractCompareFiles).mockResolvedValue([]);
    vi.mocked(compareExtractJobs).mockResolvedValue({
      comparisons: [{ left: "ก", right: "ข", jaccard: 0.1 }],
    });
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: { quality_score: 40, findings: [] } },
    } as never);
    render(<StandaloneReviewPage />);
    fireEvent.click(screen.getAllByTestId("review-upload")[0]);
    fireEvent.click(screen.getByTestId("review-extract"));
    fireEvent.click(await screen.findByTestId("review-confirm-run"));
    expect(await screen.findByText("เทียบเคียง ก กับ ข")).toBeInTheDocument();
  });
});
