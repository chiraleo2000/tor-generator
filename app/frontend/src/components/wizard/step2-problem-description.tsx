"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useWizardStore } from "@/stores/wizard-store";
import type { Step2Data } from "@/types/wizard";

const DEFAULT_STEP2_DATA: Step2Data = {
  description: "",
};

export function Step2ProblemDescription() {
  const { formData, setFormData, setValidationErrors, clearValidationErrors } =
    useWizardStore();

  const data: Step2Data = (formData[2] as Step2Data) || DEFAULT_STEP2_DATA;

  const updateDescription = (value: string) => {
    setFormData(2, { description: value });
    clearValidationErrors(2);
  };

  // Validate step 2
  React.useEffect(() => {
    const errors: string[] = [];
    if (!data.description?.trim()) {
      errors.push("กรุณาระบุคำอธิบายปัญหาและความเป็นมา");
    }
    if (errors.length > 0) {
      setValidationErrors(2, errors);
    } else {
      clearValidationErrors(2);
    }
  }, [data.description, setValidationErrors, clearValidationErrors]);

  const charCount = data.description.length;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 2: ความเป็นมาและปัญหา
        </h2>
        <p className="text-sm text-muted-foreground">
          อธิบายความเป็นมา สภาพปัญหา
          และเหตุผลความจำเป็นในการจัดซื้อจัดจ้างครั้งนี้
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">
          คำอธิบายปัญหาและความเป็นมา <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="description"
          value={data.description}
          onChange={(e) => updateDescription(e.target.value)}
          placeholder="อธิบายสภาพปัญหาปัจจุบัน ความเป็นมาของโครงการ และเหตุผลความจำเป็นที่ต้องดำเนินการจัดซื้อจัดจ้าง เช่น ระบบเดิมมีอายุการใช้งานเกิน 10 ปี ไม่สามารถรองรับปริมาณงานที่เพิ่มขึ้นได้..."
          className="min-h-[200px] break-words leading-relaxed"
          lang="th"
          style={{ wordBreak: "keep-all", overflowWrap: "break-word" }}
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <p>
            แนะนำ: อธิบายให้ครอบคลุมสภาพปัญหา ผลกระทบ
            และความจำเป็นในการแก้ไข
          </p>
          <span>{charCount.toLocaleString("th-TH")} ตัวอักษร</span>
        </div>
      </div>

      {/* Guidance Box */}
      <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
        <h3 className="text-sm font-medium text-blue-800 mb-2">
          คำแนะนำในการเขียน
        </h3>
        <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
          <li>ระบุสภาพปัญหาปัจจุบันที่เป็นรูปธรรม</li>
          <li>อธิบายผลกระทบที่เกิดขึ้นจากปัญหา</li>
          <li>ระบุเหตุผลความจำเป็นที่ต้องดำเนินการ</li>
          <li>อ้างอิงนโยบายหรือแผนงานที่เกี่ยวข้อง (ถ้ามี)</li>
          <li>ใช้ภาษาราชการที่เป็นทางการ</li>
        </ul>
      </div>
    </div>
  );
}
