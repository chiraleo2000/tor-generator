/** Client contract for standalone review Jaccard compare.

  POST /review/extract — multipart `file` → job `{ id, extracted_text, ... }`
  POST /review/compare-projects — `{ extract_ids: string[] }` (≥ 2)
  data: `{ comparisons: { left, right, left_id?, right_id?, jaccard }[] }`

If compare-projects returns 404/405/501, fall back to local Jaccard on
`extracted_text`.
*/

import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";

export const COMPARE_EXTRACTS_PATH = "/review/compare-projects";

export interface ReviewExtractJob {
  id: string;
  filename?: string;
  extracted_text?: string;
  status?: string;
}

export interface JaccardComparison {
  left: string;
  right: string;
  jaccard: number;
}

export interface CompareExtractsResponse {
  comparisons: JaccardComparison[];
}

export function httpStatusOf(err: unknown): number {
  if (!err || typeof err !== "object") {
    return 0;
  }
  const status = (err as { response?: { status?: unknown } }).response?.status;
  return typeof status === "number" ? status : 0;
}

export function isMissingCompareExtractsEndpoint(err: unknown): boolean {
  const status = httpStatusOf(err);
  return status === 404 || status === 405 || status === 501;
}

export function tokenSet(value: string): Set<string> {
  return new Set(
    value.replaceAll("\n", " ").split(" ").filter((part) => part.length > 1)
  );
}

export function jaccard(left: string, right: string): number {
  const a = tokenSet(left);
  const b = tokenSet(right);
  const union = new Set<string>(Array.from(a).concat(Array.from(b)));
  if (union.size === 0) {
    return 0;
  }
  let overlap = 0;
  for (const token of Array.from(a)) {
    if (b.has(token)) {
      overlap += 1;
    }
  }
  return overlap / union.size;
}

export function roundJaccard(value: number): number {
  return Math.round(value * 10000) / 10000;
}

export function localCompareExtracts(
  primary: ReviewExtractJob,
  others: ReviewExtractJob[]
): JaccardComparison[] {
  const leftName = primary.filename || primary.id;
  const leftText = primary.extracted_text || "";
  return others.map((row) => ({
    left: leftName,
    right: row.filename || row.id,
    jaccard: roundJaccard(jaccard(leftText, row.extracted_text || "")),
  }));
}

export async function extractReviewFile(file: File): Promise<ReviewExtractJob> {
  const body = new FormData();
  body.append("file", file);
  const payload = unwrapData<ReviewExtractJob>(
    await apiClient.post("/review/extract", body)
  );
  return {
    id: payload.id,
    filename: payload.filename || file.name,
    extracted_text: payload.extracted_text,
    status: payload.status,
  };
}

export async function extractCompareFiles(
  rows: { name: string; file: File | null }[]
): Promise<ReviewExtractJob[]> {
  const jobs: ReviewExtractJob[] = [];
  for (const row of rows) {
    if (!row.file) {
      continue;
    }
    const job = await extractReviewFile(row.file);
    jobs.push({
      ...job,
      filename: row.name.trim() || job.filename || row.file.name,
    });
  }
  return jobs;
}

export async function compareExtractJobs(
  primary: ReviewExtractJob,
  others: ReviewExtractJob[]
): Promise<CompareExtractsResponse> {
  if (others.length === 0) {
    return { comparisons: [] };
  }
  const body = {
    extract_ids: [primary.id, ...others.map((row) => row.id)],
  };
  try {
    const response = await apiClient.post(COMPARE_EXTRACTS_PATH, body);
    return unwrapData<CompareExtractsResponse>(response);
  } catch (err: unknown) {
    if (!isMissingCompareExtractsEndpoint(err)) {
      throw err;
    }
    return { comparisons: localCompareExtracts(primary, others) };
  }
}
