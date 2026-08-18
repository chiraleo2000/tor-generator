"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useWizardStore } from "@/stores/wizard-store";
import type { Step6Data } from "@/types/wizard";
import { useRowKeys } from "@/lib/use-row-keys";

const DEFAULT_STEP6_DATA: Step6Data = {
  budget_breakdown: [{ item: "", amount: 0 }],
  payment_schedule: [{ percentage: 0, deliverable: "" }],
  penalty_rate: null,
  warranty: "",
  duration_days: null,
};

export function Step6BudgetPayment() {
  const { formData, setFormData, setValidationErrors, clearValidationErrors } =
    useWizardStore();

  const data: Step6Data = (formData[6] as Step6Data) || DEFAULT_STEP6_DATA;
  const { keys: breakdownKeys, removeAt: removeBreakdownKey } = useRowKeys(
    data.budget_breakdown.length
  );
  const { keys: scheduleKeys, removeAt: removeScheduleKey } = useRowKeys(
    data.payment_schedule.length
  );

  const updateData = (updated: Partial<Step6Data>) => {
    setFormData(6, { ...data, ...updated });
    clearValidationErrors(6);
  };

  // --- Budget Breakdown ---
  const handleBreakdownChange = (
    index: number,
    field: "item" | "amount",
    value: string
  ) => {
    const updated = [...data.budget_breakdown];
    if (field === "amount") {
      const rawValue = value.replaceAll(",", "");
      const numValue = rawValue === "" ? 0 : Number.parseFloat(rawValue);
      if (!Number.isNaN(numValue) && numValue >= 0) {
        updated[index] = { ...updated[index], amount: numValue };
      }
    } else {
      updated[index] = { ...updated[index], item: value };
    }
    updateData({ budget_breakdown: updated });
  };

  const addBreakdownItem = () => {
    updateData({
      budget_breakdown: [...data.budget_breakdown, { item: "", amount: 0 }],
    });
  };

  const removeBreakdownItem = (index: number) => {
    if (data.budget_breakdown.length <= 1) return;
    removeBreakdownKey(index);
    const updated = data.budget_breakdown.filter((_, i) => i !== index);
    updateData({ budget_breakdown: updated });
  };

  const totalBudget = data.budget_breakdown.reduce(
    (sum, item) => sum + item.amount,
    0
  );

  // --- Payment Schedule ---
  const handleScheduleChange = (
    index: number,
    field: "percentage" | "deliverable",
    value: string
  ) => {
    const updated = [...data.payment_schedule];
    if (field === "percentage") {
      const numValue = value === "" ? 0 : Number.parseFloat(value);
      if (!Number.isNaN(numValue) && numValue >= 0 && numValue <= 100) {
        updated[index] = { ...updated[index], percentage: numValue };
      }
    } else {
      updated[index] = { ...updated[index], deliverable: value };
    }
    updateData({ payment_schedule: updated });
  };

  const addScheduleItem = () => {
    updateData({
      payment_schedule: [
        ...data.payment_schedule,
        { percentage: 0, deliverable: "" },
      ],
    });
  };

  const removeScheduleItem = (index: number) => {
    if (data.payment_schedule.length <= 1) return;
    removeScheduleKey(index);
    const updated = data.payment_schedule.filter((_, i) => i !== index);
    updateData({ payment_schedule: updated });
  };

  const totalPercentage = data.payment_schedule.reduce(
    (sum, item) => sum + item.percentage,
    0
  );

  // --- Penalty Rate ---
  const handlePenaltyRateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value === "") {
      updateData({ penalty_rate: null });
      return;
    }
    const numValue = Number.parseFloat(value);
    if (!Number.isNaN(numValue)) {
      updateData({ penalty_rate: numValue });
    }
  };

  // Validation
  React.useEffect(() => {
    const errors: string[] = [];

    // Budget breakdown: at least one item with name and amount
    const hasValidBreakdown = data.budget_breakdown.some(
      (item) => item.item.trim() !== "" && item.amount > 0
    );
    if (!hasValidBreakdown) {
      errors.push("กรุณาระบุรายการงบประมาณอย่างน้อย 1 รายการ");
    }

    // Payment schedule: at least one item, total must equal 100%
    const hasValidSchedule = data.payment_schedule.some(
      (item) => item.percentage > 0 && item.deliverable.trim() !== ""
    );
    if (!hasValidSchedule) {
      errors.push("กรุณาระบุงวดการจ่ายเงินอย่างน้อย 1 งวด");
    }

    // Percentage sum check
    if (hasValidSchedule && Math.abs(totalPercentage - 100) > 0.01) {
      errors.push(
        `ผลรวมเปอร์เซ็นต์การจ่ายเงินต้องเท่ากับ 100% (ปัจจุบัน: ${totalPercentage.toFixed(2)}%)`
      );
    }

    // Individual installment range check (5%-50%)
    const invalidInstallments = data.payment_schedule.filter(
      (item) =>
        item.percentage > 0 && (item.percentage < 5 || item.percentage > 50)
    );
    if (invalidInstallments.length > 0) {
      errors.push("แต่ละงวดต้องอยู่ระหว่าง 5% ถึง 50%");
    }

    // Penalty rate validation (0.01-0.20%)
    if (data.penalty_rate === null) {
      errors.push("กรุณาระบุอัตราค่าปรับ");
    } else if (data.penalty_rate < 0.01 || data.penalty_rate > 0.20) {
      errors.push("อัตราค่าปรับต้องอยู่ระหว่าง 0.01% ถึง 0.20% ต่อวัน");
    }

    if (errors.length > 0) {
      setValidationErrors(6, errors);
    } else {
      clearValidationErrors(6);
    }
  }, [
    data.budget_breakdown,
    data.payment_schedule,
    data.penalty_rate,
    totalPercentage,
    setValidationErrors,
    clearValidationErrors,
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 6: งบประมาณและการจ่ายเงิน
        </h2>
        <p className="text-sm text-muted-foreground">
          ระบุรายละเอียดงบประมาณ กำหนดงวดการจ่ายเงิน
          และอัตราค่าปรับกรณีผิดสัญญา
        </p>
      </div>

      {/* Budget Breakdown */}
      <div className="space-y-4">
        <Label>
          รายละเอียดงบประมาณ <span className="text-destructive">*</span>
        </Label>

        {data.budget_breakdown.map((item, index) => (
          <div key={breakdownKeys[index]} className="flex flex-wrap items-start gap-2">
            <span className="mt-2.5 text-sm text-muted-foreground min-w-[24px]">
              {index + 1}.
            </span>
            <Input
              value={item.item}
              onChange={(e) =>
                handleBreakdownChange(index, "item", e.target.value)
              }
              placeholder="ระบุรายการ เช่น ค่าอุปกรณ์, ค่าแรงงาน"
              className="flex-1"
              lang="th"
              aria-label={`รายการงบประมาณที่ ${index + 1}`}
              data-testid={`budget-item-${index}`}
            />
            <Input
              type="text"
              inputMode="numeric"
              value={item.amount > 0 ? item.amount.toLocaleString("th-TH") : ""}
              onChange={(e) =>
                handleBreakdownChange(index, "amount", e.target.value)
              }
              placeholder="จำนวนเงิน"
              className="w-40"
              aria-label={`จำนวนเงินรายการที่ ${index + 1}`}
              data-testid={`budget-amount-${index}`}
            />
            <span className="mt-2.5 text-sm text-muted-foreground">บาท</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeBreakdownItem(index)}
              disabled={data.budget_breakdown.length <= 1}
              className="shrink-0 mt-0.5"
              aria-label={`ลบรายการงบประมาณที่ ${index + 1}`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 6h18" />
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              </svg>
            </Button>
          </div>
        ))}

        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addBreakdownItem}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-1"
            >
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </svg>
            เพิ่มรายการ
          </Button>
          <span className="text-sm font-medium">
            รวม: {totalBudget.toLocaleString("th-TH")} บาท
          </span>
        </div>
      </div>

      {/* Payment Schedule */}
      <div className="space-y-4">
        <Label>
          งวดการจ่ายเงิน <span className="text-destructive">*</span>
        </Label>
        <p className="text-xs text-muted-foreground">
          แต่ละงวดต้องอยู่ระหว่าง 5% ถึง 50% และผลรวมทุกงวดต้องเท่ากับ 100%
        </p>

        {data.payment_schedule.map((item, index) => (
          <div key={scheduleKeys[index]} className="flex flex-wrap items-start gap-2">
            <span className="mt-2.5 text-sm text-muted-foreground min-w-[50px]">
              งวดที่ {index + 1}
            </span>
            <div className="flex items-center gap-1">
              <Input
                type="number"
                min={5}
                max={50}
                step={0.01}
                value={item.percentage > 0 ? item.percentage : ""}
                onChange={(e) =>
                  handleScheduleChange(index, "percentage", e.target.value)
                }
                placeholder="5-50"
                className="w-24"
                aria-label={`เปอร์เซ็นต์งวดที่ ${index + 1}`}
                data-testid={`payment-pct-${index}`}
              />
              <span className="text-sm text-muted-foreground">%</span>
            </div>
            <Input
              value={item.deliverable}
              onChange={(e) =>
                handleScheduleChange(index, "deliverable", e.target.value)
              }
              placeholder="ผลงานส่งมอบที่เกี่ยวข้อง เช่น ส่งมอบรายงานผลการศึกษา"
              className="flex-1"
              lang="th"
              aria-label={`ผลงานส่งมอบงวดที่ ${index + 1}`}
              data-testid={`payment-deliverable-${index}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeScheduleItem(index)}
              disabled={data.payment_schedule.length <= 1}
              className="shrink-0 mt-0.5"
              aria-label={`ลบงวดการจ่ายเงินที่ ${index + 1}`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 6h18" />
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              </svg>
            </Button>
          </div>
        ))}

        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addScheduleItem}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-1"
            >
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </svg>
            เพิ่มงวด
          </Button>
          <span
            className={`text-sm font-medium ${
              Math.abs(totalPercentage - 100) < 0.01
                ? "text-green-600"
                : "text-amber-600"
            }`}
          >
            รวม: {totalPercentage.toFixed(2)}%
            {Math.abs(totalPercentage - 100) < 0.01 ? " ✓" : " (ต้องเท่ากับ 100%)"}
          </span>
        </div>
      </div>

      {/* Warranty */}
      <div className="space-y-2">
        <Label htmlFor="warranty">การรับประกัน</Label>
        <Textarea
          id="warranty"
          value={data.warranty ?? ""}
          onChange={(e) => updateData({ warranty: e.target.value })}
          placeholder="เช่น รับประกันผลงานไม่น้อยกว่า 1 ปี นับจากวันตรวจรับงวดสุดท้าย"
          rows={3}
          lang="th"
        />
      </div>

      {/* Penalty Rate */}
      <div className="space-y-2">
        <Label htmlFor="penalty_rate">
          อัตราค่าปรับ (% ต่อวัน) <span className="text-destructive">*</span>
        </Label>
        <div className="flex items-center gap-2">
          <Input
            id="penalty_rate"
            type="number"
            min={0.01}
            max={0.20}
            step={0.01}
            value={data.penalty_rate ?? ""}
            onChange={handlePenaltyRateChange}
            placeholder="0.01 - 0.20"
            className="w-40"
            aria-label="อัตราค่าปรับเป็นเปอร์เซ็นต์ต่อวัน"
          />
          <span className="text-sm text-muted-foreground">% ต่อวัน</span>
        </div>
        <p className="text-xs text-muted-foreground">
          ตามระเบียบจัดซื้อจัดจ้างฯ กำหนดอัตราค่าปรับระหว่าง 0.01% ถึง 0.20%
          ของราคาสัญญาต่อวัน
        </p>
      </div>

      {/* Summary */}
      <div className="rounded-md border bg-muted/30 p-4 space-y-2">
        <h3 className="text-sm font-medium">สรุป</h3>
        <div className="text-sm space-y-1">
          <p>
            งบประมาณรวม: {totalBudget.toLocaleString("th-TH")} บาท (
            {data.budget_breakdown.filter((b) => b.item.trim() !== "").length}{" "}
            รายการ)
          </p>
          <p>
            จำนวนงวดการจ่ายเงิน: {data.payment_schedule.length} งวด (รวม{" "}
            {totalPercentage.toFixed(2)}%)
          </p>
          <p>
            อัตราค่าปรับ:{" "}
            {data.penalty_rate !== null
              ? `${data.penalty_rate}% ต่อวัน`
              : "ยังไม่ระบุ"}
          </p>
        </div>
      </div>
    </div>
  );
}
