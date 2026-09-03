"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UploadArea } from "@/components/brand/upload-area";
import { CheckItem } from "@/components/brand/check-item";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { toReviewFinding, type ReviewFinding } from "@/lib/review-findings";
import {
  persistReviewJobId,
  readReviewJobId,
  restoredReviewFromPayload,
  reviewRestoreStatus,
} from "@/lib/review-job-persist";
import {
  compareExtractJobs,
  extractCompareFiles,
  extractReviewFile,
  type JaccardComparison,
  type ReviewExtractJob,
} from "@/lib/review-compare";
import { ReviewFindingBuckets } from "@/components/review/finding-buckets";
import { cn } from "@/lib/utils";

interface ReviewResult {
  quality_score?: number;
  findings?: ReviewFinding[];
  overall_assessment?: string;
}

interface CompareRow {
  id: string;
  name: string;
  file: File | null;
}

type ReviewStep = 1 | 2 | 3;

const LAW_REFS = [
  "พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
  "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ พ.ศ. 2560",
  "คู่มือการจัดซื้อจัดจ้างตาม พ.ร.บ. 2560",
  "มาตรฐาน e-Bidding กรมบัญชีกลาง",
  "ประกาศราคากลาง (จากคลังความรู้)",
];

const STEP_LABELS = ["เลือกไฟล์", "สกัดข้อความ", "ผลการตรวจสอบ"] as const;
const PREVIEW_MAX = 20000;

function previewSnippet(text: string): string {
  const trimmed = text.trim();
  if (trimmed.length <= PREVIEW_MAX) return trimmed;
  return `${trimmed.slice(0, PREVIEW_MAX)}\n…`;
}

function ReviewStepper({ step }: Readonly<{ step: ReviewStep }>) {
  return (
    <ol className="mb-4 flex flex-wrap gap-2 text-[12px]" data-testid="review-stepper">
      {STEP_LABELS.map((label, index) => {
        const id = (index + 1) as ReviewStep;
        return (
          <li
            key={label}
            className={cn(
              "rounded-full border px-3 py-1 font-bold",
              step === id
                ? "border-crimson bg-brand-orange text-navy"
                : "border-gray-200 bg-gray-50 text-muted-foreground"
            )}
          >
            {id}. {label}
          </li>
        );
      })}
    </ol>
  );
}

function ExtractPreview({
  preview,
  busy,
  onBack,
  onConfirm,
}: Readonly<{
  preview: string;
  busy: boolean;
  onBack: () => void;
  onConfirm: () => void;
}>) {
  return (
    <div className="mt-5" data-testid="review-extract-preview">
      <h4 className="mb-2 text-sm font-bold text-navy">ตัวอย่างข้อความที่สกัดได้</h4>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md bg-gray-50 p-3 text-[12px]">
        {preview || "(ไม่มีข้อความ)"}
      </pre>
      <div className="mt-3 flex flex-col gap-2">
        <Button
          variant="outline"
          className="w-full"
          data-testid="review-back"
          onClick={onBack}
          disabled={busy}
        >
          ย้อนกลับ
        </Button>
        <Button
          className="w-full"
          data-testid="review-confirm-run"
          onClick={onConfirm}
          disabled={busy}
        >
          {busy ? "กำลังตรวจสอบ..." : "ยืนยันเริ่มตรวจสอบ"}
        </Button>
      </div>
    </div>
  );
}

function ReviewResults({
  result,
  findings,
  comparisons,
}: Readonly<{
  result: ReviewResult | null;
  findings: ReviewFinding[];
  comparisons: JaccardComparison[];
}>) {
  if (!result) {
    return (
      <p className="py-10 text-center text-muted-foreground">
        สกัดข้อความแล้วกดยืนยันเริ่มตรวจสอบเพื่อดูผล
      </p>
    );
  }
  return (
    <div>
      <div data-testid="review-score">
        <CheckItem
          tone={(result.quality_score ?? 0) >= 70 ? "pass" : "warn"}
          title={`คะแนนความพร้อม ${result.quality_score ?? "—"}/100`}
          detail={
            (result.quality_score ?? 0) >= 70
              ? "ผ่านเกณฑ์เบื้องต้น"
              : "ยังไม่ผ่านเกณฑ์ 70 — ดูรายการด้านล่าง"
          }
        />
      </div>
      {result.overall_assessment ? (
        <p className="mb-3 text-sm text-navy" data-testid="review-assessment">
          {result.overall_assessment}
        </p>
      ) : null}
      <ReviewFindingBuckets findings={findings} />
      {comparisons.map((row) => (
        <CheckItem
          key={`${row.left}-${row.right}`}
          tone={row.jaccard >= 0.5 ? "pass" : "warn"}
          title={`เทียบเคียง ${row.left} กับ ${row.right}`}
          detail={`ความคล้าย ${row.jaccard}`}
        />
      ))}
    </div>
  );
}

export default function StandaloneReviewPage() {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<ReviewStep>(1);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [comparisons, setComparisons] = useState<JaccardComparison[]>([]);
  const [compares, setCompares] = useState<CompareRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [extracted, setExtracted] = useState<ReviewExtractJob | null>(null);

  function applyRestoredJob(data: Record<string, unknown>) {
    const restored = restoredReviewFromPayload(data);
    if (!restored) return;
    persistReviewJobId(restored.id);
    if (restored.extractedText) {
      setExtracted({
        id: restored.id,
        extracted_text: restored.extractedText,
        status: restored.status,
      });
    }
    if (restored.step === 3 && typeof restored.qualityScore === "number") {
      setResult({
        quality_score: restored.qualityScore,
        findings: restored.findings
          .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
          .map((item) => toReviewFinding(item)),
      });
      setStep(3);
      setStatus(reviewRestoreStatus(restored.qualityScore));
      return;
    }
    setStep(2);
    setStatus("สกัดข้อความสำเร็จ — ตรวจตัวอย่างแล้วกดยืนยันเริ่มตรวจสอบ");
  }

  useEffect(() => {
    const jobId = readReviewJobId();
    if (!jobId) return undefined;
    let cancelled = false;
    apiClient
      .get(`/review/${jobId}`)
      .then((response) => {
        if (cancelled) return;
        applyRestoredJob(unwrapData<Record<string, unknown>>(response));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  function resetToUpload(next: File | null) {
    persistReviewJobId(null);
    setFile(next);
    setStep(1);
    setExtracted(null);
    setResult(null);
    setComparisons([]);
    setStatus("");
    setError(null);
  }

  function backToUpload() {
    setStep(1);
    setStatus("");
    setError(null);
  }

  async function extract() {
    if (!file) return;
    setBusy(true);
    setStatus("กำลังสกัดข้อความ...");
    setError(null);
    setResult(null);
    try {
      const primary = await extractReviewFile(file);
      persistReviewJobId(primary.id);
      setExtracted(primary);
      setStep(2);
      setStatus("สกัดข้อความสำเร็จ — ตรวจตัวอย่างแล้วกดยืนยันเริ่มตรวจสอบ");
    } catch (err: unknown) {
      setStatus("");
      setError(apiErrorMessage(err, "สกัดข้อความไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  async function confirmRun() {
    if (!extracted) return;
    setBusy(true);
    setStatus("กำลังตรวจด้วยกฎระเบียบ...");
    setError(null);
    try {
      const compareJobs = await extractCompareFiles(compares);
      const compared = await compareExtractJobs(extracted, compareJobs);
      const ran = unwrapData<ReviewResult>(
        await apiClient.post("/review/run", { id: extracted.id })
      );
      persistReviewJobId(extracted.id);
      const normalized: ReviewResult = {
        ...ran,
        findings: (ran.findings || []).map((item) =>
          toReviewFinding(item as unknown as Record<string, unknown>)
        ),
      };
      setResult(normalized);
      setComparisons(compared.comparisons);
      setStep(3);
      const score = ran.quality_score ?? 0;
      setStatus(
        score >= 70
          ? `ตรวจเสร็จ — ผ่านเกณฑ์เบื้องต้น (${score}/100)`
          : `ตรวจเสร็จ — ยังไม่ผ่านเกณฑ์ 70 (${score}/100)`
      );
    } catch (err: unknown) {
      setStatus("");
      setError(apiErrorMessage(err, "ตรวจสอบไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  const findings = result?.findings || [];
  const preview = previewSnippet(extracted?.extracted_text || "");

  return (
    <div className="grid gap-4 lg:grid-cols-2" data-testid="review-page">
      <div className="gov-card">
        <h3 className="mb-3 text-navy">อัปโหลด TOR ที่ต้องการตรวจสอบ</h3>
        <ReviewStepper step={step} />
        <p className="mb-3 text-sm text-muted-foreground">
          เลือกไฟล์แล้วสกัดข้อความก่อน — ระบบจะไม่ตรวจด้วยกฎจนกว่าคุณยืนยัน
        </p>
        <UploadArea
          label="ลากไฟล์ TOR วาง หรือคลิกเพื่อเลือก"
          hint="PDF, Word (.docx), ข้อความ (.txt) หรือรูปภาพสแกน"
          onFiles={(list) => resetToUpload(list[0] || null)}
        />
        {file ? (
          <p className="mt-2 text-[12.5px]">
            {file.name} · {Math.round(file.size / 1024)} KB
          </p>
        ) : null}
        {busy ? (
          <output className="mt-2 block text-sm text-navy" data-testid="review-busy">
            {status || "กำลังทำงาน..."}
          </output>
        ) : null}
        {error ? (
          <p className="mt-2 text-sm text-destructive" role="alert" data-testid="review-error">
            {error}
          </p>
        ) : null}
        {!busy && status ? (
          <p
            className={`mt-2 text-sm ${
              (result?.quality_score ?? 0) >= 70 ? "text-brand-green" : "text-navy"
            }`}
            data-testid="review-status"
          >
            {status}
          </p>
        ) : null}

        <h3 className="mb-2 mt-6 text-navy">เอกสารอ้างอิงบังคับ</h3>
        <div className="rounded-lg bg-gray-50 p-3">
          {LAW_REFS.map((name) => (
            <div key={name} className="flex justify-between py-1.5 text-[12.5px]">
              <span>{name}</span>
              <span className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-bold text-red-700">
                บังคับ
              </span>
            </div>
          ))}
        </div>

        <h3 className="mb-2 mt-6 text-navy">โครงการเปรียบเทียบ (Optional)</h3>
        {compares.map((row, index) => (
          <div key={row.id} className="mb-3 rounded-[10px] border bg-gray-50 p-3">
            <Input
              placeholder="ชื่อโครงการเปรียบเทียบ"
              value={row.name}
              onChange={(event) =>
                setCompares((prev) =>
                  prev.map((item) =>
                    item.id === row.id ? { ...item, name: event.target.value } : item
                  )
                )
              }
            />
            <UploadArea
              label="อัปโหลดไฟล์โครงการเปรียบเทียบ"
              hint="PDF หรือ Word"
              onFiles={(list) =>
                setCompares((prev) =>
                  prev.map((item) =>
                    item.id === row.id ? { ...item, file: list[0] || null } : item
                  )
                )
              }
            />
            {row.file ? (
              <p className="mt-1 text-[12.5px] text-muted-foreground">{row.file.name}</p>
            ) : null}
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => setCompares((prev) => prev.filter((item) => item.id !== row.id))}
            >
              ลบ #{index + 1}
            </Button>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            setCompares((prev) => [
              ...prev,
              { id: crypto.randomUUID(), name: "", file: null },
            ])
          }
        >
          + เพิ่มโครงการเปรียบเทียบ
        </Button>
        {step === 1 ? (
          <Button
            className="mt-5 w-full"
            data-testid="review-extract"
            onClick={extract}
            disabled={!file || busy}
          >
            {busy ? "กำลังสกัดข้อความ..." : "อัปโหลดและสกัดข้อความ"}
          </Button>
        ) : null}
        {step >= 2 && extracted ? (
          <ExtractPreview
            preview={preview}
            busy={busy}
            onBack={backToUpload}
            onConfirm={() => {
              confirmRun().catch(() => undefined);
            }}
          />
        ) : null}
      </div>

      <div className="gov-card" data-testid="review-result">
        <h3 className="mb-3 text-navy">ผลการตรวจสอบ</h3>
        <ReviewResults result={result} findings={findings} comparisons={comparisons} />
      </div>
    </div>
  );
}
