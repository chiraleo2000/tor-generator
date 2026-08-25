export const REVIEW_JOB_STORAGE_KEY = "tor-standalone-review-job";

export interface RestoredReviewJob {
  id: string;
  step: 2 | 3;
  qualityScore?: number;
  findings: unknown[];
  extractedText?: string;
  status: string;
}

function canUseWindow(): boolean {
  return typeof window !== "undefined";
}

export function persistReviewJobId(id: string | null): void {
  if (!canUseWindow()) return;
  const url = new URL(window.location.href);
  if (!id) {
    sessionStorage.removeItem(REVIEW_JOB_STORAGE_KEY);
    url.searchParams.delete("job");
  } else {
    sessionStorage.setItem(REVIEW_JOB_STORAGE_KEY, id);
    url.searchParams.set("job", id);
  }
  const query = url.searchParams.toString();
  window.history.replaceState(null, "", query ? `${url.pathname}?${query}` : url.pathname);
}

export function readReviewJobId(): string | null {
  if (!canUseWindow()) return null;
  return new URLSearchParams(window.location.search).get("job") || sessionStorage.getItem(REVIEW_JOB_STORAGE_KEY);
}

export function restoredReviewFromPayload(data: Record<string, unknown>): RestoredReviewJob | null {
  const id = typeof data.id === "string" ? data.id : "";
  const score = data.quality_score;
  if (typeof score === "number" && id) {
    const text = typeof data.extracted_text === "string" ? data.extracted_text : "";
    return {
      id,
      step: 3,
      qualityScore: score,
      findings: Array.isArray(data.findings) ? data.findings : [],
      extractedText: text || undefined,
      status: typeof data.status === "string" ? data.status : "completed",
    };
  }
  const text = typeof data.extracted_text === "string" ? data.extracted_text : "";
  if (id && text) {
    return {
      id,
      step: 2,
      findings: [],
      extractedText: text,
      status: typeof data.status === "string" ? data.status : "extracted",
    };
  }
  return null;
}

export function reviewRestoreStatus(score: number): string {
  if (score >= 70) {
    return `ตรวจเสร็จ — ผ่านเกณฑ์เบื้องต้น (${score}/100)`;
  }
  return `ตรวจเสร็จ — ยังไม่ผ่านเกณฑ์ 70 (${score}/100)`;
}
