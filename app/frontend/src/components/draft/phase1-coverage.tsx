"use client";

import { Button } from "@/components/ui/button";

export interface CoverageRow {
  key: string;
  label: string;
  status: string;
  filled: boolean;
  fact_required: boolean;
  preview?: string;
}

function phase1StatusCopy(
  fillingRefs: boolean,
  ready: boolean,
  factReady: boolean
) {
  if (fillingRefs) {
    return (
      <div className="mt-2" data-testid="phase1-filling-refs">
        <p className="text-sm text-navy">กำลังดึงกฎระเบียบที่เกี่ยวข้อง...</p>
        <progress className="mt-2 w-full" />
      </div>
    );
  }
  if (ready) {
    return (
      <p className="mt-2 text-sm text-brand-green" data-testid="phase1-ready-banner">
        ข้อมูลครบถ้วนแล้ว สามารถยืนยันเพื่อไปขั้นถัดไปได้
      </p>
    );
  }
  return (
    <p className="mt-2 text-sm text-navy">
      {factReady
        ? "ข้อมูลข้อเท็จจริงพร้อม — ไปสอบถามเพิ่มได้เมื่อต้องการเติมช่องที่เหลือ"
        : "พร้อมไปขั้นถัดไปเมื่อช่องข้อเท็จจริงบังคับครบ"}
    </p>
  );
}

export function Phase1Coverage({
  coverage,
  gaps,
  fillingRefs,
  ready = false,
  busy,
  message,
  isError,
  onEnterQa,
}: Readonly<{
  coverage: CoverageRow[];
  gaps: string[];
  fillingRefs: boolean;
  ready?: boolean;
  busy: boolean;
  message: string | null;
  isError: boolean;
  onEnterQa: () => void;
}>) {
  const factReady = coverage.some((row) => row.fact_required && row.filled);
  return (
    <div className="space-y-4" data-testid="phase1-coverage">
      <div className="gov-card">
        <h3 className="text-navy">Phase 1: ผลวิเคราะห์ความต้องการ</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          สิ่งที่ระบบอ่านได้จากเอกสาร — กดไปคุยต่อใน Phase 2 บอทจะเปิดบทด้วยสรุปนี้ ไม่ต้องกรอกใหม่
        </p>
        <FilledFactList coverage={coverage} />
        {phase1StatusCopy(fillingRefs, ready, factReady)}
        {message ? (
          <p
            className={`mt-2 text-sm ${isError ? "text-destructive" : "text-brand-green"}`}
            role={isError ? "alert" : undefined}
          >
            {message}
          </p>
        ) : null}
      </div>
      {coverage.length ? (
        <CoverageTable coverage={coverage} gaps={gaps} />
      ) : null}
      <Button
        type="button"
        className="mt-1"
        data-testid="intake-enter-qa"
        disabled={busy}
        onClick={onEnterQa}
      >
        ไปคุยต่อใน Phase 2
      </Button>
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
              <td>{row.status}</td>
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
