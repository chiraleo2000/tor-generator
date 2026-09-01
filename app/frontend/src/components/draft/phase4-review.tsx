"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { CheckItem } from "@/components/brand/check-item";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { findingCheckTone, type ReviewFinding } from "@/lib/review-findings";
import type { ReviewSuggestion, SectionPayload } from "@/components/draft/draft-types";
import { ReviewChat } from "@/components/draft/review-chat";
import { RichDraftText } from "@/components/draft/rich-draft-text";
import {
  TOR_SECTION_LABELS,
  labeledSectionBlocks,
  scopeSubsectionTitle,
  type TorSectionKey,
} from "@/lib/tor-sections";

export function Phase4Review({
  projectId,
  sections,
  filledCount,
  total,
  score,
  findings,
  suggestions,
  assessment,
  busy,
  error,
  onBack,
  onReview,
  onSubmit,
  onAsk,
}: Readonly<{
  projectId: string;
  sections?: SectionPayload[];
  filledCount: number;
  total: number;
  score: number | null;
  findings: ReviewFinding[];
  suggestions: ReviewSuggestion[];
  assessment?: string;
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onReview: (force?: boolean) => Promise<void>;
  onSubmit: () => Promise<void>;
  onAsk?: (question: string) => Promise<string>;
}>) {
  const pct = Math.round((filledCount / total) * 100);
  return (
    <div className="gov-card" data-testid="phase4-review">
      <h3 className="mb-2 text-navy">ขั้นที่ ๔: ทบทวนและอนุมัติ</h3>
      <p className="mb-2 text-xs text-muted-foreground">
        ด้านล่างคือตัวอย่างเอกสารที่จะถูกส่งออก — หมวดขอบเขตงานแสดงเป็นหัวข้อย่อย ๔.๑–๔.๑๔ ที่รวมจากขั้นที่ ๓
        ขั้นนี้ตรวจร่างกับ พ.ร.บ. การจัดซื้อจัดจ้าง กฎระเบียบ และเอกสารที่อัปโหลดในขั้นที่ ๐ ของโครงการนี้
        ตารางในเนื้อหาจะถูกแปลงเป็นตารางจริงในไฟล์เวิร์ด/พีดีเอฟ
      </p>
      <p className="text-sm">ความครบถ้วน: {filledCount}/{total} หมวด</p>
      <div className="my-2 h-2 overflow-hidden rounded bg-gray-200">
        <div
          className="h-full bg-gradient-to-r from-navy to-brand-orange-dark"
          style={{ width: `${pct}%` }}
        />
      </div>
      {pct < 100 ? (
        <CheckItem tone="warn" title="ยังกรอกไม่ครบทุกหมวด" detail="กลับไปขั้นที่ ๓ เพื่อกรอกให้ครบ" />
      ) : (
        <CheckItem tone="pass" title="ข้อมูลครบถ้วนทุกหมวด พร้อมส่งทบทวน" />
      )}
      {sections?.length ? <MergedTorPreview sections={sections} /> : null}
      {assessment ? (
        <div className="my-3 rounded-lg border border-navy/20 bg-slate-50 p-3" data-testid="phase4-assessment">
          <p className="text-xs font-bold text-navy">ความเห็นจากการตรวจ (เข้มงวด)</p>
          <p className="mt-1 text-sm text-navy">{assessment}</p>
        </div>
      ) : null}
      {score != null ? (
        <div data-testid="phase4-rule-score">
          <CheckItem
            tone={score >= 70 ? "pass" : "warn"}
            title={`คะแนนคุณภาพจากการตรวจกฎ ${score}/100`}
          />
        </div>
      ) : (
        <CheckItem tone="warn" title="ยังไม่ได้รันตรวจสอบ" detail="กดตรวจกฎเพื่อตรวจกฎหมาย ความครบถ้วน และความสอดคล้อง" />
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
          ข้อเสนอแนะจากการทบทวน ({suggestions.length})
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
        onAsk={onAsk}
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
            {busy ? "กำลังตรวจสอบ..." : "ตรวจด้วยกฎระเบียบ"}
          </Button>
          <Button
            onClick={onSubmit}
            disabled={pct < 100 || busy}
            data-testid="phase4-submit"
          >
            ส่งขออนุมัติ
          </Button>
        </div>
      </div>
      {pct < 100 ? (
        <p className="mt-2 text-xs text-muted-foreground" data-testid="phase4-submit-hint">
          กรอกให้ครบ ๑๓ หมวดก่อนส่งขออนุมัติ
        </p>
      ) : null}
    </div>
  );
}

function MergedTorPreview({ sections }: Readonly<{ sections: SectionPayload[] }>) {
  return (
    <div
      className="my-4 max-h-[22rem] space-y-3 overflow-y-auto rounded-lg border bg-white p-3"
      data-testid="phase4-merged-preview"
    >
      <h4 className="text-sm font-bold text-navy">ตัวอย่างเอกสารรวม (ก่อนส่งออก)</h4>
      {sections.map((section, index) => {
        const title =
          TOR_SECTION_LABELS[section.key as TorSectionKey] || section.title || section.key;
        const subs = (section.subs || []).filter((sub) => (sub.content || "").trim());
        return (
          <article key={section.key} className="border-b border-gray-100 pb-2 last:border-0">
            <h5 className="text-sm font-semibold text-navy">
              {index + 1}. {title}
            </h5>
            {subs.length ? (
              <div className="mt-1 space-y-2 pl-2">
                {subs.map((sub) => (
                  <div key={sub.key}>
                    <p className="text-xs font-semibold text-foreground">
                      {sub.key.replace("s4.", "4.")} {scopeSubsectionTitle(sub.key, sub.title)}
                    </p>
                    <RichDraftText text={sub.content || ""} className="text-muted-foreground" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-1 space-y-2">
                {labeledSectionBlocks(section.key, section.content || "").map((block) => (
                  <div key={`${section.key}-${block.label || "body"}`}>
                    {block.label ? (
                      <p className="text-xs font-semibold text-foreground">{block.label}</p>
                    ) : null}
                    <RichDraftText text={block.text} className="text-muted-foreground" />
                  </div>
                ))}
              </div>
            )}
          </article>
        );
      })}
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
