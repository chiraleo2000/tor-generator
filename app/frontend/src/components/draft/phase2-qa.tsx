"use client";

import { Button } from "@/components/ui/button";
import { DraftConversation } from "@/components/draft/draft-conversation";
import type { CoverageRow } from "@/components/draft/phase1-coverage";

export function Phase2Qa({
  projectId,
  coverage,
  ready,
  busy,
  fillingRefs,
  message,
  isError,
  apiBase,
  onConfirmReady,
  onChatReady,
}: Readonly<{
  projectId: string;
  coverage: CoverageRow[];
  ready: boolean;
  busy: boolean;
  fillingRefs: boolean;
  message: string | null;
  isError: boolean;
  apiBase: string;
  onConfirmReady: () => void;
  onChatReady: () => void;
}>) {
  const facts = coverage.filter((row) => row.fact_required);
  const missingFacts = facts.filter((row) => !row.filled);
  const factReady = facts.length > 0 && missingFacts.length === 0;

  return (
    <div className="space-y-4" data-testid="phase2-qa">
      <div className="gov-card">
        <h3 className="text-navy">Phase 2: คุยต่อจากผลวิเคราะห์ — ทีละช่อง</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          บอทเปิดด้วยสิ่งที่อ่านได้จาก Phase 1 แล้วถามทีละช่องที่ยังขาด — ตอบเป็นภาษาพูด ระบบบันทึกด้านหลังเอง ไม่มีตารางกรอก
        </p>
        {fillingRefs ? (
          <p className="mt-2 text-sm text-navy" data-testid="phase2-filling-refs">
            กำลังดึงกฎระเบียบที่เกี่ยวข้องไว้ด้านหลัง...
          </p>
        ) : (
          <p className="mt-2 text-sm text-navy">
            {factReady
              ? "ข้อเท็จจริงหลักครบแล้ว — ยืนยันเมื่อพร้อมไปร่าง TOR"
              : "ตอบช่องที่บอทถามอยู่ แล้วระบบจะไปช่องถัดไปให้"}
          </p>
        )}
        {message ? (
          <p
            className={`mt-2 text-sm ${isError ? "text-destructive" : "text-brand-green"}`}
            role={isError ? "alert" : undefined}
          >
            {message}
          </p>
        ) : null}
      </div>
      <FactStatusChips coverage={facts} />
      <Button
        type="button"
        className="mt-1"
        data-testid="intake-confirm-ready"
        disabled={busy || !factReady}
        onClick={onConfirmReady}
      >
        ครบแล้ว — ไปร่าง TOR (Phase 3)
      </Button>
      {ready ? <p className="mt-2 text-sm text-green-800">ยืนยันพร้อมร่างแล้ว</p> : null}
      <DraftConversation
        projectId={projectId}
        mode="intake"
        apiBase={apiBase}
        placeholder="ตอบช่องที่บอทถาม เป็นภาษาพูดได้เลย"
        onCoverage={() => onChatReady()}
      />
    </div>
  );
}

function FactStatusChips({ coverage }: Readonly<{ coverage: CoverageRow[] }>) {
  if (!coverage.length) return null;
  return (
    <div className="flex flex-wrap gap-2" data-testid="phase2-fact-chips">
      {coverage.map((row) => (
        <span
          key={row.key}
          data-testid={`coverage-row-${row.key}`}
          data-status={row.status}
          title={row.preview || row.label}
          className={
            row.filled
              ? "max-w-full rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-900"
              : "max-w-full rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-900"
          }
        >
          {row.filled ? `${row.label}: ${row.preview || "ได้แล้ว"}` : `ยังขาด ${row.label}`}
        </span>
      ))}
    </div>
  );
}
