"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { CheckItem } from "@/components/brand/check-item";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { findingCheckTone, type ReviewFinding } from "@/lib/review-findings";
import type { ReviewSuggestion } from "@/components/draft/draft-types";
import { ReviewChat } from "@/components/draft/review-chat";

export function Phase4Review({
  projectId,
  filledCount,
  total,
  hitlReady,
  score,
  findings,
  suggestions,
  busy,
  error,
  onBack,
  onReview,
  onSubmit,
  onAcceptHitl,
}: Readonly<{
  projectId: string;
  filledCount: number;
  total: number;
  hitlReady: boolean;
  score: number | null;
  findings: ReviewFinding[];
  suggestions: ReviewSuggestion[];
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onReview: (force?: boolean) => Promise<void>;
  onSubmit: () => Promise<void>;
  onAcceptHitl?: (sectionKey: string) => Promise<void>;
}>) {
  const pct = Math.round((filledCount / total) * 100);
  return (
    <div className="gov-card" data-testid="phase4-review">
      <h3 className="mb-2 text-navy">Phase 4: ทบทวนและอนุมัติ</h3>
      <p className="text-sm">ความครบถ้วน: {filledCount}/{total} หมวด</p>
      <div className="my-2 h-2 overflow-hidden rounded bg-gray-200">
        <div
          className="h-full bg-gradient-to-r from-navy to-brand-orange-dark"
          style={{ width: `${pct}%` }}
        />
      </div>
      {pct < 100 ? (
        <CheckItem tone="warn" title="ยังกรอกไม่ครบทุกหมวด" detail="กลับไป Phase 3 เพื่อกรอกให้ครบ" />
      ) : (
        <CheckItem tone="pass" title="ข้อมูลครบถ้วนทุกหมวด พร้อมส่งทบทวน" />
      )}
      {hitlReady ? (
        <CheckItem tone="pass" title="หมวดกฎหมาย งบ งวดจ่าย ค่าปรับ เงื่อนไขอื่น ได้รับการยืนยัน" />
      ) : (
        <CheckItem tone="warn" title="ยังไม่ได้ยืนยันหมวดที่เจ้าหน้าที่ต้องตรวจ" />
      )}
      {score != null ? (
        <div data-testid="phase4-rule-score">
          <CheckItem
            tone={score >= 70 ? "pass" : "warn"}
            title={`คะแนนคุณภาพจาก Rule Engine ${score}/100`}
          />
        </div>
      ) : (
        <CheckItem tone="warn" title="ยังไม่ได้รันตรวจสอบ" detail="กดรัน Rule Engine เพื่อตรวจกฎหมาย ความครบถ้วน และความสอดคล้อง" />
      )}
      {findings.map((finding, index) => (
        <CheckItem
          key={`${finding.rule}-${index}`}
          tone={findingCheckTone(finding.severity)}
          title={finding.message}
          detail={[finding.section, finding.recommendation].filter(Boolean).join(" — ")}
        />
      ))}
      {suggestions.length ? (
        <h4 className="mb-1 mt-3 text-sm font-bold text-navy">
          ข้อเสนอแนะจาก ReviewAgent ({suggestions.length})
        </h4>
      ) : null}
      {suggestions.map((item) => (
        <CheckItem
          key={item.id}
          tone="warn"
          title={`${item.category}: ${item.suggested_text}`}
          detail={item.section_key}
        />
      ))}
      {error ? (
        <p className="mt-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <RequirementsUpload projectId={projectId} />
      <ReviewChat
        score={score}
        findings={findings}
        busy={busy}
        onReview={onReview}
        onAcceptHitl={onAcceptHitl || (async () => undefined)}
      />
      <div className="mt-4 flex justify-between">
        <Button variant="secondary" onClick={onBack} data-testid="phase3-back">
          ย้อนกลับไปแก้ไข
        </Button>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => {
              onReview(true).catch(() => undefined);
            }}
            disabled={busy}
            data-testid="run-review"
          >
            {busy ? "กำลังตรวจสอบ..." : "รัน Rule Engine"}
          </Button>
          <Button
            onClick={onSubmit}
            disabled={pct < 100 || !hitlReady || busy}
            data-testid="phase4-submit"
          >
            ส่งขออนุมัติ / สร้าง TOR
          </Button>
        </div>
      </div>
      {pct < 100 || !hitlReady ? (
        <p className="mt-2 text-xs text-muted-foreground" data-testid="phase4-submit-hint">
          {pct < 100
            ? "กรอกให้ครบ 13 หมวดก่อนส่งขออนุมัติ"
            : "ยืนยันหมวดที่เจ้าหน้าที่ต้องตรวจครบ 5 หมวดก่อนส่ง"}
        </p>
      ) : null}
    </div>
  );
}

function RequirementsUpload({ projectId }: Readonly<{ projectId: string }>) {
  const [hasReqs, setHasReqs] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [reqError, setReqError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .get(`/projects/${projectId}/review/requirements`)
      .then((res) => {
        const data = unwrapData<{ has_requirements?: boolean; preview?: string }>(res);
        setHasReqs(Boolean(data.has_requirements));
        setPreview(data.preview || null);
      })
      .catch((err: unknown) => {
        const status = (err as { response?: { status?: number } }).response?.status;
        if (status === 404) {
          return;
        }
        setReqError(apiErrorMessage(err, "โหลดข้อกำหนดไม่สำเร็จ"));
      });
  }, [projectId]);

  async function upload(file: File) {
    setUploading(true);
    setReqError(null);
    try {
      const body = new FormData();
      body.append("file", file);
      await apiClient.post(`/projects/${projectId}/review/requirements`, body);
      setHasReqs(true);
      const res = await apiClient.get(`/projects/${projectId}/review/requirements`);
      const data = unwrapData<{ preview?: string }>(res);
      setPreview(data.preview || null);
    } catch (err: unknown) {
      setReqError(apiErrorMessage(err, "อัปโหลดข้อกำหนดไม่สำเร็จ"));
    } finally {
      setUploading(false);
    }
  }

  async function clear() {
    try {
      await apiClient.delete(`/projects/${projectId}/review/requirements`);
      setHasReqs(false);
      setPreview(null);
    } catch (err: unknown) {
      setReqError(apiErrorMessage(err, "ลบข้อกำหนดไม่สำเร็จ"));
    }
  }

  return (
    <div className="mt-3 rounded-lg border bg-gray-50 p-3">
      <p className="mb-2 text-xs font-bold text-navy">
        ข้อกำหนดเพิ่มเติม (ถ้ามี)
      </p>
      {hasReqs ? (
        <div>
          <p className="text-xs text-muted-foreground mb-1">
            {preview ? preview.slice(0, 200) + "..." : "อัปโหลดแล้ว"}
          </p>
          <Button size="sm" variant="outline" onClick={clear}>
            ลบข้อกำหนด
          </Button>
        </div>
      ) : (
        <label className="block cursor-pointer">
          <span className="text-xs text-muted-foreground">
            อัปโหลดไฟล์ข้อกำหนดเฉพาะโครงการ (PDF/DOCX/TXT) เพื่อให้ ReviewAgent ตรวจสอบเพิ่มเติม
          </span>
          <input
            type="file"
            className="mt-1 block text-sm"
            accept=".pdf,.docx,.txt"
            disabled={uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload(file);
            }}
          />
        </label>
      )}
      {reqError ? (
        <p className="mt-1 text-xs text-destructive" role="alert">{reqError}</p>
      ) : null}
    </div>
  );
}
