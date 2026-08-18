"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useWizardStore } from "@/stores/wizard-store";
import type { Step3Data } from "@/types/wizard";
import { useRowKeys } from "@/lib/use-row-keys";

export function Step3Objectives() {
  const { formData, setFormData, setValidationErrors, clearValidationErrors } =
    useWizardStore();

  const data: Step3Data = {
    objectives:
      Array.isArray((formData[3] as Step3Data | undefined)?.objectives) &&
      (formData[3] as Step3Data).objectives.length > 0
        ? (formData[3] as Step3Data).objectives
        : [""],
  };

  const { keys: objectiveKeys, removeAt: removeObjectiveKey } = useRowKeys(
    data.objectives.length
  );

  const updateObjectives = (objectives: string[]) => {
    setFormData(3, { objectives });
    clearValidationErrors(3);
  };

  const handleObjectiveChange = (index: number, value: string) => {
    const updated = [...data.objectives];
    updated[index] = value;
    updateObjectives(updated);
  };

  const addObjective = () => {
    updateObjectives([...data.objectives, ""]);
  };

  const removeObjective = (index: number) => {
    if (data.objectives.length <= 1) return; // Keep at least one
    removeObjectiveKey(index);
    const updated = data.objectives.filter((_, i) => i !== index);
    updateObjectives(updated);
  };

  // Validate step 3
  React.useEffect(() => {
    const errors: string[] = [];
    const nonEmptyObjectives = data.objectives.filter((o) => o.trim() !== "");
    if (nonEmptyObjectives.length === 0) {
      errors.push("กรุณาระบุวัตถุประสงค์อย่างน้อย 1 ข้อ");
    }
    if (errors.length > 0) {
      setValidationErrors(3, errors);
    } else {
      clearValidationErrors(3);
    }
  }, [data.objectives, setValidationErrors, clearValidationErrors]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 3: วัตถุประสงค์
        </h2>
        <p className="text-sm text-muted-foreground">
          ระบุวัตถุประสงค์ของโครงการ โดยควรเขียนให้ชัดเจนตามหลัก SMART
        </p>
      </div>

      {/* SMART Format Guidance */}
      <div className="rounded-md border border-green-200 bg-green-50 p-4">
        <h3 className="text-sm font-medium text-green-800 mb-2">
          หลัก SMART ในการเขียนวัตถุประสงค์
        </h3>
        <ul className="text-sm text-green-700 space-y-1">
          <li>
            <span className="font-medium">S</span> - Specific: เจาะจงชัดเจน
            ระบุสิ่งที่ต้องการบรรลุอย่างเป็นรูปธรรม
          </li>
          <li>
            <span className="font-medium">M</span> - Measurable: วัดผลได้
            ระบุตัวชี้วัดที่ประเมินได้
          </li>
          <li>
            <span className="font-medium">A</span> - Achievable: ทำได้จริง
            สอดคล้องกับงบประมาณและทรัพยากร
          </li>
          <li>
            <span className="font-medium">R</span> - Relevant: สอดคล้อง
            เกี่ยวข้องกับปัญหาที่ต้องการแก้ไข
          </li>
          <li>
            <span className="font-medium">T</span> - Time-bound: มีกรอบเวลา
            กำหนดระยะเวลาที่ชัดเจน
          </li>
        </ul>
      </div>

      {/* Objectives List */}
      <div className="space-y-3">
        <Label>
          วัตถุประสงค์ <span className="text-destructive">*</span>
        </Label>

        {data.objectives.map((objective, index) => (
          <div key={objectiveKeys[index]} className="flex items-start gap-2">
            <span className="mt-2.5 text-sm text-muted-foreground min-w-[24px]">
              {index + 1}.
            </span>
            <Input
              value={objective}
              onChange={(e) => handleObjectiveChange(index, e.target.value)}
              placeholder={`ระบุวัตถุประสงค์ข้อที่ ${index + 1} เช่น เพื่อจัดหาระบบ...ที่สามารถรองรับผู้ใช้งาน...คนภายใน...เดือน`}
              className="flex-1 break-words"
              lang="th"
              data-testid={`objective-${index}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeObjective(index)}
              disabled={data.objectives.length <= 1}
              className="shrink-0 mt-0.5"
              aria-label={`ลบวัตถุประสงค์ข้อที่ ${index + 1}`}
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
          onClick={addObjective}
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
          เพิ่มวัตถุประสงค์
        </Button>
      </div>

      {/* Summary */}
      <p className="text-xs text-muted-foreground">
        จำนวนวัตถุประสงค์: {data.objectives.filter((o) => o.trim() !== "").length}{" "}
        ข้อ
      </p>
    </div>
  );
}
