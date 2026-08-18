"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useProjectStore } from "@/stores/project-store";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import type { ProjectType } from "@/types";

const PROJECT_TYPE_OPTIONS = [
  { value: "it", label: "ระบบเทคโนโลยีสารสนเทศ" },
  { value: "construction", label: "งานก่อสร้าง" },
  { value: "consulting", label: "งานจ้างที่ปรึกษา" },
  { value: "general", label: "จัดซื้อจัดจ้างทั่วไป" },
];

function isAsciiDigitString(value: string): boolean {
  if (!value) {
    return false;
  }
  for (const ch of value) {
    if (ch < "0" || ch > "9") {
      return false;
    }
  }
  return true;
}

/** Strip commas, then accept ASCII digits only. Thai digits fail. */
export function parseProjectBudget(raw: string): number | null {
  const digits = raw.replaceAll(",", "").trim();
  if (!isAsciiDigitString(digits)) {
    return null;
  }
  const value = Number.parseInt(digits, 10);
  if (!Number.isFinite(value) || value < 1) {
    return null;
  }
  return value;
}

interface NewProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NewProjectDialog({
  open,
  onOpenChange,
}: Readonly<NewProjectDialogProps>) {
  const router = useRouter();
  const createProject = useProjectStore((s) => s.createProject);
  const [name, setName] = useState("");
  const [ministry, setMinistry] = useState("");
  const [budget, setBudget] = useState("");
  const [projectType, setProjectType] = useState<ProjectType>("general");
  const [templateId, setTemplateId] = useState("");
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    apiClient
      .get("/templates", { params: { status: "published" } })
      .then((res) => {
        const payload = unwrapData<{ items?: { id: string; name: string }[] }>(res);
        setTemplates(payload.items || []);
      })
      .catch(() => setTemplates([]));
  }, [open]);

  async function handleCreate() {
    setError(null);
    const budgetNum = parseProjectBudget(budget);
    if (!name.trim() || !ministry.trim() || budgetNum === null) {
      setError("กรุณากรอกชื่อโครงการ หน่วยงาน และงบประมาณ");
      return;
    }
    setSaving(true);
    try {
      const project = await createProject({
        name: name.trim(),
        ministry: ministry.trim(),
        budget: budgetNum,
        projectType,
        templateId: templateId || undefined,
      });
      onOpenChange(false);
      router.push(`/projects/${project.id}/draft`);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "สร้างโครงการไม่สำเร็จ กรุณาลองใหม่"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle>สร้างโครงการใหม่</DialogTitle>
        <DialogDescription>
          กรอกข้อมูลพื้นฐานแล้วเข้าสู่กระบวนการร่าง TOR แบบ 5 Phase
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-3 px-1 py-2" data-testid="new-project-dialog">
        {error ? (
          <p className="text-sm text-destructive" data-testid="new-project-error">
            {error}
          </p>
        ) : null}
        <div className="space-y-1">
          <Label htmlFor="np-name">ชื่อโครงการ</Label>
          <Input
            id="np-name"
            data-testid="new-project-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            lang="th"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-ministry">หน่วยงาน</Label>
          <Input
            id="np-ministry"
            data-testid="new-project-ministry"
            value={ministry}
            onChange={(e) => setMinistry(e.target.value)}
            lang="th"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-budget">งบประมาณ (บาท)</Label>
          <Input
            id="np-budget"
            data-testid="new-project-budget"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            inputMode="numeric"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-type">ประเภท</Label>
          <Select
            id="np-type"
            value={projectType}
            onChange={(e) => setProjectType(e.target.value as ProjectType)}
            options={PROJECT_TYPE_OPTIONS}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-template">แม่แบบ</Label>
          <Select
            id="np-template"
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            options={[
              { value: "", label: "-- ไม่เลือก --" },
              ...templates.map((t) => ({ value: t.id, label: t.name })),
            ]}
          />
        </div>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
          ยกเลิก
        </Button>
        <Button
          onClick={handleCreate}
          disabled={saving}
          data-testid="create-project-submit"
        >
          {saving ? "กำลังสร้าง..." : "สร้างและเริ่มร่าง"}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
