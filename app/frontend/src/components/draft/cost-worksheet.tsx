"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  COST_LINE_KEYS,
  COST_LINE_LABELS,
  COST_WORKSHEET_DISCLAIMER,
  costWorksheetFromAnalysis,
  emptyCostWorksheet,
  fetchCostWorksheet,
  normalizeCostWorksheet,
  parseCostFromSectionContent,
  saveCostWorksheet,
  type CostLineKey,
  type CostWorksheet,
} from "@/lib/cost-worksheet";

function formatBaht(value: number): string {
  return value > 0 ? value.toLocaleString("th-TH") : "";
}

export function CostWorksheetEditor({
  projectId,
  analysis,
  sectionContent,
  onChange,
}: Readonly<{
  projectId?: string;
  analysis?: Record<string, unknown> | null;
  sectionContent?: string;
  onChange?: (sheet: CostWorksheet) => void;
}>) {
  const [sheet, setSheet] = useState<CostWorksheet>(() => {
    const fromAnalysis = costWorksheetFromAnalysis(analysis);
    if (fromAnalysis.total > 0) return fromAnalysis;
    return parseCostFromSectionContent(sectionContent ?? "") || emptyCostWorksheet();
  });
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    fetchCostWorksheet(projectId)
      .then((next) => {
        if (cancelled) return;
        setSheet(next);
        onChange?.(next);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once per project
  }, [projectId]);

  function updateLine(key: CostLineKey, raw: string) {
    const digits = raw.replaceAll(",", "");
    const next = normalizeCostWorksheet({ ...sheet, [key]: digits === "" ? 0 : digits });
    setSheet(next);
    onChange?.(next);
    setInfo(null);
  }

  async function persist() {
    if (!projectId) {
      onChange?.(sheet);
      setInfo("เก็บในร่างหมวดวงเงินแล้ว — ยังไม่ใช่ราคากลาง");
      return;
    }
    setBusy(true);
    try {
      const saved = await saveCostWorksheet(projectId, sheet);
      setSheet(saved);
      onChange?.(saved);
      setInfo("บันทึกใบประมาณแล้ว — ไม่ใช่ราคากลาง");
    } catch {
      setInfo("บันทึกใบประมาณไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="space-y-3 border border-navy/20 bg-white p-3"
      data-testid="cost-worksheet"
    >
      <div>
        <p className="text-sm font-semibold text-navy">ใบประมาณค่าใช้จ่าย</p>
        <p className="text-xs text-muted-foreground" data-testid="cost-worksheet-disclaimer">
          {COST_WORKSHEET_DISCLAIMER} แยกจากช่องราคากลางด้านล่าง เจ้าหน้าที่แก้ตัวเลขได้
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {COST_LINE_KEYS.map((key) => (
          <div key={key}>
            <Label htmlFor={`cost-${key}`}>{COST_LINE_LABELS[key]} (บาท)</Label>
            <Input
              id={`cost-${key}`}
              className="mt-1"
              type="text"
              inputMode="numeric"
              value={formatBaht(sheet[key])}
              data-testid={`cost-worksheet-${key}`}
              onChange={(event) => updateLine(key, event.target.value)}
            />
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-navy" data-testid="cost-worksheet-total">
          รวมใบประมาณ {sheet.total.toLocaleString("th-TH")} บาท (ไม่ใช่ราคากลาง)
        </p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy}
          data-testid="cost-worksheet-save"
          onClick={() => {
            void persist();
          }}
        >
          บันทึกใบประมาณ
        </Button>
      </div>
      {info ? (
        <p className="text-xs text-brand-green" data-testid="cost-worksheet-info">
          {info}
        </p>
      ) : null}
    </div>
  );
}
