"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useWizardStore } from "@/stores/wizard-store";
import { apiClient } from "@/lib/api-client";
import type { Step1Data, TemplateOption } from "@/types/wizard";
import { ExtractionConfirm } from "@/components/projects/extraction-confirm";

const PROJECT_TYPE_OPTIONS = [
  { value: "it", label: "ระบบเทคโนโลยีสารสนเทศ" },
  { value: "construction", label: "งานก่อสร้าง" },
  { value: "consulting", label: "งานจ้างที่ปรึกษา" },
  { value: "general", label: "จัดซื้อจัดจ้างทั่วไป" },
];

const DEFAULT_STEP1_DATA: Step1Data = {
  project_name: "",
  ministry: "",
  budget: null,
  project_type: "general",
  template_id: null,
  location: "",
  duration_days: null,
};

export function Step1ProjectInfo() {
  const { formData, setFormData, setValidationErrors, clearValidationErrors, projectId } =
    useWizardStore();

  const data: Step1Data = (formData[1] as Step1Data) || DEFAULT_STEP1_DATA;

  const [templates, setTemplates] = React.useState<TemplateOption[]>([]);
  const [loadingTemplates, setLoadingTemplates] = React.useState(false);
  const [showOverwriteDialog, setShowOverwriteDialog] = React.useState(false);
  const [pendingTemplateId, setPendingTemplateId] = React.useState<
    string | null
  >(null);

  // Fetch published templates on mount
  React.useEffect(() => {
    setLoadingTemplates(true);
    apiClient
      .get("/templates", { params: { status: "published" } })
      .then((res) => {
        const items = res.data?.data?.items || res.data?.items || [];
        setTemplates(items);
      })
      .catch(() => {
        // Templates are optional - non-critical if unavailable
        setTemplates([]);
      })
      .finally(() => {
        setLoadingTemplates(false);
      });
  }, []);

  const updateField = <K extends keyof Step1Data>(
    field: K,
    value: Step1Data[K]
  ) => {
    const updated = { ...data, [field]: value };
    setFormData(1, updated);
    clearValidationErrors(1);
  };

  const handleBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value.replaceAll(",", "");
    if (rawValue === "") {
      updateField("budget", null);
      return;
    }
    const numValue = Number.parseInt(rawValue, 10);
    if (!Number.isNaN(numValue) && numValue >= 0) {
      updateField("budget", numValue);
    }
  };

  const handleTemplateSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newTemplateId = e.target.value || null;

    // Check if user has modified content (isDirty or has description/objectives)
    const step2Data = formData[2] as { description?: string } | undefined;
    const step3Data = formData[3] as { objectives?: string[] } | undefined;
    const hasExistingContent =
      (step2Data?.description && step2Data.description.trim() !== "") ||
      (step3Data?.objectives && step3Data.objectives.length > 0);

    if (hasExistingContent && newTemplateId && newTemplateId !== data.template_id) {
      // Show confirmation dialog
      setPendingTemplateId(newTemplateId);
      setShowOverwriteDialog(true);
    } else {
      updateField("template_id", newTemplateId);
    }
  };

  const confirmTemplateOverwrite = () => {
    updateField("template_id", pendingTemplateId);
    setShowOverwriteDialog(false);
    setPendingTemplateId(null);
  };

  const cancelTemplateOverwrite = () => {
    setShowOverwriteDialog(false);
    setPendingTemplateId(null);
  };

  // Validate step 1
  React.useEffect(() => {
    const errors: string[] = [];
    if (!data.project_name.trim()) {
      errors.push("กรุณาระบุชื่อโครงการ");
    }
    if (!data.ministry.trim()) {
      errors.push("กรุณาระบุหน่วยงาน");
    }
    if (data.budget === null || data.budget <= 0) {
      errors.push("กรุณาระบุงบประมาณที่เป็นจำนวนเต็มบวก");
    }
    if (errors.length > 0) {
      setValidationErrors(1, errors);
    } else {
      clearValidationErrors(1);
    }
  }, [data.project_name, data.ministry, data.budget, setValidationErrors, clearValidationErrors]);

  const formatBudgetDisplay = (budget: number | null): string => {
    if (budget === null) return "";
    return budget.toLocaleString("th-TH");
  };

  const templateOptions = templates.map((t) => ({
    value: t.id,
    label: t.name,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 1: ข้อมูลโครงการ
        </h2>
        <p className="text-sm text-muted-foreground">
          กรอกข้อมูลพื้นฐานของโครงการจัดซื้อจัดจ้าง
        </p>
      </div>

      {/* Project Name */}
      <div className="space-y-2">
        <Label htmlFor="project_name">
          ชื่อโครงการ <span className="text-destructive">*</span>
        </Label>
        <Input
          id="project_name"
          value={data.project_name}
          onChange={(e) => updateField("project_name", e.target.value)}
          placeholder="ระบุชื่อโครงการ เช่น โครงการจัดซื้อระบบคอมพิวเตอร์"
          className="break-words"
          lang="th"
        />
      </div>

      {/* Ministry */}
      <div className="space-y-2">
        <Label htmlFor="ministry">
          หน่วยงาน <span className="text-destructive">*</span>
        </Label>
        <Input
          id="ministry"
          value={data.ministry}
          onChange={(e) => updateField("ministry", e.target.value)}
          placeholder="ระบุชื่อหน่วยงาน เช่น กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม"
          lang="th"
        />
      </div>

      {/* Budget */}
      <div className="space-y-2">
        <Label htmlFor="budget">
          งบประมาณ (บาท) <span className="text-destructive">*</span>
        </Label>
        <Input
          id="budget"
          type="text"
          inputMode="numeric"
          value={formatBudgetDisplay(data.budget)}
          onChange={handleBudgetChange}
          placeholder="ระบุงบประมาณ เช่น 1,000,000"
        />
        {data.budget !== null && data.budget > 0 && (
          <p className="text-xs text-muted-foreground">
            ทุนจดทะเบียนขั้นต่ำของผู้เสนอราคา:{" "}
            {Math.floor(data.budget / 4).toLocaleString("th-TH")} บาท
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="location">สถานที่ดำเนินการ</Label>
          <Input
            id="location"
            value={data.location || ""}
            onChange={(e) => updateField("location", e.target.value)}
            placeholder="เช่น สำนักงานกระทรวง... กรุงเทพมหานคร"
            lang="th"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="duration_days">ระยะเวลาดำเนินการ (วัน)</Label>
          <Input
            id="duration_days"
            type="number"
            min={1}
            value={data.duration_days ?? ""}
            onChange={(e) => {
              if (!e.target.value) {
                updateField("duration_days", null);
                return;
              }
              const parsed = Number.parseInt(e.target.value, 10);
              if (!Number.isNaN(parsed) && parsed >= 1) {
                updateField("duration_days", parsed);
              }
            }}
            placeholder="เช่น 180"
          />
        </div>
      </div>

      {/* Project Type */}
      <div className="space-y-2">
        <Label htmlFor="project_type">ประเภทโครงการ</Label>
        <Select
          id="project_type"
          value={data.project_type}
          onChange={(e) =>
            updateField(
              "project_type",
              e.target.value as Step1Data["project_type"]
            )
          }
          options={PROJECT_TYPE_OPTIONS}
        />
      </div>

      {/* Template Selection */}
      <div className="space-y-2">
        <Label htmlFor="template_id">เทมเพลต TOR (ไม่บังคับ)</Label>
        <Select
          id="template_id"
          value={data.template_id || ""}
          onChange={handleTemplateSelect}
          options={templateOptions}
          placeholder={
            loadingTemplates ? "กำลังโหลดเทมเพลต..." : "-- เลือกเทมเพลต --"
          }
          disabled={loadingTemplates}
        />
        <p className="text-xs text-muted-foreground">
          การเลือกเทมเพลตจะเติมโครงสร้างและข้อความแนะนำที่เหมาะสมกับประเภทงาน
        </p>
      </div>

      {/* Template overwrite confirmation dialog */}
      <Dialog open={showOverwriteDialog} onOpenChange={setShowOverwriteDialog}>
        <DialogHeader>
          <DialogTitle>ยืนยันการเปลี่ยนเทมเพลต</DialogTitle>
          <DialogDescription>
            คุณมีข้อมูลที่กรอกไว้แล้ว
            การเปลี่ยนเทมเพลตจะเขียนทับข้อมูลที่แก้ไขไว้ทั้งหมด
            ต้องการดำเนินการต่อหรือไม่?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={cancelTemplateOverwrite}>
            ยกเลิก
          </Button>
          <Button variant="destructive" onClick={confirmTemplateOverwrite}>
            ยืนยันเปลี่ยนเทมเพลต
          </Button>
        </DialogFooter>
      </Dialog>

      {projectId && <ExtractionConfirm projectId={projectId} />}
    </div>
  );
}
