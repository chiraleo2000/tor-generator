"use client";

import { Button } from "@/components/ui/button";
import { factTopicsComplete } from "@/lib/intake-complete";
import { coverageStatusLabel } from "@/lib/phase-handoff";

export interface CoverageRow {
  key: string;
  label: string;
  status: string;
  filled: boolean;
  fact_required: boolean;
  preview?: string;
}

function phase1StatusCopy(ready: boolean, factReady: boolean) {
  if (ready || factReady) {
    return (
      <p className="mt-2 text-sm text-brand-green" data-testid="phase1-ready-banner">
        ข้อมูลข้อเท็จจริงครบแล้ว — กดไปสอบถามเพิ่มหรือยืนยันในขั้นถัดไปได้
      </p>
    );
  }
  return (
    <p className="mt-2 text-sm text-navy">
      ยังมีช่องข้อเท็จจริงบังคับที่ยังไม่ครบ — กดไปขั้นที่ ๒ เพื่อให้บอทถามทีละช่องจนครบ
    </p>
  );
}

export function Phase1Coverage({
  coverage,
  gaps,
  ready = false,
  busy,
  message,
  isError,
  onEnterQa,
}: Readonly<{
  coverage: CoverageRow[];
  gaps: string[];
  ready?: boolean;
  busy: boolean;
  message: string | null;
  isError: boolean;
  onEnterQa: () => void;
}>) {
  const factReady = factTopicsComplete(coverage);

  function continueToQa() {
    onEnterQa();
  }

  return (
    <div className="space-y-4" data-testid="phase1-coverage">
      <div className="gov-card">
        <h3 className="text-navy">ขั้นที่ ๑: ผลวิเคราะห์ความต้องการ</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          สิ่งที่ระบบจัดเข้าช่องจากเอกสารแล้ว — กดปุ่มด้านล่างเพื่อไปขั้นที่ ๒
        </p>
        <FilledFactList coverage={coverage} />
        {phase1StatusCopy(ready, factReady)}
        {message ? (
          <p
            className={`mt-2 text-sm ${isError ? "text-destructive" : "text-brand-green"}`}
            role={isError ? "alert" : undefined}
          >
            {message}
          </p>
        ) : null}
        <div className="mt-3 flex items-center gap-3">
          <Button
            size="sm"
            disabled={busy || coverage.length === 0}
            data-testid="phase1-skip"
            onClick={continueToQa}
          >
            {factReady ? "ไปขั้นที่ ๒" : "ไปสอบถามเพิ่ม (ขั้นที่ ๒) — เติมช่องที่ยังขาด"}
          </Button>
        </div>
      </div>
      {coverage.length ? <CoverageTable coverage={coverage} gaps={gaps} /> : null}
    </div>
  );
}

function FilledFactList({ coverage }: Readonly<{ coverage: CoverageRow[] }>) {
  const filled = coverage.filter((row) => row.fact_required && row.filled && row.preview);
  if (!filled.length) return null;
  return (
    <ul className="mt-3 space-y-1 text-sm" data-testid="phase1-fact-summary">
      {filled.map((row) => (
        <li key={row.key}>
          <span className="font-bold text-navy">{row.label}:</span> {row.preview}
        </li>
      ))}
    </ul>
  );
}

export function CoverageTable({
  coverage,
  gaps,
}: Readonly<{
  coverage: CoverageRow[];
  gaps: string[];
}>) {
  return (
    <div className="gov-card overflow-x-auto">
      <h4 className="mb-2 font-bold text-navy">รายละเอียดที่จัดเข้าช่อง</h4>
      <table className="w-full text-left text-sm">
        <thead>
          <tr>
            <th>ช่อง</th>
            <th>สถานะ</th>
            <th>ข้อความที่ได้</th>
          </tr>
        </thead>
        <tbody>
          {coverage.map((row) => (
            <tr
              key={row.key}
              className="border-t"
              data-testid={`coverage-row-${row.key}`}
              data-status={row.status}
            >
              <td className="py-1">
                {row.key} {row.label}
                {row.fact_required ? " *" : ""}
              </td>
              <td>{coverageStatusLabel(row.status)}</td>
              <td className="max-w-xs truncate text-xs text-muted-foreground">
                {row.preview || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {gaps.length ? (
        <ul className="mt-2 list-disc pl-5 text-sm">
          {gaps.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
