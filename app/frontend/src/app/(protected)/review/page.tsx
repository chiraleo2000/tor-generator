"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UploadArea } from "@/components/brand/upload-area";
import { CheckItem } from "@/components/brand/check-item";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { findingCheckTone } from "@/lib/review-findings";
import {
  compareExtractJobs,
  extractCompareFiles,
  extractReviewFile,
  type JaccardComparison,
} from "@/lib/review-compare";

interface Finding {
  severity: string;
  rule: string;
  section: string;
  message: string;
  recommendation?: string | null;
}

interface ReviewResult {
  quality_score?: number;
  findings?: Finding[];
}

interface CompareRow {
  id: string;
  name: string;
  file: File | null;
}

const LAW_REFS = [
  "พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
  "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ พ.ศ. 2560",
  "คู่มือการจัดซื้อจัดจ้างตาม พ.ร.บ. 2560",
  "มาตรฐาน e-Bidding กรมบัญชีกลาง",
  "ประกาศราคากลาง (จากคลังความรู้)",
];

export default function StandaloneReviewPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [comparisons, setComparisons] = useState<JaccardComparison[]>([]);
  const [compares, setCompares] = useState<CompareRow[]>([]);
  const [busy, setBusy] = useState(false);

  async function run() {
    if (!file) {
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const primary = await extractReviewFile(file);
      setStatus("สกัดข้อความสำเร็จ");
      const compareJobs = await extractCompareFiles(compares);
      const compared = await compareExtractJobs(primary, compareJobs);
      const ran = unwrapData<ReviewResult>(
        await apiClient.post("/review/run", { id: primary.id })
      );
      setResult(ran);
      setComparisons(compared.comparisons);
    } catch (err: unknown) {
      setStatus(apiErrorMessage(err, "ตรวจสอบไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  const findings = result?.findings || [];

  return (
    <div className="grid gap-4 lg:grid-cols-2" data-testid="review-page">
      <div className="gov-card">
        <h3 className="mb-3 text-navy">อัปโหลด TOR ที่ต้องการตรวจสอบ</h3>
        <UploadArea
          label="ลากไฟล์ TOR วาง หรือคลิกเพื่อเลือก"
          hint="PDF, Word (.docx) หรือรูปภาพสแกน"
          onFiles={(list) => setFile(list[0] || null)}
        />
        {file ? (
          <p className="mt-2 text-[12.5px]">
            {file.name} · {Math.round(file.size / 1024)} KB
          </p>
        ) : null}
        {status ? <p className="mt-2 text-sm text-brand-green">{status}</p> : null}

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
        <Button className="mt-5 w-full" onClick={run} disabled={!file || busy}>
          {busy ? "กำลังตรวจสอบ..." : "เริ่มตรวจสอบ TOR"}
        </Button>
      </div>

      <div className="gov-card">
        <h3 className="mb-3 text-navy">ผลการตรวจสอบ</h3>
        {!result ? (
          <p className="py-10 text-center text-muted-foreground">
            อัปโหลดไฟล์ TOR แล้วกดเริ่มตรวจสอบเพื่อดูผล
          </p>
        ) : (
          <div>
            <CheckItem
              tone="pass"
              title={`คะแนนความพร้อม ${result.quality_score ?? "—"}/100`}
            />
            {findings.map((finding, index) => (
              <CheckItem
                key={`${finding.rule}-${index}`}
                tone={findingCheckTone(finding.severity)}
                title={finding.message}
                detail={finding.recommendation || finding.section}
              />
            ))}
            {comparisons.map((row) => (
              <CheckItem
                key={`${row.left}-${row.right}`}
                tone={row.jaccard >= 0.5 ? "pass" : "warn"}
                title={`เทียบเคียง ${row.left} กับ ${row.right}`}
                detail={`Jaccard ${row.jaccard}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
