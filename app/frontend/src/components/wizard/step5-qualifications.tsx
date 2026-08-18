"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useWizardStore } from "@/stores/wizard-store";
import type { Step1Data, Step5Data } from "@/types/wizard";
import { useRowKeys } from "@/lib/use-row-keys";

export function Step5Qualifications() {
  const { formData, setFormData, setValidationErrors, clearValidationErrors } =
    useWizardStore();

  const data: Step5Data = {
    qualifications:
      Array.isArray((formData[5] as Step5Data | undefined)?.qualifications) &&
      (formData[5] as Step5Data).qualifications.length > 0
        ? (formData[5] as Step5Data).qualifications
        : [""],
    paid_up_capital:
      (formData[5] as Step5Data | undefined)?.paid_up_capital ?? null,
  };
  const step1Data = formData[1] as Step1Data | undefined;
  const { keys: qualificationKeys, removeAt: removeQualificationKey } =
    useRowKeys(data.qualifications.length);

  // Auto-calculate paid_up_capital = budget / 4 (floor)
  const calculatedCapital =
    step1Data?.budget && step1Data.budget > 0
      ? Math.floor(step1Data.budget / 4)
      : null;

  // Sync calculated capital into form data when budget changes
  React.useEffect(() => {
    const current = useWizardStore.getState().formData[5] as Step5Data | undefined;
    if (calculatedCapital !== (current?.paid_up_capital ?? null)) {
      setFormData(5, {
        qualifications: current?.qualifications?.length
          ? current.qualifications
          : [""],
        paid_up_capital: calculatedCapital,
      });
    }
  }, [calculatedCapital, setFormData]);

  const updateQualifications = (qualifications: string[]) => {
    setFormData(5, { ...data, qualifications });
    clearValidationErrors(5);
  };

  const handleQualificationChange = (index: number, value: string) => {
    const updated = [...data.qualifications];
    updated[index] = value;
    updateQualifications(updated);
  };

  const addQualification = () => {
    updateQualifications([...data.qualifications, ""]);
  };

  const removeQualification = (index: number) => {
    if (data.qualifications.length <= 1) return;
    removeQualificationKey(index);
    const updated = data.qualifications.filter((_, i) => i !== index);
    updateQualifications(updated);
  };

  // Validation
  React.useEffect(() => {
    const errors: string[] = [];
    const hasValidQualification = data.qualifications.some(
      (q) => q.trim() !== ""
    );
    if (!hasValidQualification) {
      errors.push("กรุณาระบุคุณสมบัติผู้เสนอราคาอย่างน้อย 1 ข้อ");
    }
    if (errors.length > 0) {
      setValidationErrors(5, errors);
    } else {
      clearValidationErrors(5);
    }
  }, [data.qualifications, setValidationErrors, clearValidationErrors]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 5: คุณสมบัติผู้เสนอราคา
        </h2>
        <p className="text-sm text-muted-foreground">
          ระบุคุณสมบัติที่ผู้เสนอราคาต้องมี
          ทุนจดทะเบียนจะถูกคำนวณอัตโนมัติจากงบประมาณ
        </p>
      </div>

      {/* Auto-calculated Paid-up Capital */}
      <div className="rounded-md border border-blue-200 bg-blue-50 p-4 space-y-2">
        <Label className="text-blue-800">
          ทุนจดทะเบียนชำระแล้วขั้นต่ำ (คำนวณอัตโนมัติ = งบประมาณ / 4)
        </Label>
        <div className="flex items-center gap-2">
          <Input
            value={
              calculatedCapital !== null
                ? calculatedCapital.toLocaleString("th-TH")
                : ""
            }
            readOnly
            disabled
            className="bg-white max-w-xs"
            aria-label="ทุนจดทะเบียนชำระแล้วขั้นต่ำ"
          />
          <span className="text-sm text-blue-700">บาท</span>
        </div>
        {step1Data?.budget && step1Data.budget > 0 ? (
          <p className="text-xs text-blue-600">
            คำนวณจากงบประมาณ {step1Data.budget.toLocaleString("th-TH")} บาท
            หารด้วย 4 (ปัดลง) ตาม พ.ร.บ. จัดซื้อจัดจ้างฯ พ.ศ. 2560
          </p>
        ) : (
          <p className="text-xs text-amber-600">
            กรุณากรอกงบประมาณในขั้นตอนที่ 1 เพื่อคำนวณทุนจดทะเบียน
          </p>
        )}
      </div>

      {/* Qualifications List */}
      <div className="space-y-3">
        <Label>
          คุณสมบัติผู้เสนอราคา <span className="text-destructive">*</span>
        </Label>

        {data.qualifications.map((qualification, index) => (
          <div key={qualificationKeys[index]} className="flex items-start gap-2">
            <span className="mt-2.5 text-sm text-muted-foreground min-w-[24px]">
              {index + 1}.
            </span>
            <Input
              value={qualification}
              onChange={(e) =>
                handleQualificationChange(index, e.target.value)
              }
              placeholder={getQualificationPlaceholder(index)}
              className="flex-1"
              lang="th"
              data-testid={`qualification-${index}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeQualification(index)}
              disabled={data.qualifications.length <= 1}
              className="shrink-0 mt-0.5"
              aria-label={`ลบคุณสมบัติข้อที่ ${index + 1}`}
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

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addQualification}
          className="mt-2"
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
          เพิ่มคุณสมบัติ
        </Button>
      </div>

      {/* Common qualifications guidance */}
      <div className="rounded-md border border-green-200 bg-green-50 p-4">
        <h3 className="text-sm font-medium text-green-800 mb-2">
          ตัวอย่างคุณสมบัติที่มักกำหนด
        </h3>
        <ul className="text-sm text-green-700 space-y-1 list-disc list-inside">
          <li>เป็นนิติบุคคลที่จดทะเบียนในประเทศไทย</li>
          <li>ไม่เป็นผู้ถูกแจ้งเวียนเป็นผู้ทิ้งงาน</li>
          <li>มีผลงานในลักษณะเดียวกันในวงเงินไม่น้อยกว่า...</li>
          <li>มีบุคลากรที่มีคุณวุฒิและประสบการณ์ตามที่กำหนด</li>
          <li>ต้องไม่เป็นผู้มีผลประโยชน์ร่วมกับผู้เสนอราคารายอื่น</li>
        </ul>
      </div>

      {/* Summary */}
      <p className="text-xs text-muted-foreground">
        จำนวนคุณสมบัติ:{" "}
        {data.qualifications.filter((q) => q.trim() !== "").length} ข้อ
      </p>
    </div>
  );
}

function getQualificationPlaceholder(index: number): string {
  const placeholders = [
    "เช่น เป็นนิติบุคคลที่จดทะเบียนในประเทศไทย",
    "เช่น ไม่เป็นผู้ถูกแจ้งเวียนเป็นผู้ทิ้งงานของทางราชการ",
    "เช่น มีผลงานในลักษณะเดียวกันในวงเงินไม่น้อยกว่า...",
    "เช่น มีบุคลากรหลักที่มีคุณวุฒิปริญญาตรีขึ้นไป",
  ];
  return placeholders[index] || `ระบุคุณสมบัติข้อที่ ${index + 1}`;
}
