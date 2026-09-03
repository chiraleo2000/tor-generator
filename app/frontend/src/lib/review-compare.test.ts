import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api-client";
import {
  COMPARE_EXTRACTS_PATH,
  compareExtractJobs,
  extractCompareFiles,
  extractReviewFile,
  httpStatusOf,
  isMissingCompareExtractsEndpoint,
  jaccard,
  localCompareExtracts,
  roundJaccard,
  tokenSet,
} from "./review-compare";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe("review compare helpers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("builds token sets and Jaccard like compare-projects", () => {
    expect(Array.from(tokenSet("foo\nbar  x")).sort()).toEqual(["bar", "foo"]);
    expect(jaccard("alpha beta", "alpha gamma")).toBeCloseTo(1 / 3);
    expect(jaccard("", "")).toBe(0);
    expect(roundJaccard(0.12345)).toBe(0.1235);
  });

  it("treats 404/405/501 as a missing compare-extracts endpoint", () => {
    expect(httpStatusOf(null)).toBe(0);
    expect(isMissingCompareExtractsEndpoint({ response: { status: 404 } })).toBe(true);
    expect(isMissingCompareExtractsEndpoint({ response: { status: 405 } })).toBe(true);
    expect(isMissingCompareExtractsEndpoint({ response: { status: 501 } })).toBe(true);
    expect(isMissingCompareExtractsEndpoint({ response: { status: 500 } })).toBe(false);
  });

  it("computes local Jaccard rows from extracted text", () => {
    const rows = localCompareExtracts(
      { id: "p", filename: "primary.docx", extracted_text: "วงเงิน งบประมาณ โครงการ" },
      [{ id: "c", filename: "other.docx", extracted_text: "วงเงิน โครงการ อื่น" }]
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].left).toBe("primary.docx");
    expect(rows[0].right).toBe("other.docx");
    expect(rows[0].jaccard).toBeGreaterThan(0);
  });

  it("extracts a review file and skips compare rows without a file", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        ok: true,
        data: { id: "job-1", filename: "a.pdf", extracted_text: "hello world", status: "extracted" },
      },
    });
    const file = new File(["hello"], "a.pdf", { type: "application/pdf" });
    const job = await extractReviewFile(file);
    expect(job.id).toBe("job-1");
    expect(apiClient.post).toHaveBeenCalledWith("/review/extract", expect.any(FormData));

    const compares = await extractCompareFiles([
      { name: "", file: null },
      { name: "คู่เทียบ", file },
    ]);
    expect(compares).toHaveLength(1);
    expect(compares[0].filename).toBe("คู่เทียบ");
  });

  it("posts compare-projects with extract_ids when the endpoint exists", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        ok: true,
        data: { comparisons: [{ left: "a", right: "b", jaccard: 0.5 }] },
      },
    });
    const result = await compareExtractJobs(
      { id: "p1", filename: "a.docx", extracted_text: "one two" },
      [{ id: "c1", filename: "b.docx", extracted_text: "one three" }]
    );
    expect(apiClient.post).toHaveBeenCalledWith(COMPARE_EXTRACTS_PATH, {
      extract_ids: ["p1", "c1"],
    });
    expect(result.comparisons[0].jaccard).toBe(0.5);
  });

  it("falls back to local Jaccard when compare-extracts is missing", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({ response: { status: 404 } });
    const result = await compareExtractJobs(
      { id: "p1", filename: "a.docx", extracted_text: "alpha beta" },
      [{ id: "c1", filename: "b.docx", extracted_text: "alpha gamma" }]
    );
    expect(result.comparisons).toHaveLength(1);
    expect(result.comparisons[0].jaccard).toBe(roundJaccard(1 / 3));
  });

  it("returns no comparisons when there are no compare jobs", async () => {
    await expect(
      compareExtractJobs({ id: "p1", extracted_text: "x" }, [])
    ).resolves.toEqual({ comparisons: [] });
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it("rethrows compare-projects failures that are not a missing endpoint", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({ response: { status: 500 } });
    await expect(
      compareExtractJobs(
        { id: "p1", extracted_text: "x" },
        [{ id: "c1", extracted_text: "y" }]
      )
    ).rejects.toMatchObject({ response: { status: 500 } });
  });
});
