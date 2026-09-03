import { describe, expect, it, beforeEach } from "vitest";
import {
  REVIEW_JOB_STORAGE_KEY,
  persistReviewJobId,
  readReviewJobId,
  restoredReviewFromPayload,
  reviewRestoreStatus,
} from "./review-job-persist";

describe("review-job-persist", () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.replaceState(null, "", "/review");
  });

  it("stores and reads the job id from sessionStorage and the query string", () => {
    persistReviewJobId("job-42");
    expect(sessionStorage.getItem(REVIEW_JOB_STORAGE_KEY)).toBe("job-42");
    expect(readReviewJobId()).toBe("job-42");
    persistReviewJobId(null);
    expect(readReviewJobId()).toBeNull();
  });

  it("restores a completed Rule Engine payload to step 3", () => {
    const restored = restoredReviewFromPayload({
      id: "job-9",
      quality_score: 81,
      findings: [{ message: "ok" }],
      status: "completed",
    });
    expect(restored).toEqual({
      id: "job-9",
      step: 3,
      qualityScore: 81,
      findings: [{ message: "ok" }],
      extractedText: undefined,
      status: "completed",
    });
    expect(reviewRestoreStatus(81)).toContain("ผ่านเกณฑ์");
    expect(reviewRestoreStatus(40)).toContain("ยังไม่ผ่านเกณฑ์");
  });

  it("restores an extract-only payload to step 2", () => {
    const restored = restoredReviewFromPayload({
      id: "job-2",
      extracted_text: "ร่าง TOR",
      status: "extracted",
    });
    expect(restored?.step).toBe(2);
    expect(restored?.extractedText).toBe("ร่าง TOR");
  });

  it("returns null when the payload has no usable id", () => {
    expect(restoredReviewFromPayload({ quality_score: 80 })).toBeNull();
    expect(restoredReviewFromPayload({ id: "x" })).toBeNull();
  });
});
