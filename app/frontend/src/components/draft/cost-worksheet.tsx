"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  COST_LINE_KEYS,
  COST_LINE_LABELS,
  COST_WORKSHEET_DISCLAIMER,
  TRAINING_PART_KEYS,
  TRAINING_PART_LABELS,
  costWorksheetFromAnalysis,
  emptyCostWorksheet,
  fetchCostWorksheet,
  normalizeCostWorksheet,
  parseCostFromSectionContent,
  saveCostWorksheet,
  type CostLineKey,
  type CostWorksheet,
  type TrainingPartKey,
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
    return parseCostFromSectionContent(sectionContent ?? "") ?? emptyCostWorksheet();
  });
  const [teamSize, setTeamSize] = useState("2");
  const [months, setMonths] = useState("1");
  const [years, setYears] = useState("");
  const [trainingDays, setTrainingDays] = useState("1");
  const [dayPart, setDayPart] = useState("full");
  const [attendees, setAttendees] = useState("1");
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

  function updateLine(key: CostLineKey | TrainingPartKey, raw: string) {
    const digits = raw.replaceAll(",", "");
    const next = normalizeCostWorksheet({ ...sheet, [key]: digits === "" ? 0 : digits });
    setSheet(next);
    onChange?.(next);
    setInfo(null);
  }

  function calculationInput() {
    const yearText = years.trim();
    return {
      team_size: Number(teamSize) || 0,
      months: Number(months) || 1,
      years: yearText === "" ? null : Number(yearText),
      training_days: Number(trainingDays) || 0,
      day_part: dayPart,
      attendees: Number(attendees) || 0,
    };
  }

  async function persist(applyCalculated: boolean) {
    if (!projectId) {
      onChange?.(sheet);
      setInfo("เก็บในร่างหมวดวงเงินแล้ว — ยังไม่ใช่ราคากลาง");
      return;
    }
    setBusy(true);
    try {
      const saved = await saveCostWorksheet(
        projectId,
        sheet,
        applyCalculated ? { ...calculationInput(), apply_calculated: true } : undefined
      );
      setSheet(saved);
      onChange?.(saved);
      setInfo(
        applyCalculated
          ? "ใช้ตัวเลขที่คำนวณแล้ว — ไม่ใช่ราคากลาง"
          : "บันทึกใบประมาณแล้ว — ไม่ใช่ราคากลาง"
      );
    } catch {
      setInfo(applyCalculated ? "ใช้ตัวเลขที่คำนวณไม่สำเร็จ" : "บันทึกใบประมาณไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 border border-navy/20 bg-white p-3" data-testid="cost-worksheet">
      <div>
        <p className="text-sm font-semibold text-navy">ใบประมาณค่าใช้จ่าย</p>
        <p className="text-xs text-muted-foreground" data-testid="cost-worksheet-disclaimer">
          {COST_WORKSHEET_DISCLAIMER} แยกจากช่องราคากลางด้านล่าง เจ้าหน้าที่แก้ตัวเลขได้
          อุปกรณ์และการจัดซื้อที่ไม่มีราคาในเอกสารอัตรา ไม่ใส่ราคาตลาด
        </p>
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-navy" data-testid="cost-worksheet-rules">
          <li>จัดทีมสลับวุฒิปริญญาโทแล้วปริญญาเอก</li>
          <li>ค่าเริ่มต้นเป็นอัตราภาคเอกชน ไม่ใช้ข้าราชการ บุคลากรในหน่วยงานของรัฐ หรือสถาบันของรัฐ</li>
          <li>สถานที่อบรมค่าเริ่มต้นเป็นโรงแรมหรือสถานที่เอกชน</li>
          <li>หากไม่ได้กำหนดอายุงาน ใช้ 2 ปี และเลือกแถวราคาต่ำสุดที่ตรงวุฒิ</li>
          <li>ครึ่งวันเช้าหรือครึ่งวันบ่ายคืออาหาร 1 มื้อและอาหารว่าง 1 มื้อ</li>
          <li>เต็มวันทั้งเช้าและบ่ายคืออาหาร 2 มื้อและอาหารว่าง 2 มื้อ</li>
          <li>เอกสารคิดทุกครั้งตามจำนวนผู้เข้าอบรม</li>
        </ul>
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
      <div className="grid gap-2 sm:grid-cols-2 border border-navy/10 p-2">
        <p className="sm:col-span-2 text-xs font-semibold text-navy">รายละเอียดค่าอบรม</p>
        {TRAINING_PART_KEYS.map((key) => (
          <div key={key}>
            <Label htmlFor={`cost-${key}`}>{TRAINING_PART_LABELS[key]} (บาท)</Label>
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
      <div className="grid gap-2 sm:grid-cols-3">
        <div>
          <Label htmlFor="cost-team-size">จำนวนที่ปรึกษา (คน)</Label>
          <Input
            id="cost-team-size"
            className="mt-1"
            inputMode="numeric"
            value={teamSize}
            data-testid="cost-worksheet-team-size"
            onChange={(event) => setTeamSize(event.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="cost-months">จำนวนเดือน</Label>
          <Input
            id="cost-months"
            className="mt-1"
            inputMode="decimal"
            value={months}
            data-testid="cost-worksheet-months"
            onChange={(event) => setMonths(event.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="cost-years">อายุงาน (ว่างไว้ = 2 ปี)</Label>
          <Input
            id="cost-years"
            className="mt-1"
            inputMode="numeric"
            value={years}
            data-testid="cost-worksheet-years"
            onChange={(event) => setYears(event.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="cost-training-days">จำนวนวันอบรม</Label>
          <Input
            id="cost-training-days"
            className="mt-1"
            inputMode="numeric"
            value={trainingDays}
            data-testid="cost-worksheet-training-days"
            onChange={(event) => setTrainingDays(event.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="cost-day-part">ช่วงวันอบรม</Label>
          <select
            id="cost-day-part"
            className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
            value={dayPart}
            data-testid="cost-worksheet-day-part"
            onChange={(event) => setDayPart(event.target.value)}
          >
            <option value="full">เต็มวัน (อาหาร 2 มื้อ อาหารว่าง 2 มื้อ)</option>
            <option value="half_morning">ครึ่งวันเช้า (อาหาร 1 มื้อ อาหารว่าง 1 มื้อ)</option>
            <option value="half_afternoon">ครึ่งวันบ่าย (อาหาร 1 มื้อ อาหารว่าง 1 มื้อ)</option>
          </select>
        </div>
        <div>
          <Label htmlFor="cost-attendees">ผู้เข้าอบรม (คน)</Label>
          <Input
            id="cost-attendees"
            className="mt-1"
            inputMode="numeric"
            value={attendees}
            data-testid="cost-worksheet-attendees"
            onChange={(event) => setAttendees(event.target.value)}
          />
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-navy" data-testid="cost-worksheet-total">
          รวมใบประมาณ {sheet.total.toLocaleString("th-TH")} บาท (ไม่ใช่ราคากลาง)
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={busy}
            data-testid="cost-worksheet-apply"
            onClick={() => {
              void persist(true);
            }}
          >
            ใช้ตัวเลขที่คำนวณ
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={busy}
            data-testid="cost-worksheet-save"
            onClick={() => {
              void persist(false);
            }}
          >
            บันทึกใบประมาณ
          </Button>
        </div>
      </div>
      {info ? (
        <p className="text-xs text-brand-green" data-testid="cost-worksheet-info">
          {info}
        </p>
      ) : null}
    </div>
  );
}
