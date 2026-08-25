import { describe, expect, it, beforeEach } from "vitest";
import {
  markProjectReviewFinished,
  markProjectReviewStarted,
  resetReviewRunGuard,
  shouldSkipProjectReview,
} from "./review-run-guard";

describe("review-run-guard", () => {
  beforeEach(() => {
    resetReviewRunGuard();
  });

  it("skips when project id is missing", () => {
    expect(shouldSkipProjectReview(null, false)).toBe(true);
    expect(shouldSkipProjectReview("", false)).toBe(true);
  });

  it("skips a second auto-run while in flight or after success", () => {
    expect(shouldSkipProjectReview("p1", false)).toBe(false);
    markProjectReviewStarted("p1");
    expect(shouldSkipProjectReview("p1", false)).toBe(true);
    markProjectReviewFinished("p1", true);
    expect(shouldSkipProjectReview("p1", false)).toBe(true);
  });

  it("allows a forced rerun after success", () => {
    markProjectReviewStarted("p1");
    markProjectReviewFinished("p1", true);
    expect(shouldSkipProjectReview("p1", true)).toBe(false);
  });

  it("allows another auto-run after a failed attempt", () => {
    markProjectReviewStarted("p1");
    markProjectReviewFinished("p1", false);
    expect(shouldSkipProjectReview("p1", false)).toBe(false);
  });
});
