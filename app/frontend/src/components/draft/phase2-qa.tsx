"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DraftConversation } from "@/components/draft/draft-conversation";
import { CoverageTable, type CoverageRow } from "@/components/draft/phase1-coverage";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";

export function Phase2Qa({
  projectId,
  coverage,
  ready,
  busy,
  message,
  isError,
  apiBase,
  onConfirmReady,
  onChatReady,
  onCoverage,
}: Readonly<{
  projectId: string;
  coverage: CoverageRow[];
  ready: boolean;
  busy: boolean;
  message: string | null;
  isError: boolean;
  apiBase: string;
  onConfirmReady: () => void;
  onChatReady: () => void;
  onCoverage?: (rows: CoverageRow[]) => void;
}>) {
  const facts = coverage.filter((row) => row.fact_required);
  const missingFacts = facts.filter((row) => !row.filled);
  const gapNonFacts = coverage.filter(
    (row) => !row.fact_required && row.status === "gap"
  );
  const factReady = facts.length > 0 && missingFacts.length === 0;
  const [standardBusy, setStandardBusy] = useState(false);
  const [standardMsg, setStandardMsg] = useState<string | null>(null);

  async function applyCentralStandards() {
    setStandardBusy(true);
    setStandardMsg(null);
    try {
      const response = await apiClient.post(
        `/projects/${projectId}/intake/fill-references`,
        {}
      );
      const payload = unwrapData<{
        coverage?: CoverageRow[];
        filled_keys?: string[];
      }>(response);
      if (payload.coverage) {
        onCoverage?.(payload.coverage);
      }
      onChatReady();
      const n = payload.filled_keys?.length ?? 0;
      setStandardMsg(
        n > 0
          ? `เติมมาตรฐานกลางจากคลังแล้ว ${n} ช่อง — แก้ในแชทได้ถ้าหน่วยงานมีเงื่อนไขพิเศษ`
          : "คลังยังไม่มีข้อความสำหรับช่องที่ว่าง — ตอบในแชทหรือวางข้อความชุดใหญ่ได้"
      );
    } catch (err: unknown) {
      setStandardMsg(apiErrorMessage(err, "ดึงมาตรฐานกลางไม่สำเร็จ"));
    } finally {
      setStandardBusy(false);
    }
  }

  return (
    <div className="space-y-4" data-testid="phase2-qa">
      <div className="gov-card">
        <h3 className="text-navy">ขั้นที่ ๒: คุยต่อ — เติมช่องที่ยังขาด</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          วางข้อความชุดใหญ่ได้เลย ระบบจัดเข้าหลายช่องเอง แล้วถามเฉพาะที่ยังขาด
          ช่องกฎหมาย/มาตรฐานกดปุ่มด้านล่างเพื่อใช้ตาม พ.ร.บ. และระเบียบกลางจากคลัง
        </p>
        <p className="mt-2 text-sm text-navy">
          {factReady
            ? "ข้อเท็จจริงหลักครบแล้ว — ยืนยันเมื่อพร้อมไปร่างเนื้อหา"
            : `ยังขาดข้อเท็จจริง ${missingFacts.length} ช่อง — ตอบในแชทหรือวางข้อความยาวได้`}
        </p>
        {gapNonFacts.length > 0 ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              data-testid="phase2-apply-standards"
              disabled={busy || standardBusy}
              onClick={() => {
                applyCentralStandards().catch(() => undefined);
              }}
            >
              {standardBusy
                ? "กำลังดึงมาตรฐานกลาง..."
                : `ใช้มาตรฐานกลางเติมช่องว่าง (${gapNonFacts.length})`}
            </Button>
          </div>
        ) : null}
        {standardMsg ? (
          <p className="mt-2 text-sm text-brand-green">{standardMsg}</p>
        ) : null}
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
      {coverage.length ? <CoverageTable coverage={coverage} gaps={[]} /> : null}
      <Button
        type="button"
        className="mt-1"
        data-testid="intake-confirm-ready"
        disabled={busy || !factReady}
        onClick={onConfirmReady}
      >
        ครบแล้ว — ไปร่าง (ขั้นที่ ๓)
      </Button>
      {ready ? <p className="mt-2 text-sm text-green-800">ยืนยันพร้อมร่างแล้ว</p> : null}
      <DraftConversation
        projectId={projectId}
        mode="intake"
        apiBase={apiBase}
        placeholder="ตอบช่องที่ขาด หรือวางข้อความชุดใหญ่ — ระบบจัดเข้าช่องให้"
        coverage={coverage}
        onCoverage={(rows) => {
          onCoverage?.(rows);
          onChatReady();
        }}
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
          data-testid={`phase2-chip-${row.key}`}
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
