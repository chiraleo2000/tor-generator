"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useWizardStore } from "@/stores/wizard-store";
import type { Step4Data } from "@/types/wizard";
import { SCOPE_SUBSECTIONS } from "@/lib/tor-sections";
import { useRowKeys } from "@/lib/use-row-keys";

const MAX_SUBSECTIONS = 14;

const DEFAULT_STEP4_DATA: Step4Data = {
  scope_items: SCOPE_SUBSECTIONS.map((item) => ({
    title: item.title,
    details: "",
  })),
  deliverables: [""],
};

export function Step4ScopeOfWork() {
  const { formData, setFormData, setValidationErrors, clearValidationErrors } =
    useWizardStore();

  const data: Step4Data = (formData[4] as Step4Data) || DEFAULT_STEP4_DATA;
  const { keys: scopeKeys, removeAt: removeScopeKey } = useRowKeys(
    data.scope_items.length
  );
  const { keys: deliverableKeys, removeAt: removeDeliverableKey } = useRowKeys(
    data.deliverables.length
  );

  const updateData = (updated: Partial<Step4Data>) => {
    setFormData(4, { ...data, ...updated });
    clearValidationErrors(4);
  };

  // --- Scope Items ---
  const handleScopeItemChange = (
    index: number,
    field: "title" | "details",
    value: string
  ) => {
    const updated = [...data.scope_items];
    updated[index] = { ...updated[index], [field]: value };
    updateData({ scope_items: updated });
  };

  const addScopeItem = () => {
    if (data.scope_items.length >= MAX_SUBSECTIONS) return;
    updateData({ scope_items: [...data.scope_items, { title: "", details: "" }] });
  };

  const removeScopeItem = (index: number) => {
    if (data.scope_items.length <= 1) return;
    removeScopeKey(index);
    const updated = data.scope_items.filter((_, i) => i !== index);
    updateData({ scope_items: updated });
  };

  // --- Deliverables ---
  const handleDeliverableChange = (index: number, value: string) => {
    const updated = [...data.deliverables];
    updated[index] = value;
    updateData({ deliverables: updated });
  };

  const addDeliverable = () => {
    updateData({ deliverables: [...data.deliverables, ""] });
  };

  const removeDeliverable = (index: number) => {
    if (data.deliverables.length <= 1) return;
    removeDeliverableKey(index);
    const updated = data.deliverables.filter((_, i) => i !== index);
    updateData({ deliverables: updated });
  };

  // Validation
  React.useEffect(() => {
    const errors: string[] = [];
    const hasValidScope = data.scope_items.some(
      (item) => item.title.trim() !== ""
    );
    if (!hasValidScope) {
      errors.push("กรุณาระบุขอบเขตงานอย่างน้อย 1 รายการ");
    }
    const hasValidDeliverable = data.deliverables.some(
      (d) => d.trim() !== ""
    );
    if (!hasValidDeliverable) {
      errors.push("กรุณาระบุผลงานส่งมอบอย่างน้อย 1 รายการ");
    }
    if (errors.length > 0) {
      setValidationErrors(4, errors);
    } else {
      clearValidationErrors(4);
    }
  }, [data.scope_items, data.deliverables, setValidationErrors, clearValidationErrors]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 4: ขอบเขตของงาน (Scope of Work)
        </h2>
        <p className="text-sm text-muted-foreground">
          ระบุขอบเขตงาน โดยแบ่งเป็นหัวข้อย่อยได้สูงสุด {MAX_SUBSECTIONS}{" "}
          หัวข้อ พร้อมรายการผลงานส่งมอบ (Deliverables)
        </p>
      </div>

      {/* Scope Items / Subsections */}
      <div className="space-y-4">
        <Label>
          ขอบเขตงาน <span className="text-destructive">*</span>
        </Label>

        {data.scope_items.map((item, index) => (
          <div
            key={scopeKeys[index]}
            className="rounded-md border p-4 space-y-3 relative"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                หัวข้อที่ {index + 1}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeScopeItem(index)}
                disabled={data.scope_items.length <= 1}
                aria-label={`ลบหัวข้อขอบเขตงานที่ ${index + 1}`}
                className="h-8 w-8"
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

            <div className="space-y-2">
              <Label htmlFor={`scope-title-${index}`}>ชื่อหัวข้อ</Label>
              <Input
                id={`scope-title-${index}`}
                value={item.title}
                onChange={(e) =>
                  handleScopeItemChange(index, "title", e.target.value)
                }
                placeholder={`ระบุชื่อหัวข้อย่อย เช่น การจัดหาอุปกรณ์, การติดตั้งระบบ`}
                lang="th"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor={`scope-details-${index}`}>รายละเอียด</Label>
              <Textarea
                id={`scope-details-${index}`}
                value={item.details}
                onChange={(e) =>
                  handleScopeItemChange(index, "details", e.target.value)
                }
                placeholder="อธิบายรายละเอียดของขอบเขตงานในหัวข้อนี้"
                rows={3}
                lang="th"
              />
            </div>
          </div>
        ))}

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addScopeItem}
          disabled={data.scope_items.length >= MAX_SUBSECTIONS}
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
          เพิ่มหัวข้อขอบเขตงาน ({data.scope_items.length}/{MAX_SUBSECTIONS})
        </Button>
      </div>

      {/* Deliverables */}
      <div className="space-y-3">
        <Label>
          ผลงานส่งมอบ (Deliverables) <span className="text-destructive">*</span>
        </Label>

        {data.deliverables.map((deliverable, index) => (
          <div key={deliverableKeys[index]} className="flex items-start gap-2">
            <span className="mt-2.5 text-sm text-muted-foreground min-w-[24px]">
              {index + 1}.
            </span>
            <Input
              value={deliverable}
              onChange={(e) => handleDeliverableChange(index, e.target.value)}
              placeholder={`ระบุผลงานส่งมอบ เช่น รายงานการวิเคราะห์ระบบ, ซอฟต์แวร์ที่พัฒนาแล้ว`}
              className="flex-1"
              lang="th"
              data-testid={`deliverable-${index}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeDeliverable(index)}
              disabled={data.deliverables.length <= 1}
              className="shrink-0 mt-0.5"
              aria-label={`ลบผลงานส่งมอบที่ ${index + 1}`}
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
          onClick={addDeliverable}
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
          เพิ่มผลงานส่งมอบ
        </Button>
      </div>

      {/* Summary */}
      <div className="text-xs text-muted-foreground space-y-1">
        <p>
          จำนวนหัวข้อขอบเขตงาน:{" "}
          {data.scope_items.filter((s) => s.title.trim() !== "").length} หัวข้อ
        </p>
        <p>
          จำนวนผลงานส่งมอบ:{" "}
          {data.deliverables.filter((d) => d.trim() !== "").length} รายการ
        </p>
      </div>
    </div>
  );
}
