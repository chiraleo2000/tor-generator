"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

export interface CoverageRow {
  key: string;
  label: string;
  status: string;
  filled: boolean;
  fact_required: boolean;
  preview?: string;
}

function phase1StatusCopy(ready: boolean, factReady: boolean) {
  if (ready) {
    return (
      <p className="mt-2 text-sm text-brand-green" data-testid="phase1-ready-banner">
        ข้อมูลครบถ้วนแล้ว — กำลังไปสอบถามเพิ่มใน Phase 2
      </p>
    );
  }
  return (
    <p className="mt-2 text-sm text-navy">
      {factReady
        ? "ข้อมูลข้อเท็จจริงพร้อม — กำลังไปคุยต่อเพื่อเติมช่องที่เหลือ"
        : "พร้อมไปขั้นถัดไปเมื่อช่องข้อเท็จจริงบังคับครบ — บอทจะถามช่องที่ยังขาด"}
    </p>
  );
}

const AUTO_TRANSITION_SECONDS = 8;

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
  const required = coverage.filter((row) => row.fact_required);
  const factReady = required.length > 0 && required.every((row) => row.filled);
  const [countdown, setCountdown] = useState(AUTO_TRANSITION_SECONDS);
  const transitioned = useRef(false);
  const onEnterQaRef = useRef(onEnterQa);
  onEnterQaRef.current = onEnterQa;

  useEffect(() => {
    if (transitioned.current) {
      return undefined;
    }
    setCountdown(AUTO_TRANSITION_SECONDS);
    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      const left = AUTO_TRANSITION_SECONDS - Math.floor((Date.now() - startedAt) / 1000);
      if (left > 0) {
        setCountdown(left);
        return;
      }
      window.clearInterval(interval);
      setCountdown(0);
      if (transitioned.current) {
        return;
      }
      transitioned.current = true;
      onEnterQaRef.current();
    }, 250);
    return () => window.clearInterval(interval);
  }, []);

  function skipToQa() {
    if (transitioned.current) {
      return;
    }
    transitioned.current = true;
    onEnterQa();
  }

  return (
    <div className="space-y-4" data-testid="phase1-coverage">
      <div className="gov-card">
        <h3 className="text-navy">Phase 1: ผลวิเคราะห์ความต้องการ</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          สิ่งที่ระบบอ่านได้จากเอกสาร — จะไปคุยต่อใน Phase 2 อัตโนมัติ บอทจะถามช่องที่ยังขาด
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
        {countdown > 0 ? (
          <div className="mt-3 flex items-center gap-3 rounded-lg border border-navy/20 bg-blue-50 px-4 py-2">
            <span className="text-sm text-navy" data-testid="phase1-countdown">
              ไปสอบถามเพิ่มอัตโนมัติใน <strong>{countdown}</strong> วินาที...
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              data-testid="phase1-skip"
              onClick={skipToQa}
            >
              ไปเลย
            </Button>
          </div>
        ) : null}
      </div>
      {coverage.length ? (
        <CoverageTable coverage={coverage} gaps={gaps} />
      ) : null}
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
